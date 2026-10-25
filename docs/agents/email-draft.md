---
name: email-draft
title: Email drafting with human sign-off
level: Beginner
tech: Templates + wording rules
industry: Sales and customer success
tags: [drafting, human-in-the-loop, communications]
batch: 2
---

# Email drafting with human sign-off

Drafts short business emails from bullet points, removes commitment wording, and waits for a person to approve sending.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Templates + wording rules |
| Industry | Sales and customer success |
| Tags | drafting, human-in-the-loop, communications |
| Source | [`src/entagents/agents/email_draft.py`](../../src/entagents/agents/email_draft.py) |

## Run it

```bash
entagents run email-draft
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "subject": "Next steps",
    "body": "Hi Ravi,\n\nFollowing up on our conversation, here are the next steps.\n- Share the pilot plan by Friday\n- We [removed: commitment wording] results\n\nBest regards,\nAccount team",
    "flags": 1,
    "send_status": "waiting for approval (#0)"
  },
  "tier": "small",
  "tokens": 62,
  "tool_calls": [
    "email.compose"
  ],
  "pending_approvals": [
    0
  ],
  "pii_redacted": 1,
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

- send is a risky action that needs a named approver
- guarantee/promise wording removed and flagged
- recipient address redacted in logs
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
