"""Ordered list of agents. Batches are added here as they are built."""

from __future__ import annotations

import importlib

BATCHES = [
    ["sql_nl", "code_review", "resume_match", "csv_analysis", "meeting_actions"],
    ["issue_triage", "doc_qa", "web_research", "email_draft", "support_escalation"],
    ["unit_test_gen", "doc_writer", "news_briefing", "travel_planner", "recipe_rec"],
]


def modules() -> list[str]:
    return [m for b in BATCHES for m in b]


def agents():
    return [importlib.import_module(f"entagents.agents.{m}").AGENT for m in modules()]


def by_name(name: str):
    for a in agents():
        if a.META["name"] == name:
            return a
    raise KeyError(name)
