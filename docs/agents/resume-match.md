---
name: resume-match
title: Resume parsing and matching
level: Intermediate
tech: Rule parser + skill-coverage scorer
industry: HR and recruiting
tags: [hr, fairness, explainable, human-in-the-loop]
batch: 1
---

# Resume parsing and matching

Parses resumes, hides identity, ranks job fits with reasons, and holds shortlists for recruiter sign-off.

| Field | Value |
|---|---|
| Level | Intermediate |
| Tech | Rule parser + skill-coverage scorer |
| Industry | HR and recruiting |
| Tags | hr, fairness, explainable, human-in-the-loop |
| Source | [`src/entagents/agents/resume_match.py`](../../src/entagents/agents/resume_match.py) |

## Run it

```bash
entagents run resume-match
```

## Real sample output (demo input, synthetic data)

```json
{
  "status": "ok",
  "output": {
    "profile": {
      "skills": [
        "airflow",
        "java",
        "python",
        "spark",
        "sql"
      ],
      "years": 7
    },
    "ranked": [
      {
        "job": "data-engineer",
        "score": 1.0,
        "because": [
          "airflow",
          "python",
          "spark",
          "sql"
        ],
        "missing": []
      },
      {
        "job": "bi-analyst",
        "score": 0.333,
        "because": [
          "sql"
        ],
        "missing": [
          "excel",
          "tableau"
        ]
      },
      {
        "job": "ml-engineer",
        "score": 0.333,
        "because": [
          "python"
        ],
        "missing": [
          "kubernetes",
          "pytorch"
  ... (truncated)
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

- identity stripped before scoring
- PII redaction
- reason shown for every match
- name-swap invariance test
- recruiter approval to send
- audit log
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
