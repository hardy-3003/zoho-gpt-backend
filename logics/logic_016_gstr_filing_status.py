from typing import Dict, Any, List
from helpers.rules_engine import load_regulation_rules

try:  # noqa: F401
    from helpers.zoho_client import get_json  # type: ignore
except Exception:  # pragma: no cover

    def get_json(_url: str, headers: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {}


try:
    from helpers.history_store import append_event  # type: ignore
except Exception:  # pragma: no cover
    try:
        from helpers.history_store import write_event as _write_event  # type: ignore

        def append_event(logic_id: str, data: Dict[str, Any]) -> None:  # type: ignore
            _write_event(f"logic_{logic_id}", data)

    except Exception:

        def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore
            return None


LOGIC_META = {
    "id": "L-016",
    "title": "GSTR Filing Status",
    "tags": ["gst", "gstr", "compliance", "filing"],
}


def _validate_gstr(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        allowed = {"filed", "pending", "late"}
        for r in result.get("returns", []) or []:
            status = str(r.get("status", ""))
            if status not in allowed:
                alerts.append("invalid status detected")
                break
        # simple pending alert: if any pending
        if any((r.get("status") == "pending") for r in result.get("returns", []) or []):
            alerts.append("pending returns present")
    except Exception:
        alerts.append("validation error")
    return alerts


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        returns = result.get("returns", []) or []
        if any((r.get("status") == "pending") for r in returns):
            signals.append("pending:>0")
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
                "period": {
                    "start": payload.get("start_date"),
                    "end": payload.get("end_date"),
                },
                "signals": signals,
                "summary": {"size": len(returns)},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id = payload.get("org_id")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        # Load regulation rule snapshot based on effective date (end_date)
        rules = load_regulation_rules("gst", payload.get("end_date"))
        allowed_status = set(
            (
                rules.get("data", {}).get("return_status_values")
                or ["filed", "pending", "late"]
            )
        )
        sources.append("/books/v3/taxes/returns?date_start=&date_end=")
        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "returns": [],
            "summary": {s: 0 for s in sorted(list(allowed_status))},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_gstr(result)
    learn = _learn_from_history(payload, result, alerts)

    base_conf = 0.6
    if alerts:
        base_conf -= 0.15
    # structural empty: no returns and all summary zeros
    try:
        if (
            not (result.get("returns") or [])
            and sum(result.get("summary", {}).values()) == 0
        ):
            base_conf -= 0.10
    except Exception:
        pass

    return {
        "result": result,
        "provenance": {"sources": sources},
        "confidence": max(0.1, min(0.95, base_conf)),
        "alerts": alerts,
        "meta": {
            "strategy": "l4-v0",
            "org_id": org_id,
            "query": query,
            "notes": learn.get("notes", []),
        },
    }
