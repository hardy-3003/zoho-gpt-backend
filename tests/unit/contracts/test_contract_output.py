from logics.logic_001_profit_and_loss_summary import handle as pnl
from logics.logic_006_zone_wise_expenses import handle as zone


def test_pnl_contract_fields():
    out = pnl(
        {
            "org_id": "t",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "headers": {},
            "api_domain": "https://www.zohoapis.in",
            "query": "pnl",
            "sample_size": 10,
        }
    )
    assert "provenance" in out and isinstance(out["provenance"], dict)
    assert "confidence" in out and isinstance(out["confidence"], (int, float))


def test_zone_contract_fields():
    out = zone(
        {
            "org_id": "t",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "headers": {},
            "api_domain": "https://www.zohoapis.in",
            "query": "zone",
            "sample_size": 5,
        }
    )
    assert "provenance" in out and isinstance(out["provenance"], dict)
    assert "confidence" in out and isinstance(out["confidence"], (int, float))
