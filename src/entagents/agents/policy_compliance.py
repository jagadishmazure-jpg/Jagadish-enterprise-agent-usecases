"""Policy compliance check: evaluates system configurations against written controls.

Each finding names the control, the observed value and the expected value, so an auditor can
verify it without rerunning anything.
"""

from __future__ import annotations

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

CONTROLS = [
    ("PW-1", "password minimum length is at least 14", lambda c: c.get("password_min_length", 0) >= 14, "password_min_length", ">= 14"),
    ("MFA-1", "MFA enforced for all users", lambda c: c.get("mfa") == "all", "mfa", "all"),
    ("ENC-1", "storage encrypted at rest", lambda c: c.get("encryption_at_rest") is True, "encryption_at_rest", "true"),
    ("LOG-1", "audit logs kept 365 days or more", lambda c: c.get("log_retention_days", 0) >= 365, "log_retention_days", ">= 365"),
    ("NET-1", "no public admin ports", lambda c: not set(c.get("public_ports", [])) & {22, 3389}, "public_ports", "no 22 or 3389"),
    ("DATA-1", "data stays in approved regions", lambda c: set(c.get("regions", [])) <= {"us-east", "us-west"}, "regions", "subset of us-east, us-west"),
    ("BAK-1", "backups tested in the last 90 days", lambda c: c.get("days_since_restore_test", 999) <= 90, "days_since_restore_test", "<= 90"),
]


def check(config: dict) -> dict:
    findings = []
    for cid, desc, ok, key, want in CONTROLS:
        if key not in config:
            findings.append({"control": cid, "result": "unknown", "detail": f"{key} not provided", "expected": want})
        elif not ok(config):
            findings.append({"control": cid, "result": "fail", "detail": desc, "observed": config[key], "expected": want})
    fails = [f for f in findings if f["result"] == "fail"]
    return {
        "compliant": not findings,
        "fails": [f["control"] for f in fails],
        "unknown": [f["control"] for f in findings if f["result"] == "unknown"],
        "findings": findings,
        "controls_checked": len(CONTROLS),
    }


GOOD = {"password_min_length": 16, "mfa": "all", "encryption_at_rest": True, "log_retention_days": 400, "public_ports": [443], "regions": ["us-east"], "days_since_restore_test": 30}
CASES = [
    (GOOD, []),
    ({**GOOD, "password_min_length": 8}, ["PW-1"]),
    ({**GOOD, "mfa": "admins"}, ["MFA-1"]),
    ({**GOOD, "public_ports": [443, 22]}, ["NET-1"]),
    ({**GOOD, "regions": ["us-east", "eu-central"], "log_retention_days": 90}, ["LOG-1", "DATA-1"]),
    ({**GOOD, "encryption_at_rest": False, "days_since_restore_test": 200}, ["ENC-1", "BAK-1"]),
    ({**GOOD, "public_ports": [3389, 80], "mfa": "none", "password_min_length": 10}, ["PW-1", "MFA-1", "NET-1"]),
]


class PolicyAgent(Agent):
    META = {
        "name": "policy-compliance",
        "title": "Policy compliance check",
        "level": "Beginner",
        "tech": "Rules engine over configuration",
        "industry": "Governance, risk and compliance",
        "tags": ["compliance", "audit", "security", "explainable"],
        "summary": "Checks a system configuration against written controls and reports each failure with observed and expected values.",
        "guardrails": ["missing evidence reported as unknown, never as pass", "observed vs expected on every finding", "read-only", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"config.read"}))

    def handle(self, ctx, payload):
        return ctx.tool("config.read", check, payload["config"])

    def demo(self):
        return {"system": "billing-api", "config": {**GOOD, "public_ports": [443, 22], "log_retention_days": 30}}

    def eval_cases(self):
        cases = [({"config": c}, (e, [])) for c, e in CASES]
        cases.append(({"config": {k: v for k, v in GOOD.items() if k != "mfa"}}, ([], ["MFA-1"])))
        return cases

    def score(self, res, expected):
        o = res["output"]
        return float((o["fails"], o["unknown"]) == expected)


AGENT = PolicyAgent()
