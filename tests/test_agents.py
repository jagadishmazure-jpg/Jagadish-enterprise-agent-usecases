"""Every agent: metadata for the catalog, demo run, task eval threshold and shared safety checks."""

import pytest

from entagents.framework.evals import safety_eval, task_eval
from entagents.framework.runtime import Runtime
from entagents.registry import agents

AGENTS = agents()
IDS = [a.META["name"] for a in AGENTS]
FIELDS = {"name", "title", "level", "tech", "industry", "tags", "summary", "guardrails"}


@pytest.mark.parametrize("agent", AGENTS, ids=IDS)
def test_metadata_complete(agent):
    assert FIELDS <= set(agent.META) and agent.META["level"] in {"Beginner", "Intermediate", "Advanced"} and agent.META["tags"]


@pytest.mark.parametrize("agent", AGENTS, ids=IDS)
def test_demo_runs(agent):
    r = Runtime().run(agent, agent.demo())
    assert r["status"] == "ok" and r["tokens"] > 0


@pytest.mark.parametrize("agent", AGENTS, ids=IDS)
def test_task_eval_meets_floor(agent):
    r = task_eval(agent)
    assert r["cases"] >= 5 and r["score"] >= 0.8 and r["audit_chain_ok"]


@pytest.mark.parametrize("agent", AGENTS, ids=IDS)
def test_injection_blocked(agent):
    assert safety_eval(agent)["injection_blocked"]


@pytest.mark.parametrize("agent", AGENTS, ids=IDS)
def test_no_pii_leak(agent):
    assert not safety_eval(agent)["pii_leaked"]


def test_names_unique():
    assert len(set(IDS)) == len(IDS)
