---
name: contract-review
title: Contract clause review
level: Intermediate
tech: Clause classifier + playbook rules
industry: Legal
tags: [legal, risk, explainable, human-in-the-loop]
batch: 4
---

# Contract clause review

Splits a contract into clauses, compares each with a negotiation playbook and gives a risk level with the reason.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Clause classifier + playbook rules |
| Industry | Legal |
| Tags | legal, risk, explainable, human-in-the-loop |
| Source | [`src/entagents/agents/contract_review.py`](../../src/entagents/agents/contract_review.py) |

## Run it

```bash
entagents run contract-review
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "clauses": [
      {
        "clause": 1,
        "type": "liability",
        "risk": "high",
        "reason": "unlimited liability; playbook caps at 12 months of fees"
      },
      {
        "clause": 2,
        "type": "indemnity",
        "risk": "high",
        "reason": "one-sided indemnity"
      },
      {
        "clause": 3,
        "type": "termination",
        "risk": "medium",
        "reason": "termination for convenience on 10 days; playbook wants 30+"
      },
      {
        "clause": 4,
        "type": "payment",
        "risk": "medium",
        "reason": "net 60 is longer than the net 45 playbook"
      },
      {
        "clause": 5,
        "type": "governing_law",
        "risk": "low",
        "reason": "standard clause"
      }
    ],
    "missing_standard_clauses": [
      "confidentiality"
    ],
    "note": "Decision support only; a lawyer signs off."
  },
  "tier": "small",
  "tokens": 132,
  "tool_calls": [
    "contract.parse"
  ],
  ... (truncated)
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

- decision support only, lawyer signs off
- every risk has a stated reason
- flags missing standard clauses
- PII redaction
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
