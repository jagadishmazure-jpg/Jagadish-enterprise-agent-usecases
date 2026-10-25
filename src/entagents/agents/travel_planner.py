"""Travel planner over a synthetic price catalog: fits a trip to a budget or says it cannot.

Booking is a risky action held for approval. Prices are made up for fictional carriers and hotels.
"""

from __future__ import annotations

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

CATALOG = {
    "lisbon": {
        "flights": [("Gullwing Air", 420), ("Saltmarsh Airways", 365)],
        "hotels": [("Tilework Inn", 95), ("Harbor Steps Hotel", 160)],
        "activities": [("tram tour", 25, "history"), ("fado night", 40, "music"), ("surf lesson", 70, "outdoors"), ("tile museum", 10, "history"), ("food walk", 55, "food")],
    },
    "kyoto": {
        "flights": [("Gullwing Air", 980), ("Paper Crane Air", 870)],
        "hotels": [("Maple Lane Ryokan", 140), ("Station Pod Hotel", 60)],
        "activities": [("temple walk", 15, "history"), ("tea ceremony", 45, "culture"), ("bamboo hike", 0, "outdoors"), ("market tasting", 35, "food")],
    },
    "reykjavik": {
        "flights": [("Northlight Air", 510)],
        "hotels": [("Basalt House", 180)],
        "activities": [("glacier hike", 120, "outdoors"), ("hot spring", 60, "wellness"), ("whale boat", 95, "outdoors")],
    },
}


def plan(city: str, nights: int, budget: float, interests: list[str]) -> dict:
    c = CATALOG.get(city.lower())
    if not c:
        return {"feasible": False, "reason": f"no catalog data for '{city}'"}
    flight = min(c["flights"], key=lambda f: f[1])
    hotel = min(c["hotels"], key=lambda h: h[1])
    base = flight[1] + hotel[1] * nights
    if base > budget:
        return {"feasible": False, "reason": f"cheapest flight and hotel cost {base}, over the budget of {budget}", "minimum": base}
    left = budget - base
    picks = []
    for name, price, tag in sorted(c["activities"], key=lambda a: (a[2] not in interests, a[1])):
        if price <= left and (tag in interests or not interests):
            picks.append({"activity": name, "price": price, "why": tag})
            left -= price
    total = budget - left
    return {
        "feasible": True,
        "flight": {"carrier": flight[0], "price": flight[1]},
        "hotel": {"name": hotel[0], "per_night": hotel[1], "nights": nights},
        "activities": picks,
        "total": total,
        "under_budget_by": round(left, 2),
    }


CASES = [
    ({"city": "Lisbon", "nights": 4, "budget": 1000, "interests": ["history", "food"]}, (True, {"tram tour", "tile museum", "food walk"})),
    ({"city": "Lisbon", "nights": 4, "budget": 800, "interests": ["music"]}, (True, {"fado night"})),
    ({"city": "Kyoto", "nights": 5, "budget": 1000, "interests": ["history"]}, (False, None)),
    ({"city": "Kyoto", "nights": 5, "budget": 1300, "interests": ["outdoors", "culture"]}, (True, {"bamboo hike", "tea ceremony"})),
    ({"city": "Reykjavik", "nights": 3, "budget": 1300, "interests": ["outdoors"]}, (True, {"glacier hike", "whale boat"})),
    ({"city": "Atlantis", "nights": 2, "budget": 5000, "interests": []}, (False, None)),
    ({"city": "Reykjavik", "nights": 3, "budget": 1250, "interests": ["outdoors", "wellness"]}, (True, {"hot spring", "whale boat"})),
]


class TravelAgent(Agent):
    META = {
        "name": "travel-planner",
        "title": "Travel planner",
        "level": "Intermediate",
        "tech": "Constraint fitting over a price catalog",
        "industry": "Travel and hospitality",
        "tags": ["planning", "budget", "human-in-the-loop"],
        "summary": "Builds a trip from a synthetic catalog within a hard budget, explains each pick, and says so when the budget cannot work.",
        "guardrails": ["hard budget check (never exceeds)", "prices only from the catalog", "booking held for approval", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"catalog.search", "booking.create"}), risky=frozenset({"booking.create"}))

    def handle(self, ctx, payload):
        p = ctx.tool("catalog.search", plan, payload["city"], int(payload["nights"]), float(payload["budget"]), payload.get("interests", []))
        if p["feasible"]:
            p["booking_status"] = f"held for approval (#{ctx.request_approval('booking.create', {'city': payload['city'], 'total': p['total']})})"
        return p

    def demo(self):
        return {"city": "Lisbon", "nights": 4, "budget": 1000, "interests": ["history", "food"]}

    def eval_cases(self):
        return [(p, (*exp, p["budget"])) for p, exp in CASES]

    def score(self, res, expected):
        o = res["output"]
        feas, acts, budget = expected
        if not feas:
            return float(not o["feasible"] and not res["pending_approvals"])
        return float(o["feasible"] and o["total"] <= budget and {a["activity"] for a in o["activities"]} == acts)


AGENT = TravelAgent()
