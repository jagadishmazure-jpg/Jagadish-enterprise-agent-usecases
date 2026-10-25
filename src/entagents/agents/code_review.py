"""Static code review for Python snippets using the standard-library AST (no model needed).

Findings carry a rule id, line number and a fix hint. The reviewer never executes the code.
"""

from __future__ import annotations

import ast
import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

SECRET = re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]")
HINTS = {
    "eval-exec": "avoid eval/exec on data; parse it explicitly",
    "bare-except": "catch specific exceptions",
    "mutable-default": "use None as the default and create the list/dict inside",
    "shell-true": "pass an argument list and keep shell=False",
    "hardcoded-secret": "load secrets from the environment or a vault",
    "sql-format": "use parameterised queries",
    "assert-runtime": "do not rely on assert for runtime checks (stripped under -O)",
}


def review(src: str) -> list[dict]:
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"rule": "syntax", "line": e.lineno or 0, "hint": "file does not parse"}]
    out = []

    def add(rule: str, node: ast.AST) -> None:
        out.append({"rule": rule, "line": getattr(node, "lineno", 0), "hint": HINTS[rule]})

    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            if fname in {"eval", "exec"}:
                add("eval-exec", n)
            if any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords):
                add("shell-true", n)
            if fname in {"execute", "executemany"} and n.args and isinstance(n.args[0], ast.JoinedStr | ast.BinOp):
                add("sql-format", n)
            if fname in {"execute", "executemany"} and n.args and isinstance(n.args[0], ast.Call) and getattr(n.args[0].func, "attr", "") == "format":
                add("sql-format", n)
        elif isinstance(n, ast.ExceptHandler) and n.type is None:
            add("bare-except", n)
        elif isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
            for d in n.args.defaults + n.args.kw_defaults:
                if isinstance(d, ast.List | ast.Dict | ast.Set):
                    add("mutable-default", d)
        elif isinstance(n, ast.Assert):
            add("assert-runtime", n)
    for i, line in enumerate(src.splitlines(), 1):
        if SECRET.search(line):
            out.append({"rule": "hardcoded-secret", "line": i, "hint": HINTS["hardcoded-secret"]})
    return sorted(out, key=lambda x: (x["line"], x["rule"]))


CASES = [
    ("x = eval(user_input)\n", {"eval-exec"}),
    ("try:\n    go()\nexcept:\n    pass\n", {"bare-except"}),
    ("def f(a, items=[]):\n    items.append(a)\n    return items\n", {"mutable-default"}),
    ("import subprocess\nsubprocess.run(cmd, shell=True)\n", {"shell-true"}),
    ("API_KEY = 'placeholder-value-0001'\n", {"hardcoded-secret"}),
    ('cur.execute(f"select * from t where id={uid}")\n', {"sql-format"}),
    ("cur.execute('select * from t where id=%s' % uid)\n", {"sql-format"}),
    ("cur.execute('select * from t where id={}'.format(uid))\n", {"sql-format"}),
    ("def check(x):\n    assert x > 0\n    return x\n", {"assert-runtime"}),
    ("def ok(a, b=None):\n    b = b or []\n    return a + len(b)\n", set()),
    ("cur.execute('select * from t where id=?', (uid,))\n", set()),
    ("import subprocess\nsubprocess.run(['ls', '-l'])\n", set()),
    ("def g(d={}):\n    exec(d['code'])\n", {"mutable-default", "eval-exec"}),
    ("password = 'hunter22hunter22'\ntry:\n    x()\nexcept:\n    y()\n", {"hardcoded-secret", "bare-except"}),
    ("value = ast.literal_eval(text)\n", set()),
    # Known miss kept visible: aliasing eval defeats the name-based rule.
    ("run = eval\nrun(user_input)\n", {"eval-exec"}),
]


class CodeReviewAgent(Agent):
    META = {
        "name": "code-review",
        "title": "Code review",
        "level": "Intermediate",
        "tech": "Python AST rules",
        "industry": "Software engineering",
        "tags": ["static-analysis", "security", "devex"],
        "summary": "Reviews Python snippets for risky patterns and explains each finding with a fix hint.",
        "guardrails": ["never executes reviewed code", "AST parse only", "secret values masked in findings", "injection screen", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"ast.parse"}))

    def handle(self, ctx, payload):
        findings = ctx.tool("ast.parse", review, payload["code"])
        return {"findings": findings, "verdict": "changes requested" if findings else "looks fine"}

    def demo(self):
        return {"code": CASES[12][0] + CASES[3][0]}

    def eval_cases(self):
        return [({"code": c}, exp) for c, exp in CASES]

    def score(self, res, expected):
        got = {f["rule"] for f in res["output"]["findings"]}
        return float(got == expected)


AGENT = CodeReviewAgent()
