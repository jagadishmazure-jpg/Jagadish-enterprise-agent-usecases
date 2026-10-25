"""Run all five layers on the synthetic set and measure what each adds. Writes results/layers.json."""

from __future__ import annotations

import statistics
import time

from . import layers
from .graph import Graph, InvalidTransition, Runner
from .loop_policy import cost_per_accepted_change
from .task import build


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    acc = sum(r["correct"] for r in rows)
    total_cost = sum(r["cost"] for r in rows)
    return {
        "cases": n,
        "accuracy": round(acc / n, 4),
        "cited_correct": round(sum(r["cited_ok"] for r in rows) / n, 4),
        "checked_output": round(sum(r["checked"] for r in rows) / n, 4),
        "tokens_per_case": round(sum(r["tokens"] for r in rows) / n, 1),
        "sim_cost_per_case_usd": round(total_cost / n, 8),
        "sim_cost_per_accepted_usd": round(cost_per_accepted_change(total_cost, acc) or 0, 8),
        "sim_latency_p50_ms": round(statistics.median(r["ms"] for r in rows), 1),
        "model_calls_per_case": round(sum(r["calls"] for r in rows) / n, 2),
        "wrong_by_kind": {k: sum(1 for r in rows if r["kind"] == k and not r["correct"]) for k in sorted({r["kind"] for r in rows})},
    }


def graph_extras(cases) -> dict:
    # 1) crash mid-run, then resume: graph vs free-form loop
    c = next(x for x in cases if x.kind == "clean")
    store: dict = {}
    g = layers.build_graph(crash_at={"review"})
    r = Runner(g, store)
    try:
        r.run({"text": c.text}, thread="crash")
    except RuntimeError:
        pass
    before = list(r.executed)
    r2 = Runner(g, store)
    r2.run(thread="crash")
    redone_graph = sum(1 for n in r2.executed if n in before)
    redone_loop = len(before)  # a loop with no checkpoint starts again from the top
    # 2) parallel fan-out: simulated latency over the full set, plus a real wall-clock check
    rows = [layers.l5(x) for x in cases]
    par = statistics.median(r["ms"] for r in rows)
    seq = statistics.median(r["seq_ms"] for r in rows)

    def slow(_s):
        time.sleep(0.05)
        return {}

    gw = Graph(schema={"x": int}).node("a", lambda s: {}).node("b", slow).node("c", slow).node("j", lambda s: {})
    gw.parallel("a", ["b", "c"], "j")
    t0 = time.perf_counter()
    Runner(gw, {}).run({"x": 1})
    wall_par = (time.perf_counter() - t0) * 1000
    # 3) deterministic route audit: two runs, same route hashes
    again = [layers.l5(x) for x in cases]
    same = sum(a["route_hash"] == b["route_hash"] for a, b in zip(rows, again, strict=True))
    # 4) invalid transitions blocked
    blocked = 0
    for x in cases:
        bg = layers.build_graph(bad_router=True)
        try:
            Runner(bg, {}).run({"text": x.text})
        except InvalidTransition:
            blocked += 1
    return {
        "crash_resume": {"nodes_done_before_crash": len(before), "nodes_redone_graph": redone_graph, "nodes_redone_freeform_loop": redone_loop},
        "parallel": {
            "sim_p50_ms_parallel": round(par, 1),
            "sim_p50_ms_sequential": round(seq, 1),
            "sim_saving_pct": round(100 * (1 - par / seq), 1),
            "real_wall_ms_two_50ms_branches": round(wall_par),
        },
        "route_audit": {"runs": len(rows), "identical_route_hashes": same},
        "invalid_transitions": {"attempted": len(cases), "blocked": blocked, "followed": len(cases) - blocked},
    }


def run() -> dict:
    cases = build()
    rows = {
        "L1 prompt": [layers.l1(c) for c in cases],
        "L2 context": [layers.l2(c) for c in cases],
        "L3 harness": [layers.l3(c, i) for i, c in enumerate(cases)],
        "L4 loop": [layers.l4(c, i) for i, c in enumerate(cases)],
        "L5 graph": [layers.l5(c) for c in cases],
    }
    l4_ends: dict = {}
    for r in rows["L4 loop"]:
        l4_ends[r["end"]] = l4_ends.get(r["end"], 0) + 1
    return {
        "note": "Synthetic invoices, simulated model, SIMULATED token prices and latency. Deterministic.",
        "layers": {k: summarize(v) for k, v in rows.items()},
        "l4_end_states": dict(sorted(l4_ends.items())),
        "l3_retries": sum(r["retries"] for r in rows["L3 harness"]),
        "l3_guard_hits": sum(r["guard_hit"] for r in rows["L3 harness"]),
        "graph": graph_extras(cases),
    }
