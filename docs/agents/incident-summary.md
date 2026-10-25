---
name: incident-summary
title: Incident summary
level: Intermediate
tech: Log parser + temporal correlation
industry: IT operations
tags: [sre, observability, summarisation]
batch: 4
---

# Incident summary

Turns raw logs into a timeline with the first error, the likely trigger, affected services and impact window.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Log parser + temporal correlation |
| Industry | IT operations |
| Tags | sre, observability, summarisation |
| Source | [`src/entagents/agents/incident_summary.py`](../../src/entagents/agents/incident_summary.py) |

## Run it

```bash
entagents run incident-summary
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "first_error": {
      "at": "09:03:00",
      "service": "api",
      "line": "500 on /checkout"
    },
    "likely_trigger": {
      "kind": "deploy",
      "at": "09:00:00",
      "service": "api",
      "line": "deployed v2.4.1"
    },
    "error_count": 2,
    "services_affected": [
      "api",
      "payments"
    ],
    "impact_minutes": 7.0,
    "recovered": true,
    "timeline": [
      "09:00:00 INFO api: deployed v2.4.1",
      "09:02:10 WARN api: p95 latency 900ms",
      "09:03:00 ERROR api: 500 on /checkout",
      "09:03:30 ERROR payments: upstream timeout",
      "09:10:00 INFO api: rolled back to v2.4.0"
    ],
    "note": "Likely trigger is a correlation in time, not a confirmed root cause."
  },
  "tier": "small",
  "tokens": 112,
  "tool_calls": [
    "logs.read"
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

- trigger labelled as correlation, not root cause
- summary built only from log lines
- PII redaction on log text
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
