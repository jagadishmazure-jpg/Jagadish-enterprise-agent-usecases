# ADR 0004: five-layer demo with a simulated model and a stdlib graph runner

Status: accepted (PR on branch grokbot/four-layers)

## Context
The portfolio shows each engineering layer in separate repos, but nothing runs one task through every
layer and measures what each adds. The demo has to be free, offline and deterministic so CI can check it.

## Decision
- Use a simulated, rule-based model. Each layer controls what the model "sees" (policy clauses, guard results,
  tool outputs), and the simulated model's decision follows from that. Tokens, cost and latency are simulated and labelled.
- Write a small graph runner with the standard library instead of adding a framework dependency, so the
  mechanics (checkpoints, allowed edges, interrupts) are visible and testable in a few hundred lines.
- Keep prompts as versioned JSON files with a content hash, and gate changes on a committed golden file.
- Put everything under `src/entagents/fourlayers/` with its own CI workflow so it does not touch the
  small-router PR's files.

## Consequences
- Numbers show mechanisms, not real-model quality; the docs say so next to every table.
- Swapping in a real local model later only changes the decision function in `layers.py`.
