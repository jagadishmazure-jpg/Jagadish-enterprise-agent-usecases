"""Documentation writer: API reference in Markdown from Python source, plus a list of gaps."""

from __future__ import annotations

import ast

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent


def signature(fn: ast.FunctionDef) -> str:
    args = fn.args
    defaults = [None] * (len(args.args) - len(args.defaults)) + list(args.defaults)
    parts = []
    for a, d in zip(args.args, defaults, strict=True):
        s = a.arg + (f": {ast.unparse(a.annotation)}" if a.annotation else "")
        parts.append(s + (f" = {ast.unparse(d)}" if d is not None else ""))
    ret = f" -> {ast.unparse(fn.returns)}" if fn.returns else ""
    return f"{fn.name}({', '.join(parts)}){ret}"


def write_docs(src: str, title: str = "module") -> dict:
    tree = ast.parse(src)
    md = [f"# {title}", "", (ast.get_docstring(tree) or "_No module docstring._"), ""]
    gaps, documented = [], []
    items = [(n, None) for n in tree.body if isinstance(n, ast.FunctionDef)]
    for c in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        md += [f"## class `{c.name}`", "", ast.get_docstring(c) or "_Undocumented._", ""]
        if not ast.get_docstring(c):
            gaps.append(c.name)
        items += [(n, c.name) for n in c.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    for fn, owner in items:
        if fn.name.startswith("_") and owner is None:
            continue
        qual = f"{owner}.{fn.name}" if owner else fn.name
        doc = ast.get_docstring(fn)
        md += [f"### `{signature(fn)}`" if not owner else f"### `{owner}.{signature(fn)}`", "", doc.splitlines()[0] if doc else "_Undocumented._", ""]
        (documented if doc else gaps).append(qual)
        if not fn.returns:
            gaps.append(f"{qual} (no return type)")
    return {"markdown": "\n".join(md), "documented": documented, "gaps": gaps}


SAMPLES = [
    ('"""Pricing helpers."""\n\ndef net(gross: float, rate: float = 0.2) -> float:\n    """Remove tax."""\n    return gross / (1 + rate)\n', (["net"], [])),
    ("def a(x):\n    return x\n\ndef _hidden():\n    pass\n", ([], ["a", "a (no return type)"])),
    (
        'class Cart:\n    """A basket."""\n\n    def add(self, sku: str) -> None:\n        """Add one item."""\n\n    def total(self):\n        return 0\n',
        (["Cart.add"], ["Cart.total", "Cart.total (no return type)"]),
    ),
    ('def f(a: int, b: int = 2) -> int:\n    """Sum."""\n    return a + b\n\ndef g() -> str:\n    """Hi."""\n    return "hi"\n', (["f", "g"], [])),
    ("class Empty:\n    pass\n", ([], ["Empty"])),
    ('def parse(text: str) -> list[str]:\n    """Split lines.\n\n    Longer text here.\n    """\n    return text.splitlines()\n', (["parse"], [])),
]


class DocWriterAgent(Agent):
    META = {
        "name": "doc-writer",
        "title": "Documentation writer",
        "level": "Beginner",
        "tech": "Python AST",
        "industry": "Software engineering",
        "tags": ["documentation", "devex", "code-analysis"],
        "summary": "Writes a Markdown API reference from source code and lists what is undocumented or missing a return type.",
        "guardrails": ["reads source only, never executes it", "describes only what the code declares", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"ast.parse"}))

    def handle(self, ctx, payload):
        return ctx.tool("ast.parse", write_docs, payload["code"], payload.get("title", "module"))

    def demo(self):
        return {"code": SAMPLES[2][0], "title": "cart"}

    def eval_cases(self):
        return [({"code": c}, e) for c, e in SAMPLES]

    def score(self, res, expected):
        o = res["output"]
        return float((o["documented"], o["gaps"]) == expected)


AGENT = DocWriterAgent()
