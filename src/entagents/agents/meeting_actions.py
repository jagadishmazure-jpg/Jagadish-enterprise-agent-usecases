"""Meeting notes into action items: owner, task and due date (synthetic notes).

Only explicit commitments become actions. Vague remarks ("we should think about...") are not
turned into tasks, so the list stays short and trustworthy.
"""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

DUE = r"(?i:\s+(?:by|before|on)\s+(?P<due>monday|tuesday|wednesday|thursday|friday|eod|end of (?:day|week|month)|next week|\d{4}-\d{2}-\d{2}))?"
PATTERNS = [
    re.compile(r"^\s*(?:action|ai|todo)\s*[:\-]\s*(?P<owner>[A-Z][a-z]+)\s+(?:to|will)\s+(?P<task>.+?)" + DUE + r"\s*\.?$", re.I),
    re.compile(r"^\s*@(?P<owner>[A-Za-z]+)\s+(?:to\s+)?(?P<task>.+?)" + DUE + r"\s*\.?$", re.I),
    re.compile(r"^\s*(?P<owner>[A-Z][a-z]+)\s+(?:will|agreed to|is going to|owns)\s+(?P<task>.+?)" + DUE + r"\s*\.?$"),
]


def extract(notes: str) -> list[dict]:
    items = []
    for line in notes.splitlines():
        for p in PATTERNS:
            m = p.match(line.strip("-* "))
            if m:
                items.append({"owner": m["owner"].capitalize(), "task": m["task"].strip().rstrip("."), "due": (m["due"] or "unspecified").lower()})
                break
    return items


NOTES = [
    ("Sync on launch\nPriya will update the pricing page by Friday.\nWe should think about a rebrand.\nAction: Tom to email the vendor list.", [("Priya", "friday"), ("Tom", "unspecified")]),
    ("@lena draft the QBR deck by next week\n- Marco agreed to fix the login bug by eod", [("Lena", "next week"), ("Marco", "eod")]),
    ("Discussed hiring. Nothing decided.\nMaybe revisit in Q3.", []),
    ("TODO: Sam to rerun the forecast by 2026-11-03", [("Sam", "2026-11-03")]),
    ("* Ravi owns the incident postmortem by Monday\n* Ana will book the venue", [("Ravi", "monday"), ("Ana", "unspecified")]),
    ("AI - Chen will review the contract by end of week", [("Chen", "end of week")]),
    ("Team felt good about the demo.\nJo said the numbers look odd.", []),
    ("@kofi to share the dashboard link\nLee is going to update the runbook by Thursday", [("Kofi", "unspecified"), ("Lee", "thursday")]),
    ("Bea will ping finance on the budget before Tuesday.", [("Bea", "tuesday")]),
    # Known miss kept visible: passive voice hides the owner.
    ("The SLA doc will be updated by Wednesday by Nora.", [("Nora", "wednesday")]),
]


class MeetingAgent(Agent):
    META = {
        "name": "meeting-actions",
        "title": "Meeting notes to action items",
        "level": "Beginner",
        "tech": "Pattern extractor",
        "industry": "Productivity",
        "tags": ["summarisation", "extraction", "workflow"],
        "summary": "Turns raw meeting notes into owner / task / due-date items and skips vague remarks.",
        "guardrails": ["explicit commitments only", "PII redaction", "injection screen", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"notes.extract"}))

    def handle(self, ctx, payload):
        return {"actions": ctx.tool("notes.extract", extract, payload["notes"])}

    def demo(self):
        return {"notes": NOTES[0][0] + "\n" + NOTES[1][0]}

    def eval_cases(self):
        return [({"notes": n}, exp) for n, exp in NOTES]

    def score(self, res, expected):
        got = [(a["owner"], a["due"]) for a in res["output"]["actions"]]
        return float(got == expected)


AGENT = MeetingAgent()
