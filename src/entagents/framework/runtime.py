"""The governed runtime every agent runs through.

Order of operations for one request:
  1. screen every input string for prompt injection (block on a hit)
  2. redact PII from the input
  3. look up the response cache
  4. route to a model tier and meter tokens
  5. run the agent; its tool calls go through the allow-list and the retry budget,
     and risky actions are parked in the approval queue instead of executing
  6. redact PII from the output
  7. append a hash-chained audit entry
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .approval import ApprovalQueue
from .audit import AuditLog
from .controls import LRUCache, Meter, RetryBudget, route, tokens
from .guards import ToolDenied, ToolPolicy, injection_hits, redact


def _strings(x: Any) -> list[str]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings(v)]
    if isinstance(x, list | tuple):
        return [s for v in x for s in _strings(v)]
    return []


def _map_strings(x: Any, fn) -> Any:
    if isinstance(x, str):
        return fn(x)
    if isinstance(x, dict):
        return {k: _map_strings(v, fn) for k, v in x.items()}
    if isinstance(x, list):
        return [_map_strings(v, fn) for v in x]
    if isinstance(x, tuple):
        return tuple(_map_strings(v, fn) for v in x)
    return x


class Agent:
    """Base class. Subclasses set META and TOOLS and implement handle()."""

    META: dict = {}
    TOOLS = ToolPolicy(frozenset())
    HARD = False  # route to the large tier

    def handle(self, ctx: Context, payload: dict) -> dict:  # pragma: no cover - interface
        raise NotImplementedError

    def demo(self) -> dict:  # pragma: no cover - interface
        raise NotImplementedError

    def eval_cases(self) -> list[tuple[dict, Any]]:  # pragma: no cover - interface
        raise NotImplementedError

    def score(self, out: dict, expected: Any) -> float:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class Context:
    agent: Agent
    rt: Runtime
    tool_calls: list[str] = field(default_factory=list)
    pending: list[int] = field(default_factory=list)

    def tool(self, name: str, fn, *a, **kw):
        self.agent.TOOLS.check(name)
        if name in self.agent.TOOLS.risky:
            raise ToolDenied(f"'{name}' is risky; use ctx.request_approval")
        self.tool_calls.append(name)
        return self.rt.budget.call(fn, *a, **kw)

    def request_approval(self, action: str, detail: dict) -> int:
        self.agent.TOOLS.check(action)
        p = self.rt.approvals.request(self.agent.META["name"], action, detail)
        self.pending.append(p.id)
        return p.id


@dataclass
class Runtime:
    audit: AuditLog = field(default_factory=AuditLog)
    approvals: ApprovalQueue = field(default_factory=ApprovalQueue)
    cache: LRUCache = field(default_factory=LRUCache)
    budget: RetryBudget = field(default_factory=RetryBudget)
    meter: Meter = field(default_factory=Meter)
    stats: dict = field(default_factory=lambda: {"blocked": 0, "pii_redacted_in": 0, "pii_redacted_out": 0, "denied_tools": 0})

    def run(self, agent: Agent, payload: dict) -> dict:
        name = agent.META["name"]
        hits = [h for s in _strings(payload) for h in injection_hits(s)]
        if hits:
            self.stats["blocked"] += 1
            self.audit.append({"agent": name, "status": "blocked", "reason": "prompt_injection", "patterns": len(hits)})
            return {"status": "blocked", "reason": "prompt injection detected", "output": None}

        red_in = 0

        def r_in(s: str) -> str:
            nonlocal red_in
            r = redact(s)
            red_in += r.total
            return r.text

        clean = _map_strings(payload, r_in)
        self.stats["pii_redacted_in"] += red_in
        key = LRUCache.key(name, clean)
        cached = self.cache.get(key)
        if cached is not None:
            self.audit.append({"agent": name, "status": "ok", "cache": "hit"})
            return {**cached, "cache": "hit"}

        text_in = " ".join(_strings(clean))
        tier = route(text_in, agent.HARD)
        ctx = Context(agent, self)
        try:
            out = agent.handle(ctx, clean)
        except ToolDenied as e:
            self.stats["denied_tools"] += 1
            self.audit.append({"agent": name, "status": "denied", "reason": str(e)})
            return {"status": "denied", "reason": str(e), "output": None}
        except (ValueError, KeyError, TypeError, SyntaxError) as e:
            # Bad input: fail closed with the error type only (never echo raw payload values).
            self.audit.append({"agent": name, "status": "error", "error": type(e).__name__})
            return {"status": "error", "reason": f"invalid input ({type(e).__name__})", "output": None}

        red_out = 0

        def r_out(s: str) -> str:
            nonlocal red_out
            r = redact(s)
            red_out += r.total
            return r.text

        out = _map_strings(out, r_out)
        self.stats["pii_redacted_out"] += red_out
        t_in, t_out = tokens(text_in), tokens(" ".join(_strings(out)))
        self.meter.add(tier, t_in + t_out)
        res = {
            "status": "ok",
            "output": out,
            "tier": tier,
            "tokens": t_in + t_out,
            "tool_calls": ctx.tool_calls,
            "pending_approvals": ctx.pending,
            "pii_redacted": red_in + red_out,
            "cache": "miss",
        }
        digest = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()[:16]
        self.audit.append({"agent": name, "status": "ok", "tier": tier, "tokens": t_in + t_out, "tools": ctx.tool_calls, "pending": ctx.pending, "out_sha": digest})
        self.cache.put(key, res)
        return res
