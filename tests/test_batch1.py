import sqlite3

import pytest

from entagents.agents import code_review, csv_analysis, meeting_actions, resume_match, sql_nl
from entagents.framework.grounding import IDK
from entagents.framework.runtime import Runtime


def test_sql_connection_is_read_only():
    con = sql_nl.build_db()
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("delete from orders")


def test_sql_unmapped_abstains():
    r = Runtime().run(sql_nl.AGENT, {"question": "drop everything please"})
    assert r["output"]["answer"] == IDK and r["output"]["sql"] is None


def test_sql_uses_parameters():
    sql, args = sql_nl.plan("revenue in the east region")
    assert "?" in sql and args == ("east",)


def test_code_review_never_runs_code(tmp_path):
    marker = tmp_path / "ran"
    code_review.review(f"open({str(marker)!r}, 'w').write('x')\n")
    assert not marker.exists()


def test_code_review_syntax_error():
    assert code_review.review("def (")[0]["rule"] == "syntax"


def test_code_review_known_miss_alias():
    assert code_review.review("run = eval\nrun(x)\n") == []  # documented limitation


def test_resume_identity_stripped_and_name_swap_invariant():
    base = "Skills: Python, SQL, Spark, Airflow. 5 years."
    a = resume_match.match(resume_match.parse(resume_match.strip_identity("Asha Verma\n" + base)))
    b = resume_match.match(resume_match.parse(resume_match.strip_identity("John Smith\n" + base)))
    assert a == b


def test_resume_shortlist_waits_for_approval():
    rt = Runtime()
    r = rt.run(resume_match.AGENT, resume_match.AGENT.demo())
    pid = r["pending_approvals"][0]
    assert not rt.approvals.executed(pid)
    rt.approvals.decide(pid, True, "recruiter-7")
    assert rt.approvals.executed(pid)


def test_resume_email_redacted():
    r = Runtime().run(resume_match.AGENT, {"resume": "Ana Ruiz\nana@mail.example 3 years SQL Excel Tableau"})
    assert "ana@mail.example" not in str(r) and r["output"]["ranked"][0]["job"] == "bi-analyst"


def test_resume_reasons_present():
    top = resume_match.match({"skills": ["react", "typescript"], "years": 1})[0]
    assert top["job"] == "frontend-dev" and top["because"] == ["react", "typescript"] and top["missing"] == []


def test_csv_outlier_planted_row():
    assert csv_analysis.analyse(csv_analysis.load(csv_analysis.sample_csv()), "outliers in sales")["value"] == [17]


def test_csv_custom_file():
    r = Runtime().run(csv_analysis.AGENT, {"question": "correlation between a and b", "csv": "a,b\n1,2\n2,4\n3,6\n"})
    assert r["output"]["value"] == 1.0


def test_meeting_skips_vague():
    assert meeting_actions.extract("We should think about pricing.\nMaybe later.") == []


def test_meeting_known_miss_passive():
    assert meeting_actions.extract("The SLA doc will be updated by Wednesday by Nora.") == []
