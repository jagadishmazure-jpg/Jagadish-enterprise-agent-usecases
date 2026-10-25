# ADR 0001: one shared runtime for all agents

Status: accepted

Context: each use case needs the same controls (injection screen, PII redaction, tool limits, approvals, audit, evals). Writing them per agent duplicates code and lets controls drift.

Decision: agents implement only `handle()`, `demo()`, `eval_cases()` and `score()`. The `Runtime` wraps every call and is the only path to tools and approvals.

Consequences: controls are uniform and tested once; agents cannot opt out. The cost is that the runtime must stay generic (it works on any JSON-like payload).
