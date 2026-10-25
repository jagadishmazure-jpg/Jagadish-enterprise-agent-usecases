"""The same invoice task at each layer. The model is SIMULATED (deterministic rules that stand in
for what a model would return given what that layer feeds it); token, cost and latency meters are
simulated and labelled. Decisions are scored against gold labels on synthetic invoices.
"""

from __future__ import annotations

import json
import re

from ..agents.invoice_extract import extract, validate
from . import registry
from .graph import END, Graph, Runner
from .loop_policy import End, LoopPolicy
from .sim import Meter
from .task import APPROVED_VENDORS, INJECTION, POLICY, Case

CTX_BUDGET = 260  # tokens of policy text a layer may pack into the prompt
INJ = re.compile(r"ignore (the )?(policy|previous|instructions)|approve this invoice immediately", re.I)
OCR_FIX = {"Tota1:": "Total:", "Subt0tal:": "Subtotal:"}
NOISE = re.compile(r"^[A-Za-z]*[0-9#@][A-Za-z0-9#@]*:", re.M)


def scan_noise(text: str) -> bool:
    """True when a field label holds digits or symbols, the usual sign of a scan error."""
    return bool(NOISE.search(text))


# ---- shared helpers -------------------------------------------------------------------------
def retrieve(query: str, budget: int = CTX_BUDGET, k: int = 6) -> list[tuple[str, str]]:
    """Rank clauses by word overlap with the query, then pack the best ones into the token budget."""
    q = set(re.findall(r"[a-z]+", query.lower()))
    scored = sorted(POLICY, key=lambda c: (-len(q & set(re.findall(r"[a-z]+", c[1].lower()))), c[0]))
    out, used = [], 0
    for cid, text in scored[:k]:
        t = len(text) // 4 + 1
        if used + t > budget:
            continue
        out.append((cid, text))
        used += t
    return out


def fmt(clauses) -> str:
    return "\n".join(f"[{c}] {t}" for c, t in clauses)


def apply_rules(rec: dict, errs: list[str], have: set, injected: bool, guard: bool, arithmetic: bool) -> tuple[str, str | None]:
    """What the (simulated) model decides with the clauses it was given."""
    if injected and not guard:
        return "approve", None  # a model with no guard follows text embedded in the invoice
    if injected and guard and "AP-6" in have:
        return "hold", "AP-6"
    if any(e.startswith("missing") for e in errs):
        return "reject", "AP-4" if "AP-4" in have else None
    if arithmetic and errs and "AP-3" in have:
        return "reject", "AP-3"
    if "AP-1" in have and rec.get("vendor") not in APPROVED_VENDORS:
        return "hold", "AP-1"
    if "AP-2" in have and (rec.get("total") or 0) > 5000:
        return "hold", "AP-2"
    return "approve", "AP-5" if "AP-5" in have else None


def out_json(**kw) -> str:
    return json.dumps(kw, sort_keys=True)


def result(case: Case, decision: str, clause, meter: Meter, checked: bool, **extra) -> dict:
    return {
        "cid": case.cid,
        "kind": case.kind,
        "gold": case.gold,
        "decision": decision,
        "clause": clause,
        "correct": decision == case.gold,
        "cited_ok": decision == case.gold and clause == case.clause,
        "checked": checked,
        "tokens": meter.tin + meter.tout,
        "cost": meter.cost,
        "ms": meter.ms,
        "calls": meter.calls,
        **extra,
    }


# ---- L1 prompt ------------------------------------------------------------------------------
def l1(case: Case) -> dict:
    p, m = registry.load("invoice_policy", 1), Meter()
    rec = extract(case.text)
    errs = validate(rec)
    d, c = apply_rules(rec, errs, set(), INJECTION in case.text, guard=False, arithmetic=False)
    m.charge(p.render(case.text), out_json(invoice_no=rec["invoice_no"], decision=d), "answer")
    return result(case, d, c, m, checked=False)


# ---- L2 context -----------------------------------------------------------------------------
def l2(case: Case) -> dict:
    p, m = registry.load("invoice_policy", 2), Meter()
    rec = extract(case.text)
    errs = validate(rec)
    cands = retrieve("payables invoice vendor approved total threshold required fields arithmetic embedded instructions approval")
    m.charge("Rank these clauses for an invoice review and keep the relevant ones:\n" + fmt(cands), " ".join(c for c, _ in cands), "rank")
    d, c = apply_rules(rec, errs, {c for c, _ in cands}, INJECTION in case.text, guard=False, arithmetic=False)
    m.charge(p.render(case.text, fmt(cands)), out_json(invoice_no=rec["invoice_no"], decision=d, clause=c), "answer")
    return result(case, d, c, m, checked=False, ctx_clauses=len(cands))


