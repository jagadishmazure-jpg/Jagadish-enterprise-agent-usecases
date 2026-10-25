"""Tests for the five-layer demo: registry, gate, LoopPolicy, graph runner and per-layer behaviour."""

from __future__ import annotations

import json

import pytest

from entagents.fourlayers import bench, gate, layers, registry
from entagents.fourlayers.graph import END, Graph, Interrupted, InvalidTransition, Runner
from entagents.fourlayers.loop_policy import End, LoopPolicy, cost_per_accepted_change
from entagents.fourlayers.sim import Meter, tokens
from entagents.fourlayers.task import APPROVED_VENDORS, INJECTION, POLICY, build

CASES = build()


@pytest.fixture(scope="module")
def result():
    return bench.run()


# ---- task -----------------------------------------------------------------------------------
def test_task_is_deterministic():
    assert [c.text for c in build()] == [c.text for c in CASES]


def test_task_size_and_kinds():
    assert len(CASES) == 37
    assert {c.kind for c in CASES} == {"clean", "over_limit", "bad_vendor", "bad_math", "missing", "injection", "ocr", "ocr_hard"}


def test_gold_clauses_exist_in_policy():
    ids = {c for c, _ in POLICY}
    assert all(c.clause in ids for c in CASES)


def test_injection_cases_carry_instruction():
    assert all(INJECTION in c.text for c in CASES if c.kind == "injection")


def test_bad_vendor_not_approved():
    assert all(not any(v in c.text for v in APPROVED_VENDORS) for c in CASES if c.kind == "bad_vendor")


# ---- meters ---------------------------------------------------------------------------------
def test_tokens_rule_of_thumb():
    assert tokens("abcd") == 1 and tokens("abcde") == 2 and tokens("") == 0


def test_meter_charges_cost_and_latency():
    m = Meter()
    ms = m.charge("x" * 400, "y" * 40, "t")
    assert m.tin == 100 and m.tout == 10 and m.calls == 1
    assert ms == pytest.approx(350 + 0.02 * 100 + 8 * 10)
    assert m.cost == pytest.approx(100 * 0.40e-6 + 10 * 1.60e-6)


# ---- registry -------------------------------------------------------------------------------
def test_registry_loads_latest_by_default():
    assert registry.load("invoice_policy").version == 2


def test_registry_versions_listed():
    assert registry.versions("invoice_policy") == [1, 2]


def test_registry_specific_version_and_hash():
    p1, p2 = registry.load("invoice_policy", 1), registry.load("invoice_policy", 2)
    assert p1.sha != p2.sha and len(p1.sha) == 12
    assert "clause" in p2.output_keys and "clause" not in p1.output_keys


def test_registry_unknown_raises():
    with pytest.raises(KeyError):
        registry.load("nope")
    with pytest.raises(KeyError):
        registry.load("invoice_policy", 99)


def test_registry_render_fills_slots():
    out = registry.load("invoice_policy", 2).render("INV-1", "[AP-5] ok")
    assert "INV-1" in out and "[AP-5] ok" in out and "{" not in out


def test_registry_rejects_incomplete_file(tmp_path, monkeypatch):
    (tmp_path / "bad.v1.json").write_text(json.dumps({"id": "bad", "version": 1}))
    monkeypatch.setattr(registry, "DIR", tmp_path)
    with pytest.raises(ValueError):
        registry.load("bad")


# ---- golden gate ----------------------------------------------------------------------------
def test_gate_passes_on_committed_golden():
    r = gate.check()
    assert r["passed"] and r["schema_violations"] == 0 and r["drift_rate"] == 0.0


def test_gate_fails_on_drift():
    g = json.loads(gate.GOLDEN.read_text())
    for k in list(g["cases"])[:5]:
        g["cases"][k]["decision"] = "approve" if g["cases"][k]["decision"] != "approve" else "hold"
    r = gate.check(golden=g)
    assert not r["passed"] and r["drift_rate"] > gate.MAX_DRIFT


def test_gate_fails_on_cost_rise():
    g = json.loads(gate.GOLDEN.read_text())
    g["cost_per_case"] = g["cost_per_case"] / 2
    r = gate.check(golden=g)
    assert not r["passed"] and r["cost_rise"] > gate.MAX_COST_RISE


