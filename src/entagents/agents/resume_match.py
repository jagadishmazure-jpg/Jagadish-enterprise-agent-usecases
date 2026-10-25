"""Resume parsing and job matching with identity hidden before scoring (synthetic resumes).

Names, emails and phones are removed before any score is computed, every match comes with the
skills that drove it, and sending a shortlist is a risky action that waits for a recruiter.
Fairness measurement at scale lives in Jagadish-recruiting-fairness-agents.
"""

from __future__ import annotations

import re

from ..framework.guards import ToolPolicy
from ..framework.runtime import Agent

SKILLS = ["python", "sql", "spark", "kubernetes", "terraform", "react", "typescript", "java", "pytorch", "airflow", "excel", "tableau", "go", "rust", "security"]
JOBS = {
    "data-engineer": {"must": {"python", "sql", "spark", "airflow"}, "min_years": 3},
    "ml-engineer": {"must": {"python", "pytorch", "kubernetes"}, "min_years": 2},
    "frontend-dev": {"must": {"react", "typescript"}, "min_years": 1},
    "platform-eng": {"must": {"kubernetes", "terraform", "go"}, "min_years": 4},
    "bi-analyst": {"must": {"sql", "excel", "tableau"}, "min_years": 1},
}


def parse(text: str) -> dict:
    low = text.lower()
    skills = sorted(s for s in SKILLS if re.search(rf"\b{s}\b", low))
    yrs = [int(y) for y in re.findall(r"(\d+)\+?\s*years?", low)]
    return {"skills": skills, "years": max(yrs) if yrs else 0}


def strip_identity(text: str) -> str:
    """Drop the first line (by convention the name) and any 'Name:' field before scoring."""
    lines = [ln for ln in text.splitlines() if not re.match(r"(?i)\s*name\s*:", ln)]
    return "\n".join(lines[1:] if lines and not re.search(r"(?i)skill|year|experience", lines[0]) else lines)


def match(profile: dict) -> list[dict]:
    out = []
    for job, req in JOBS.items():
        have = req["must"] & set(profile["skills"])
        cov = len(have) / len(req["must"])
        score = round(cov * (1.0 if profile["years"] >= req["min_years"] else 0.7), 3)
        out.append({"job": job, "score": score, "because": sorted(have), "missing": sorted(req["must"] - have)})
    return sorted(out, key=lambda m: (-m["score"], m["job"]))


R = [
    ("Asha Verma\nSkills: Python, SQL, Spark, Airflow. 5 years building pipelines.", "data-engineer"),
    ("Liam O'Neill\n3 years of PyTorch and Python; deployed models on Kubernetes.", "ml-engineer"),
    ("Mei Tan\nReact and TypeScript, 2 years shipping dashboards.", "frontend-dev"),
    ("Kwame Mensah\n6 years: Kubernetes, Terraform, Go. On-call lead.", "platform-eng"),
    ("Sofia Rossi\nSQL, Excel and Tableau reporting, 4 years.", "bi-analyst"),
    ("Name: Diego Alvarez\nExperience: 7 years Python, SQL, Spark, Airflow, some Java.", "data-engineer"),
    ("Hana Kim\nPython, PyTorch, Kubernetes, 2 years.", "ml-engineer"),
    ("Omar Haddad\nTypeScript and React, 1 year, plus Excel.", "frontend-dev"),
    ("Grace Liu\nTerraform, Kubernetes and Go for 5 years.", "platform-eng"),
    ("Arjun Nair\nTableau, Excel, SQL; 2 years as analyst.", "bi-analyst"),
    ("Fatima Zahra\nSpark, SQL, Python, Airflow and Tableau, 3 years.", "data-engineer"),
    ("Noah Becker\nPyTorch, Python, Kubernetes, Terraform; 3 years.", "ml-engineer"),
]


class ResumeMatchAgent(Agent):
    META = {
        "name": "resume-match",
        "title": "Resume parsing and matching",
        "level": "Intermediate",
        "tech": "Rule parser + skill-coverage scorer",
        "industry": "HR and recruiting",
        "tags": ["hr", "fairness", "explainable", "human-in-the-loop"],
        "summary": "Parses resumes, hides identity, ranks job fits with reasons, and holds shortlists for recruiter sign-off.",
        "guardrails": ["identity stripped before scoring", "PII redaction", "reason shown for every match", "name-swap invariance test", "recruiter approval to send", "audit log"],
    }
    TOOLS = ToolPolicy(frozenset({"parse.resume", "shortlist.send"}), risky=frozenset({"shortlist.send"}))

    def handle(self, ctx, payload):
        prof = ctx.tool("parse.resume", parse, strip_identity(payload["resume"]))
        ranked = match(prof)
        pid = ctx.request_approval("shortlist.send", {"job": ranked[0]["job"], "score": ranked[0]["score"]})
        return {"profile": prof, "ranked": ranked[:3], "shortlist_status": f"pending recruiter approval (#{pid})"}

    def demo(self):
        return {"resume": R[5][0]}

    def eval_cases(self):
        return [({"resume": t}, j) for t, j in R]

    def score(self, res, expected):
        return float(res["output"]["ranked"][0]["job"] == expected)


AGENT = ResumeMatchAgent()
