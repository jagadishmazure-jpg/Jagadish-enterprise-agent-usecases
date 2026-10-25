"""Simulated model and meters. No network, no real model.

Token count: 1 token per 4 characters (rounded up), a common rule of thumb.
SIMULATED prices and latency, labelled everywhere they are shown:
  input $0.40 per 1M tokens, output $1.60 per 1M tokens,
  latency 350 ms per call + 0.02 ms per input token + 8 ms per output token.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

PRICE_IN, PRICE_OUT = 0.40 / 1e6, 1.60 / 1e6
CALL_MS, IN_MS, OUT_MS = 350.0, 0.02, 8.0


def tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


@dataclass
class Meter:
    calls: int = 0
    tin: int = 0
    tout: int = 0
    ms: float = 0.0
    log: list = field(default_factory=list)

    def charge(self, prompt: str, output: str, label: str) -> float:
        i, o = tokens(prompt), tokens(output)
        ms = CALL_MS + IN_MS * i + OUT_MS * o
        self.calls += 1
        self.tin += i
        self.tout += o
        self.ms += ms
        self.log.append((label, i, o, round(ms, 2)))
        return ms

    @property
    def cost(self) -> float:
        return self.tin * PRICE_IN + self.tout * PRICE_OUT
