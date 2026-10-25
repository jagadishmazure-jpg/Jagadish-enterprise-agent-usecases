"""Step router with confidence handoff, rule fallback, human approval and audit.

Decision order for one step:
  1. try the tiny model; if it is missing or raises, fall back to the rule router
  2. if its confidence is below the threshold, hand the step to the stronger decider
  3. whatever was decided, a step that would publish from an agent with risky tools is
     parked for a named human approver, and an unsafe verdict from any source blocks it
  4. every decision is appended to the hash-chained audit log

The stronger decider is SIMULATED: it sees the hidden true review quality and is wrong on
a seeded 2% of steps, with made-up per-call price and latency. It stands in for a frontier model.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..framework.approval import ApprovalQueue
from ..framework.audit import AuditLog
from .traces import WORKERS, State, oracle

# Simulated unit prices and latencies (illustrative, not quotes from any provider).
SMALL_COST_USD, SMALL_MS = 0.0, 0.2
BIG_COST_USD, BIG_MS = 0.004, 900.0
RULE_COST_USD, RULE_MS = 0.0, 0.05


class BigDecider:
    """Simulated stronger decider. Labelled simulated everywhere it is reported."""

    def __init__(self, error_rate: float = 0.02, seed: int = 5):
        self.error_rate, self.rng = error_rate, random.Random(seed)

    def decide(self, s: State) -> dict:
        w, safe, stop = oracle(s)
        if self.rng.random() < self.error_rate:
            w = (w + 1) % len(WORKERS)
        return {"worker": w, "safe": safe, "stop": stop, "confidence": 1.0}


def rule_router(s: State) -> dict:
    """Fixed rules from visible features only (thresholds the noisy review signal at 0.5)."""
    f = s.flags
    x = dict(zip(["bias", "step", "r", "t", "d", "rev", "sig"], s.x, strict=False))
    s2 = State(s.agent, s.run_id, s.step, s.x, x["sig"] if f["reviewed"] else 0.0, f)
    w, safe, stop = oracle(s2)
    return {"worker": w, "safe": safe, "stop": stop, "confidence": 1.0}


@dataclass
class StepRouter:
    model: object | None
    threshold: float = 0.8
    big: BigDecider = field(default_factory=BigDecider)
    audit: AuditLog = field(default_factory=AuditLog)
    approvals: ApprovalQueue = field(default_factory=ApprovalQueue)

    def decide(self, s: State) -> dict:
        source, d = "small", None
        try:
            if self.model is None:
                raise RuntimeError("no model loaded")
            d = self.model.predict(s.x)
        except Exception as e:  # noqa: BLE001 - any model failure must fall back, never crash a run
            source, d = "rule_fallback", {**rule_router(s), "error": type(e).__name__}
        small_conf = d["confidence"] if source == "small" else None
        if source == "small" and d["confidence"] < self.threshold:
            source, d = "big", self.big.decide(s)
        cost, ms = {"small": (SMALL_COST_USD, SMALL_MS), "big": (BIG_COST_USD, BIG_MS), "rule_fallback": (RULE_COST_USD, RULE_MS)}[source]
        worker = WORKERS[d["worker"]]
        action = "run"
        if not d["safe"]:
            action = "blocked"
        elif worker == "publish" and s.x[10] >= 1.0 and not d["stop"]:
            p = self.approvals.request(s.agent, "publish", {"run": s.run_id, "step": s.step})
            action = f"pending_approval#{p.id}"
        rec = {
            "run": s.run_id,
            "step": s.step,
            "source": source,
            "worker": worker,
            "safe": d["safe"],
            "stop": d["stop"],
            "confidence": round(d["confidence"], 4),
            "small_confidence": None if small_conf is None else round(small_conf, 4),
            "action": action,
            "sim_cost_usd": cost,
            "sim_ms": ms,
        }
        self.audit.append({"event": "route", **rec})
        return rec
