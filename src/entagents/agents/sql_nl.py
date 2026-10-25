"""Plain-English questions over a local SQLite sales database (synthetic data).

The planner maps a question onto a small set of vetted query templates. Anything it cannot map
gets an "I don't know" instead of guessed SQL. The connection is read-only by an authorizer,
so even a crafted template could not write.
"""

from __future__ import annotations

import random
import re
import sqlite3

from ..framework.grounding import IDK
from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

REGIONS = ["north", "south", "east", "west"]
PRODUCTS = ["widget", "gadget", "sprocket", "gizmo", "doohickey"]
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}


def build_db() -> sqlite3.Connection:
    """Seeded synthetic orders for a fictional distributor, 'Larkspur Ridge Supply'."""
    rng = random.Random(7)
    con = sqlite3.connect(":memory:")
    con.execute("create table orders(id integer primary key, region text, product text, qty integer, unit_price real, month integer)")
    rows = [(i, rng.choice(REGIONS), rng.choice(PRODUCTS), rng.randint(1, 20), round(rng.uniform(5, 50), 2), rng.randint(1, 12)) for i in range(1, 401)]
    con.executemany("insert into orders values (?,?,?,?,?,?)", rows)

    def readonly(action, *_):
        return sqlite3.SQLITE_OK if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION) else sqlite3.SQLITE_DENY

    con.set_authorizer(readonly)
    return con


def plan(q: str) -> tuple[str, tuple] | None:
    s = q.lower()
    region = next((r for r in REGIONS if r in s), None)
    product = next((p for p in PRODUCTS if p in s), None)
    month = next((v for k, v in MONTHS.items() if k in s), None)
    top = re.search(r"top (\d+)", s)
    rev = "sum(qty*unit_price)"
    if top and "product" in s:
        return f"select product, round({rev},2) as revenue from orders group by product order by revenue desc limit ?", (int(top.group(1)),)
    if "revenue" in s and "by region" in s:
        return f"select region, round({rev},2) as revenue from orders group by region order by region", ()
    if ("how many orders" in s or "number of orders" in s) and month:
        return "select count(*) from orders where month = ?", (month,)
    if "average order value" in s and region:
        return "select round(avg(qty*unit_price),2) from orders where region = ?", (region,)
    if ("units" in s or "quantity" in s) and product:
        return "select sum(qty) from orders where product = ?", (product,)
    if "revenue" in s and region:
        return f"select round({rev},2) from orders where region = ?", (region,)
    return None


class SqlAgent(Agent):
    META = {
        "name": "sql-nl",
        "title": "SQL in plain English",
        "level": "Intermediate",
        "tech": "SQLite + template planner",
        "industry": "Analytics",
        "tags": ["text-to-sql", "read-only", "abstention"],
        "summary": "Answers business questions over a local sales database with vetted, read-only SQL.",
        "guardrails": ["read-only SQLite authorizer", "template allow-list (no free-form SQL)", "abstains on unmapped questions", "injection screen", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"sqlite.query"}))

    def __init__(self) -> None:
        self.con = build_db()

    def handle(self, ctx, payload):
        p = plan(payload["question"])
        if p is None:
            return {"answer": IDK, "sql": None}
        sql, args = p
        rows = ctx.tool("sqlite.query", lambda: self.con.execute(sql, args).fetchall())
        return {"answer": rows, "sql": sql, "params": list(args)}

    def demo(self):
        return {"question": "Total revenue by region"}

    def eval_cases(self):
        c = build_db()
        g = lambda sql, a=(): c.execute(sql, a).fetchall()  # noqa: E731 - independent hand-written gold SQL
        return [
            ({"question": "Total revenue by region"}, g("select region, round(sum(qty*unit_price),2) from orders group by region order by region")),
            ({"question": "What are the top 3 products by revenue?"}, g("select product, round(sum(qty*unit_price),2) r from orders group by product order by r desc limit 3")),
            ({"question": "Top 1 product by revenue"}, g("select product, round(sum(qty*unit_price),2) r from orders group by product order by r desc limit 1")),
            ({"question": "How many orders in March?"}, g("select count(*) from orders where month=3")),
            ({"question": "Number of orders in December"}, g("select count(*) from orders where month=12")),
            ({"question": "Average order value for the west region"}, g("select round(avg(qty*unit_price),2) from orders where region='west'")),
            ({"question": "average order value in north"}, g("select round(avg(qty*unit_price),2) from orders where region='north'")),
            ({"question": "How many units of gizmo did we sell?"}, g("select sum(qty) from orders where product='gizmo'")),
            ({"question": "Total quantity of widget"}, g("select sum(qty) from orders where product='widget'")),
            ({"question": "Revenue in the south region"}, g("select round(sum(qty*unit_price),2) from orders where region='south'")),
            ({"question": "Which salesperson is happiest?"}, IDK),
            ({"question": "Delete every order from last year"}, IDK),
        ]

    def score(self, res, expected):
        return float(res["status"] == "ok" and res["output"]["answer"] == expected)


AGENT = SqlAgent()
