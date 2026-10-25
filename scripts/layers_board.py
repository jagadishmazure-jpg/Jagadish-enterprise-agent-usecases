"""Draw results/layers_board.png from results/layers.json (needs the optional 'board' extra)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    r = json.loads((ROOT / "results/layers.json").read_text())
    L, g = r["layers"], r["graph"]
    names = list(L)
    fig, axes = plt.subplots(2, 3, figsize=(17, 9.5))
    fig.suptitle("Five layers, one invoice task: what each layer adds (synthetic invoices, simulated model, SIMULATED cost and latency)", fontsize=13)
    col = ["#a0aec0", "#63b3ed", "#3182ce", "#2c5282", "#2f855a"]

    def bars(ax, key, title, fmt, scale=1.0):
        v = [L[n][key] * scale for n in names]
        ax.bar(range(5), v, color=col)
        ax.set_xticks(range(5), [n.replace(" ", "\n") for n in names], fontsize=9)
        ax.set_title(title)
        for i, x in enumerate(v):
            ax.text(i, x, fmt.format(x), ha="center", va="bottom", fontsize=9)

    bars(axes[0][0], "accuracy", f"Decision accuracy, % (n={L[names[0]]['cases']})", "{:.1f}", 100)
    bars(axes[0][1], "tokens_per_case", "Tokens per case (simulated count)", "{:.0f}")
    bars(axes[0][2], "sim_cost_per_accepted_usd", "Simulated $ per accepted decision (x1e-4)", "{:.2f}", 1e4)
    bars(axes[1][0], "sim_latency_p50_ms", "Simulated latency p50, ms", "{:.0f}")
    ax = axes[1][1]
    kinds = list(L[names[0]]["wrong_by_kind"])
    for i, n in enumerate(names):
        ax.plot(kinds, [L[n]["wrong_by_kind"][k] for k in kinds], marker="o", color=col[i], label=n)
    ax.set_title("Wrong decisions by case type")
    ax.tick_params(axis="x", rotation=35, labelsize=8)
    ax.legend(fontsize=8)
    bx = axes[1][2]
    bx.axis("off")
    p, c = g["parallel"], g["crash_resume"]
    lines = [
        "What the graph (L5) adds over the free-form loop (L4)",
        f"Crash mid-run then resume: nodes redone {c['nodes_redone_graph']} vs {c['nodes_redone_freeform_loop']}",
        f"Parallel extract + rank: p50 {p['sim_p50_ms_parallel']:.0f} vs {p['sim_p50_ms_sequential']:.0f} ms (-{p['sim_saving_pct']}%, simulated)",
        f"Route audit: {g['route_audit']['identical_route_hashes']}/{g['route_audit']['runs']} identical route hashes on rerun",
        f"Invalid transitions: {g['invalid_transitions']['blocked']}/{g['invalid_transitions']['attempted']} blocked, {g['invalid_transitions']['followed']} followed",
        "",
        f"L3 guard hits: {r['l3_guard_hits']}   L3 retries: {r['l3_retries']}",
        f"L4 end states: {r['l4_end_states']}",
        "Known miss: 2 unreadable scans stop as 'stalled' and go",
        "to a person (counted wrong, never reported as success).",
    ]
    bx.text(0, 1, "\n".join(lines), va="top", fontsize=10.5, family="monospace")
    fig.tight_layout()
    fig.savefig(ROOT / "results/layers_board.png", dpi=110)


if __name__ == "__main__":
    main()
