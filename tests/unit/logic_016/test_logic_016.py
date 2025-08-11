from typing import Dict, Any

from logics.logic_016_gstr_filing_status import handle


def make_payload() -> Dict[str, Any]:
    return {
        "org_id": "test",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "https://www.zohoapis.in",
        "query": "gst filing jan 2025",
    }


def test_basic_shape():
    out = handle(make_payload())
    assert set(["result", "provenance", "confidence", "alerts", "meta"]) <= set(
        out.keys()
    )


def test_summary_keys_from_rules():
    out = handle(make_payload())
    summary = out["result"]["result"].get("summary", {})
    assert set(summary.keys()) >= {"filed", "pending", "late"}
