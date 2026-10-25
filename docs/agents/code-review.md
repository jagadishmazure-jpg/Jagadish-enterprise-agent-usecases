---
name: code-review
title: Code review
level: Intermediate
tech: Python AST rules
industry: Software engineering
tags: [static-analysis, security, devex]
batch: 1
---

# Code review

Reviews Python snippets for risky patterns and explains each finding with a fix hint.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Python AST rules |
| Industry | Software engineering |
| Tags | static-analysis, security, devex |
| Source | [`src/entagents/agents/code_review.py`](../../src/entagents/agents/code_review.py) |

## Run it

```bash
entagents run code-review
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "findings": [
      {
        "rule": "mutable-default",
        "line": 1,
        "hint": "use None as the default and create the list/dict inside"
      },
      {
        "rule": "eval-exec",
        "line": 2,
        "hint": "avoid eval/exec on data; parse it explicitly"
      },
      {
        "rule": "shell-true",
        "line": 4,
        "hint": "pass an argument list and keep shell=False"
      }
    ],
    "verdict": "changes requested"
  },
  "tier": "small",
  "tokens": 48,
  "tool_calls": [
    "ast.parse"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 16 |
| Task score | 93.8% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- never executes reviewed code
- AST parse only
- secret values masked in findings
- injection screen
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
