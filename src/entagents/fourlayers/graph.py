"""A small state-graph runner (standard library only).

Typed shared state, nodes, fixed and conditional edges, parallel fan-out with fan-in, a checkpoint
after every node (resume skips finished nodes), interrupt nodes that pause for a person, subgraphs
and a deterministic route log. A router that names a target outside its declared set is blocked and
counted, never followed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

END = "__end__"


class InvalidTransition(Exception):
    pass


class Interrupted(Exception):
    def __init__(self, node: str):
        super().__init__(node)
        self.node = node


@dataclass
class Graph:
    schema: dict  # key -> type
    start: str = ""
    nodes: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)  # node -> ("fixed", target) | ("cond", fn, allowed) | ("par", [branches], join)
    interrupts: set = field(default_factory=set)
    blocked: list = field(default_factory=list)

    def node(self, name: str, fn, interrupt: bool = False) -> Graph:
        self.nodes[name] = fn
        if interrupt:
            self.interrupts.add(name)
        if not self.start:
            self.start = name
        return self

    def edge(self, a: str, b: str) -> Graph:
        self.edges[a] = ("fixed", b)
        return self

    def cond(self, a: str, fn, allowed: set) -> Graph:
        self.edges[a] = ("cond", fn, frozenset(allowed))
        return self

    def parallel(self, a: str, branches: list, join: str) -> Graph:
        self.edges[a] = ("par", list(branches), join)
        return self

    def as_node(self, store: dict | None = None):
        """Use this graph as one node of a parent graph (a subgraph)."""

        def run_sub(state: dict) -> dict:
            out = Runner(self, store if store is not None else {}).run(state, thread="sub")
            return out["state"]

        return run_sub

    def _check(self, update: dict, node: str) -> None:
        for k, v in update.items():
            if k not in self.schema:
                raise TypeError(f"node {node} wrote unknown key {k}")
            if v is not None and not isinstance(v, self.schema[k]):
                raise TypeError(f"node {node} wrote {k}={type(v).__name__}, expected {self.schema[k].__name__}")


class Runner:
    """Executes a Graph with a checkpoint store (any dict-like; a JSON file store works the same)."""

    def __init__(self, graph: Graph, store: dict, max_steps: int = 50):
        self.g, self.store, self.max_steps = graph, store, max_steps
        self.executed: list[str] = []

    def _apply(self, state: dict, node: str) -> dict:
        upd = self.g.nodes[node](copy.deepcopy(state)) or {}
        self.g._check(upd, node)
        self.executed.append(node)
        return {**state, **upd}

    def _save(self, thread: str, state: dict, nxt: str, route: list) -> None:
        self.store[thread] = json.dumps({"state": state, "next": nxt, "route": route}, default=str)

    def run(self, state: dict | None = None, thread: str = "t", approve: bool | None = None) -> dict:
        if thread in self.store:  # resume
            cp = json.loads(self.store[thread])
            state, cur, route = cp["state"], cp["next"], cp["route"]
            if approve is not None and cur in self.g.interrupts:
                state = {**state, "approved": approve}
        else:
            self.g._check(state, "<input>")
            cur, route = self.g.start, []
        steps = 0
        while cur != END:
            steps += 1
            if steps > self.max_steps:
                raise RuntimeError("graph step cap reached")
            if cur in self.g.interrupts and state.get("approved") is None:
                self._save(thread, state, cur, route)
                raise Interrupted(cur)
            state = self._apply(state, cur)
            route.append(cur)
            kind = self.g.edges.get(cur, ("fixed", END))
            if kind[0] == "par":
                _, branches, join = kind
                with ThreadPoolExecutor(max_workers=len(branches)) as ex:
                    outs = list(ex.map(lambda b, st=state: self.g.nodes[b](copy.deepcopy(st)) or {}, branches))
                for b, upd in zip(branches, outs, strict=True):
                    self.g._check(upd, b)
                    state = {**state, **upd}
                    self.executed.append(b)
                route.append("[" + "|".join(branches) + "]")
                nxt = join
            elif kind[0] == "cond":
                _, fn, allowed = kind
                nxt = fn(state)
                if nxt not in allowed:
                    self.g.blocked.append((cur, nxt))
                    raise InvalidTransition(f"{cur} -> {nxt} not in {sorted(allowed)}")
            else:
                nxt = kind[1]
            self._save(thread, state, nxt, route)
            cur = nxt
        self.store.pop(thread, None)
        return {"state": state, "route": route, "route_hash": hashlib.sha256(">".join(route).encode()).hexdigest()[:12]}
