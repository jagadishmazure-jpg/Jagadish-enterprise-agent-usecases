"""System-design controls: model-tier routing, a response cache, a retry budget and a token/cost meter.

The "models" here are deterministic local functions, so the cost figures are simulated unit prices
(labelled as such in every report). They exist to show the accounting, not real spend.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field

# Simulated price per 1k tokens for two local tiers (not a real price list).
TIER_PRICE_PER_1K = {"small": 0.0002, "large": 0.0030}


def tokens(text: str) -> int:
    """Rough token estimate: whitespace words * 1.3, rounded up (good enough for metering)."""
    n = len(text.split())
    return -(-n * 13 // 10)


def route(text: str, hard: bool = False) -> str:
    """Send short, simple requests to the small tier; long or flagged-hard ones to the large tier."""
    return "large" if hard or tokens(text) > 400 else "small"


class LRUCache:
    def __init__(self, size: int = 256) -> None:
        self.size, self.data, self.hits, self.misses = size, OrderedDict(), 0, 0

    @staticmethod
    def key(*parts: object) -> str:
        return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()

    def get(self, k: str):
        if k in self.data:
            self.data.move_to_end(k)
            self.hits += 1
            return self.data[k]
        self.misses += 1
        return None

    def put(self, k: str, v) -> None:
        self.data[k] = v
        self.data.move_to_end(k)
        while len(self.data) > self.size:
            self.data.popitem(last=False)


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class RetryBudget:
    """Retries allowed as a fraction of first attempts (plus a small floor), so retries cannot storm."""

    ratio: float = 0.2
    floor: int = 3
    attempts: int = 0
    retries: int = 0

    def call(self, fn, *a, max_tries: int = 3, **kw):
        self.attempts += 1
        last: Exception | None = None
        for i in range(max_tries):
            if i:
                if self.retries >= self.floor + self.ratio * self.attempts:
                    raise BudgetExhausted("retry budget spent") from last
                self.retries += 1
            try:
                return fn(*a, **kw)
            except (TimeoutError, ConnectionError) as e:
                last = e
        raise BudgetExhausted(f"gave up after {max_tries} tries") from last


@dataclass
class Meter:
    by_tier: dict[str, int] = field(default_factory=lambda: {"small": 0, "large": 0})
    calls: int = 0

    def add(self, tier: str, n: int) -> None:
        self.by_tier[tier] += n
        self.calls += 1

    @property
    def simulated_cost(self) -> float:
        return round(sum(TIER_PRICE_PER_1K[t] * n / 1000 for t, n in self.by_tier.items()), 6)
