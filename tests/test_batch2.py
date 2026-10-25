from entagents.agents import doc_qa, email_draft, issue_triage, support_escalation, web_research
from entagents.framework.grounding import BM25, IDK
from entagents.framework.runtime import Runtime


def test_triage_security_is_p0_and_appsec():
    o = issue_triage.triage("SQL injection in search", "")
    assert o["label"] == "security" and o["priority"] == "P0" and o["team"] == "appsec"


def test_triage_duplicate_found():
    assert issue_triage.triage("Typo in README install section", "")["duplicates"][0]["issue"] == 103


def test_triage_known_miss_no_keywords():
    assert issue_triage.triage("Sidebar overlaps the chart on narrow screens", "")["label"] == "question"


def test_docqa_cites_source():
    o = doc_qa.answer(BM25(doc_qa.POLICIES), "How fast must on-call engineers acknowledge pages?")
    assert o["citations"] == ["ops-oncall"] and "15 minutes" in o["answer"]


def test_docqa_abstains_off_topic():
    assert doc_qa.answer(BM25(doc_qa.POLICIES), "best pizza in town")["answer"] == IDK


def test_docqa_known_miss_parental_leave():
    assert doc_qa.answer(BM25(doc_qa.POLICIES), "What is the parental leave policy?")["answer"] != IDK


def test_web_research_quarantines_poisoned_page():
    o = web_research.research(BM25(web_research.WEB), "heat pumps")
    assert o["quarantined"] == ["w5"] and "w5" not in o["sources"]
    assert all("[w" in p for s in o["sections"] for p in s["points"])


def test_web_research_unknown_topic_abstains():
    assert web_research.research(BM25(web_research.WEB), "quantum batteries")["report"] == IDK


def test_email_send_waits_for_approval():
    rt = Runtime()
    r = rt.run(email_draft.AGENT, email_draft.AGENT.demo())
    assert r["pending_approvals"] == [0] and not rt.approvals.executed(0)
    assert "ravi@client.example" not in str(r) and "guarantee" not in r["output"]["body"].lower()


def test_email_unknown_intent_no_send():
    r = Runtime().run(email_draft.AGENT, {"intent": "threat", "to_name": "X", "points": []})
    assert "error" in r["output"] and r["pending_approvals"] == []


def test_support_legal_escalates_before_anything_else():
    assert support_escalation.decide("Refund $10 or I sue")["reason"] == "legal"


def test_support_answer_has_citation():
    o = support_escalation.decide("How do I reset my password?")
    assert o["action"] == "answer" and o["citation"] == "kb-password"
