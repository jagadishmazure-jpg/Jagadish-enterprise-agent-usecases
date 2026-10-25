---
name: recipe-rec
title: Recipe recommendation
level: Beginner
tech: Coverage ranking + hard filters
industry: Consumer and food
tags: [recommendation, personalisation, safety-filter]
batch: 3
---

# Recipe recommendation

Suggests recipes that use what is in the pantry, never suggests one containing a listed allergen, and says what is missing.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Coverage ranking + hard filters |
| Industry | Consumer and food |
| Tags | recommendation, personalisation, safety-filter |
| Source | [`src/entagents/agents/recipe_rec.py`](../../src/entagents/agents/recipe_rec.py) |

## Run it

```bash
entagents run recipe-rec
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "top": [
      {
        "recipe": "rice salad",
        "coverage": 0.8,
        "missing": [
          "olive oil"
        ],
        "minutes": 15
      },
      {
        "recipe": "shrimp stir fry",
        "coverage": 0.5,
        "missing": [
          "shrimp",
          "soy sauce"
        ],
        "minutes": 20
      },
      {
        "recipe": "chickpea curry",
        "coverage": 0.4,
        "missing": [
          "chickpeas",
          "coconut milk",
          "tomato"
        ],
        "minutes": 35
      }
    ],
    "excluded_for_allergy": [
      {
        "recipe": "veg omelette",
        "because": [
          "egg"
        ]
      }
    ]
  },
  "tier": "small",
  "tokens": 33,
  "tool_calls": [
    "recipes.search"
  ... (truncated)
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

- allergens are a hard filter, not a score
- excluded recipes listed with the reason
- time limit respected
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
