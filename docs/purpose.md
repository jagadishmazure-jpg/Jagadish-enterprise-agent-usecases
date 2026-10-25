# Purpose

Most agent demos solve one task and skip the controls. This repo inverts that: one governed runtime is written once and every use case runs through it, so adding an agent means writing only its task logic, its eval cases and its metadata.

Audiences:
- hiring managers looking for evidence of shipped-quality agent engineering;
- enterprise teams evaluating an implementation partner across several departments;
- engineers who want a small, readable pattern to copy.

What it proves, with numbers regenerated on every CI run:

<!-- BEGIN:headline -->
| What | Measured (synthetic data, deterministic local run) |
|---|---|
| Agents built | 10 of 22 (batches 2 of 5) |
| Task eval cases | 107, mean task score 96.8% |
| Planted prompt injection blocked | 100% of agents |
| Planted email leaked to output | 0% of agents |
| Audit chains valid | True |
| Demo run, simulated cost (unit prices, not real spend) | $0.000395 |
| Tests | 102 |
<!-- END:headline -->
