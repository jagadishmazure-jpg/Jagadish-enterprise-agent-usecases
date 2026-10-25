"""Generate agent pages, the catalog metadata file and README blocks from a real run.

    python scripts/render_docs.py          # rewrite docs/agents/*.md, catalog/agents.json and README blocks
    python scripts/render_docs.py --check  # CI: re-run evals, fail if results.json or any generated file drifted

Latency (p50_ms) is machine-dependent, so it is excluded from the drift comparison.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import count_tests  # noqa: E402

from entagents.cli import run_all  # noqa: E402
from entagents.framework.runtime import Runtime  # noqa: E402
from entagents.registry import BATCHES, agents  # noqa: E402

REPO = "https://github.com/jagadishmazure-jpg/Jagadish-enterprise-agent-usecases"


def strip_latency(r: dict) -> dict:
    return {**r, "agents": [{k: v for k, v in a.items() if k != "task_p50_ms"} for a in r["agents"]]}


def sample(agent) -> str:
    out = json.dumps(Runtime().run(agent, agent.demo()), indent=2, default=str).splitlines()
    return "\n".join(out[:45] + (["  ... (truncated)"] if len(out) > 45 else []))


def page(agent, row: dict, batch: int) -> str:
    m = agent.META
    tags = ", ".join(m["tags"])
    return f"""---
name: {m["name"]}
title: {m["title"]}
level: {m["level"]}
tech: {m["tech"]}
industry: {m["industry"]}
tags: [{tags}]
batch: {batch}
---

# {m["title"]}

{m["summary"]}

| Field | Value |
|---|---|
| Level | {m["level"]} |
| Tech | {m["tech"]} |
| Industry | {m["industry"]} |
| Tags | {tags} |
| Source | [`src/entagents/agents/{agent.__module__.rsplit(".", 1)[1]}.py`](../../src/entagents/agents/{agent.__module__.rsplit(".", 1)[1]}.py) |

## Run it

```bash
entagents run {m["name"]}
```

## Real sample output (demo input, synthetic data)

```json
{sample(agent)}
```

## Measured eval (synthetic regression set, deterministic)

| Metric | Value |
|---|---|
| Task cases | {row["task_cases"]} |
| Task score | {row["task_score"] * 100:.1f}% |
| Planted injection blocked | {"yes" if row["injection_blocked"] else "NO"} |
| Planted email leaked | {"NO" if not row["pii_leaked"] else "yes"} |
| Audit chain valid | {"yes" if row["task_audit_chain_ok"] and row["audit_chain_ok"] else "NO"} |

The cases are small, self-written regression checks, not a quality benchmark. Known misses are kept in the set on purpose.

## Guardrails

{chr(10).join(f"- {g}" for g in m["guardrails"])}
- shared runtime: injection screen, PII redaction in and out, tool allow-list, retry budget, cache, token meter, hash-chained audit log
"""


def catalog(r: dict) -> dict:
    rows = {a["name"]: a for a in r["agents"]}
    items = []
    for b, mods in enumerate(BATCHES, 1):
        for a in agents():
            if a.__module__.rsplit(".", 1)[1] in mods:
                m = a.META
                items.append(
                    {
                        **{k: m[k] for k in ("name", "title", "level", "tech", "industry", "tags", "summary", "guardrails")},
                        "batch": b,
                        "run": f"entagents run {m['name']}",
                        "page": f"{REPO}/blob/main/docs/agents/{m['name']}.md",
                        "task_score": rows[m["name"]]["task_score"],
                        "task_cases": rows[m["name"]]["task_cases"],
                        "data": "synthetic",
                    }
                )
    return {"repo": REPO, "schema": "agent-card/v1", "agents": items}


def blocks(r: dict, tests: int) -> dict[str, str]:
    s = r["summary"]
    tbl = ["| # | Agent | Level | Industry | Tech | Task score (cases) |", "|---|---|---|---|---|---|"]
    for i, (a, row) in enumerate(zip(agents(), r["agents"], strict=True), 1):
        m = a.META
        tbl.append(f"| {i} | [{m['title']}](docs/agents/{m['name']}.md) | {m['level']} | {m['industry']} | {m['tech']} | {row['task_score'] * 100:.1f}% ({row['task_cases']}) |")
    head = "\n".join(
        [
            "| What | Measured (synthetic data, deterministic local run) |",
            "|---|---|",
            f"| Agents built | {s['agents']} of 22 (batches {s['batches_built']} of 5) |",
            f"| Task eval cases | {s['eval_cases']}, mean task score {s['mean_task_score'] * 100:.1f}% |",
            f"| Planted prompt injection blocked | {s['injection_block_rate'] * 100:.0f}% of agents |",
            f"| Planted email leaked to output | {s['pii_leak_rate'] * 100:.0f}% of agents |",
            f"| Audit chains valid | {s['audit_chains_valid']} |",
            f"| Demo run, simulated cost (unit prices, not real spend) | ${s['simulated_cost_demo_run_usd']} |",
            f"| Tests | {tests} |",
        ]
    )
    return {"agents": "\n".join(tbl), "headline": head, "tests": f"**{tests} tests**"}


def apply(text: str, bl: dict[str, str]) -> str:
    for k, v in bl.items():
        text = re.sub(rf"(<!-- BEGIN:{k} -->\n).*?(<!-- END:{k} -->)", lambda m, v=v: m.group(1) + v + "\n" + m.group(2), text, flags=re.S)
    return text


def main() -> int:
    check = "--check" in sys.argv
    stored = json.loads((ROOT / "results/results.json").read_text())
    bad = []
    if check and strip_latency(run_all()) != strip_latency(stored):
        bad.append("results/results.json (re-run: entagents eval --out results/results.json)")
    rows = {a["name"]: a for a in stored["agents"]}
    targets: dict[Path, str] = {}
    for b, mods in enumerate(BATCHES, 1):
        for a in agents():
            if a.__module__.rsplit(".", 1)[1] in mods:
                targets[ROOT / f"docs/agents/{a.META['name']}.md"] = page(a, rows[a.META["name"]], b)
    targets[ROOT / "catalog/agents.json"] = json.dumps(catalog(stored), indent=2) + "\n"
    bl = blocks(stored, count_tests.count())
    for f in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        targets[f] = apply(f.read_text(), bl)
    for f, new in targets.items():
        old = f.read_text() if f.exists() else None
        if old != new:
            if check:
                bad.append(str(f.relative_to(ROOT)))
            else:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(new)
    if bad:
        print("out of date:", ", ".join(bad), "- run: python scripts/render_docs.py")
        return 1
    print("docs, agent pages and catalog/agents.json match a fresh run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
