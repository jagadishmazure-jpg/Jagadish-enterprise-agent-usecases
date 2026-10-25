"""Reusable stopping policy for agent loops.

A loop ends in exactly one named state. Success needs a verified result; an error, a cap or a
stall can never be reported as success. Caps: turns, cost and a wall-clock deadline (the clock is
injectable so tests do not sleep). Stall: the same action with the same arguments, or the same
state, repeated `stall_window` times in a row.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class End(str, Enum):
    SUCCESS = "success"
    NO_OP = "no-op"
    BLOCKED = "blocked"
    STALLED = "stalled"
    EXHAUSTED = "exhausted"


def _h(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()[:16]


@dataclass
class LoopPolicy:
    max_turns: int = 6
    max_cost_usd: float = 0.01
    deadline_s: float = 30.0
    stall_window: int = 3
    clock: object = time.monotonic
    turns: int = 0
    cost: float = 0.0
    reason: str = ""
    _start: float | None = None
    _recent: deque = field(default_factory=deque)

    def start(self) -> None:
        self._start = self.clock()
        self.turns, self.cost, self._recent = 0, 0.0, deque(maxlen=self.stall_window)

    def step(self, action: str, args, state, cost: float) -> End | None:
        """Record one turn. Returns an End state if the loop must stop now, else None."""
        if self._start is None:
            self.start()
        self.turns += 1
        self.cost += cost
        self._recent.append((_h([action, args]), _h(state)))
        if self.cost > self.max_cost_usd:
            return self._stop(End.EXHAUSTED, f"cost {self.cost:.6f} > cap {self.max_cost_usd}")
        if self.clock() - self._start > self.deadline_s:
            return self._stop(End.EXHAUSTED, "deadline passed")
        if len(self._recent) == self.stall_window and (len({a for a, _ in self._recent}) == 1 or len({s for _, s in self._recent}) == 1):
            return self._stop(End.STALLED, f"no progress over {self.stall_window} turns")
        if self.turns >= self.max_turns:
            return self._stop(End.EXHAUSTED, f"turn cap {self.max_turns}")
        return None

    def finish(self, verified: bool, changed: bool = True, error: str | None = None) -> End:
        """Close a loop that stopped by itself. Errors and unverified results never count as success."""
        if error:
            return self._stop(End.BLOCKED, error)
        if not verified:
            return self._stop(End.BLOCKED, "result failed verification")
        if not changed:
            return self._stop(End.NO_OP, "nothing to change")
        return self._stop(End.SUCCESS, "verified")

    def _stop(self, end: End, why: str) -> End:
        self.reason = why
        return end


def cost_per_accepted_change(total_cost: float, accepted: int) -> float | None:
    """Spend divided by results that passed verification. None when nothing was accepted (cost is wasted, not free)."""
    return None if accepted == 0 else total_cost / accepted
