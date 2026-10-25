"""Draw results/evidence_board.png from results/results.json (needs the optional 'board' extra)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    r = json.loads((ROOT / "results/results.json").read_text())
    rows, s = r["agents"], r["summary"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 0.45 * len(rows) + 3), gridspec_kw={"width_ratios": [3, 2]})
    names = [a["name"] for a in rows][::-1]
    sc = [a["task_score"] * 100 for a in rows][::-1]
    ax.barh(names, sc, color=["#2f855a" if v >= 95 else "#d69e2e" for v in sc])
    for i, (v, a) in enumerate(zip(sc, rows[::-1], strict=True)):
        ax.text(v + 1, i, f"{v:.1f}% (n={a['task_cases']})", va="center", fontsize=9)
    ax.set_xlim(0, 125)
    ax.set_xlabel("task score on synthetic regression cases (%)")
    ax.set_title("Per-agent task score")
    bx.axis("off")
    lines = [
        f"Agents built: {s['agents']} / 22",
        f"Eval cases: {s['eval_cases']}",
        f"Mean task score: {s['mean_task_score'] * 100:.1f}%",
        f"Injection blocked: {s['injection_block_rate'] * 100:.0f}% of agents",
        f"PII leak: {s['pii_leak_rate'] * 100:.0f}% of agents",
        f"Audit chains valid: {s['audit_chains_valid']}",
        f"Simulated demo cost: ${s['simulated_cost_demo_run_usd']:.5f}",
        "",
        "Synthetic data, deterministic local run.",
        "Amber bars keep known misses visible.",
    ]
    bx.text(0, 0.95, "\n".join(lines), va="top", fontsize=12, family="monospace")
    bx.set_title("Shared runtime, measured")
    fig.suptitle("Enterprise agent use cases - evidence board", fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(ROOT / "results/evidence_board.png", dpi=110)


if __name__ == "__main__":
    main()
