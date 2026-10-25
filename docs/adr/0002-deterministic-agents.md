# ADR 0002: deterministic local logic instead of hosted models

Status: accepted

Context: the repo must run free, offline and give identical numbers on every machine so CI can verify the docs.

Decision: agents use rules, templates, standard-library parsing and small retrieval. Costs are shown with simulated unit prices.

Consequences: results are reproducible and nothing is billable, but coverage is narrow. A local-model backend is planned behind `ctx.tool("llm.generate")` so controls stay in place.
