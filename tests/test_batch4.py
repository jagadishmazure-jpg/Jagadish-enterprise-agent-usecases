from entagents.agents import contract_review, incident_summary, invoice_extract, policy_compliance, stock_research
from entagents.framework.runtime import Runtime


def test_stock_prices_deterministic_and_labelled():
    assert stock_research.prices("LUMA") == stock_research.prices("LUMA")
    o = stock_research.research("profile", ["TIDE"])
    assert "Simulated" in o["disclaimer"] and o["metrics"]["TIDE"]["max_drawdown_pct"] <= 0


def test_stock_refuses_advice():
    r = Runtime().run(stock_research.AGENT, {"question": "Should I buy KILN?", "tickers": ["KILN"]})
    assert "refused" in r["output"] and "metrics" not in r["output"]


def test_contract_missing_clauses_flagged():
    assert contract_review.review("Payment is net 30.")["missing_standard_clauses"] == ["liability", "confidentiality", "governing_law"]


def test_contract_known_miss_hold_harmless():
    assert contract_review.review("Customer will hold Supplier harmless.")["clauses"][0]["type"] == "other"


def test_invoice_rejects_extra_field():
    rec = invoice_extract.extract(invoice_extract.CASES[0][0])
    assert invoice_extract.validate(rec) == []
    assert "unexpected field iban" in invoice_extract.validate({**rec, "iban": "x"})


def test_invoice_mismatch_goes_to_human():
    r = Runtime().run(invoice_extract.AGENT, {"invoice": invoice_extract.CASES[3][0]})
    assert r["output"]["status"] == "needs human review" and r["output"]["record"] is None


def test_policy_missing_evidence_is_unknown_not_pass():
    o = policy_compliance.check({})
    assert not o["compliant"] and len(o["unknown"]) == o["controls_checked"]


def test_incident_trigger_is_correlation_only():
    o = incident_summary.summarise(incident_summary.LOG_A)
    assert o["likely_trigger"]["kind"] == "deploy" and "not a confirmed root cause" in o["note"]
    assert o["services_affected"] == ["api", "payments"]
