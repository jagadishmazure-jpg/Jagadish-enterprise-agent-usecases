"""GitHub-style issue triage: label, priority, owning team and likely duplicates (synthetic issues)."""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

LABELS = {
    "security": ["vulnerability", "xss", "csrf", "token leak", "leak", "injection", "cve", "auth bypass"],
    "bug": ["crash", "error", "exception", "broken", "fails", "regression", "500", "stack trace", "wrong"],
    "feature": ["add support", "feature request", "would be nice", "please add", "allow", "option to"],
    "docs": ["docs", "documentation", "readme", "typo", "example missing"],
    "question": ["how do i", "how to", "is it possible", "question", "?"],
}
TEAMS = {"security": "appsec", "bug": "core", "feature": "product", "docs": "devrel", "question": "support"}
EXISTING = [
    (101, "Login page crashes on submit with empty password"),
    (102, "Add support for dark mode in the dashboard"),
    (103, "Typo in README install section"),
    (104, "Export to CSV fails with 500 error for large reports"),
]


def words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower())) - {"the", "a", "in", "on", "with", "for", "to", "of", "and", "is"}


def jaccard(a: str, b: str) -> float:
    x, y = words(a), words(b)
    return len(x & y) / len(x | y) if x | y else 0.0


def triage(title: str, body: str) -> dict:
    text = f"{title} {body}".lower()
    scores = {lab: sum(text.count(k) for k in kws) for lab, kws in LABELS.items()}
    label = max(scores, key=lambda k: (scores[k], -list(LABELS).index(k)))
    if scores[label] == 0:
        label = "question"
    if label == "security" or re.search(r"data loss|outage|all users|production down", text):
        prio = "P0"
    elif label == "bug" and re.search(r"regression|crash|500", text):
        prio = "P1"
    elif label == "bug":
        prio = "P2"
    else:
        prio = "P3"
    dups = [{"issue": n, "similarity": round(j, 2)} for n, t in EXISTING if (j := jaccard(title, t)) >= 0.45]
    return {"label": label, "priority": prio, "team": TEAMS[label], "duplicates": dups}


ISSUES = [
    (("Login page crashes on submit with empty password", "Stack trace attached."), ("bug", "P1", [101])),
    (("Please add CSV import", "Feature request: allow bulk upload."), ("feature", "P3", [])),
    (("Stored XSS in comment field", "Script tags render in the feed. Possible token leak."), ("security", "P0", [])),
    (("How do I rotate API keys?", "Is it possible from the CLI?"), ("question", "P3", [])),
    (("Typo in README install section", "pip comand is misspelled"), ("docs", "P3", [103])),
    (("Export to CSV fails with 500 error on big reports", ""), ("bug", "P1", [104])),
    (("Totals are wrong on invoice page", "Rounding looks off by a cent."), ("bug", "P2", [])),
    (("Production down for all users after deploy", "Error on every page."), ("bug", "P0", [])),
    (("Dark mode for the dashboard", "Would be nice to add support for dark mode."), ("feature", "P3", [102])),
    (("Docs example missing for webhooks", ""), ("docs", "P3", [])),
    (("Regression: search broken since 2.3", "Worked in 2.2."), ("bug", "P1", [])),
    # Known miss kept visible: no keywords, so it falls back to 'question' though it is a bug report.
    (("Sidebar overlaps the chart on narrow screens", ""), ("bug", "P2", [])),
]


class IssueTriageAgent(Agent):
    META = {
        "name": "issue-triage",
        "title": "GitHub issue triage",
        "level": "Beginner",
        "tech": "Keyword classifier + Jaccard dedupe",
        "industry": "Software engineering",
        "tags": ["triage", "classification", "devops"],
        "summary": "Labels new issues, sets priority and owning team, and flags likely duplicates of open issues.",
        "guardrails": ["suggests labels only (no write access to the tracker)", "injection screen on issue text", "PII redaction", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"issues.read"}))

    def handle(self, ctx, payload):
        return ctx.tool("issues.read", triage, payload["title"], payload.get("body", ""))

    def demo(self):
        return {"title": ISSUES[2][0][0], "body": ISSUES[2][0][1]}

    def eval_cases(self):
        return [({"title": t, "body": b}, exp) for (t, b), exp in ISSUES]

    def score(self, res, expected):
        o = res["output"]
        return float((o["label"], o["priority"], [d["issue"] for d in o["duplicates"]]) == expected)


AGENT = IssueTriageAgent()
