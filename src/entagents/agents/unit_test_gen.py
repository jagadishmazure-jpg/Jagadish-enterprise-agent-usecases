"""Unit test generator: turns doctest examples into pytest tests, runs them in an isolated
subprocess and measures how many planted bugs (mutants) the generated tests catch.

Code is only executed if it passes an import and call allow-list first.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

SAFE_IMPORTS = {"math", "re", "statistics", "string", "decimal", "fractions"}
UNSAFE_CALLS = {"eval", "exec", "open", "compile", "__import__", "input", "globals", "setattr", "getattr"}


def safe_to_run(src: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False, "does not parse"
    for n in ast.walk(tree):
        if isinstance(n, ast.Import | ast.ImportFrom):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            if any(m.split(".")[0] not in SAFE_IMPORTS for m in mods):
                return False, f"import not allowed: {mods}"
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in UNSAFE_CALLS:
            return False, f"call not allowed: {n.func.id}"
        if isinstance(n, ast.Attribute) and n.attr.startswith("__"):
            return False, "dunder attribute access not allowed"
    return True, "ok"


def generate(src: str, module: str = "target") -> str:
    tree = ast.parse(src)
    lines = [f"from {module} import *  # noqa: F403", ""]
    for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
        doc = ast.get_docstring(fn) or ""
        examples = re.findall(r">>> (.+)\n\s*(.+)", doc)
        for i, (call, want) in enumerate(examples):
            lines += [f"def test_{fn.name}_{i}():", f"    assert {call} == {want}", ""]
    return "\n".join(lines)


def run_tests(src: str, tests: str, timeout: int = 20) -> dict:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "target.py").write_text(src)
        Path(d, "test_target.py").write_text(tests)
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", d], cwd=d, env=env, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603 - fixed argv, code passed safe_to_run first
    m = re.search(r"(\d+) passed", p.stdout)
    f = re.search(r"(\d+) failed", p.stdout)
    return {"passed": int(m.group(1)) if m else 0, "failed": int(f.group(1)) if f else 0}


SAMPLES = [
    (
        'def clamp(x, lo, hi):\n    """Limit x to [lo, hi].\n\n    >>> clamp(5, 0, 3)\n    3\n    >>> clamp(-1, 0, 3)\n    0\n    >>> clamp(2, 0, 3)\n    2\n    """\n    return max(lo, min(x, hi))\n',
        ("min(x, hi)", "min(x, lo)"),
    ),
    (
        'def slug(s):\n    """Lowercase words joined by dashes.\n\n    >>> slug("Hello World")\n    \'hello-world\'\n    >>> slug("  A  b ")\n    \'a-b\'\n    """\n    return "-".join(s.lower().split())\n',
        ('"-".join', '"_".join'),
    ),
    (
        'def vat(net, rate=0.2):\n    """Gross amount, rounded to cents.\n\n    >>> vat(100)\n    120.0\n    >>> vat(10, 0.05)\n    10.5\n    """\n    return round(net * (1 + rate), 2)\n',
        ("1 + rate", "1 - rate"),
    ),
    (
        'import statistics\n\ndef spread(xs):\n    """Max minus min.\n\n    >>> spread([3, 9, 4])\n    6\n    >>> spread([5])\n    0\n    """\n    return max(xs) - min(xs)\n',
        ("max(xs) - min(xs)", "max(xs) - statistics.mean(xs)"),
    ),
    (
        'def is_leap(y):\n    """Gregorian leap year.\n\n    >>> is_leap(2024)\n    True\n    >>> is_leap(1900)\n    False\n    >>> is_leap(2000)\n    True\n    """\n    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)\n',
        ("y % 400 == 0", "y % 300 == 0"),
    ),
    # Known miss kept visible: the only example does not exercise the mutated branch.
    (
        'def sign(x):\n    """Sign of x.\n\n    >>> sign(4)\n    1\n    """\n    return 1 if x > 0 else (-1 if x < 0 else 0)\n',
        ("-1 if x < 0", "1 if x < 0"),
    ),
]


class UnitTestGenAgent(Agent):
    META = {
        "name": "unit-test-gen",
        "title": "Unit test generator",
        "level": "Advanced",
        "tech": "AST + doctest mining + mutation check",
        "industry": "Software engineering",
        "tags": ["testing", "code-generation", "sandbox", "mutation-testing"],
        "summary": "Generates pytest tests from docstring examples, runs them in an isolated process and reports how many planted bugs they catch.",
        "guardrails": ["import and call allow-list before any execution", "subprocess with empty environment and timeout", "temporary directory only", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"code.generate", "sandbox.run"}))
    HARD = True

    def handle(self, ctx, payload):
        src = payload["code"]
        ok, why = safe_to_run(src)
        tests = ctx.tool("code.generate", generate, src) if ok else ""
        if not ok:
            return {"tests": "", "refused": why}
        base = ctx.tool("sandbox.run", run_tests, src, tests)
        out = {"tests": tests, "on_original": base}
        if payload.get("mutant"):
            a, b = payload["mutant"]
            out["on_mutant"] = ctx.tool("sandbox.run", run_tests, src.replace(a, b), tests)
            out["mutant_killed"] = out["on_mutant"]["failed"] > 0
        return out

    def demo(self):
        return {"code": SAMPLES[0][0], "mutant": list(SAMPLES[0][1])}

    def eval_cases(self):
        cases = [({"code": s, "mutant": list(m)}, True) for s, m in SAMPLES]
        cases.append(({"code": "import os\ndef f():\n    return os.listdir('/')\n"}, "refuse"))
        cases.append(({"code": "def f(s):\n    return eval(s)\n"}, "refuse"))
        return cases

    def score(self, res, expected):
        o = res["output"]
        if expected == "refuse":
            return float(bool(o.get("refused")))
        return float(o["on_original"]["failed"] == 0 and o["on_original"]["passed"] > 0 and o["mutant_killed"])


AGENT = UnitTestGenAgent()
