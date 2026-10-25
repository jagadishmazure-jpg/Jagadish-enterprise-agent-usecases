---
name: web-research
title: Web research report (offline corpus)
level: Advanced
tech: Planner + BM25 + source screening
industry: Research and strategy
tags: [research, multi-step, citations, indirect-injection]
batch: 2
---

# Web research report (offline corpus)

Plans sub-questions, retrieves pages from a local corpus, quarantines poisoned pages and writes a cited report.

| Field | Value |
|---|---|
| Level | Advanced |
| Tech | Planner + BM25 + source screening |
| Industry | Research and strategy |
| Tags | research, multi-step, citations, indirect-injection |
| Source | [`src/entagents/agents/web_research.py`](../../src/entagents/agents/web_research.py) |

## Run it

```bash
entagents run web-research
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "topic": "heat pumps",
    "sections": [
      {
        "aspect": "benefits",
        "points": [
          "Heat pumps cut household heating energy use by roughly half compared with resistive heaters in mild climates. [w1]",
          "Cold-climate heat pump models keep useful output down to minus 25 degrees Celsius. [w4]",
          "Heat pump installs need a load calculation; undersized units struggle below minus 15 degrees Celsius. [w2]",
          "Upfront heat pump costs are higher, but many regions offer rebates that shorten payback to 5 to 8 years. [w3]"
        ]
      },
      {
        "aspect": "costs",
        "points": []
      },
      {
        "aspect": "limits and risks",
        "points": []
      }
    ],
    "sources": [
      "w1",
      "w2",
      "w3",
      "w4"
    ],
    "quarantined": [
      "w5"
    ]
  },
  "tier": "large",
  "tokens": 107,
  "tool_calls": [
    "web.search"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
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

- retrieved pages screened for injection and quarantined
- every point cites a page
- abstains when nothing relevant is found
- read-only search tool
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
