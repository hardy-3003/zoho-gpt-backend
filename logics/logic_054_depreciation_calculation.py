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
    "id": "L-054",
    "title": "Depreciation Calculation",
    "tags": ["depreciation", "fixed assets"],
}


def _validate_depreciation(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    assets = result.get("assets", [])
    total = float(result.get("totals", {}).get("depr_amount", 0.0) or 0.0)
    sum_amt = 0.0
    for a in assets:
        rate = float(a.get("rate_pct", 0.0) or 0.0)
        amt = float(a.get("depr_amount", 0.0) or 0.0)
        if amt < 0:
            alerts.append(f"negative_depreciation:{a.get('asset','')}")
        if rate <= 0 or rate > 100:
            alerts.append(f"rate_out_of_bounds:{a.get('asset','')}")
        sum_amt += amt
    if abs(sum_amt - total) > 0.01:
        alerts.append("totals_mismatch")
    return alerts


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
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        fa_url = f"{api_domain}/books/v3/fixedassets?organization_id={org_id}"
        sources.append(fa_url)
        _ = get_json(fa_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "assets": [],
            "totals": {"depr_amount": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_depreciation(result)
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
