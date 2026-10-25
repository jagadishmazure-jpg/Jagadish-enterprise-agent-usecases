---
name: unit-test-gen
title: Unit test generator
level: Advanced
tech: AST + doctest mining + mutation check
industry: Software engineering
tags: [testing, code-generation, sandbox, mutation-testing]
batch: 3
---

# Unit test generator

Generates pytest tests from docstring examples, runs them in an isolated process and reports how many planted bugs they catch.

| Field | Value |
|---|---|
| Level | Advanced |
| Tech | AST + doctest mining + mutation check |
| Industry | Software engineering |
| Tags | testing, code-generation, sandbox, mutation-testing |
| Source | [`src/entagents/agents/unit_test_gen.py`](../../src/entagents/agents/unit_test_gen.py) |

## Run it

```bash
entagents run unit-test-gen
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "tests": "from target import *  # noqa: F403\n\ndef test_clamp_0():\n    assert clamp(5, 0, 3) == 3\n\ndef test_clamp_1():\n    assert clamp(-1, 0, 3) == 0\n\ndef test_clamp_2():\n    assert clamp(2, 0, 3) == 2\n",
    "on_original": {
      "passed": 3,
      "failed": 0
    },
    "on_mutant": {
      "passed": 1,
      "failed": 2
    },
    "mutant_killed": true
  },
  "tier": "large",
  "tokens": 84,
  "tool_calls": [
    "code.generate",
    "sandbox.run",
    "sandbox.run"
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
| Task score | 87.5% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- import and call allow-list before any execution
- subprocess with empty environment and timeout
- temporary directory only
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
