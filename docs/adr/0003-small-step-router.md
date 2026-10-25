# ADR 0003: a tiny step router with confidence handoff

**Status:** accepted (synthetic evaluation only)

**Context.** Sending every step decision of an agent run to a large model is slow and costly, but most steps (what to do after research, whether to stop after a clean review) are routine.

**Decision.** A 144-weight logistic-regression router, written in pure Python so CI needs no new dependency, decides each step. Below a confidence threshold tuned on validation runs it escalates to a stronger decider. The rule router is the fallback. The approval gate and the audit log sit after the router so no routing choice can bypass them.

**Consequences.** On held-out synthetic runs the tiny model takes 85.5% of steps at 97.3% agreement with the always-big baseline. The threshold is now a tuned setting that must be revisited when agents change. Confidence calibration is still open.
