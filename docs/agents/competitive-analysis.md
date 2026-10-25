---
name: competitive-analysis
title: Competitive analysis (multi-step)
level: Advanced
tech: Plan, retrieve, extract, compare
industry: Strategy and product
tags: [multi-step, research, citations, fictional-companies]
batch: 5
---

# Competitive analysis (multi-step)

Plans comparison dimensions, gathers cited facts for each fictional company, builds a matrix and names leaders only where sources exist.

| Field | Value |
|---|---|
| Level | Advanced |
| Tech | Plan, retrieve, extract, compare |
| Industry | Strategy and product |
| Tags | multi-step, research, citations, fictional-companies |
| Source | [`src/entagents/agents/competitive_analysis.py`](../../src/entagents/agents/competitive_analysis.py) |

## Run it

```bash
entagents run competitive-analysis
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "steps": [
      "plan: 3 dimensions x 4 companies",
      "gather: 10 cited cells",
      "compare: leaders chosen only among cited cells"
    ],
    "matrix": {
      "Ferngate Analytics": {
        "price_per_user": {
          "value": 49,
          "cite": "c1"
        },
        "connectors": {
          "value": 120,
          "cite": "c2"
        },
        "support_hours": {
          "value": 24,
          "cite": "c3"
        }
      },
      "Stillwater Metrics": {
        "price_per_user": {
          "value": 35,
          "cite": "c4"
        },
        "connectors": {
          "value": 60,
          "cite": "c5"
        },
        "support_hours": {
          "value": 4,
          "cite": "c6"
        }
      },
      "Orchard Signal": {
        "price_per_user": {
          "value": 59,
          "cite": "c7"
        },
        "connectors": {
          "value": 200,
          "cite": "c8"
  ... (truncated)
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 5 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- every matrix cell cites a fact or says no source
- leaders picked only from cited cells
- fictional companies only
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
