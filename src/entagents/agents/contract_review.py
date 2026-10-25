"""Contract clause review against a negotiation playbook (synthetic contract text).

Each clause is classified, compared with the playbook position and given a risk level with the
reason. Final legal judgement stays with a lawyer; the output says so.
"""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

CLAUSE_TYPES = {  # order matters: the first match wins, so specific types come before "termination"
    "confidentiality": r"confidential",
    "liability": r"liabilit",
    "indemnity": r"indemnif",
    "termination": r"terminat",
    "payment": r"payment|invoice|net \d+",
    "governing_law": r"governed by|governing law",
    "auto_renewal": r"automatically renew|auto-renew",
}


def assess(kind: str, text: str) -> tuple[str, str]:
    t = text.lower()
    if kind == "liability":
        if "unlimited" in t:
            return "high", "unlimited liability; playbook caps at 12 months of fees"
        m = re.search(r"(\d+)\s*months", t)
        if m and int(m.group(1)) > 12:
            return "medium", f"cap of {m.group(1)} months exceeds the 12-month playbook cap"
        return "low", "cap within playbook"
    if kind == "indemnity":
        return ("high", "one-sided indemnity") if "mutual" not in t else ("low", "mutual indemnity")
    if kind == "termination":
        m = re.search(r"(\d+)\s*days", t)
        if "for convenience" in t and m and int(m.group(1)) < 30:
            return "medium", f"termination for convenience on {m.group(1)} days; playbook wants 30+"
        return "low", "termination terms acceptable"
    if kind == "payment":
        m = re.search(r"net\s*(\d+)", t)
        if m and int(m.group(1)) > 45:
            return "medium", f"net {m.group(1)} is longer than the net 45 playbook"
        return "low", "payment terms acceptable"
    if kind == "auto_renewal":
        m = re.search(r"(\d+)\s*days", t)
        return ("medium", "auto-renewal with notice under 60 days") if not m or int(m.group(1)) < 60 else ("low", "renewal notice adequate")
    if kind == "confidentiality":
        return ("medium", "no survival period") if "surviv" not in t else ("low", "confidentiality survives termination")
    return "low", "standard clause"


def review(contract: str) -> dict:
    clauses = [c.strip() for c in re.split(r"\n\s*\n|(?=\n\d+\.\s)", contract) if c.strip()]
    out = []
    for i, c in enumerate(clauses, 1):
        kind = next((k for k, p in CLAUSE_TYPES.items() if re.search(p, c, re.I)), "other")
        risk, why = assess(kind, c)
        out.append({"clause": i, "type": kind, "risk": risk, "reason": why})
    found = {o["type"] for o in out}
    missing = [k for k in ("liability", "confidentiality", "governing_law") if k not in found]
    return {"clauses": out, "missing_standard_clauses": missing, "note": "Decision support only; a lawyer signs off."}


SAMPLE = """1. Supplier's total liability is unlimited for any claim.

2. Customer shall indemnify Supplier against all third-party claims.

3. Either party may terminate for convenience with 10 days notice.

4. Payment is due net 60 from invoice date.

5. This agreement is governed by the laws of the State of New York."""

CASES = [
    ("Liability is capped at 12 months of fees.", [("liability", "low")]),
    ("Liability is capped at 24 months of fees.", [("liability", "medium")]),
    ("Total liability is unlimited.", [("liability", "high")]),
    ("Each party shall indemnify the other; this indemnity is mutual.", [("indemnity", "low")]),
    ("Customer shall indemnify Supplier for all losses.", [("indemnity", "high")]),
    ("Either party may terminate for convenience on 15 days notice.", [("termination", "medium")]),
    ("Invoices are payable net 30.", [("payment", "low")]),
    ("Payment terms are net 90.", [("payment", "medium")]),
    ("This contract will automatically renew unless notice is given 30 days before the end.", [("auto_renewal", "medium")]),
    ("Confidential information obligations survive termination for 3 years.", [("confidentiality", "low")]),
    (SAMPLE, [("liability", "high"), ("indemnity", "high"), ("termination", "medium"), ("payment", "medium"), ("governing_law", "low")]),
    # Known miss kept visible: "hold harmless" means indemnity but has no trigger word.
    ("Customer will hold Supplier harmless from all claims.", [("indemnity", "high")]),
]


class ContractReviewAgent(Agent):
    META = {
        "name": "contract-review",
        "title": "Contract clause review",
        "level": "Intermediate",
        "tech": "Clause classifier + playbook rules",
        "industry": "Legal",
        "tags": ["legal", "risk", "explainable", "human-in-the-loop"],
        "summary": "Splits a contract into clauses, compares each with a negotiation playbook and gives a risk level with the reason.",
        "guardrails": ["decision support only, lawyer signs off", "every risk has a stated reason", "flags missing standard clauses", "PII redaction", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"contract.parse"}))

    def handle(self, ctx, payload):
        return ctx.tool("contract.parse", review, payload["contract"])

    def demo(self):
        return {"contract": SAMPLE}

    def eval_cases(self):
        return [({"contract": c}, e) for c, e in CASES]

    def score(self, res, expected):
        return float([(c["type"], c["risk"]) for c in res["output"]["clauses"]] == expected)


AGENT = ContractReviewAgent()
