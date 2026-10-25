---
name: doc-qa
title: Document Q&A with citations
level: Intermediate
tech: BM25 retrieval + citation check
industry: Enterprise knowledge
tags: [rag, citations, abstention, hallucination-control]
batch: 2
---

# Document Q&A with citations

Answers policy questions from a document set, cites the source, and says I don't know when the documents do not cover it.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | BM25 retrieval + citation check |
| Industry | Enterprise knowledge |
| Tags | rag, citations, abstention, hallucination-control |
| Source | [`src/entagents/agents/doc_qa.py`](../../src/entagents/agents/doc_qa.py) |

## Run it

```bash
entagents run doc-qa
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "answer": "Meals on business travel are reimbursed up to 60 dollars per day.",
    "citations": [
      "fin-expense"
    ],
    "top_score": 3.0727
  },
  "tier": "small",
  "tokens": 29,
  "tool_calls": [
    "docs.search"
  ],
  "pending_approvals": [],
  "pii_redacted": 0,
  "cache": "miss"
}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | 13 |
| Task score | 92.3% |
| Planted injection blocked | yes |
| Planted email leaked | NO |
| Audit chain valid | yes |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

- answer must cite a retrieved document
- unsupported claims dropped
- score threshold then abstain
- PII redaction
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
