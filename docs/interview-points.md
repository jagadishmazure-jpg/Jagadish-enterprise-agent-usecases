# Interview points

- **Why one runtime?** Safety written once is tested once. Twenty-two agents share injection screening, redaction, allow-lists, approvals and audit, so a new agent is mostly task logic plus eval cases.
- **Excessive agency.** Agents get capabilities, not access: a per-agent allow-list, and risky actions (sending a shortlist, sending an email) are queued for a named human.
- **Text-to-SQL safely.** Templates instead of free-form SQL, parameters instead of string building, and a SQLite authorizer that denies writes even if a template were wrong. Unmapped questions get "I don't know".
- **Retry budgets vs naive retries.** Retries are capped as a share of first attempts, so an outage does not triple load.
- **Evals as a gate.** Every agent has task cases plus shared safety probes; CI re-runs them and fails on drift, and safety metrics must be perfect (block rate 100%, leak rate 0%).
- **Honesty.** Known misses stay in the eval sets and in the tests, and every number is regenerated from a run.
- **Fairness in hiring.** Identity is stripped before scoring and a name-swap test proves scores do not change; the deeper fairness metrics live in the recruiting fairness repo.

## Small step router

- Tiny model decides 85.5% of held-out synthetic steps at 97.3% agreement with always-big; threshold tuned on validation, not test.
- Guardrails sit after the router, so no confidence level skips human approval or the audit log.
- Split by run to avoid leakage; savings are simulated and equal the tiny-model share only because it is priced at zero.
