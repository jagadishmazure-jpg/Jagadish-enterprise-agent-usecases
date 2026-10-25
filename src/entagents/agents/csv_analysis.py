"""Questions over a CSV file: summaries, group-by means, correlation and outliers (synthetic data).

Numbers come from code, never from free text, and every answer names the column and row count used.
"""

from __future__ import annotations

import csv
import io
import math
import random
import re
import statistics as st

from ..framework.grounding import IDK
from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent


def sample_csv(seed: int = 3, n: int = 120) -> str:
    """Synthetic store-day rows for a fictional grocer, 'Maple Lantern Markets'."""
    rng = random.Random(seed)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["store", "visitors", "basket", "sales"])
    for i in range(n):
        store = rng.choice(["A", "B", "C"])
        v = rng.randint(200, 900)
        b = round(rng.gauss(32 + (5 if store == "C" else 0), 4), 2)
        s = round(v * b * rng.uniform(0.9, 1.1), 2)
        if i == 17:
            s *= 6  # planted outlier
        w.writerow([store, v, b, round(s, 2)])
    return buf.getvalue()


def load(text: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except ValueError:
                pass
    return rows


def pearson(x: list[float], y: list[float]) -> float:
    mx, my = st.fmean(x), st.fmean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    return num / math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))


def analyse(rows: list[dict], q: str) -> dict:
    s = q.lower()
    cols = list(rows[0])
    num = [c for c in cols if isinstance(rows[0][c], float)]
    named = [c for c in cols if re.search(rf"\b{c}\b", s)]
    if "correlat" in s and len([c for c in named if c in num]) >= 2:
        a, b = [c for c in named if c in num][:2]
        return {"kind": "correlation", "columns": [a, b], "value": round(pearson([r[a] for r in rows], [r[b] for r in rows]), 4), "rows": len(rows)}
    if ("average" in s or "mean" in s) and " by " in s:
        target = next((c for c in named if c in num), None)
        by = next((c for c in named if c not in num), None)
        if target and by:
            groups: dict[str, list[float]] = {}
            for r in rows:
                groups.setdefault(r[by], []).append(r[target])
            return {"kind": "group_mean", "columns": [target, by], "value": {k: round(st.fmean(v), 2) for k, v in sorted(groups.items())}, "rows": len(rows)}
    if "outlier" in s:
        c = next((c for c in named if c in num), None)
        if c:
            xs = [r[c] for r in rows]
            med = st.median(xs)
            mad = st.median(abs(x - med) for x in xs) or 1.0
            idx = [i for i, x in enumerate(xs) if abs(x - med) / (1.4826 * mad) > 5]
            return {"kind": "outliers", "columns": [c], "value": idx, "rows": len(rows)}
    if "summar" in s or "describe" in s:
        c = next((c for c in named if c in num), None)
        if c:
            xs = [r[c] for r in rows]
            return {"kind": "summary", "columns": [c], "value": {"mean": round(st.fmean(xs), 2), "median": round(st.median(xs), 2), "min": min(xs), "max": max(xs)}, "rows": len(rows)}
    return {"kind": "unknown", "value": IDK}


class CsvAgent(Agent):
    META = {
        "name": "csv-analysis",
        "title": "CSV data analysis",
        "level": "Beginner",
        "tech": "Python csv + statistics",
        "industry": "Retail",
        "tags": ["analytics", "tabular", "abstention"],
        "summary": "Answers questions about a CSV with computed statistics and states which columns and rows were used.",
        "guardrails": ["numbers computed, never generated", "read-only file tool", "abstains on unsupported questions", "PII redaction", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"csv.read"}))

    def handle(self, ctx, payload):
        rows = ctx.tool("csv.read", load, payload.get("csv") or sample_csv())
        return analyse(rows, payload["question"])

    def demo(self):
        return {"question": "Average basket by store"}

    def eval_cases(self):
        rows = load(sample_csv())
        sales = [r["sales"] for r in rows]
        g = {k: round(st.fmean([r["basket"] for r in rows if r["store"] == k]), 2) for k in "ABC"}
        return [
            ({"question": "Average basket by store"}, g),
            ({"question": "mean basket by store please"}, g),
            ({"question": "Correlation between visitors and sales"}, round(st.correlation([r["visitors"] for r in rows], sales), 4)),
            ({"question": "Find outliers in sales"}, [17]),
            ({"question": "Summarize sales"}, {"mean": round(st.fmean(sales), 2), "median": round(st.median(sales), 2), "min": min(sales), "max": max(sales)}),
            ({"question": "Describe visitors"}, None),
            ({"question": "Which store has the nicest staff?"}, IDK),
        ]

    def score(self, res, expected):
        v = res["output"]["value"]
        if expected is None:  # check against an independent computation
            xs = [r["visitors"] for r in load(sample_csv())]
            return float(v["mean"] == round(st.fmean(xs), 2))
        return float(v == expected)


AGENT = CsvAgent()
