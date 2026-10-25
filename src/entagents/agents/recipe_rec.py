"""Recipe recommendation: rank by what is already in the pantry, with allergens as a hard filter."""

from __future__ import annotations

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

RECIPES = [
    ("tomato pasta", {"pasta", "tomato", "garlic", "olive oil"}, {"gluten"}, 20),
    ("peanut noodles", {"noodles", "peanut butter", "soy sauce", "lime"}, {"peanut", "gluten", "soy"}, 15),
    ("veg omelette", {"egg", "pepper", "onion", "cheese"}, {"egg", "dairy"}, 10),
    ("chickpea curry", {"chickpeas", "tomato", "onion", "coconut milk", "rice"}, set(), 35),
    ("shrimp stir fry", {"shrimp", "pepper", "soy sauce", "rice"}, {"shellfish", "soy"}, 20),
    ("lentil soup", {"lentils", "onion", "carrot", "garlic"}, set(), 40),
    ("cheese toastie", {"bread", "cheese", "butter"}, {"gluten", "dairy"}, 8),
    ("rice salad", {"rice", "pepper", "onion", "olive oil", "lime"}, set(), 15),
]


def recommend(pantry: list[str], allergies: list[str], max_minutes: int = 60, k: int = 3) -> dict:
    have, avoid = {p.lower() for p in pantry}, {a.lower() for a in allergies}
    ranked, excluded = [], []
    for name, ing, allergens, mins in RECIPES:
        if allergens & avoid:
            excluded.append({"recipe": name, "because": sorted(allergens & avoid)})
            continue
        if mins > max_minutes:
            continue
        cov = len(ing & have) / len(ing)
        ranked.append({"recipe": name, "coverage": round(cov, 2), "missing": sorted(ing - have), "minutes": mins})
    ranked.sort(key=lambda r: (-r["coverage"], r["minutes"], r["recipe"]))
    return {"top": ranked[:k], "excluded_for_allergy": excluded}


CASES = [
    ({"pantry": ["pasta", "tomato", "garlic", "olive oil"], "allergies": []}, ("tomato pasta", None)),
    ({"pantry": ["pasta", "tomato", "garlic", "olive oil"], "allergies": ["gluten"]}, (None, {"gluten"})),
    ({"pantry": ["egg", "pepper", "onion", "cheese", "rice"], "allergies": ["egg"]}, ("rice salad", {"egg"})),
    ({"pantry": ["lentils", "onion", "carrot", "garlic"], "allergies": [], "max_minutes": 30}, (None, None)),
    ({"pantry": ["rice", "shrimp", "pepper", "soy sauce"], "allergies": ["shellfish"]}, ("rice salad", {"shellfish"})),
    ({"pantry": ["chickpeas", "tomato", "onion", "coconut milk", "rice"], "allergies": ["peanut"]}, ("chickpea curry", {"peanut"})),
    ({"pantry": ["bread", "cheese", "butter"], "allergies": ["dairy"]}, (None, {"dairy"})),
    ({"pantry": ["lentils", "onion", "carrot", "garlic"], "allergies": []}, ("lentil soup", None)),
]


class RecipeAgent(Agent):
    META = {
        "name": "recipe-rec",
        "title": "Recipe recommendation",
        "level": "Beginner",
        "tech": "Coverage ranking + hard filters",
        "industry": "Consumer and food",
        "tags": ["recommendation", "personalisation", "safety-filter"],
        "summary": "Suggests recipes that use what is in the pantry, never suggests one containing a listed allergen, and says what is missing.",
        "guardrails": ["allergens are a hard filter, not a score", "excluded recipes listed with the reason", "time limit respected", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"recipes.search"}))

    def handle(self, ctx, payload):
        return ctx.tool("recipes.search", recommend, payload["pantry"], payload.get("allergies", []), int(payload.get("max_minutes", 60)))

    def demo(self):
        return {"pantry": ["rice", "pepper", "onion", "egg", "lime"], "allergies": ["egg"]}

    def eval_cases(self):
        return [(p, (*exp, {a.lower() for a in p.get("allergies", [])})) for p, exp in CASES]

    def score(self, res, expected):
        o, (top, must_exclude, avoid) = res["output"], expected
        allergens = {r[0]: r[2] for r in RECIPES}
        safe = all(not (allergens[t["recipe"]] & avoid) for t in o["top"])
        ok_top = top is None or (o["top"] and o["top"][0]["recipe"] == top)
        ok_ex = must_exclude is None or all(set(e["because"]) <= must_exclude for e in o["excluded_for_allergy"]) and o["excluded_for_allergy"]
        if top is None and must_exclude is None:  # time-limit case: lentil soup (40 min) must not appear
            ok_top = all(t["recipe"] != "lentil soup" for t in o["top"])
        return float(bool(safe and ok_top and ok_ex))


AGENT = RecipeAgent()
