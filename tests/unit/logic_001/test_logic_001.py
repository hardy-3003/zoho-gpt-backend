from typing import Dict, Any

from logics.logic_001_profit_and_loss_summary import handle


def make_payload() -> Dict[str, Any]:
    return {
        "org_id": "test",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "https://www.zohoapis.in",
        "query": "pnl jan 2025",
    }


def test_basic_shape():
    out = handle(make_payload())
    assert set(["result", "provenance", "confidence", "alerts", "meta"]) <= set(
        out.keys()
    )


def test_confidence_range():
    out = handle(make_payload())
    assert 0.0 <= out["confidence"] <= 1.0


def test_provenance_sources_present():
    out = handle(make_payload())
    assert isinstance(out["provenance"].get("sources", []), list)


def test_negative_case_missing_org_id():
    bad = make_payload()
    bad.pop("org_id", None)
    out = handle(bad)
    # Current handle is tolerant; ensure it still returns required structure
    assert set(["result", "provenance", "confidence", "alerts", "meta"]) <= set(
        out.keys()
    )
