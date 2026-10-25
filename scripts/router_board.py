"""Evidence board for the small step router: one held-out run's route graph with per-step
confidence, plus the threshold sweep. Reads results/router.json and replays one test run.

    pip install -e ".[board]" && python scripts/router_board.py   ->  results/router_board.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from entagents.router.evaluate import train  # noqa: E402
from entagents.router.router import StepRouter  # noqa: E402
from entagents.router.traces import build  # noqa: E402

r = json.loads((ROOT / "results/router.json").read_text())
m, _tr, _va, te = train(build())
thr = r["tuned_threshold"]
runs: dict[str, list] = {}
for s in te:
    runs.setdefault(s.run_id, []).append(s)
# pick the first test run that has a rework loop and at least one handoff to the stronger decider
pick = None
for rid, steps in runs.items():
    recs = [StepRouter(m, threshold=thr).decide(s) for s in steps]
    if any(x["source"] == "big" for x in recs) and len(recs) >= 7:
        pick = (rid, recs)
        break
rid, recs = pick

fig = plt.figure(figsize=(15, 9))
fig.suptitle("Small step router - evidence board (synthetic runs, simulated prices)", fontsize=15, weight="bold")
ax = fig.add_subplot(2, 1, 1)
col = {"small": "#2b8a3e", "big": "#c92a2a", "rule_fallback": "#868e96"}
for i, x in enumerate(recs):
    ax.add_patch(plt.Rectangle((i * 1.6, 0), 1.3, 1, color=col[x["source"]], alpha=0.85))
    ax.text(i * 1.6 + 0.65, 0.62, x["worker"], ha="center", color="white", fontsize=11, weight="bold")
    ax.text(i * 1.6 + 0.65, 0.35, f"tiny conf {x['small_confidence']:.2f}", ha="center", color="white", fontsize=9)
    ax.text(i * 1.6 + 0.65, 0.12, x["action"].split("#")[0] + (" STOP" if x["stop"] else ""), ha="center", color="white", fontsize=8)
    if i:
        ax.annotate("", xy=(i * 1.6, 0.5), xytext=(i * 1.6 - 0.3, 0.5), arrowprops={"arrowstyle": "->"})
ax.set_xlim(-0.2, len(recs) * 1.6)
ax.set_ylim(-0.3, 1.3)
ax.axis("off")
ax.set_title(f"Route of held-out run {rid}: green = tiny model, red = handed to the stronger decider (conf < {thr})", fontsize=11)

ax2 = fig.add_subplot(2, 2, 3)
sw = r["sweep_test"]
t = [p["threshold"] for p in sw]
ax2.plot(t, [p["small_share"] for p in sw], "o-", label="share handled by tiny model")
ax2.plot(t, [p["agreement_vs_big"] for p in sw], "s-", label="agreement with always-big")
ax2.plot(t, [p["accuracy_vs_truth"] for p in sw], "^-", label="accuracy vs true policy")
ax2.axvline(thr, ls="--", c="k")
ax2.set_xlabel("confidence threshold")
ax2.set_title("Threshold sweep on held-out test runs")
ax2.legend(fontsize=8)
ax2.grid(alpha=0.3)

ax3 = fig.add_subplot(2, 2, 4)
ax3.axis("off")
x = r["test"]
lines = [
    f"Held-out test steps: {x['steps']} ({r['states']['runs']} runs total)",
    f"Tuned threshold: {thr} (tuned on validation for >= {r['target_agreement']} agreement)",
    f"Handled by tiny model: {x['small_share'] * 100:.1f}%",
    f"Agreement with always-big baseline: {x['agreement_vs_big'] * 100:.1f}%",
    f"Accuracy vs true policy: {x['accuracy_vs_truth'] * 100:.1f}% (always-big {x['big_accuracy_vs_truth'] * 100:.1f}%)",
    f"Rule router accuracy: {r['rule_router_accuracy_vs_truth'] * 100:.1f}%",
    f"Unsafe steps blocked: {x['unsafe_caught']} of {x['unsafe_steps']}",
    f"Simulated cost: USD {x['sim_cost_usd']} vs USD {x['sim_cost_always_big_usd']} ({x['sim_cost_saved_pct'] * 100:.1f}% saved)",
    f"Simulated latency saved: {x['sim_latency_saved_pct'] * 100:.1f}%",
    f"Publishes parked for human approval: {x['pending_approvals']}",
    f"Audit entries: {x['audit_entries']}, chain valid: {x['audit_chain_ok']}",
    f"Model: {r['model']['params']} weights, pure Python, CPU",
]
for i, line in enumerate(lines):
    ax3.text(0, 1 - i * 0.085, line, fontsize=10.5, family="monospace", transform=ax3.transAxes)
fig.tight_layout()
fig.savefig(ROOT / "results/router_board.png", dpi=110)
print("wrote results/router_board.png", rid)
