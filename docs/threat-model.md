# Threat model

Scope: the shared runtime and the agents in this repo, run locally on synthetic data.

## STRIDE

| Threat | Example | Control |
|---|---|---|
| Spoofing | Approving a risky action anonymously | named approver required |
| Tampering | Editing an audit entry after the fact | hash chain, `verify()` |
| Repudiation | "The agent never sent that shortlist" | audit entry with pending approval id |
| Information disclosure | Email or card number echoed in output | redaction in and out, planted-email probe |
| Denial of service | Retry storms on a failing tool | retry budget |
| Elevation of privilege | Agent calls a tool outside its job | allow-list, risky tools only via approval |

## OWASP LLM Top 10 (2025) mapping

| Risk | Control here |
|---|---|
| LLM01 Prompt injection | input screen, allow-lists limit blast radius |
| LLM02 Sensitive information disclosure | PII redaction both ways |
| LLM05 Improper output handling | SQL agent uses templates and a read-only authorizer; code reviewer never executes input |
| LLM06 Excessive agency | allow-lists, approval queue |
| LLM09 Misinformation | citation enforcement and "I don't know" |
| LLM10 Unbounded consumption | token meter, routing, retry budget, cache |

Residual risk: paraphrased injections, PII types not covered, and rules that do not generalise. See [limitations.md](limitations.md).
