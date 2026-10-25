"""Incident summary from raw logs: timeline, first error, likely trigger, impact window (synthetic logs)."""

from __future__ import annotations

import datetime as dt
import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

LINE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s+(INFO|WARN|ERROR)\s+(\S+)\s+(.*)$")
TRIGGERS = [("deploy", r"deploy(ed)?\s+v?[\d.]+"), ("config", r"config (change|update)"), ("dependency", r"(timeout|refused).*(db|database|cache|upstream)")]


def summarise(log: str) -> dict:
    ev = [m.groups() for ln in log.splitlines() if (m := LINE.match(ln.strip()))]
    if not ev:
        return {"summary": "no parseable log lines", "timeline": []}
    errs = [e for e in ev if e[1] == "ERROR"]
    if not errs:
        return {"summary": "no errors found", "timeline": [], "first_error": None}
    first = errs[0]
    before = [e for e in ev if e[0] <= first[0]]
    trigger = None
    for e in reversed(before):
        for kind, pat in TRIGGERS:
            if re.search(pat, e[3], re.I):
                trigger = {"kind": kind, "at": e[0], "service": e[2], "line": e[3]}
                break
        if trigger:
            break
    recov = next((e for e in ev if e[0] > errs[-1][0] and re.search(r"recovered|healthy|rolled back", e[3], re.I)), None)
    t = lambda s: dt.datetime.strptime(s, "%H:%M:%S")  # noqa: E731
    end = recov[0] if recov else errs[-1][0]
    services = sorted({e[2] for e in errs})
    return {
        "first_error": {"at": first[0], "service": first[2], "line": first[3]},
        "likely_trigger": trigger,
        "error_count": len(errs),
        "services_affected": services,
        "impact_minutes": round((t(end) - t(first[0])).seconds / 60, 1),
        "recovered": bool(recov),
        "timeline": [f"{e[0]} {e[1]} {e[2]}: {e[3]}" for e in ev if e[1] != "INFO" or e is recov or (trigger and e[0] == trigger["at"])],
        "note": "Likely trigger is a correlation in time, not a confirmed root cause.",
    }


LOG_A = """09:00:00 INFO api deployed v2.4.1
09:02:10 WARN api p95 latency 900ms
09:03:00 ERROR api 500 on /checkout
09:03:30 ERROR payments upstream timeout
09:10:00 INFO api rolled back to v2.4.0
09:12:00 INFO api healthy"""
LOG_B = """14:00:00 INFO auth config update: token ttl 5m
14:01:00 ERROR auth token validation failed
14:01:05 ERROR web login failed for user
14:20:00 INFO auth recovered after config revert"""
LOG_C = """02:00:00 INFO worker started
02:30:00 WARN worker connection refused by db
02:30:01 ERROR worker job failed: db connection refused"""
LOG_D = """10:00:00 INFO api ok\n10:05:00 INFO api ok"""

CASES = [
    (LOG_A, ("deploy", "09:03:00", 7.0, True)),
    (LOG_B, ("config", "14:01:00", 19.0, True)),
    (LOG_C, ("dependency", "02:30:01", 0.0, False)),
    (LOG_D, None),
    (LOG_A.replace("deployed v2.4.1", "started"), (None, "09:03:00", 7.0, True)),
]


class IncidentAgent(Agent):
    META = {
        "name": "incident-summary",
        "title": "Incident summary",
        "level": "Intermediate",
        "tech": "Log parser + temporal correlation",
        "industry": "IT operations",
        "tags": ["sre", "observability", "summarisation"],
        "summary": "Turns raw logs into a timeline with the first error, the likely trigger, affected services and impact window.",
        "guardrails": ["trigger labelled as correlation, not root cause", "summary built only from log lines", "PII redaction on log text", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"logs.read"}))

    def handle(self, ctx, payload):
        return ctx.tool("logs.read", summarise, payload["log"])

    def demo(self):
        return {"log": LOG_A}

    def eval_cases(self):
        return [({"log": lg}, e) for lg, e in CASES]

    def score(self, res, expected):
        o = res["output"]
        if expected is None:
            return float(o.get("first_error") is None)
        kind, at, mins, rec = expected
        got_kind = o["likely_trigger"]["kind"] if o["likely_trigger"] else None
        return float((got_kind, o["first_error"]["at"], o["impact_minutes"], o["recovered"]) == (kind, at, mins, rec))


AGENT = IncidentAgent()
