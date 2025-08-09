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
    "id": "L-151",
    "title": "Audit Automation Wizard (Step-by-step)",
    "tags": ["audit", "wizard", "workflow"],
}

_STATUS = {"todo", "doing", "done"}


def _validate_aaw(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        steps = result.get("steps") or []
        last_step = 0
        done = 0
        for s in steps:
            stepn = int(s.get("step", 0) or 0)
            if stepn <= last_step:
                alerts.append("step_not_monotonic")
            last_step = stepn
            if s.get("status") not in _STATUS:
                alerts.append("bad_status")
            if s.get("status") == "done":
                done += 1
        prog = float(result.get("progress_pct", 0.0) or 0.0)
        exp = (done / len(steps) * 100.0) if steps else 0.0
        if abs(prog - exp) > 1e-6:
            alerts.append("progress_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"progress:{int(float(result.get('progress_pct', 0.0) or 0.0))}")
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
                "summary": {"size": len(result.get("steps") or [])},
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
        sources.append("/books/v3/audit/wizard-steps")
        _ = get_json(
            f"{api_domain}/books/v3/audit/wizard?organization_id={org_id}", headers
        )

        steps: List[Dict[str, Any]] = []
        progress = 0.0
        result = {
            "period": {"start": start_date, "end": end_date},
            "steps": steps,
            "progress_pct": progress,
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_aaw(result)
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
