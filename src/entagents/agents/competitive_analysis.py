"""Competitive analysis in steps: plan dimensions, gather cited facts per company, build a matrix,
then summarise who leads on each dimension. Cells with no source say so instead of guessing.
All companies are fictional.
"""

from __future__ import annotations

import re

from ..framework.grounding import BM25, Doc
from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

FACTS = [
    Doc("c1", "Ferngate Analytics charges 49 dollars per user per month for its standard plan.", "Ferngate Analytics pricing"),
    Doc("c2", "Ferngate Analytics offers 120 data connectors.", "Ferngate Analytics connectors"),
    Doc("c3", "Ferngate Analytics support responds within 24 hours on standard plans.", "Ferngate Analytics support"),
    Doc("c4", "Stillwater Metrics charges 35 dollars per user per month.", "Stillwater Metrics pricing"),
    Doc("c5", "Stillwater Metrics offers 60 data connectors.", "Stillwater Metrics connectors"),
    Doc("c6", "Stillwater Metrics support responds within 4 hours for all customers.", "Stillwater Metrics support"),
    Doc("c7", "Orchard Signal charges 59 dollars per user per month.", "Orchard Signal pricing"),
    Doc("c8", "Orchard Signal offers 200 data connectors.", "Orchard Signal connectors"),
    Doc("c9", "Brightmoss BI offers 90 data connectors.", "Brightmoss BI connectors"),
    Doc("c10", "Brightmoss BI support responds within 12 hours.", "Brightmoss BI support"),
]
COMPANIES = ["Ferngate Analytics", "Stillwater Metrics", "Orchard Signal", "Brightmoss BI"]
DIMENSIONS = {
    "price_per_user": (r"(\d+) dollars per user", "lower"),
    "connectors": (r"(\d+) data connectors", "higher"),
    "support_hours": (r"within (\d+) hours", "lower"),
}
QUERIES = {"price_per_user": "charges dollars per user month pricing", "connectors": "data connectors", "support_hours": "support responds hours"}


def analyse(companies: list[str]) -> dict:
    index = BM25(FACTS)
    steps, matrix = [f"plan: {len(DIMENSIONS)} dimensions x {len(companies)} companies"], {}
    for co in companies:
        row = {}
        for dim, (pat, _) in DIMENSIONS.items():
            hit = next((d for d, _ in index.search(f"{co} {QUERIES[dim]}", k=10) if d.title.startswith(co) and re.search(pat, d.text)), None)
            row[dim] = {"value": int(re.search(pat, hit.text).group(1)), "cite": hit.id} if hit else {"value": None, "cite": None, "note": "no source"}
        matrix[co] = row
    steps.append(f"gather: {sum(v['cite'] is not None for r in matrix.values() for v in r.values())} cited cells")
    leaders = {}
    for dim, (_, better) in DIMENSIONS.items():
        vals = {co: matrix[co][dim]["value"] for co in companies if matrix[co][dim]["value"] is not None}
        if vals:
            leaders[dim] = (min if better == "lower" else max)(vals, key=vals.get)
    steps.append("compare: leaders chosen only among cited cells")
    gaps = [f"{co}: {dim}" for co in companies for dim in DIMENSIONS if matrix[co][dim]["value"] is None]
    return {"steps": steps, "matrix": matrix, "leaders": leaders, "gaps": gaps}


CASES = [
    (COMPANIES, ({"price_per_user": "Stillwater Metrics", "connectors": "Orchard Signal", "support_hours": "Stillwater Metrics"}, ["Orchard Signal: support_hours", "Brightmoss BI: price_per_user"])),
    (["Ferngate Analytics", "Orchard Signal"], ({"price_per_user": "Ferngate Analytics", "connectors": "Orchard Signal", "support_hours": "Ferngate Analytics"}, ["Orchard Signal: support_hours"])),
    (["Brightmoss BI"], ({"connectors": "Brightmoss BI", "support_hours": "Brightmoss BI"}, ["Brightmoss BI: price_per_user"])),
    (["Ferngate Analytics", "Brightmoss BI"], ({"price_per_user": "Ferngate Analytics", "connectors": "Ferngate Analytics", "support_hours": "Brightmoss BI"}, ["Brightmoss BI: price_per_user"])),
    (["Stillwater Metrics", "Brightmoss BI"], ({"price_per_user": "Stillwater Metrics", "connectors": "Brightmoss BI", "support_hours": "Stillwater Metrics"}, ["Brightmoss BI: price_per_user"])),
]


class CompetitiveAgent(Agent):
    META = {
        "name": "competitive-analysis",
        "title": "Competitive analysis (multi-step)",
        "level": "Advanced",
        "tech": "Plan, retrieve, extract, compare",
        "industry": "Strategy and product",
        "tags": ["multi-step", "research", "citations", "fictional-companies"],
        "summary": "Plans comparison dimensions, gathers cited facts for each fictional company, builds a matrix and names leaders only where sources exist.",
        "guardrails": ["every matrix cell cites a fact or says no source", "leaders picked only from cited cells", "fictional companies only", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"facts.search"}))
    HARD = True

    def handle(self, ctx, payload):
        return ctx.tool("facts.search", analyse, payload["companies"])

    def demo(self):
        return {"companies": COMPANIES}

    def eval_cases(self):
        return [({"companies": c}, e) for c, e in CASES]

    def score(self, res, expected):
        o = res["output"]
        leaders, gaps = expected
        cites_ok = all(v["cite"] is None or v["cite"] in {d.id for d in FACTS} for r in o["matrix"].values() for v in r.values())
        return float(o["leaders"] == leaders and sorted(o["gaps"]) == sorted(gaps) and cites_ok)


AGENT = CompetitiveAgent()