def test_gate_fails_on_schema_when_version_lacks_clause():
    g = json.loads(gate.GOLDEN.read_text())
    r = gate.check(version=1, golden=g)
    assert not r["passed"]  # v1 has no clause and drifts from the v2 golden


def test_golden_matches_prompt_hash():
    g = json.loads(gate.GOLDEN.read_text())
    assert g["sha"] == registry.load("invoice_policy", g["version"]).sha


# ---- LoopPolicy -----------------------------------------------------------------------------
def test_loop_turn_cap_exhausts():
    p = LoopPolicy(max_turns=3, stall_window=5, clock=lambda: 0.0)
    p.start()
    ends = [p.step("a", i, i, 0.0) for i in range(3)]
    assert ends[:2] == [None, None] and ends[2] == End.EXHAUSTED


def test_loop_cost_cap_exhausts():
    p = LoopPolicy(max_cost_usd=0.001, clock=lambda: 0.0)
    p.start()
    assert p.step("a", 1, 1, 0.0005) is None
    assert p.step("a", 2, 2, 0.0006) == End.EXHAUSTED and "cost" in p.reason


def test_loop_deadline_exhausts():
    t = iter([0.0, 10.0, 31.0])
    p = LoopPolicy(deadline_s=30, clock=lambda: next(t))
    p.start()
    assert p.step("a", 1, 1, 0) is None
    assert p.step("a", 2, 2, 0) == End.EXHAUSTED and "deadline" in p.reason


def test_loop_stall_on_repeated_action():
    p = LoopPolicy(stall_window=3, clock=lambda: 0.0)
    p.start()
    assert [p.step("fix", "same", i, 0) for i in range(3)][-1] == End.STALLED


def test_loop_stall_on_unchanged_state():
    p = LoopPolicy(stall_window=2, clock=lambda: 0.0)
    p.start()
    p.step("a", 1, "s", 0)
    assert p.step("b", 2, "s", 0) == End.STALLED


def test_loop_progress_is_not_stall():
    p = LoopPolicy(max_turns=10, stall_window=3, clock=lambda: 0.0)
    p.start()
    assert all(p.step("a", i, i, 0) is None for i in range(5))


def test_loop_error_never_success():
    p = LoopPolicy()
    assert p.finish(verified=True, error="tool crashed") == End.BLOCKED


def test_loop_unverified_never_success():
    assert LoopPolicy().finish(verified=False) == End.BLOCKED


def test_loop_no_op_and_success():
    assert LoopPolicy().finish(verified=True, changed=False) == End.NO_OP
    assert LoopPolicy().finish(verified=True) == End.SUCCESS


def test_cost_per_accepted_change():
    assert cost_per_accepted_change(0.01, 4) == pytest.approx(0.0025)
    assert cost_per_accepted_change(0.01, 0) is None


# ---- graph runner ---------------------------------------------------------------------------
def _line():
    g = Graph(schema={"n": int, "path": list, "approved": bool})
    g.node("a", lambda s: {"n": s["n"] + 1}).node("b", lambda s: {"n": s["n"] * 10})
    g.edge("a", "b").edge("b", END)
    return g


def test_graph_runs_in_order():
    out = Runner(_line(), {}).run({"n": 1})
    assert out["state"]["n"] == 20 and out["route"] == ["a", "b"]


def test_graph_typed_state_rejects_wrong_type():
    g = Graph(schema={"n": int}).node("a", lambda s: {"n": "x"})
    with pytest.raises(TypeError):
        Runner(g, {}).run({"n": 1})


def test_graph_rejects_unknown_key():
    g = Graph(schema={"n": int}).node("a", lambda s: {"zzz": 1})
    with pytest.raises(TypeError):
        Runner(g, {}).run({"n": 1})


def test_graph_conditional_edge():
    g = Graph(schema={"n": int}).node("a", lambda s: {}).node("big", lambda s: {"n": 100}).node("small", lambda s: {"n": 0})
    g.cond("a", lambda s: "big" if s["n"] > 5 else "small", {"big", "small"})
    assert Runner(g, {}).run({"n": 9})["state"]["n"] == 100
    assert Runner(g, {}).run({"n": 1})["state"]["n"] == 0


