"""Small step router: training data, model, handoff, guardrails, audit and measured results."""

import json
from pathlib import Path

import pytest

from entagents.router import evaluate
from entagents.router.model import SoftmaxHead, softmax
from entagents.router.router import BigDecider, StepRouter, rule_router
from entagents.router.traces import FEATURES, WORKERS, build, oracle, split

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def trained():
    return evaluate.train(build())


@pytest.fixture(scope="module")
def stored():
    return json.loads((ROOT / "results/router.json").read_text())


def test_features_fixed_width():
    assert all(len(s.x) == len(FEATURES) for s in build(variants=1))


def test_traces_cover_all_22_agents():
    assert len({s.agent for s in build(variants=1)}) == 22


def test_split_is_by_run_no_leak():
    tr, va, te = split(build(variants=1))
    a, b, c = ({s.run_id for s in x} for x in (tr, va, te))
    assert not (a & b or a & c or b & c)


def test_build_is_deterministic():
    assert [s.x for s in build(variants=1)] == [s.x for s in build(variants=1)]


def test_every_label_is_a_known_worker():
    assert {s.y_worker for s in build(variants=1)} <= set(range(len(WORKERS)))


def test_oracle_stops_unsafe_steps():
    s = next(s for s in build() if s.flags["injection"])
    assert oracle(s)[1:] == (0, 1)


def test_softmax_sums_to_one():
    assert abs(sum(softmax([1.0, 2.0, -3.0])) - 1) < 1e-9


def test_head_learns_separable_toy():
    h = SoftmaxHead(2, 2).fit([[1, 0], [1, 1]] * 20, [0, 1] * 20, epochs=30)
    assert h.proba([1, 1])[1] > 0.9 and h.proba([1, 0])[0] > 0.9


def test_model_is_tiny(trained):
    assert trained[0].n_params() == 9 * len(FEATURES) < 200


def test_model_serialises(trained):
    assert set(json.loads(trained[0].to_json())) == {"worker", "safe", "stop"}


def test_low_threshold_keeps_everything_small(trained):
    r = StepRouter(trained[0], threshold=0.0)
    assert all(r.decide(s)["source"] == "small" for s in trained[3][:200])


def test_threshold_above_one_escalates_everything(trained):
    r = StepRouter(trained[0], threshold=1.01)
    assert all(r.decide(s)["source"] == "big" for s in trained[3][:200])


def test_missing_model_falls_back_to_rules(trained):
    rec = StepRouter(None).decide(trained[3][0])
    assert rec["source"] == "rule_fallback"


def test_broken_model_falls_back_to_rules(trained):
    class Broken:
        def predict(self, x):
            raise ValueError("bad weights")

    assert StepRouter(Broken()).decide(trained[3][0])["source"] == "rule_fallback"


def test_risky_publish_needs_human_even_when_confident(trained):
    s = next(s for s in trained[3] if s.y_worker == WORKERS.index("publish") and not s.y_stop and s.x[10] == 1.0)

    class Sure:
        def predict(self, x):
            return {"worker": WORKERS.index("publish"), "safe": 1, "stop": 0, "confidence": 1.0}

    r = StepRouter(Sure())
    rec = r.decide(s)
    assert rec["action"].startswith("pending_approval") and r.approvals.items[0].status == "pending"


def test_unsafe_verdict_blocks(trained):
    class No:
        def predict(self, x):
            return {"worker": 0, "safe": 0, "stop": 1, "confidence": 1.0}

    assert StepRouter(No()).decide(trained[3][0])["action"] == "blocked"


def test_every_decision_is_audited_and_chain_verifies(trained):
    r = StepRouter(trained[0], threshold=0.9)
    for s in trained[3][:300]:
        r.decide(s)
    assert len(r.audit.entries) == 300 and r.audit.verify()


def test_tampering_breaks_audit_chain(trained):
    r = StepRouter(trained[0])
    for s in trained[3][:5]:
        r.decide(s)
    r.audit.entries[2]["source"] = "small"
    r.audit.entries[2]["worker"] = "publish"
    assert not r.audit.verify()


def test_big_decider_error_rate_is_seeded():
    s = build(variants=1)[:500]
    a, b = BigDecider(), BigDecider()
    assert [a.decide(x)["worker"] for x in s] == [b.decide(x)["worker"] for x in s]


def test_rule_router_returns_valid_decision():
    d = rule_router(build(variants=1)[3])
    assert 0 <= d["worker"] < 5 and d["safe"] in (0, 1)


def test_results_match_fresh_run(stored):
    assert evaluate.run() == stored


def test_tuned_threshold_meets_agreement_target(stored):
    assert stored["test"]["agreement_vs_big"] >= stored["target_agreement"] - 0.01


def test_all_unsafe_steps_blocked(stored):
    assert stored["test"]["unsafe_caught"] == stored["test"]["unsafe_steps"] > 0


def test_small_model_handles_most_steps(stored):
    assert stored["test"]["small_share"] >= 0.8


def test_sweep_share_is_monotone(stored):
    sh = [p["small_share"] for p in stored["sweep_test"]]
    assert sh == sorted(sh, reverse=True)


def test_results_label_simulated_and_synthetic(stored):
    assert "simulated" in stored["prices"] and "synthetic" in stored["data"]


def test_catalog_has_router_card():
    cards = json.loads((ROOT / "catalog/agents.json").read_text())["agents"]
    assert any(c["name"] == "small-router" and c["data"] == "synthetic" for c in cards)
