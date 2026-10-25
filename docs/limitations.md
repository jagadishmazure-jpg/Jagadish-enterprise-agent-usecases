# Limitations and known failures

- **Rules, not models.** Agents use deterministic parsers and templates so results are repeatable and free. They cover the phrasings in their eval sets and little beyond. An optional local-model backend is planned behind the same interface.
- **Small eval sets.** Each agent has 5-20 self-written cases. Treat scores as regression checks, not quality claims.
- **Pattern-based injection screen.** Paraphrased or encoded attacks will pass; real deployments need a classifier plus least privilege (which is why tool allow-lists exist regardless).
- **PII coverage** is limited to emails, phones, US SSNs and card numbers. Names are not redacted globally; the resume agent strips them structurally instead.

Known misses kept as tests and visible in scores:

| Agent | Miss | Test |
|---|---|---|
| code-review | `run = eval; run(x)` is not flagged (name-based rule) | `test_code_review_known_miss_alias` |
| meeting-actions | passive voice ("will be updated by Wednesday by Nora") loses the owner | `test_meeting_known_miss_passive` |