def test_graph_blocks_invalid_transition():
    g = Graph(schema={"n": int}).node("a", lambda s: {}).node("b", lambda s: {})
    g.cond("a", lambda s: "delete_all", {"b"})
    with pytest.raises(InvalidTransition):
        Runner(g, {}).run({"n": 1})
    assert g.blocked == [("a", "delete_all")]


def test_graph_parallel_fan_out_and_in():
    g = Graph(schema={"x": int, "y": int, "z": int}).node("s", lambda s: {}).node("x", lambda s: {"x": 1}).node("y", lambda s: {"y": 2}).node("j", lambda s: {"z": s["x"] + s["y"]})
    g.parallel("s", ["x", "y"], "j")
    out = Runner(g, {}).run({"x": 0})
    assert out["state"]["z"] == 3 and "[x|y]" in out["route"]


def test_graph_checkpoint_resume_skips_done_nodes():
    calls = []
    boom = {"on": True}

    def b(s):
        if boom["on"]:
            boom["on"] = False
            raise RuntimeError("crash")
        calls.append("b")
        return {"n": s["n"] + 1}

    g = Graph(schema={"n": int}).node("a", lambda s: calls.append("a") or {"n": 1}).node("b", b)
    g.edge("a", "b")
    store: dict = {}
    with pytest.raises(RuntimeError):
        Runner(g, store).run({"n": 0}, thread="t1")
    out = Runner(g, store).run(thread="t1")
    assert calls == ["a", "b"] and out["state"]["n"] == 2 and "t1" not in store


def test_graph_interrupt_pauses_and_resumes():
    g = Graph(schema={"n": int, "approved": bool}).node("a", lambda s: {"n": 1}).node("ok", lambda s: {"n": 2 if s["approved"] else -1}, interrupt=True)
    g.edge("a", "ok")
    store: dict = {}
    with pytest.raises(Interrupted):
        Runner(g, store).run({"n": 0}, thread="h")
    assert Runner(g, store).run(thread="h", approve=True)["state"]["n"] == 2


def test_graph_subgraph_as_node():
    inner = Graph(schema={"n": int}).node("double", lambda s: {"n": s["n"] * 2})
    outer = Graph(schema={"n": int}).node("inc", lambda s: {"n": s["n"] + 1}).node("sub", inner.as_node())
    outer.edge("inc", "sub")
    assert Runner(outer, {}).run({"n": 2})["state"]["n"] == 6


def test_graph_step_cap():
    g = Graph(schema={"n": int}).node("a", lambda s: {})
    g.cond("a", lambda s: "a", {"a"})
    with pytest.raises(RuntimeError):
        Runner(g, {}, max_steps=5).run({"n": 0})


def test_graph_route_hash_deterministic():
    a, b = Runner(_line(), {}).run({"n": 1}), Runner(_line(), {}).run({"n": 1})
    assert a["route_hash"] == b["route_hash"]


# ---- layers on the task ---------------------------------------------------------------------
def _by(kind):
    return [c for c in CASES if c.kind == kind]


def test_l1_obeys_injection():
    assert all(layers.l1(c)["decision"] == "approve" for c in _by("injection"))


def test_l2_follows_retrieved_vendor_clause():
    assert all(layers.l2(c)["decision"] == "hold" and layers.l2(c)["clause"] == "AP-1" for c in _by("bad_vendor"))


