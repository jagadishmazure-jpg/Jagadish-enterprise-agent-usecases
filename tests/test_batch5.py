from entagents.agents import competitive_analysis, debate_judge


def test_competitive_no_guessing():
    o = competitive_analysis.analyse(["Orchard Signal"])
    assert o["matrix"]["Orchard Signal"]["support_hours"] == {"value": None, "cite": None, "note": "no source"}
    assert "support_hours" not in o["leaders"]


def test_competitive_cells_cite_matching_company():
    o = competitive_analysis.analyse(competitive_analysis.COMPANIES)
    ids = {d.id: d for d in competitive_analysis.FACTS}
    for co, row in o["matrix"].items():
        for cell in row.values():
            assert cell["cite"] is None or ids[cell["cite"]].title.startswith(co)


def test_judge_penalises_fabricated_citation():
    honest = debate_judge.debate("cache")["verdict"]["scores"]["pro"]
    faked = debate_judge.debate("cache", fabricate_side="pro")["verdict"]["scores"]["pro"]
    assert faked == honest - 2


def test_judge_ignores_length():
    assert debate_judge.debate("rewrite", verbose_side="pro")["verdict"] == debate_judge.debate("rewrite")["verdict"]


def test_judge_order_flip_rate_zero():
    flips = [debate_judge.debate(m)["order_flip"] for m in ["remote", "rewrite", "cache", "vendor"]]
    assert sum(flips) == 0
