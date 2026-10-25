---
name: stock-research
title: Stock research (simulated data)
level: Intermediate
tech: Seeded random walk + risk metrics
industry: Financial services
tags: [finance, analytics, simulated-data, refusal]
batch: 4
---

# Stock research (simulated data)

Computes return, volatility, drawdown and trend for fictional tickers on simulated prices, and refuses to give buy or sell advice.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Seeded random walk + risk metrics |
| Industry | Financial services |
| Tags | finance, analytics, simulated-data, refusal |
| Source | [`src/entagents/agents/stock_research.py`](../../src/entagents/agents/stock_research.py) |

## Run it

```bash
entagents run stock-research
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "metrics": {
      "LUMA": {
        "total_return_pct": 55.92,
        "annual_vol_pct": 19.97,
        "max_drawdown_pct": -10.63,
        "trend": "up (50-day above 200-day)"
      },
      "TIDE": {
        "total_return_pct": 35.94,
        "annual_vol_pct": 12.81,
        "max_drawdown_pct": -6.94,
        "trend": "up (50-day above 200-day)"
      },
      "KILN": {
        "total_return_pct": 56.27,
        "annual_vol_pct": 45.64,
        "max_drawdown_pct": -30.15,
        "trend": "up (50-day above 200-day)"
      }
    },
    "lowest_volatility": "TIDE",
    "disclaimer": "Simulated prices for fictional tickers. Educational analysis only, not investment advice."
  },
  "tier": "small",
  "tokens": 39,
  "tool_calls": [
    "prices.read"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 7 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- simulated-data disclaimer on every answer
- refuses buy/sell and price-target questions
- numbers computed, not generated
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
