"""Document Q&A with required citations and an "I don't know" when the sources do not answer."""

from __future__ import annotations

from ..framework.grounding import BM25, IDK, Claim, enforce_citations, sentences, terms
from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent
from ._corpus import POLICIES

MIN_SCORE = 2.0
MIN_COVERAGE = 0.5


def stems(text: str) -> set[str]:
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in terms(text)}


def answer(index: BM25, q: str) -> dict:
    hits = index.search(q, k=2)
    if not hits or hits[0][1] < MIN_SCORE:
        return {"answer": IDK, "citations": [], "top_score": hits[0][1] if hits else 0.0}
    doc = hits[0][0]
    qt = stems(q)
    if len(qt & stems(doc.title + " " + doc.text)) / max(len(qt), 1) < MIN_COVERAGE:
        return {"answer": IDK, "citations": [], "top_score": hits[0][1]}
    best = max(sentences(doc.text), key=lambda s: len(qt & set(terms(s))))
    kept, _ = enforce_citations([Claim(best, doc.id)], {d.id: d.text for d, _ in hits})
    if not kept:
        return {"answer": IDK, "citations": [], "top_score": hits[0][1]}
    return {"answer": kept[0].text, "citations": [doc.id], "top_score": hits[0][1]}


QA = [
    ("How many days of paid leave do employees accrue per month?", "hr-leave", "1.5 days"),
    ("How much unused leave carries over?", "hr-leave", "10 days"),
    ("How many days per week can staff work remotely?", "hr-remote", "3 days"),
    ("What is the minimum number of characters for passwords?", "it-password", "14 characters"),
    ("When are company laptops replaced?", "it-devices", "every 4 years"),
    ("What is the daily meal limit on business travel?", "fin-expense", "60 dollars"),
    ("How many approvals do purchases above 5000 dollars need?", "fin-approval", "two approvals"),
    ("How fast must on-call engineers acknowledge pages?", "ops-oncall", "15 minutes"),
    ("When is a postmortem due for severity 1 incidents?", "ops-oncall", "5 business days"),
    ("Can I share customer exports by personal email?", "sec-data", "prohibited"),
    ("Who won the football league last season?", None, None),
    ("What is the office wifi password?", None, None),
    # Known miss kept visible: title words ("leave policy") give enough coverage to answer the wrong question.
    ("What is the parental leave policy?", None, None),
]


class DocQAAgent(Agent):
    META = {
        "name": "doc-qa",
        "title": "Document Q&A with citations",
        "level": "Intermediate",
        "tech": "BM25 retrieval + citation check",
        "industry": "Enterprise knowledge",
        "tags": ["rag", "citations", "abstention", "hallucination-control"],
        "summary": "Answers policy questions from a document set, cites the source, and says I don't know when the documents do not cover it.",
        "guardrails": ["answer must cite a retrieved document", "unsupported claims dropped", "score threshold then abstain", "PII redaction", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"docs.search"}))

    def __init__(self) -> None:
        self.index = BM25(POLICIES)

    def handle(self, ctx, payload):
        return ctx.tool("docs.search", answer, self.index, payload["question"])

    def demo(self):
        return {"question": QA[5][0]}

    def eval_cases(self):
        return [({"question": q}, (d, a)) for q, d, a in QA]

    def score(self, res, expected):
        d, a = expected
        o = res["output"]
        if d is None:
            return float(o["answer"] == IDK)
        return float(o["citations"] == [d] and a.lower() in o["answer"].lower())


AGENT = DocQAAgent()
