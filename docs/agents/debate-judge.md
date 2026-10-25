---
name: debate-judge
title: Multi-agent debate with a judge
level: Advanced
tech: Two debaters + evidence-scored judge
industry: Decision support
tags: [multi-agent, llm-as-judge, bias-testing, citations]
batch: 5
---

# Multi-agent debate with a judge

Two agents argue a decision from shared evidence; a judge scores verified citations, penalises made-up ones and is checked for order and length bias.

| Field | Value |
|---|---|
| Level | Advanced |
| Tech | Two debaters + evidence-scored judge |
| Industry | Decision support |
| Tags | multi-agent, llm-as-judge, bias-testing, citations |
| Source | [`src/entagents/agents/debate_judge.py`](../../src/entagents/agents/debate_judge.py) |

## Run it

```bash
entagents run debate-judge
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "motion": "rewrite",
    "pro": {
      "stance": "pro",
      "cites": [
        "e5",
        "e8"
      ],
      "argument": "The old codebase uses an unsupported framework version. Engineers prefer modern tooling."
    },
    "con": {
      "stance": "con",
      "cites": [
        "e6",
        "e7"
      ],
      "argument": "Past rewrites at the firm ran 2x over schedule. Incremental refactoring already cut incidents by a third."
    },
    "verdict": {
      "scores": {
        "pro": 2,
        "con": 5
      },
      "winner": "con"
    },
    "verdict_swapped_order": {
      "scores": {
        "con": 5,
        "pro": 2
      },
      "winner": "con"
    },
    "order_flip": false
  },
  "tier": "large",
  "tokens": 52,
  "tool_calls": [
    "evidence.read"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 9 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- judge scores verified citations only
- fabricated citations penalised
- both speaking orders judged (order-flip rate)
- length ignored (verbosity probe)
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
