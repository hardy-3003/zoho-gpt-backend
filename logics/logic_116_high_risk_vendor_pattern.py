"""
Title: High Risk Vendor Pattern
ID: L-116
Tags: []
Required Inputs: schema://high_risk_vendor_pattern.input.v1
Outputs: schema://high_risk_vendor_pattern.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from typing import Dict, Any, List

try:
    from helpers.zoho_client import get_json
except Exception:

    def get_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        return {}


try:
    from helpers.history_store import append_event
except Exception:

    def append_event(*args, **kwargs) -> None:
        return None


LOGIC_META = {
    "id": "L-116",
    "title": "High Risk Vendor Pattern",
    "tags": ["vendor", "risk", "pattern"],
}


def _validate_vendor_risk(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    for v in result.get("vendors", []) or []:
        try:
            s = float(v.get("risk_score", 0.0) or 0.0)
            if s < 0.0 or s > 100.0:
                alerts.append("score_out_of_bounds")
            if s > 70.0 and not (v.get("signals") or []):
                alerts.append("missing_signals_for_high")
        except Exception:
            alerts.append("invalid_score")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "period": {
                    "start": payload.get("start_date"),
                    "end": payload.get("end_date"),
                },
                "signals": ["l4-v0-run", "schema:stable"],
            },
        )
    except Exception:
        pass
    return {"notes": []}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id = payload.get("org_id")
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        ven_url = (
            f"{api_domain}/books/v3/contacts?category=vendor&organization_id={org_id}"
        )
        bills_url = f"{api_domain}/books/v3/bills?status=all&organization_id={org_id}"
        sources.extend([ven_url, bills_url])
        _ = get_json(ven_url, headers)
        _ = get_json(bills_url, headers)

        result = {
            "as_of": end_date,
            "vendors": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_vendor_risk(result)
    learn = _learn_from_history(payload, result)
    conf = 0.6 - (0.15 if alerts else 0.0) - (0.1 if not result else 0.0)
    conf = max(0.1, min(0.95, conf))

    return {
        "result": result,
        "provenance": {"sources": sources},
        "confidence": conf,
        "alerts": alerts,
        "meta": {
            "strategy": "l4-v0",
            "org_id": org_id,
            "query": query,
            "notes": learn.get("notes", []),
        },
    }
