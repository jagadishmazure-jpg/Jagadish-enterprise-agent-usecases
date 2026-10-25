"""Email drafting with a human sign-off: the agent writes, a person approves, only then is it sent."""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

OPENERS = {
    "follow-up": "Following up on our conversation, here are the next steps.",
    "decline": "Thank you for thinking of us. We will not be able to take this on right now.",
    "schedule": "Could we find time to meet? A few options are below.",
    "thanks": "Thank you for your help this week.",
}
BANNED = re.compile(r"(?i)\b(guarantee[sd]?|promise[sd]?|100% sure|risk[- ]free)\b")


def draft(intent: str, to_name: str, points: list[str], sender: str) -> dict:
    if intent not in OPENERS:
        return {"error": f"unknown intent '{intent}'", "allowed": sorted(OPENERS)}
    clean = [BANNED.sub("[removed: commitment wording]", p) for p in points]
    body = "\n".join([f"Hi {to_name},", "", OPENERS[intent], *[f"- {p}" for p in clean], "", "Best regards,", sender])
    subject = {"follow-up": "Next steps", "decline": "Re: your request", "schedule": "Time to meet?", "thanks": "Thank you"}[intent]
    return {"subject": subject, "body": body, "flags": sum(1 for p in points if BANNED.search(p))}


CASES = [
    ({"intent": "follow-up", "to_name": "Ravi", "points": ["Share the pilot plan by Friday", "Confirm data access"]}, ("Next steps", 0)),
    ({"intent": "decline", "to_name": "Mara", "points": ["We can revisit in Q2"]}, ("Re: your request", 0)),
    ({"intent": "schedule", "to_name": "Jon", "points": ["Tue 10:00", "Wed 14:00"]}, ("Time to meet?", 0)),
    ({"intent": "thanks", "to_name": "Ade", "points": ["The demo went well"]}, ("Thank you", 0)),
    ({"intent": "follow-up", "to_name": "Lia", "points": ["We guarantee a 40% saving"]}, ("Next steps", 1)),
    ({"intent": "follow-up", "to_name": "Kai", "points": ["This is risk-free", "We promise delivery in May"]}, ("Next steps", 2)),
    ({"intent": "apology", "to_name": "Zed", "points": ["x"]}, (None, None)),
    ({"intent": "schedule", "to_name": "Ana", "points": ["Thu 09:30"]}, ("Time to meet?", 0)),
]


class EmailDraftAgent(Agent):
    META = {
        "name": "email-draft",
        "title": "Email drafting with human sign-off",
        "level": "Beginner",
        "tech": "Templates + wording rules",
        "industry": "Sales and customer success",
        "tags": ["drafting", "human-in-the-loop", "communications"],
        "summary": "Drafts short business emails from bullet points, removes commitment wording, and waits for a person to approve sending.",
        "guardrails": ["send is a risky action that needs a named approver", "guarantee/promise wording removed and flagged", "recipient address redacted in logs", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"email.compose", "email.send"}), risky=frozenset({"email.send"}))

    def handle(self, ctx, payload):
        d = ctx.tool("email.compose", draft, payload["intent"], payload["to_name"], payload["points"], payload.get("sender", "Account team"))
        if "error" in d:
            return d
        pid = ctx.request_approval("email.send", {"subject": d["subject"], "to": payload.get("to_email", "")})
        return {**d, "send_status": f"waiting for approval (#{pid})"}

    def demo(self):
        return {"intent": "follow-up", "to_name": "Ravi", "to_email": "ravi@client.example", "points": ["Share the pilot plan by Friday", "We guarantee results"]}

    def eval_cases(self):
        return CASES

    def score(self, res, expected):
        o = res["output"]
        subj, flags = expected
        if subj is None:
            return float("error" in o and not res["pending_approvals"])
        return float(o["subject"] == subj and o["flags"] == flags and not BANNED.search(o["body"]) and len(res["pending_approvals"]) == 1)


AGENT = EmailDraftAgent()
