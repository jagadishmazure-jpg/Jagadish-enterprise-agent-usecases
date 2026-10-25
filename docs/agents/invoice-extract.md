---
name: invoice-extract
title: Invoice extraction
level: Intermediate
tech: Regex extraction + strict schema + reconciliation
industry: Finance operations
tags: [document-ai, structured-output, validation, human-review]
batch: 4
---

# Invoice extraction

Extracts invoice fields into a fixed schema, checks that every line and total adds up, and routes mismatches to a person.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Regex extraction + strict schema + reconciliation |
| Industry | Finance operations |
| Tags | document-ai, structured-output, validation, human-review |
| Source | [`src/entagents/agents/invoice_extract.py`](../../src/entagents/agents/invoice_extract.py) |

## Run it

```bash
entagents run invoice-extract
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "record": {
      "invoice_no": "INV-1001",
      "date": "2026-10-14",
      "vendor": "Cobalt Fern Supplies",
      "lines": [
        {
          "item": "Paper reams",
          "qty": 10,
          "unit": 4.5,
          "amount": 45.0
        },
        {
          "item": "Toner",
          "qty": 2,
          "unit": 89.0,
          "amount": 178.0
        }
      ],
      "subtotal": 223.0,
      "tax": 17.84,
      "total": 240.84
    },
    "status": "accepted",
    "errors": []
  },
  "tier": "small",
  "tokens": 53,
  "tool_calls": [
    "doc.extract"
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

- fixed schema, extra or missing keys rejected
- arithmetic reconciliation
- mismatch routed to human review
- errors never echo raw values
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
