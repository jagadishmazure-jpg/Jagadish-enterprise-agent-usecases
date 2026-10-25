from entagents.agents import doc_writer, news_briefing, recipe_rec, travel_planner, unit_test_gen
from entagents.framework.runtime import Runtime


def test_unsafe_code_refused_before_execution():
    for src in ["import os\n", "import subprocess\n", "def f():\n    open('x','w')\n", "x = ().__class__\n"]:
        assert not unit_test_gen.safe_to_run(src)[0]


def test_generated_tests_pass_then_kill_mutant():
    src, (a, b) = unit_test_gen.SAMPLES[4]
    tests = unit_test_gen.generate(src)
    assert tests.count("def test_") == 3
    assert unit_test_gen.run_tests(src, tests) == {"passed": 3, "failed": 0}
    assert unit_test_gen.run_tests(src.replace(a, b), tests)["failed"] >= 1


def test_unit_test_gen_known_miss_weak_examples():
    src, (a, b) = unit_test_gen.SAMPLES[5]
    assert unit_test_gen.run_tests(src.replace(a, b), unit_test_gen.generate(src))["failed"] == 0


def test_doc_writer_signature_and_gaps():
    o = doc_writer.write_docs("def f(a: int, b: int = 2) -> int:\n    return a\n")
    assert "f(a: int, b: int = 2) -> int" in o["markdown"] and o["gaps"] == ["f"]


def test_news_window_and_injection():
    o = news_briefing.brief("2026-10-20", "2026-10-24")
    assert "n8" in o["quarantined"] and all("[n" in b for v in o["sections"].values() for b in v)
    assert news_briefing.brief("2026-11-01", "2026-11-02")["sections"] == {}


def test_news_bad_date_fails_closed():
    r = Runtime().run(news_briefing.AGENT, {"since": "yesterday", "until": "2026-10-24"})
    assert r["status"] == "error" and "yesterday" not in r["reason"]


def test_travel_never_exceeds_budget():
    for budget in range(700, 2001, 50):
        o = travel_planner.plan("lisbon", 4, budget, ["history", "food", "music", "outdoors"])
        assert not o["feasible"] or o["total"] <= budget


def test_travel_booking_needs_approval():
    rt = Runtime()
    r = rt.run(travel_planner.AGENT, travel_planner.AGENT.demo())
    assert r["pending_approvals"] == [0] and not rt.approvals.executed(0)


def test_recipe_allergen_is_hard_filter():
    for allergy in ["gluten", "dairy", "egg", "soy", "peanut", "shellfish"]:
        o = recipe_rec.recommend([i for _, ing, _, _ in recipe_rec.RECIPES for i in ing], [allergy], k=10)
        blocked = {r[0] for r in recipe_rec.RECIPES if allergy in r[2]}
        assert not blocked & {t["recipe"] for t in o["top"]}