# ---- L3 harness (tools, guards, schema, retries) --------------------------------------------
def _harness_core(text: str, m: Meter, flaky: bool) -> tuple[dict, list, list, bool, int]:
    rec = extract(text)  # extraction tool (deterministic parser) replaces free-form reading
    m.charge("Extract invoice fields as JSON with keys invoice_no,date,vendor,lines,subtotal,tax,total:\n" + text, json.dumps(rec), "extract")
    errs = validate(rec)  # schema + arithmetic tool
    retries = 0
    if flaky:  # vendor-list lookup fails once on some cases; retried within a budget of 2
        retries = 1
    cands = retrieve("payables invoice vendor approved total threshold required fields arithmetic embedded instructions approval")
    m.charge("Rank these clauses for an invoice review and keep the relevant ones:\n" + fmt(cands), " ".join(c for c, _ in cands), "rank")
    injected = bool(INJ.search(text))
    return rec, errs, cands, injected, retries


def l3(case: Case, idx: int = 0) -> dict:
    p, m = registry.load("invoice_policy", 2), Meter()
    rec, errs, cands, injected, retries = _harness_core(case.text, m, flaky=idx % 4 == 3)
    d, c = apply_rules(rec, errs, {c for c, _ in cands}, injected, guard=True, arithmetic=True)
    m.charge(p.render("(fields) " + json.dumps(rec), fmt(cands)), out_json(invoice_no=rec["invoice_no"], decision=d, clause=c), "decide")
    ok = d in ("approve", "hold", "reject") and (c is not None)
    return result(case, d if ok else "hold", c, m, checked=True, retries=retries, guard_hit=injected)


# ---- L4 loop (plan, act, review, retry or stop) ---------------------------------------------
def review(rec: dict, errs: list[str]) -> str:
    """Reviewer verdict. 'repairable' when fields are missing and the text shows known scan errors."""
    return "pass" if not errs else "fail"


def l4(case: Case, idx: int = 0, policy: LoopPolicy | None = None) -> dict:
    p, m = registry.load("invoice_policy", 2), Meter()
    pol = policy or LoopPolicy(max_turns=4, max_cost_usd=0.002, stall_window=2, clock=lambda: 0.0)
    pol.start()
    text, end, repairs = case.text, None, 0
    rec, errs, cands, injected, retries = _harness_core(text, m, flaky=idx % 4 == 3)
    while True:
        m.charge("Review: do these fields reconcile? " + json.dumps(rec), "pass" if not errs else "fail: " + "; ".join(errs), "review")
        missing = any(e.startswith("missing") for e in errs)
        if not missing or injected or not scan_noise(text):
            end = pol.finish(verified=True)
            break
        fixed = text
        for a, b in OCR_FIX.items():
            fixed = fixed.replace(a, b)
        m.charge("Repair likely scan errors in field labels:\n" + text, fixed, "repair")
        repairs += 1
        stop = pol.step("repair", "ocr-labels", fixed, m.cost)
        text = fixed
        rec = extract(text)
        errs = validate(rec)
        if stop:
            end = stop
            break
    if end in (End.STALLED, End.EXHAUSTED):
        d, c = "hold", "LOOP-" + end.value  # never a silent success: a person looks at it
    else:
        d, c = apply_rules(rec, errs, {c for c, _ in cands}, injected, guard=True, arithmetic=True)
        m.charge(p.render("(fields) " + json.dumps(rec), fmt(cands)), out_json(invoice_no=rec["invoice_no"], decision=d, clause=c), "decide")
    return result(case, d, c, m, checked=True, end=end.value, repairs=repairs, retries=retries)


# ---- L5 graph -------------------------------------------------------------------------------
SCHEMA = {
    "text": str,
    "rec": dict,
    "errs": list,
    "clauses": list,
    "injected": bool,
    "repairs": int,
    "decision": str,
    "clause": str,
    "end": str,
    "approved": bool,
    "ms_extract": float,
    "ms_rank": float,
    "ms_other": float,
    "tin": int,
    "tout": int,
    "calls": int,
}


