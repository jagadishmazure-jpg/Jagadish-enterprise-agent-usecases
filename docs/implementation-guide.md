# Implementation guide (adding your own agent)

1. Create `src/entagents/agents/my_agent.py` with a subclass of `Agent`:
   - `META`: name, title, level (Beginner / Intermediate / Advanced), tech, industry, tags, summary, guardrails.
   - `TOOLS = ToolPolicy(frozenset({...}), risky=frozenset({...}))` with only the tools it needs.
   - `handle(ctx, payload)`: call tools through `ctx.tool(name, fn, *args)`; queue risky steps with `ctx.request_approval(action, detail)`.
   - `demo()`, `eval_cases()` and `score(result, expected)`.
   - `AGENT = MyAgent()` at module level.
2. Add the module name to a batch in `registry.py`.
3. `entagents eval --out results/results.json && python scripts/render_docs.py` to create its page and catalog entry.
4. `pytest -q`. The shared tests check metadata, the demo run, the score floor (80%), injection blocking and PII leakage automatically.

Swapping in a real model: keep `handle()` as the boundary, call the model through `ctx.tool("llm.generate", ...)` so the allow-list, retry budget and audit still apply, and pass grounded answers through `enforce_citations`.

Hardening for production: replace the injection patterns with a classifier, use keyed HMAC pseudonymisation instead of placeholders where joins are needed (see Jagadish-pii-guard), persist the audit chain to append-only storage, and back approvals with your identity provider.
