---
name: meeting-actions
title: Meeting notes to action items
level: Beginner
tech: Pattern extractor
industry: Productivity
tags: [summarisation, extraction, workflow]
batch: 1
---

# Meeting notes to action items

Turns raw meeting notes into owner / task / due-date items and skips vague remarks.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Pattern extractor |
| Industry | Productivity |
| Tags | summarisation, extraction, workflow |
| Source | [`src/entagents/agents/meeting_actions.py`](../../src/entagents/agents/meeting_actions.py) |

## Run it

```bash
entagents run meeting-actions
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "actions": [
      {
        "owner": "Priya",
        "task": "update the pricing page",
        "due": "friday"
      },
      {
        "owner": "Tom",
        "task": "email the vendor list",
        "due": "unspecified"
      },
      {
        "owner": "Lena",
        "task": "draft the QBR deck",
        "due": "next week"
      },
      {
        "owner": "Marco",
        "task": "fix the login bug",
        "due": "eod"
      }
    ]
  },
  "tier": "small",
  "tokens": 88,
  "tool_calls": [
    "notes.extract"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 10 |
| Task score | 90.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- explicit commitments only
- PII redaction
- injection screen
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
