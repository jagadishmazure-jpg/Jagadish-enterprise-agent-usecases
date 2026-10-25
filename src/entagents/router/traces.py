"""Logged agent-run states, built from real runs of this repo's 22 agents (synthetic data).

Every agent's eval cases are run through the governed Runtime. Each real run (status, tools
used, approvals parked, model tier, tokens) seeds a step-by-step trace of a
research -> tool -> write -> review -> publish loop. Seeded perturbations (review quality,
retries, a planted unsafe step) widen the set. The true label of each step comes from
`oracle()`, a written policy that sees one hidden value (true review quality) the router
only sees through a noisy signal. That hidden value is what makes some steps genuinely hard.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from ..framework.runtime import Runtime
from ..registry import agents

WORKERS = ["research", "write", "review", "tool", "publish"]
FEATURES = [
    "bias",
    "step",
    "has_research",
    "has_tool",
    "has_draft",
    "reviewed",
    "review_signal",
    "retries",
    "needs_tool",
    "needs_grounding",
    "risky_tool",
    "hard_tier",
    "tokens",
    "injection_flag",
    "error_flag",
    "last_publish",
]


@dataclass
class State:
    agent: str
    run_id: str
    step: int
    x: list[float]
    review_true: float
    flags: dict
    y_worker: int = 0
    y_safe: int = 1
    y_stop: int = 0


def oracle(s: State) -> tuple[int, int, int]:
    """Ground-truth policy for one step: (worker index, safe 0/1, stop 0/1)."""
    f = s.flags
    if f["injection"] or f["error"]:
        return WORKERS.index("review"), 0, 1
    if f["published"]:
        return WORKERS.index("publish"), 1, 1
    if not f["research"]:
        return WORKERS.index("research"), 1, 0
    if f["needs_tool"] and not f["tool"]:
        return WORKERS.index("tool"), 1, 0
    if not f["draft"]:
        return WORKERS.index("write"), 1, 0
    if not f["reviewed"]:
        return WORKERS.index("review"), 1, 0
    if s.review_true >= 0.5:
        return WORKERS.index("publish"), 1, 0
    if f["retries"] >= 2:  # out of retries: stop and hand to a person
        return WORKERS.index("review"), 1, 1
    return WORKERS.index("write"), 1, 0


def _feat(f: dict, step: int, signal: float, meta: dict) -> list[float]:
    return [
        1.0,
        step / 8,
        float(f["research"]),
        float(f["tool"]),
        float(f["draft"]),
        float(f["reviewed"]),
        signal if f["reviewed"] else 0.0,
        f["retries"] / 2,
        float(f["needs_tool"]),
        float(meta["grounding"]),
        float(meta["risky"]),
        float(meta["hard"]),
        min(meta["tokens"], 400) / 400,
        float(f["injection"]),
        float(f["error"]),
        float(f["published"]),
    ]


def _run_trace(agent: str, run_id: str, meta: dict, rng: random.Random, noise: float) -> list[State]:
    f = {"research": False, "tool": False, "draft": False, "reviewed": False, "retries": 0, "published": False, "needs_tool": meta["needs_tool"], "injection": meta["blocked"], "error": meta["error"]}
    out: list[State] = []
    review_true = rng.random()
    for step in range(9):
        signal = min(1.0, max(0.0, review_true + rng.gauss(0, noise)))
        s = State(agent, run_id, step, _feat(f, step, signal, meta), review_true, dict(f))
        s.y_worker, s.y_safe, s.y_stop = oracle(s)
        out.append(s)
        if s.y_stop:
            break
        w = WORKERS[s.y_worker]
        if w == "research":
            f["research"] = True
        elif w == "tool":
            f["tool"] = True
        elif w == "write":
            f["draft"], f["reviewed"] = True, False
            if out and len(out) > 1 and WORKERS[out[-2].y_worker] == "review":
                f["retries"] += 1
                review_true = min(1.0, review_true + rng.uniform(0.1, 0.4))
        elif w == "review":
            f["reviewed"] = True
        elif w == "publish":
            f["published"] = True
    return out


def real_run_meta() -> list[tuple[str, dict]]:
    """One metadata row per real eval-case run of each agent."""
    rows = []
    for a in agents():
        rt = Runtime()
        tags = set(a.META.get("tags", []))
        for i, (payload, _exp) in enumerate(a.eval_cases()):
            res = rt.run(a, payload)
            rows.append(
                (
                    a.META["name"],
                    {
                        "case": i,
                        "blocked": res["status"] == "blocked",
                        "error": res["status"] in ("error", "denied"),
                        "needs_tool": bool(res.get("tool_calls")) or bool(res.get("pending_approvals")),
                        "risky": bool(a.TOOLS.risky),
                        "grounding": bool(tags & {"citations", "grounding", "rag", "abstention"}),
                        "hard": res.get("tier") == "large",
                        "tokens": res.get("tokens", 0),
                    },
                )
            )
    return rows


def build(seed: int = 7, variants: int = 6, noise: float = 0.18) -> list[State]:
    rng = random.Random(seed)
    states: list[State] = []
    for agent, meta in real_run_meta():
        for v in range(variants):
            m = dict(meta)
            if rng.random() < 0.06:  # planted unsafe step (e.g. an injected tool result)
                m["blocked"] = True
            states += _run_trace(agent, f"{agent}#{meta['case']}.{v}", m, rng, noise)
    return states


def split(states: list[State], seed: int = 11) -> tuple[list[State], list[State], list[State]]:
    """Split by run (never by step) so no run leaks across train / validation / test."""
    runs = sorted({s.run_id for s in states})
    random.Random(seed).shuffle(runs)
    n = len(runs)
    tr, va = set(runs[: int(n * 0.6)]), set(runs[int(n * 0.6) : int(n * 0.8)])
    return ([s for s in states if s.run_id in tr], [s for s in states if s.run_id in va], [s for s in states if s.run_id not in tr and s.run_id not in va])
