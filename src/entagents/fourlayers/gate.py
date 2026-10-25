"""Golden regression gate for prompt versions: schema, decision drift and cost.

golden/invoice_policy.json stores, for the active prompt version, each case's expected decision and
clause plus a cost baseline. A change fails the gate if any output breaks the schema, more than
MAX_DRIFT of decisions differ from golden, or simulated cost per case rises more than MAX_COST_RISE.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import layers, registry
from .task import build

GOLDEN = Path(__file__).parent / "golden" / "invoice_policy.json"
MAX_DRIFT, MAX_COST_RISE = 0.05, 0.10


def outputs(version: int) -> tuple[dict, float]:
    p = registry.load("invoice_policy", version)
    out, cost = {}, 0.0
    for i, c in enumerate(build()):
        r = layers.l3(c, i) if p.cite_clause else layers.l1(c)
        rec = {"invoice_no": c.cid, "decision": r["decision"]}
        if p.cite_clause:
            rec["clause"] = r["clause"]
        out[c.cid] = rec
        cost += r["cost"]
    return out, cost / len(out)


def record(version: int) -> dict:
    out, cost = outputs(version)
    g = {"prompt": "invoice_policy", "version": version, "sha": registry.load("invoice_policy", version).sha, "cost_per_case": round(cost, 8), "cases": out}
    GOLDEN.parent.mkdir(exist_ok=True)
    GOLDEN.write_text(json.dumps(g, indent=1, sort_keys=True) + "\n")
    return g


def check(version: int | None = None, golden: dict | None = None) -> dict:
    g = golden or json.loads(GOLDEN.read_text())
    v = version or g["version"]
    p = registry.load("invoice_policy", v)
    out, cost = outputs(v)
    schema_bad = [k for k, r in out.items() if set(r) != set(p.output_keys) or r["decision"] not in ("approve", "hold", "reject")]
    drift = [k for k, r in out.items() if g["cases"].get(k, {}).get("decision") != r["decision"]]
    rise = cost / g["cost_per_case"] - 1
    res = {
        "version": v,
        "schema_violations": len(schema_bad),
        "drift_rate": round(len(drift) / len(out), 4),
        "cost_rise": round(rise, 4),
        "passed": not schema_bad and len(drift) / len(out) <= MAX_DRIFT and rise <= MAX_COST_RISE,
    }
    return res
