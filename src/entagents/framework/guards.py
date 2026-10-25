"""Input and output guards: PII redaction, prompt-injection screening and tool allow-lists.

The PII patterns follow the approach in Jagadish-pii-guard (pattern plus checksum where one
exists) but are rewritten here so this repo has no runtime dependency on it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+1[ -]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")
SSN = re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def luhn_ok(digits: str) -> bool:
    ds = [int(c) for c in digits if c.isdigit()]
    if not 13 <= len(ds) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(ds)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@dataclass
class Redaction:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def redact(text: str) -> Redaction:
    """Replace emails, phones, SSNs and Luhn-valid card numbers with typed placeholders."""
    counts: dict[str, int] = {}

    def sub(kind: str, pattern: re.Pattern[str], s: str, check=None) -> str:
        def rep(m: re.Match[str]) -> str:
            if check and not check(m.group(0)):
                return m.group(0)
            counts[kind] = counts.get(kind, 0) + 1
            return f"[{kind}]"

        return pattern.sub(rep, s)

    out = sub("EMAIL", EMAIL, text)
    out = sub("CARD", CARD, out, luhn_ok)
    out = sub("SSN", SSN, out)
    out = sub("PHONE", PHONE, out)
    return Redaction(out, counts)


INJECTION_PATTERNS = [
    r"ignore (?:all |any )?(?:previous|prior|above) (?:instructions|rules)",
    r"disregard (?:the |your )?(?:system|previous) (?:prompt|instructions)",
    r"you are now (?:in )?(?:developer|dan|admin) mode",
    r"reveal (?:your|the) (?:system prompt|hidden instructions|api key)",
    r"(?:print|show|dump) (?:all )?(?:secrets|credentials|env(?:ironment)? variables)",
    r"\bdrop\s+table\b",
    r"exfiltrate|send (?:the )?data to http",
    r"<\s*/?\s*system\s*>",
]
_INJ = [re.compile(p, re.I) for p in INJECTION_PATTERNS]


def injection_hits(text: str) -> list[str]:
    """Return the patterns a piece of untrusted text matches (empty list means it looks clean)."""
    return [p.pattern for p in _INJ if p.search(text)]


class ToolDenied(PermissionError):
    pass


@dataclass(frozen=True)
class ToolPolicy:
    """Least-privilege allow-list. Tools not listed are denied; risky tools need human approval."""

    allowed: frozenset[str]
    risky: frozenset[str] = frozenset()

    def check(self, tool: str) -> None:
        if tool not in self.allowed:
            raise ToolDenied(f"tool '{tool}' is not on this agent's allow-list")
