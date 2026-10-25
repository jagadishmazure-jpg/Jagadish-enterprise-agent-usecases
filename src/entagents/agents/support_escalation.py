"""Customer support with escalation: answer from the help center with a citation, or hand to a person.

Escalation rules are explicit (legal threat, high-value refund, repeated anger, unknown intent),
so a customer is never stuck in a loop with the bot.
"""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

KB = {
    "kb-shipping": "Standard shipping takes 3 to 5 business days. Tracking links are emailed at dispatch.",
    "kb-returns": "Items can be returned within 30 days in original condition for a full refund.",
    "kb-password": "Reset your password from the sign-in page using Forgot password. Links expire after 1 hour.",
    "kb-billing": "Invoices are available under Account, then Billing. Charges appear within 2 days.",
}
INTENTS = {
    "kb-shipping": ["shipping", "delivery", "tracking", "where is my order", "arrive"],
    "kb-returns": ["return", "refund", "send back"],
    "kb-password": ["password", "log in", "login", "locked out", "sign in"],
    "kb-billing": ["invoice", "charge", "billing", "charged"],
}
ANGRY = ["ridiculous", "furious", "worst", "unacceptable", "angry", "terrible"]
LEGAL = re.compile(r"(?i)\b(lawyer|attorney|sue|lawsuit|legal action|regulator)\b")


def decide(msg: str, prior_contacts: int = 0) -> dict:
    low = msg.lower()
    anger = sum(w in low for w in ANGRY)
    if LEGAL.search(msg):
        return {"action": "escalate", "reason": "legal", "queue": "legal-review"}
    amt = [float(x.replace(",", "")) for x in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)", msg)]
    intent = max(INTENTS, key=lambda k: sum(w in low for w in INTENTS[k]))
    if not any(w in low for w in INTENTS[intent]):
        return {"action": "escalate", "reason": "unknown-intent", "queue": "tier-1"}
    if intent == "kb-returns" and amt and max(amt) > 500:
        return {"action": "escalate", "reason": "high-value-refund", "queue": "tier-2"}
    if anger and prior_contacts >= 2:
        return {"action": "escalate", "reason": "repeat-frustration", "queue": "tier-2"}
    return {"action": "answer", "reply": KB[intent], "citation": intent, "sentiment": "negative" if anger else "neutral"}


TICKETS = [
    ("Where is my order? It has not arrived.", 0, "answer:kb-shipping"),
    ("I want to return a jacket.", 0, "answer:kb-returns"),
    ("I'm locked out and can't log in", 0, "answer:kb-password"),
    ("Why was I charged twice on my invoice?", 0, "answer:kb-billing"),
    ("Refund my $899 laptop now", 0, "escalate:high-value-refund"),
    ("Refund the $40 mug please", 0, "answer:kb-returns"),
    ("This is ridiculous, delivery is late again", 3, "escalate:repeat-frustration"),
    ("This is ridiculous, delivery is late", 0, "answer:kb-shipping"),
    ("My lawyer will contact you about this charge", 0, "escalate:legal"),
    ("Do you sponsor local football teams?", 0, "escalate:unknown-intent"),
    ("Tracking link please", 1, "answer:kb-shipping"),
    ("I will report you to the regulator", 0, "escalate:legal"),
]


class SupportAgent(Agent):
    META = {
        "name": "support-escalation",
        "title": "Support with escalation",
        "level": "Intermediate",
        "tech": "Intent rules + help-center lookup",
        "industry": "Customer service",
        "tags": ["support", "escalation", "citations", "human-handoff"],
        "summary": "Answers routine tickets from the help center with a citation and hands legal, high-value or repeat-frustration cases to people.",
        "guardrails": ["answers only from help-center articles (cited)", "explicit escalation rules", "no refunds issued by the bot", "PII redaction", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"kb.lookup"}))

    def handle(self, ctx, payload):
        return ctx.tool("kb.lookup", decide, payload["message"], int(payload.get("prior_contacts", 0)))

    def demo(self):
        return {"message": "Where is my order? It has not arrived.", "prior_contacts": 0}

    def eval_cases(self):
        return [({"message": m, "prior_contacts": p}, e) for m, p, e in TICKETS]

    def score(self, res, expected):
        o = res["output"]
        got = f"answer:{o['citation']}" if o["action"] == "answer" else f"escalate:{o['reason']}"
        return float(got == expected)


AGENT = SupportAgent()
