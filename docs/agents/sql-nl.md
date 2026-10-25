---
name: sql-nl
title: SQL in plain English
level: Intermediate
tech: SQLite + template planner
industry: Analytics
tags: [text-to-sql, read-only, abstention]
batch: 1
---

# SQL in plain English

Answers business questions over a local sales database with vetted, read-only SQL.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | SQLite + template planner |
| Industry | Analytics |
| Tags | text-to-sql, read-only, abstention |
| Source | [`src/entagents/agents/sql_nl.py`](../../src/entagents/agents/sql_nl.py) |

## Run it

```bash
entagents run sql-nl
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "answer": [
      [
        "east",
        31578.53
      ],
      [
        "north",
        30434.96
      ],
      [
        "south",
        30141.64
      ],
      [
        "west",
        24952.47
      ]
    ],
    "sql": "select region, round(sum(qty*unit_price),2) as revenue from orders group by region order by region",
    "params": []
  },
  "tier": "small",
  "tokens": 29,
  "tool_calls": [
    "sqlite.query"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 12 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- read-only SQLite authorizer
- template allow-list (no free-form SQL)
- abstains on unmapped questions
- injection screen
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
