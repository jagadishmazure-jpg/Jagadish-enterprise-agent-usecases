"""Tiny multinomial logistic regression in pure Python (no dependencies, CPU, about 300 weights)."""

from __future__ import annotations

import json
import math
import random


def softmax(z: list[float]) -> list[float]:
    m = max(z)
    e = [math.exp(v - m) for v in z]
    t = sum(e)
    return [v / t for v in e]


class SoftmaxHead:
    def __init__(self, n_in: int, n_out: int):
        self.w = [[0.0] * n_in for _ in range(n_out)]

    def proba(self, x: list[float]) -> list[float]:
        return softmax([sum(wi * xi for wi, xi in zip(row, x, strict=True)) for row in self.w])

    def fit(self, X: list[list[float]], y: list[int], epochs: int = 60, lr: float = 0.5, l2: float = 1e-4, seed: int = 3) -> SoftmaxHead:
        idx = list(range(len(X)))
        rng = random.Random(seed)
        for ep in range(epochs):
            rng.shuffle(idx)
            step = lr / (1 + ep * 0.05)
            for i in idx:
                p = self.proba(X[i])
                for k, row in enumerate(self.w):
                    g = p[k] - (1.0 if y[i] == k else 0.0)
                    for j, xj in enumerate(X[i]):
                        row[j] -= step * (g * xj + l2 * row[j])
        return self


class TinyRouterModel:
    """Three heads over the same step features: next worker (5), safe (2), stop (2)."""

    def __init__(self, n_in: int):
        self.worker, self.safe, self.stop = SoftmaxHead(n_in, 5), SoftmaxHead(n_in, 2), SoftmaxHead(n_in, 2)

    def fit(self, X, yw, ys, yt) -> TinyRouterModel:
        self.worker.fit(X, yw)
        self.safe.fit(X, ys)
        self.stop.fit(X, yt)
        return self

    def predict(self, x: list[float]) -> dict:
        pw, ps, pt = self.worker.proba(x), self.safe.proba(x), self.stop.proba(x)
        w, s, t = max(range(5), key=pw.__getitem__), int(ps[1] >= 0.5), int(pt[1] >= 0.5)
        conf = pw[w] * max(ps) * max(pt)  # joint confidence of the whole step decision
        return {"worker": w, "safe": s, "stop": t, "confidence": conf}

    def n_params(self) -> int:
        return sum(len(r) for h in (self.worker, self.safe, self.stop) for r in h.w)

    def to_json(self) -> str:
        return json.dumps({"worker": self.worker.w, "safe": self.safe.w, "stop": self.stop.w})
