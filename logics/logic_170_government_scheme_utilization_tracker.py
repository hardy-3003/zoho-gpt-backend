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
    "id": "L-170",
    "title": "Government Scheme Utilization Tracker",
    "tags": ["scheme", "grant", "utilization"],
}


def _validate_gsut(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    schemes = result.get("schemes") or []
    cap_t = util_t = bal_t = 0.0
    for s in schemes:
        cap = float(s.get("cap", 0.0) or 0.0)
        util = float(s.get("utilized", 0.0) or 0.0)
        bal = float(s.get("balance", 0.0) or 0.0)
        if cap < 0 or util < 0 or bal < 0:
            alerts.append("negative_values")
        if round(cap - util, 2) != round(bal, 2):
            alerts.append("balance_mismatch")
        cap_t += cap
        util_t += util
        bal_t += bal
    totals = result.get("totals") or {}
    if round(cap_t, 2) != round(float(totals.get("cap", 0.0) or 0.0), 2):
        alerts.append("totals_cap_mismatch")
    if round(util_t, 2) != round(float(totals.get("utilized", 0.0) or 0.0), 2):
        alerts.append("totals_util_mismatch")
    if round(bal_t, 2) != round(float(totals.get("balance", 0.0) or 0.0), 2):
        alerts.append("totals_bal_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        schemes = result.get("schemes") or []
        under = sum(1 for s in schemes if float(s.get("balance") or 0.0) > 0)
        over = sum(
            1
            for s in schemes
            if float(s.get("utilized") or 0.0) > float(s.get("cap") or 0.0)
        )
        signals.append(f"underutilized:{under}")
        signals.append(f"overutilized:{over}")
        if alerts:
            signals.append("alert:present")
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
        schemes: List[Dict[str, Any]] = []
        totals = {
            "cap": round(sum(float(s.get("cap") or 0.0) for s in schemes), 2),
            "utilized": round(sum(float(s.get("utilized") or 0.0) for s in schemes), 2),
            "balance": round(sum(float(s.get("balance") or 0.0) for s in schemes), 2),
        }
        result = {"as_of": end_date, "schemes": schemes, "totals": totals}
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_gsut(result)
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
