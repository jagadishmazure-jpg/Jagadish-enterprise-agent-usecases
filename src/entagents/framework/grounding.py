"""Hallucination controls: a small BM25 retriever, citation enforcement and abstention."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

IDK = "I don't know: the provided sources do not answer this."
STOP = set("a an the of to in on for and or is are was were be by with at from as it this that what which how who when does do".split())


def terms(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


@dataclass(frozen=True)
class Doc:
    id: str
    text: str
    title: str = ""


class BM25:
    def __init__(self, docs: list[Doc], k1: float = 1.4, b: float = 0.75) -> None:
        self.docs, self.k1, self.b = docs, k1, b
        self.tf = [Counter(terms(d.title + " " + d.text)) for d in docs]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = sum(self.len) / max(len(docs), 1)
        df = Counter(w for t in self.tf for w in t)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def search(self, query: str, k: int = 3) -> list[tuple[Doc, float]]:
        q = terms(query)
        scored = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            if s > 0:
                scored.append((self.docs[i], round(s, 4)))
        return sorted(scored, key=lambda x: -x[1])[:k]


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def supported(claim: str, source: str, min_overlap: float = 0.6) -> bool:
    """A claim counts as supported when most of its content words appear in the cited source."""
    c = set(terms(claim))
    return bool(c) and len(c & set(terms(source))) / len(c) >= min_overlap


@dataclass
class Claim:
    text: str
    cite: str | None


def enforce_citations(claims: list[Claim], sources: dict[str, str]) -> tuple[list[Claim], list[Claim]]:
    """Keep only claims whose citation exists and supports them; return (kept, dropped)."""
    kept, dropped = [], []
    for c in claims:
        (kept if c.cite in sources and supported(c.text, sources[c.cite]) else dropped).append(c)
    return kept, dropped
