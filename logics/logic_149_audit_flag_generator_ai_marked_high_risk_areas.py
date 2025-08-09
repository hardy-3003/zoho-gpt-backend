from typing import Dict, Any, List, Optional

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
    "id": "L-149",
    "title": "Audit Flag Generator (AI High-Risk Areas)",
    "tags": ["audit", "flag", "risk"],
}

_AREAS = {"revenue", "purchases", "payroll", "inventory", "tax"}
_SEV = {"low", "med", "high"}


def _validate_afg(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    flags = result.get("flags") or []
    totals = result.get("totals") or {}
    try:
        high = 0
        for f in flags:
            if f.get("area") not in _AREAS:
                alerts.append("bad_area")
            if f.get("severity") not in _SEV:
                alerts.append("bad_severity")
            if f.get("severity") == "high":
                high += 1
        if (totals.get("count") or 0) != len(flags) or (
            totals.get("high") or 0
        ) != high:
            alerts.append("totals_mismatch")
        if high > 0:
            alerts.append("high_present")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        high = (result.get("totals") or {}).get("high", 0)
        signals.append(f"high_flags:{int(high)}")
        flags = result.get("flags") or []
        if flags:
            # pick the first as top area for determinism
            signals.append(f"area:{flags[0].get('area')}")
    except Exception:
        pass
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "period": {
                    "start": payload.get("start_date"),
                    "end": payload.get("end_date"),
                },
                "signals": signals,
                "summary": {"size": len(result.get("flags") or [])},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        inv_url = f"{api_domain}/books/v3/invoices?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        bill_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        jrnl_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([inv_url, bill_url, jrnl_url])
        _ = get_json(inv_url, headers)
        _ = get_json(bill_url, headers)
        _ = get_json(jrnl_url, headers)

        flags: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "flags": flags,
            "totals": {"count": len(flags), "high": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_afg(result)
    learn = _learn_from_history(payload, result, alerts)
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
