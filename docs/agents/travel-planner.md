---
name: travel-planner
title: Travel planner
level: Intermediate
tech: Constraint fitting over a price catalog
industry: Travel and hospitality
tags: [planning, budget, human-in-the-loop]
batch: 3
---

# Travel planner

Builds a trip from a synthetic catalog within a hard budget, explains each pick, and says so when the budget cannot work.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Constraint fitting over a price catalog |
| Industry | Travel and hospitality |
| Tags | planning, budget, human-in-the-loop |
| Source | [`src/entagents/agents/travel_planner.py`](../../src/entagents/agents/travel_planner.py) |

## Run it

```bash
entagents run travel-planner
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "feasible": true,
    "flight": {
      "carrier": "Saltmarsh Airways",
      "price": 365
    },
    "hotel": {
      "name": "Tilework Inn",
      "per_night": 95,
      "nights": 4
    },
    "activities": [
      {
        "activity": "tile museum",
        "price": 10,
        "why": "history"
      },
      {
        "activity": "tram tour",
        "price": 25,
        "why": "history"
      },
      {
        "activity": "food walk",
        "price": 55,
        "why": "food"
      }
    ],
    "total": 835.0,
    "under_budget_by": 165.0,
    "booking_status": "held for approval (#0)"
  },
  "tier": "small",
  "tokens": 27,
  "tool_calls": [
    "catalog.search"
  ],
  "pending_approvals": [
    0
  ],
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

- hard budget check (never exceeds)
- prices only from the catalog
- booking held for approval
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
