"""Multi-agent debate with a judge.

Two debaters argue a motion from a shared evidence pool, each citing evidence ids. The judge
scores only verified citations (fabricated ids cost points), ignores wording length, and is run
in both speaking orders to measure order bias (order-flip rate).
"""

from __future__ import annotations

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

# Evidence: id -> (motion, stance, strength 1-3, text). Synthetic.
EVIDENCE = {
    "e1": ("remote", "pro", 3, "Pilot teams kept delivery dates while cutting commute time."),
    "e2": ("remote", "pro", 2, "Hiring pool widened to three new regions."),
    "e3": ("remote", "con", 2, "New joiners reported slower onboarding."),
    "e4": ("remote", "con", 1, "Some ad-hoc conversations were lost."),
    "e5": ("rewrite", "pro", 1, "The old codebase uses an unsupported framework version."),
    "e6": ("rewrite", "con", 3, "Past rewrites at the firm ran 2x over schedule."),
    "e7": ("rewrite", "con", 2, "Incremental refactoring already cut incidents by a third."),
    "e8": ("rewrite", "pro", 1, "Engineers prefer modern tooling."),
    "e9": ("cache", "pro", 3, "A cache cut p95 latency from 800 ms to 120 ms in the test."),
    "e10": ("cache", "con", 1, "Cache invalidation adds some complexity."),
    "e11": ("cache", "pro", 1, "Database load fell by half."),
    "e12": ("vendor", "pro", 2, "A managed service removes on-call for the queue."),
    "e13": ("vendor", "con", 2, "Data residency terms are unclear."),
}


def debater(motion: str, stance: str, k: int = 3, fabricate: bool = False, verbose: bool = False) -> dict:
    ev = sorted([(i, e) for i, e in EVIDENCE.items() if e[0] == motion and e[1] == stance], key=lambda x: -x[1][2])[:k]
    cites = [i for i, _ in ev] + (["e99"] if fabricate else [])
    text = " ".join(e[3] for _, e in ev)
    if verbose:
        text += " Furthermore, it is extremely important to consider this very carefully and at length." * 5
    return {"stance": stance, "cites": cites, "argument": text}


def judge(motion: str, first: dict, second: dict) -> dict:
    scores = {}
    for side in (first, second):
        s = 0
        for c in side["cites"]:
            e = EVIDENCE.get(c)
            if e is None or e[0] != motion or e[1] != side["stance"]:
                s -= 2  # fabricated or off-topic citation
            else:
                s += e[2]
        scores[side["stance"]] = s
    winner = "tie" if scores["pro"] == scores["con"] else max(scores, key=scores.get)
    return {"scores": scores, "winner": winner}


def debate(motion: str, fabricate_side: str | None = None, verbose_side: str | None = None) -> dict:
    pro = debater(motion, "pro", fabricate=fabricate_side == "pro", verbose=verbose_side == "pro")
    con = debater(motion, "con", fabricate=fabricate_side == "con", verbose=verbose_side == "con")
    a, b = judge(motion, pro, con), judge(motion, con, pro)
    return {"motion": motion, "pro": pro, "con": con, "verdict": a, "verdict_swapped_order": b, "order_flip": a["winner"] != b["winner"]}


CASES = [
    ({"motion": "remote"}, "pro"),
    ({"motion": "rewrite"}, "con"),
    ({"motion": "cache"}, "pro"),
    ({"motion": "vendor"}, "tie"),
    ({"motion": "remote", "fabricate_side": "pro"}, "tie"),  # the -2 penalty erases the lead
    ({"motion": "cache", "fabricate_side": "pro"}, "pro"),
    ({"motion": "vendor", "fabricate_side": "con"}, "pro"),
    ({"motion": "rewrite", "verbose_side": "pro"}, "con"),
    ({"motion": "vendor", "verbose_side": "pro"}, "tie"),
]


class DebateAgent(Agent):
    META = {
        "name": "debate-judge",
        "title": "Multi-agent debate with a judge",
        "level": "Advanced",
        "tech": "Two debaters + evidence-scored judge",
        "industry": "Decision support",
        "tags": ["multi-agent", "llm-as-judge", "bias-testing", "citations"],
        "summary": "Two agents argue a decision from shared evidence; a judge scores verified citations, penalises made-up ones and is checked for order and length bias.",
        "guardrails": ["judge scores verified citations only", "fabricated citations penalised", "both speaking orders judged (order-flip rate)", "length ignored (verbosity probe)", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"evidence.read"}))
    HARD = True

    def handle(self, ctx, payload):
        return ctx.tool("evidence.read", debate, payload["motion"], payload.get("fabricate_side"), payload.get("verbose_side"))

    def demo(self):
        return {"motion": "rewrite"}

    def eval_cases(self):
        return CASES

    def score(self, res, expected):
        o = res["output"]
        return float(o["verdict"]["winner"] == expected and not o["order_flip"])


AGENT = DebateAgent()
