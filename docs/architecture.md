# Architecture

```mermaid
flowchart TB
    subgraph framework [Shared framework layer]
      guards[guards.py: injection screen, PII redaction, ToolPolicy]
      controls[controls.py: route, LRUCache, RetryBudget, Meter]
      grounding[grounding.py: BM25, citation check, IDK]
      approval[approval.py: ApprovalQueue]
      audit[audit.py: AuditLog hash chain]
      runtime[runtime.py: Runtime + Context]
      evals[evals.py: task_eval, safety_eval]
    end
    subgraph agents [Use-case agents]
      a1[sql_nl] & a2[code_review] & a3[resume_match] & a4[csv_analysis] & a5[meeting_actions] & b2[batch 2..5 agents]
    end
    agents --> runtime
    runtime --> guards & controls & approval & audit
    agents -.-> grounding
    evals --> runtime
    cli[cli.py] --> evals
    render[scripts/render_docs.py] --> pages[docs/agents/*.md] & cat[catalog/agents.json] & readme[README tables]
```

Design rules:
- **Agents never touch the outside world directly.** They call `ctx.tool(name, fn)`, which checks the allow-list and wraps the call in the retry budget, or `ctx.request_approval(action, detail)` for risky steps.
- **The runtime owns safety.** An agent cannot skip injection screening, redaction or audit because it never sees the raw request.
- **Metadata is code.** Each agent's `META` drives its doc page and its catalog card, so they cannot drift.

Decisions: [ADR 0001](adr/0001-shared-runtime.md), [ADR 0002](adr/0002-deterministic-agents.md).
