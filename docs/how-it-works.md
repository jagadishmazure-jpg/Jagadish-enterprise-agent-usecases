# How it works

1. **Screen.** Every string in the request is checked against injection patterns (instruction overrides, role switching, secret dumping, system-tag spoofing, destructive SQL). One hit blocks the request and is logged.
2. **Redact.** Emails, phone numbers, SSNs and Luhn-valid card numbers are replaced with typed placeholders such as `[EMAIL]` before the agent sees the text.
3. **Cache.** The redacted request is hashed; a repeat gets the stored answer (`"cache": "hit"`).
4. **Route and meter.** Short requests go to the small tier, long or hard ones to the large tier. Tokens are estimated and priced with simulated unit prices.
5. **Act.** The agent's `handle()` runs. Tools pass the allow-list and the retry budget (retries capped at a share of first attempts plus a small floor, so failures cannot multiply load). Risky actions become pending approvals.
6. **Ground.** Agents that answer from sources keep only claims whose citation exists and supports them; with nothing left they answer "I don't know".
7. **Redact again** on the way out, in case a tool returned personal data.
8. **Audit.** Each outcome (ok, blocked, denied, cache hit) is appended to a hash chain; editing any earlier entry breaks `verify()`.
9. **Evaluate.** `entagents eval` runs each agent's task cases and the shared safety probes, then writes `results/results.json`. `scripts/render_docs.py --check` re-runs everything in CI and fails if the docs drift.
