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
    "id": "L-114",
    "title": "Client Risk Profiling",
    "tags": ["clients", "risk", "score"],
}


def _band(score: float) -> str:
    if score <= 40.0:
        return "low"
    if score <= 70.0:
        return "med"
    return "high"


def _validate_client_risk(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    for c in result.get("clients", []) or []:
        try:
            s = float(c.get("risk_score", 0.0) or 0.0)
            if s < 0.0 or s > 100.0:
                alerts.append("score_out_of_bounds")
            expected_band = _band(s)
            if c.get("band") != expected_band:
                alerts.append("band_mismatch")
            if expected_band != "low" and not (c.get("drivers") or []):
                alerts.append("missing_drivers")
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
        cust_url = f"{api_domain}/books/v3/contacts?organization_id={org_id}"
        inv_url = f"{api_domain}/books/v3/invoices?status=all&organization_id={org_id}"
        sources.extend([cust_url, inv_url])
        _ = get_json(cust_url, headers)
        _ = get_json(inv_url, headers)

        result = {
            "as_of": end_date,
            "clients": [],
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_client_risk(result)
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