def test_retrieve_respects_budget_and_ranks_policy_first():
    got = layers.retrieve("payables invoice vendor approved total threshold", budget=120)
    assert sum(len(t) // 4 + 1 for _, t in got) <= 120
    assert all(c.startswith("AP-") for c, _ in got)


def test_l3_guard_holds_injection():
    assert all(layers.l3(c)["decision"] == "hold" and layers.l3(c)["clause"] == "AP-6" for c in _by("injection"))


def test_l3_arithmetic_rejects():
    assert all(layers.l3(c)["clause"] == "AP-3" for c in _by("bad_math"))


def test_l4_repairs_scan_errors():
    rows = [layers.l4(c) for c in _by("ocr")]
    assert all(r["correct"] and r["repairs"] == 1 and r["end"] == "success" for r in rows)


def test_l4_hard_scan_stalls_to_human_not_success():
    rows = [layers.l4(c) for c in _by("ocr_hard")]
    assert all(r["end"] == "stalled" and r["decision"] == "hold" for r in rows)


def test_l4_genuine_missing_field_is_rejected_without_repair():
    rows = [layers.l4(c) for c in _by("missing")]
    assert all(r["decision"] == "reject" and r["repairs"] == 0 for r in rows)


def test_l5_matches_l4_decisions():
    assert [layers.l5(c)["decision"] for c in CASES] == [layers.l4(c, i)["decision"] for i, c in enumerate(CASES)]


def test_l5_resume_after_crash_mid_run():
    r = layers.l5(_by("clean")[0], crash_at={"review"})
    assert r["correct"] and r["executed"].count("extract") == 1


# ---- measured summary -----------------------------------------------------------------------
def test_accuracy_rises_by_layer(result):
    a = [v["accuracy"] for v in result["layers"].values()]
    assert a[0] < a[1] < a[2] < a[3] and a[3] == a[4]


def test_harness_layers_check_every_output(result):
    L = result["layers"]
    assert L["L1 prompt"]["checked_output"] == 0 and L["L3 harness"]["checked_output"] == 1.0


def test_known_miss_stays_visible(result):
    assert result["layers"]["L5 graph"]["wrong_by_kind"]["ocr_hard"] == 2


def test_graph_parallel_beats_sequential(result):
    p = result["graph"]["parallel"]
    assert p["sim_p50_ms_parallel"] < p["sim_p50_ms_sequential"] and p["real_wall_ms_two_50ms_branches"] < 95


def test_graph_crash_resume_redoes_nothing(result):
    c = result["graph"]["crash_resume"]
    assert c["nodes_redone_graph"] == 0 and c["nodes_redone_freeform_loop"] == c["nodes_done_before_crash"] > 0


def test_graph_route_audit_and_blocking(result):
    g = result["graph"]
    assert g["route_audit"]["identical_route_hashes"] == g["route_audit"]["runs"]
    assert g["invalid_transitions"]["followed"] == 0


def test_committed_results_match_fresh_run(result):
    from pathlib import Path

    saved = json.loads((Path(__file__).resolve().parents[1] / "results/layers.json").read_text())
    for d in (saved, result):
        d["graph"]["parallel"].pop("real_wall_ms_two_50ms_branches", None)
    assert saved == json.loads(json.dumps(result))


# ---- extra checks ---------------------------------------------------------------------------
def test_l2_misses_arithmetic_without_tool():
    assert all(layers.l2(c)["decision"] == "approve" for c in _by("bad_math"))


def test_cost_rises_with_layers_until_graph(result):
    c = [v["sim_cost_per_case_usd"] for v in result["layers"].values()]
    assert c[0] < c[1] < c[2] < c[3]


def test_l3_retries_counted(result):
    assert result["l3_retries"] == sum(1 for i in range(len(CASES)) if i % 4 == 3)


def test_l4_end_states_named(result):
    assert set(result["l4_end_states"]) <= {e.value for e in End} and result["l4_end_states"]["stalled"] == 2


def test_cli_gate_exit_zero(capsys):
    from entagents.fourlayers.__main__ import main

    assert main(["gate"]) == 0 and '"passed": true' in capsys.readouterr().out


def test_cli_unknown_command():
    from entagents.fourlayers.__main__ import main

    assert main(["what"]) == 2


def test_l5_holds_pause_for_a_person():
    r = layers.l5(_by("over_limit")[0])
    assert "human" in r["route"] and r["decision"] == "hold"


def test_l5_approved_path_skips_human():
    r = layers.l5(_by("clean")[0])
    assert "human" not in r["route"] and r["route"][-1] == "decide"


def test_graph_bad_router_never_reaches_decide():
    g = layers.build_graph(bad_router=True)
    r = Runner(g, {})
    with pytest.raises(InvalidTransition):
        r.run({"text": CASES[0].text})
    assert "decide" not in r.executed


def test_cost_per_accepted_reported_for_every_layer(result):
    assert all(v["sim_cost_per_accepted_usd"] >= v["sim_cost_per_case_usd"] for v in result["layers"].values())
