---
name: issue-triage
title: GitHub issue triage
level: Beginner
tech: Keyword classifier + Jaccard dedupe
industry: Software engineering
tags: [triage, classification, devops]
batch: 2
---

# GitHub issue triage

Labels new issues, sets priority and owning team, and flags likely duplicates of open issues.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Keyword classifier + Jaccard dedupe |
| Industry | Software engineering |
| Tags | triage, classification, devops |
| Source | [`src/entagents/agents/issue_triage.py`](../../src/entagents/agents/issue_triage.py) |

## Run it

```bash
entagents run issue-triage
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "label": "security",
    "priority": "P0",
    "team": "appsec",
    "duplicates": []
  },
  "tier": "small",
  "tokens": 23,
  "tool_calls": [
    "issues.read"
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
| Task score | 91.7% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- suggests labels only (no write access to the tracker)
- injection screen on issue text
- PII redaction
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
