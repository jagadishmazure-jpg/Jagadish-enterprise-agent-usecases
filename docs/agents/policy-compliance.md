---
name: policy-compliance
title: Policy compliance check
level: Beginner
tech: Rules engine over configuration
industry: Governance, risk and compliance
tags: [compliance, audit, security, explainable]
batch: 4
---

# Policy compliance check

Checks a system configuration against written controls and reports each failure with observed and expected values.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Rules engine over configuration |
| Industry | Governance, risk and compliance |
| Tags | compliance, audit, security, explainable |
| Source | [`src/entagents/agents/policy_compliance.py`](../../src/entagents/agents/policy_compliance.py) |

## Run it

```bash
entagents run policy-compliance
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "compliant": false,
    "fails": [
      "LOG-1",
      "NET-1"
    ],
    "unknown": [],
    "findings": [
      {
        "control": "LOG-1",
        "result": "fail",
        "detail": "audit logs kept 365 days or more",
        "observed": 30,
        "expected": ">= 365"
      },
      {
        "control": "NET-1",
        "result": "fail",
        "detail": "no public admin ports",
        "observed": [
          443,
          22
        ],
        "expected": "no 22 or 3389"
      }
    ],
    "controls_checked": 7
  },
  "tier": "small",
  "tokens": 34,
  "tool_calls": [
    "config.read"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 8 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- missing evidence reported as unknown, never as pass
- observed vs expected on every finding
- read-only
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
