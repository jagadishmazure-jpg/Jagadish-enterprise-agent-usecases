"""Invoice extraction into a strict schema with arithmetic validation (synthetic invoices).

Output keys are fixed; extra or missing fields fail validation. Totals must reconcile
(line items -> subtotal -> tax -> total), otherwise the invoice is routed to a person.
"""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

SCHEMA = {"invoice_no": str, "date": str, "vendor": str, "lines": list, "subtotal": float, "tax": float, "total": float}


def money(s: str) -> float:
    return float(s.replace(",", "").replace("$", ""))


def extract(text: str) -> dict:
    g = lambda p: (m.group(1).strip() if (m := re.search(p, text, re.I | re.M)) else None)  # noqa: E731
    lines = [{"item": d.strip(), "qty": int(q), "unit": money(u), "amount": money(a)} for d, q, u, a in re.findall(r"^\s*-\s*(.+?)\s+(\d+)\s*x\s*\$?([\d,.]+)\s*=\s*\$?([\d,.]+)\s*$", text, re.M)]
    rec = {
        "invoice_no": g(r"invoice\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Z0-9-]+)"),
        "date": g(r"date\s*:\s*(\d{4}-\d{2}-\d{2})"),
        "vendor": g(r"^from\s*:\s*(.+)$"),
        "lines": lines,
        "subtotal": money(v) if (v := g(r"subtotal\s*:\s*\$?([\d,.]+)")) else None,
        "tax": money(v) if (v := g(r"tax[^:\n]*:\s*\$?([\d,.]+)")) else None,
        "total": money(v) if (v := g(r"^total\s*:\s*\$?([\d,.]+)")) else None,
    }
    return rec


def validate(rec: dict) -> list[str]:
    errs = [f"missing {k}" for k, t in SCHEMA.items() if rec.get(k) is None or not isinstance(rec[k], t)]
    errs += [f"unexpected field {k}" for k in rec if k not in SCHEMA]
    if errs:
        return errs
    for ln in rec["lines"]:
        if abs(ln["qty"] * ln["unit"] - ln["amount"]) > 0.01:
            errs.append(f"line '{ln['item']}' does not multiply out")
    if abs(sum(ln["amount"] for ln in rec["lines"]) - rec["subtotal"]) > 0.01:
        errs.append("lines do not sum to subtotal")
    if abs(rec["subtotal"] + rec["tax"] - rec["total"]) > 0.01:
        errs.append("subtotal + tax != total")
    return errs


def make(no: str, lines: list[tuple[str, int, float]], tax_rate: float = 0.08, total_override: float | None = None, drop: str | None = None) -> str:
    sub = round(sum(q * u for _, q, u in lines), 2)
    tax = round(sub * tax_rate, 2)
    total = total_override if total_override is not None else round(sub + tax, 2)
    rows = [
        "From: Cobalt Fern Supplies",
        f"Invoice No: {no}",
        "Date: 2026-10-14",
        "",
        *[f"- {d} {q} x ${u:,.2f} = ${q * u:,.2f}" for d, q, u in lines],
        "",
        f"Subtotal: ${sub:,.2f}",
        f"Tax (8%): ${tax:,.2f}",
        f"Total: ${total:,.2f}",
    ]
    return "\n".join(r for r in rows if not (drop and r.lower().startswith(drop)))


CASES = [
    (make("INV-1001", [("Paper reams", 10, 4.5), ("Toner", 2, 89.0)]), "ok"),
    (make("INV-1002", [("Desk lamp", 3, 24.99)]), "ok"),
    (make("INV-1003", [("Server rack", 1, 1250.0), ("Cables", 20, 3.25)]), "ok"),
    (make("INV-1004", [("Chairs", 6, 149.0)], total_override=999.0), "subtotal + tax != total"),
    (make("INV-1005", [("Mugs", 12, 6.5)], drop="date"), "missing date"),
    (make("INV-1006", [("Notebooks", 50, 1.2), ("Pens", 100, 0.45)]), "ok"),
    (make("INV-1007", [("Monitor", 2, 219.0)], drop="subtotal"), "missing subtotal"),
    (make("INV-1008", [("Labels", 5, 12.0)]).replace("= $60.00", "= $65.00"), "line 'Labels' does not multiply out"),
]


class InvoiceAgent(Agent):
    META = {
        "name": "invoice-extract",
        "title": "Invoice extraction",
        "level": "Intermediate",
        "tech": "Regex extraction + strict schema + reconciliation",
        "industry": "Finance operations",
        "tags": ["document-ai", "structured-output", "validation", "human-review"],
        "summary": "Extracts invoice fields into a fixed schema, checks that every line and total adds up, and routes mismatches to a person.",
        "guardrails": ["fixed schema, extra or missing keys rejected", "arithmetic reconciliation", "mismatch routed to human review", "errors never echo raw values", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"doc.extract"}))

    def handle(self, ctx, payload):
        rec = ctx.tool("doc.extract", extract, payload["invoice"])
        errs = validate(rec)
        return {"record": rec if not errs else None, "status": "accepted" if not errs else "needs human review", "errors": errs}

    def demo(self):
        return {"invoice": CASES[0][0]}

    def eval_cases(self):
        return [({"invoice": t}, e) for t, e in CASES]

    def score(self, res, expected):
        o = res["output"]
        return float(o["status"] == "accepted" if expected == "ok" else expected in o["errors"])


AGENT = InvoiceAgent()
