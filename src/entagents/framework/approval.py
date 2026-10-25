"""Human-in-the-loop gate. Risky actions wait in a queue until a named person approves them."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PendingAction:
    id: int
    agent: str
    action: str
    detail: dict
    status: str = "pending"  # pending | approved | rejected
    by: str | None = None


@dataclass
class ApprovalQueue:
    items: list[PendingAction] = field(default_factory=list)

    def request(self, agent: str, action: str, detail: dict) -> PendingAction:
        p = PendingAction(len(self.items), agent, action, detail)
        self.items.append(p)
        return p

    def decide(self, pid: int, approve: bool, by: str) -> PendingAction:
        if not by:
            raise ValueError("a named approver is required")
        p = self.items[pid]
        if p.status != "pending":
            raise ValueError(f"action {pid} already {p.status}")
        p.status, p.by = ("approved" if approve else "rejected"), by
        return p

    def executed(self, pid: int) -> bool:
        return self.items[pid].status == "approved"