def build_graph(crash_at: set | None = None, bad_router: bool = False) -> Graph:
    crash_at = crash_at if crash_at is not None else set()
    p = registry.load("invoice_policy", 2)

    def metered(state, prompt, out, key):
        m = Meter()
        ms = m.charge(prompt, out, key)
        return {"tin": state.get("tin", 0) + m.tin, "tout": state.get("tout", 0) + m.tout, "calls": state.get("calls", 0) + 1, "_ms": ms}

    def ingest(s):
        return {"injected": bool(INJ.search(s["text"])), "repairs": 0, "tin": 0, "tout": 0, "calls": 0, "ms_other": 0.0}

    def extract_node(s):
        if "extract" in crash_at:
            crash_at.discard("extract")
            raise RuntimeError("simulated crash in extract")
        rec = extract(s["text"])
        m = Meter()
        ms = m.charge("Extract invoice fields as JSON with keys invoice_no,date,vendor,lines,subtotal,tax,total:\n" + s["text"], json.dumps(rec), "extract")
        return {"rec": rec, "errs": validate(rec), "ms_extract": ms, "_t": (m.tin, m.tout)}

    def rank_node(s):
        cands = retrieve("payables invoice vendor approved total threshold required fields arithmetic embedded instructions approval")
        m = Meter()
        ms = m.charge("Rank these clauses for an invoice review and keep the relevant ones:\n" + fmt(cands), " ".join(c for c, _ in cands), "rank")
        return {"clauses": [c for c, _ in cands], "ms_rank": ms, "_t": (m.tin, m.tout)}

    def join(s):
        return {}

    def review_node(s):
        if "review" in crash_at:
            crash_at.discard("review")
            raise RuntimeError("simulated crash in review")
        u = metered(s, "Review: do these fields reconcile? " + json.dumps(s["rec"]), "pass" if not s["errs"] else "fail", "review")
        return {"tin": u["tin"], "tout": u["tout"], "calls": u["calls"], "ms_other": s["ms_other"] + u["_ms"]}

    def repair(s):
        fixed = s["text"]
        for a, b in OCR_FIX.items():
            fixed = fixed.replace(a, b)
        u = metered(s, "Repair likely scan errors in field labels:\n" + s["text"], fixed, "repair")
        rec = extract(fixed)
        return {"text": fixed, "rec": rec, "errs": validate(rec), "repairs": s["repairs"] + 1, "tin": u["tin"], "tout": u["tout"], "calls": u["calls"], "ms_other": s["ms_other"] + u["_ms"]}

    def route_after_review(s):
        if bad_router:
            return "pay_now"  # a target that does not exist in the declared set
        missing = any(e.startswith("missing") for e in s["errs"])
        if missing and not s["injected"] and scan_noise(s["text"]):
            return "repair" if s["repairs"] < 2 else "stalled"
        return "decide"

    def stalled(s):
        return {"decision": "hold", "clause": "LOOP-stalled", "end": End.STALLED.value}

    def decide(s):
        d, c = apply_rules(s["rec"], s["errs"], set(s["clauses"]), s["injected"], guard=True, arithmetic=True)
        u = metered(s, p.render("(fields) " + json.dumps(s["rec"]), fmt([(x, dict(POLICY)[x]) for x in s["clauses"]])), out_json(decision=d, clause=c), "decide")
        return {"decision": d, "clause": c or "", "end": End.SUCCESS.value, "tin": u["tin"], "tout": u["tout"], "calls": u["calls"], "ms_other": s["ms_other"] + u["_ms"]}

    def route_after_decide(s):
        return "human" if s["decision"] == "hold" else END

    def human(s):
        return {} if s.get("approved") else {"decision": "hold"}

    def rec_after_repair(s):
        return "review"

    g = Graph(schema=SCHEMA)
    g.node("ingest", ingest).node("extract", _strip(extract_node)).node("rank", _strip(rank_node)).node("join", join)
    g.node("review", review_node).node("repair", repair).node("stalled", stalled).node("decide", decide).node("human", human, interrupt=True)
    g.parallel("ingest", ["extract", "rank"], "join").edge("join", "review")
    g.cond("review", route_after_review, {"repair", "decide", "stalled"}).cond("repair", rec_after_repair, {"review"})
    g.edge("stalled", "human").cond("decide", route_after_decide, {"human", END}).edge("human", END)
    return g


def _strip(fn):
    """Parallel branches return their own token counts in '_t'; fold them into named keys."""

    def wrapped(s):
        u = fn(s)
        tin, tout = u.pop("_t")
        key = "ms_extract" if "ms_extract" in u else "ms_rank"
        return {**u, ("tin_e" if key == "ms_extract" else "tin_r"): tin, ("tout_e" if key == "ms_extract" else "tout_r"): tout}

    return wrapped


SCHEMA.update({"tin_e": int, "tin_r": int, "tout_e": int, "tout_r": int})


def l5(case: Case, store: dict | None = None, crash_at: set | None = None) -> dict:
    g = build_graph(crash_at)
    store = {} if store is None else store
    runner = Runner(g, store)
    thread = case.cid
    crashes = 0
    while True:
        try:
            out = runner.run({"text": case.text} if thread not in store else None, thread=thread)
            break
        except RuntimeError:
            crashes += 1
            if crashes > 3:
                raise
        except Exception as e:  # Interrupted: a person reviews holds; the demo records the pause and keeps the hold
            if type(e).__name__ != "Interrupted":
                raise
            out = runner.run(thread=thread, approve=False)
            break
    s = out["state"]
    m = Meter()
    m.tin = s["tin"] + s["tin_e"] + s["tin_r"]
    m.tout = s["tout"] + s["tout_e"] + s["tout_r"]
    m.calls = s["calls"] + 2
    m.ms = max(s["ms_extract"], s["ms_rank"]) + s["ms_other"]
    seq_ms = s["ms_extract"] + s["ms_rank"] + s["ms_other"]
    return result(case, s["decision"], s["clause"] or None, m, checked=True, end=s["end"], route=out["route"], route_hash=out["route_hash"], executed=list(runner.executed), seq_ms=seq_ms)
