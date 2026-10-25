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
| issue-triage | an issue with no keywords ("Sidebar overlaps the chart") falls back to `question` | `test_triage_known_miss_no_keywords` |
| doc-qa | "parental leave policy" is answered from the general leave policy because title words give enough coverage | `test_docqa_known_miss_parental_leave` |
| unit-test-gen | a function with one doctest example (`sign(4)`) yields tests too weak to catch a bug in the negative branch | `test_unit_test_gen_known_miss_weak_examples` |
| contract-review | "hold harmless" wording is indemnity but is classified `other` | `test_contract_known_miss_hold_harmless` |
