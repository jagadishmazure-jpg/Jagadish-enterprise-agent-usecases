"""Command line: list agents, run one on its demo input (or your JSON), or run all evals.

entagents list
entagents run sql-nl
entagents run sql-nl --input '{"question": "Revenue in the west region"}'
entagents eval --out results/results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .framework.evals import safety_eval, task_eval
from .framework.runtime import Runtime
from .registry import BATCHES, agents, by_name


def run_all() -> dict:
    rows, rt = [], Runtime()
    for a in agents():
        t, s = task_eval(a), safety_eval(a)
        demo = rt.run(a, a.demo())
        rows.append({"name": a.META["name"], **{f"task_{k}": v for k, v in t.items()}, **s, "demo_tier": demo["tier"], "demo_tokens": demo["tokens"]})
    n = len(rows)
    return {
        "agents": rows,
        "summary": {
            "agents": n,
            "batches_built": len(BATCHES),
            "eval_cases": sum(r["task_cases"] for r in rows),
            "mean_task_score": round(sum(r["task_score"] for r in rows) / n, 4),
            "injection_block_rate": round(sum(r["injection_blocked"] for r in rows) / n, 4),
            "pii_leak_rate": round(sum(r["pii_leaked"] for r in rows) / n, 4),
            "audit_chains_valid": all(r["task_audit_chain_ok"] and r["audit_chain_ok"] for r in rows),
            "simulated_cost_demo_run_usd": rt.meter.simulated_cost,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="entagents")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("name")
    r.add_argument("--input")
    e = sub.add_parser("eval")
    e.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for ag in agents():
            print(f"{ag.META['name']:<18} {ag.META['level']:<13} {ag.META['title']}")
    elif a.cmd == "run":
        ag = by_name(a.name)
        res = Runtime().run(ag, json.loads(a.input) if a.input else ag.demo())
        print(json.dumps(res, indent=2, default=str))
    else:
        res = run_all()
        txt = json.dumps(res, indent=2)
        if a.out:
            Path(a.out).write_text(txt + "\n")
        print(json.dumps(res["summary"], indent=2))
        return 0 if res["summary"]["injection_block_rate"] == 1.0 and res["summary"]["pii_leak_rate"] == 0.0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
