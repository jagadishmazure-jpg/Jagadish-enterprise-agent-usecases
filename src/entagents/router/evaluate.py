"""Train on logged states, tune the handoff threshold on validation, report on held-out test runs.

python -m entagents.router.evaluate --out results/router.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .model import TinyRouterModel
from .router import BIG_COST_USD, BIG_MS, BigDecider, StepRouter, rule_router
from .traces import FEATURES, build, split

TARGET_AGREEMENT = 0.97  # minimum full-step agreement with the always-big baseline


def _tuple(d: dict) -> tuple:
    return (d["worker"], d["safe"], d["stop"])


def train(states):
    tr, va, te = split(states)
    m = TinyRouterModel(len(FEATURES)).fit([s.x for s in tr], [s.y_worker for s in tr], [s.y_safe for s in tr], [s.y_stop for s in tr])
    return m, tr, va, te


def score(model, states, thr: float) -> dict:
    big = BigDecider()
    base = [_tuple(big.decide(s)) for s in states]  # always-big baseline
    r = StepRouter(model, threshold=thr, big=BigDecider())
    recs = [r.decide(s) for s in states]
    from .traces import WORKERS

    got = [(WORKERS.index(x["worker"]), x["safe"], x["stop"]) for x in recs]
    truth = [(s.y_worker, s.y_safe, s.y_stop) for s in states]
    n = len(states)
    small = sum(x["source"] == "small" for x in recs)
    cost = sum(x["sim_cost_usd"] for x in recs)
    ms = sum(x["sim_ms"] for x in recs)
    unsafe = [i for i, t in enumerate(truth) if t[1] == 0]
    return {
        "threshold": thr,
        "steps": n,
        "small_share": round(small / n, 4),
        "agreement_vs_big": round(sum(a == b for a, b in zip(got, base, strict=True)) / n, 4),
        "accuracy_vs_truth": round(sum(a == b for a, b in zip(got, truth, strict=True)) / n, 4),
        "big_accuracy_vs_truth": round(sum(a == b for a, b in zip(base, truth, strict=True)) / n, 4),
        "unsafe_steps": len(unsafe),
        "unsafe_caught": sum(got[i][1] == 0 for i in unsafe),
        "sim_cost_usd": round(cost, 4),
        "sim_cost_always_big_usd": round(n * BIG_COST_USD, 4),
        "sim_cost_saved_pct": round(1 - cost / (n * BIG_COST_USD), 4),
        "sim_latency_ms": round(ms, 1),
        "sim_latency_always_big_ms": round(n * BIG_MS, 1),
        "sim_latency_saved_pct": round(1 - ms / (n * BIG_MS), 4),
        "pending_approvals": len(r.approvals.items),
        "audit_entries": len(r.audit.entries),
        "audit_chain_ok": r.audit.verify(),
    }


def run() -> dict:
    states = build()
    m, tr, va, te = train(states)
    grid = [round(0.30 + 0.05 * i, 2) for i in range(14)]
    val = [score(m, va, t) for t in grid]
    ok = [v for v in val if v["agreement_vs_big"] >= TARGET_AGREEMENT]
    tuned = max(ok, key=lambda v: v["small_share"])["threshold"] if ok else grid[-1]
    sweep = [score(m, te, t) for t in grid]
    test = score(m, te, tuned)
    rule = [rule_router(s) for s in te]
    rule_acc = sum(_tuple(d) == (s.y_worker, s.y_safe, s.y_stop) for d, s in zip(rule, te, strict=True)) / len(te)
    return {
        "data": "synthetic (logged states from real runs of the 22 agents, seeded perturbations)",
        "prices": "simulated: small model $0 and 0.2 ms per step; stronger decider $0.004 and 900 ms per step",
        "states": {"train": len(tr), "validation": len(va), "test": len(te), "runs": len({s.run_id for s in states})},
        "model": {"type": "multinomial logistic regression, 3 heads", "features": len(FEATURES), "params": m.n_params()},
        "target_agreement": TARGET_AGREEMENT,
        "tuned_threshold": tuned,
        "test": test,
        "rule_router_accuracy_vs_truth": round(rule_acc, 4),
        "sweep_test": [{k: v[k] for k in ("threshold", "small_share", "agreement_vs_big", "accuracy_vs_truth", "sim_cost_saved_pct")} for v in sweep],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    res = run()
    txt = json.dumps(res, indent=2) + "\n"
    if a.check:
        stored = Path(a.out).read_text()
        if stored != txt:
            print("results/router.json is out of date; run: python -m entagents.router.evaluate --out results/router.json")
            return 1
        print("router results match a fresh run")
        return 0
    if a.out:
        Path(a.out).write_text(txt)
    print(json.dumps({k: res[k] for k in ("states", "tuned_threshold", "test", "rule_router_accuracy_vs_truth")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
