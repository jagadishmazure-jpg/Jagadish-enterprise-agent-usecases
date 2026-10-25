---
name: doc-writer
title: Documentation writer
level: Beginner
tech: Python AST
industry: Software engineering
tags: [documentation, devex, code-analysis]
batch: 3
---

# Documentation writer

Writes a Markdown API reference from source code and lists what is undocumented or missing a return type.

| Field | Value |
|---|---|
| Level | Beginner |
| Tech | Python AST |
| Industry | Software engineering |
| Tags | documentation, devex, code-analysis |
| Source | [`src/entagents/agents/doc_writer.py`](../../src/entagents/agents/doc_writer.py) |

## Run it

```bash
entagents run doc-writer
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "markdown": "# cart\n\n_No module docstring._\n\n## class `Cart`\n\nA basket.\n\n### `Cart.add(self, sku: str) -> None`\n\nAdd one item.\n\n### `Cart.total(self)`\n\n_Undocumented._\n",
    "documented": [
      "Cart.add"
    ],
    "gaps": [
      "Cart.total",
      "Cart.total (no return type)"
    ]
  },
  "tier": "small",
  "tokens": 61,
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
| Task cases | 6 |
| Task score | 100.0% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- reads source only, never executes it
- describes only what the code declares
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
