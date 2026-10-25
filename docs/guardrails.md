# Guardrails

| Layer | Control | Notes |
|---|---|---|
| Input | Injection screen | Pattern list in `guards.py`; blocks before any agent code runs. Patterns miss paraphrased attacks, see limitations. |
| Input/output | PII redaction | Email, phone, SSN (invalid area codes skipped), cards only when the Luhn checksum passes. Fuller version: Jagadish-pii-guard. |
| Tools | Allow-list per agent | `ToolPolicy.allowed`; unknown tools raise `ToolDenied`, logged as `denied`. |
| Tools | Risky tools | Listed in `ToolPolicy.risky`; direct calls are refused, only `request_approval` can queue them. |
| Approval | Named approver | `ApprovalQueue.decide` refuses an empty approver and double decisions. |
| Reliability | Retry budget | Retries limited to `floor + ratio * attempts`; only timeouts and connection errors retry. |
| Cost | Token meter and routing | Simulated unit prices; shows where spend would go. |
| Grounding | Citations, abstention | Claims without a supporting cited source are dropped; nothing left gives "I don't know". |
| Audit | Hash chain | Every outcome logged; `verify()` detects edits. |
| Evals | Safety probes | Each agent gets a planted injection and a planted email; CI fails unless all are blocked / removed. |

Per-agent guardrails are listed on each page in [agents/](agents/).
