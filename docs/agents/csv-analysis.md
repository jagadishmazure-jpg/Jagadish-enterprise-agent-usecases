---
name: csv-analysis
title: CSV data analysis
level: Beginner
tech: Python csv + statistics
industry: Retail
tags: [analytics, tabular, abstention]
batch: 1
---

# CSV data analysis

Answers questions about a CSV with computed statistics and states which columns and rows were used.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Python csv + statistics |
| Industry | Retail |
| Tags | analytics, tabular, abstention |
| Source | [`src/entagents/agents/csv_analysis.py`](../../src/entagents/agents/csv_analysis.py) |

## Run it

```bash
entagents run csv-analysis
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "kind": "group_mean",
    "columns": [
      "basket",
      "store"
    ],
    "value": {
      "A": 32.77,
      "B": 31.74,
      "C": 36.54
    },
    "rows": 120
  },
  "tier": "small",
  "tokens": 10,
  "tool_calls": [
    "csv.read"
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

- numbers computed, never generated
- read-only file tool
- abstains on unsupported questions
- PII redaction
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
