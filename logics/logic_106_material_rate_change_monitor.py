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
    "id": "L-106",
    "title": "Material Rate Change Monitor",
    "tags": ["materials", "rates", "price-variance", "inventory"],
}


def _validate_material_rate(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    for item in result.get("items", []) or []:
        prev_rate = item.get("avg_rate_prev")
        curr_rate = item.get("avg_rate_curr")
        delta_pct = item.get("delta_pct")
        if (
            prev_rate is not None
            and curr_rate is not None
            and prev_rate not in (0, 0.0)
        ):
            expected = (
                (float(curr_rate) - float(prev_rate)) / float(prev_rate)
            ) * 100.0
            if delta_pct is None:
                # do not mutate; only validate
                pass
            else:
                try:
                    if abs(float(delta_pct) - expected) > 0.01:
                        alerts.append("delta_mismatch")
                except Exception:
                    alerts.append("delta_invalid")
            if abs(expected) > 20.0:
                alerts.append("rate_spike_gt_20pct")
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
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers = payload.get("headers", {})
    api_domain = payload.get("api_domain", "")
    query = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        items_url = f"{api_domain}/books/v3/items?organization_id={org_id}"
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([items_url, bills_url])
        _ = get_json(items_url, headers)
        _ = get_json(bills_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "items": [],
            "totals": {"items": 0, "spike_count": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_material_rate(result)
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
