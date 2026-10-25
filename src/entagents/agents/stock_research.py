"""Stock research on SIMULATED prices: returns, volatility, drawdown and trend, never advice.

Prices come from a seeded random walk for fictional tickers. Every report says so, and the agent
refuses buy/sell recommendations.
"""

from __future__ import annotations

import math
import random
import re
import statistics as st

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

DISCLAIMER = "Simulated prices for fictional tickers. Educational analysis only, not investment advice."
TICKERS = {"LUMA": (0.0006, 0.012, 11), "ORCH": (-0.0004, 0.020, 12), "TIDE": (0.0002, 0.008, 13), "KILN": (0.0010, 0.030, 14)}
ADVICE = re.compile(r"(?i)\b(should i (buy|sell)|buy or sell|price target|will it go up|guaranteed return)\b")


def prices(ticker: str, days: int = 252) -> list[float]:
    mu, sigma, seed = TICKERS[ticker]
    rng = random.Random(seed)
    p = [100.0]
    for _ in range(days - 1):
        p.append(p[-1] * math.exp(mu - sigma**2 / 2 + sigma * rng.gauss(0, 1)))
    return [round(x, 4) for x in p]


def metrics(p: list[float]) -> dict:
    r = [math.log(b / a) for a, b in zip(p, p[1:], strict=False)]
    peak, mdd = p[0], 0.0
    for x in p:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    sma50, sma200 = st.fmean(p[-50:]), st.fmean(p[-200:])
    return {
        "total_return_pct": round((p[-1] / p[0] - 1) * 100, 2),
        "annual_vol_pct": round(st.stdev(r) * math.sqrt(252) * 100, 2),
        "max_drawdown_pct": round(mdd * 100, 2),
        "trend": "up (50-day above 200-day)" if sma50 > sma200 else "down (50-day below 200-day)",
    }


def research(question: str, tickers: list[str]) -> dict:
    if ADVICE.search(question):
        return {"refused": "I can describe simulated history but do not give buy/sell advice.", "disclaimer": DISCLAIMER}
    unknown = [t for t in tickers if t not in TICKERS]
    if unknown:
        return {"error": f"unknown tickers {unknown}; available: {sorted(TICKERS)}", "disclaimer": DISCLAIMER}
    rows = {t: metrics(prices(t)) for t in tickers}
    return {"metrics": rows, "lowest_volatility": min(rows, key=lambda t: rows[t]["annual_vol_pct"]), "disclaimer": DISCLAIMER}


def _gold(t: str) -> dict:
    """Independent recomputation for the eval (simple returns based)."""
    p = prices(t)
    return {"total": round((p[-1] / p[0] - 1) * 100, 2)}


CASES = [
    ({"question": "Compare risk", "tickers": ["LUMA", "TIDE"]}, "TIDE"),
    ({"question": "Volatility summary", "tickers": ["ORCH", "KILN", "LUMA"]}, "LUMA"),
    ({"question": "Profile", "tickers": ["KILN"]}, "KILN"),
    ({"question": "Should I buy LUMA?", "tickers": ["LUMA"]}, "refuse"),
    ({"question": "What is the price target for KILN", "tickers": ["KILN"]}, "refuse"),
    ({"question": "Compare", "tickers": ["ACME"]}, "error"),
    ({"question": "All four", "tickers": ["LUMA", "ORCH", "TIDE", "KILN"]}, "TIDE"),
]


class StockResearchAgent(Agent):
    META = {
        "name": "stock-research",
        "title": "Stock research (simulated data)",
        "level": "Intermediate",
        "tech": "Seeded random walk + risk metrics",
        "industry": "Financial services",
        "tags": ["finance", "analytics", "simulated-data", "refusal"],
        "summary": "Computes return, volatility, drawdown and trend for fictional tickers on simulated prices, and refuses to give buy or sell advice.",
        "guardrails": ["simulated-data disclaimer on every answer", "refuses buy/sell and price-target questions", "numbers computed, not generated", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"prices.read"}))

    def handle(self, ctx, payload):
        return ctx.tool("prices.read", research, payload["question"], payload["tickers"])

    def demo(self):
        return {"question": "Compare risk", "tickers": ["LUMA", "TIDE", "KILN"]}

    def eval_cases(self):
        return CASES

    def score(self, res, expected):
        o = res["output"]
        if expected == "refuse":
            return float("refused" in o and "metrics" not in o)
        if expected == "error":
            return float("error" in o)
        ok_total = all(o["metrics"][t]["total_return_pct"] == _gold(t)["total"] for t in o["metrics"])
        return float(o["lowest_volatility"] == expected and ok_total and o["disclaimer"] == DISCLAIMER)


AGENT = StockResearchAgent()
