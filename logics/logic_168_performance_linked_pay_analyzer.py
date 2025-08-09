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
    "id": "L-168",
    "title": "Performance-linked Pay Analyzer",
    "tags": ["plp", "hr", "comp"],
}


def _validate_plp(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    employees = result.get("employees") or []
    total_bonus = 0.0
    for e in employees:
        score = float(e.get("score", 0.0) or 0.0)
        bonus = float(e.get("bonus_suggest", 0.0) or 0.0)
        if not (0.0 <= score <= 100.0):
            alerts.append("score_out_of_bounds")
        if bonus < 0:
            alerts.append("negative_bonus")
        total_bonus += bonus
    pool = float((result.get("totals") or {}).get("bonus_pool", 0.0) or 0.0)
    if round(total_bonus, 2) != round(pool, 2):
        alerts.append("bonus_pool_mismatch")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        employees = result.get("employees") or []
        high_perf = sum(1 for e in employees if (e.get("score") or 0) >= 80)
        pool = float((result.get("totals") or {}).get("bonus_pool") or 0.0)
        band = "0"
        if pool >= 100000:
            band = "100k+"
        elif pool > 0:
            band = "<100k"
        signals.append(f"high_perf:{high_perf}")
        signals.append(f"bonus_pool:{band}")
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
        # Deterministic stub: no external fetch; structure only
        employees: List[Dict[str, Any]] = []
        total_bonus = round(
            sum(float(e.get("bonus_suggest") or 0.0) for e in employees), 2
        )
        result = {
            "period": {"start": start_date, "end": end_date},
            "employees": employees,
            "totals": {"bonus_pool": total_bonus},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_plp(result)
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
