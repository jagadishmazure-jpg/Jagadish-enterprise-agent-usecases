---
name: support-escalation
title: Support with escalation
level: Intermediate
tech: Intent rules + help-center lookup
industry: Customer service
tags: [support, escalation, citations, human-handoff]
batch: 2
---

# Support with escalation

Answers routine tickets from the help center with a citation and hands legal, high-value or repeat-frustration cases to people.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Intent rules + help-center lookup |
| Industry | Customer service |
| Tags | support, escalation, citations, human-handoff |
| Source | [`src/entagents/agents/support_escalation.py`](../../src/entagents/agents/support_escalation.py) |

## Run it

```bash
entagents run support-escalation
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "action": "answer",
    "reply": "Standard shipping takes 3 to 5 business days. Tracking links are emailed at dispatch.",
    "citation": "kb-shipping",
    "sentiment": "neutral"
  },
  "tier": "small",
  "tokens": 34,
  "tool_calls": [
    "kb.lookup"
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

- answers only from help-center articles (cited)
- explicit escalation rules
- no refunds issued by the bot
- PII redaction
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
