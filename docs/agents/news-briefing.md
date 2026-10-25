---
name: news-briefing
title: News briefing (local corpus)
level: Beginner
tech: Date filter + Jaccard dedupe
industry: Media and communications
tags: [summarisation, dedupe, citations, indirect-injection]
batch: 3
---

# News briefing (local corpus)

Builds a dated briefing from a local news feed, removes near-duplicate stories, groups by topic and cites every item.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Date filter + Jaccard dedupe |
| Industry | Media and communications |
| Tags | summarisation, dedupe, citations, indirect-injection |
| Source | [`src/entagents/agents/news_briefing.py`](../../src/entagents/agents/news_briefing.py) |

## Run it

```bash
entagents run news-briefing
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "window": [
      "2026-10-20",
      "2026-10-24"
    ],
    "sections": {
      "energy": [
        "Port Avery council approves second wind farm phase (2026-10-23) [n7]",
        "Coastal wind farm near Port Avery reaches full output (2026-10-21) [n4]"
      ],
      "health": [
        "Riverbend clinic network extends evening hours (2026-10-24) [n11]"
      ],
      "markets": [
        "Brightwell Foods names new finance chief (2026-10-24) [n9]",
        "Brightwell Foods shares fall after weak quarter (2026-10-22) [n6]",
        "Harborline Bank raises savings rate to 4.1 percent (2026-10-20) [n1]"
      ],
      "tech": [
        "Quillfeather Labs patches login flaw in scheduling library (2026-10-22) [n5]",
        "Quillfeather Labs releases open-source scheduling library (2026-10-21) [n3]"
      ]
    },
    "duplicates_dropped": [
      "n12",
      "n2"
    ],
    "quarantined": [
      "n8"
    ]
  },
  "tier": "small",
  "tokens": 106,
  "tool_calls": [
    "feed.read"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 6 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- items screened for injection and quarantined
- every bullet cites an item id
- date window enforced
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
