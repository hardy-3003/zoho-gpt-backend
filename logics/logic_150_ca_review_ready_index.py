"""
Title: Ca Review Ready Index
ID: L-150
Tags: []
Required Inputs: schema://ca_review_ready_index.input.v1
Outputs: schema://ca_review_ready_index.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
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
    "id": "L-150",
    "title": "CA Review Ready Index",
    "tags": ["ca", "review", "readiness"],
}

_DRIVERS = ["recon_done", "filings_ok", "tb_balanced", "aging_clean"]


def _validate_carri(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        drivers = result.get("drivers") or []
        scores = [float(d.get("score", 0.0) or 0.0) for d in drivers]
        if any((s < 0 or s > 100) for s in scores):
            alerts.append("score_out_of_bounds")
        idx = float(result.get("index", 0.0) or 0.0)
        avg = (sum(scores) / len(scores)) if scores else 0.0
        if abs(avg - idx) > 1e-6:
            alerts.append("index_mismatch")
        if idx < 70.0:
            alerts.append("index_low")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        idx = int(float(result.get("index", 0.0) or 0.0))
        signals.append(f"index:{idx}")
        # weak driver: min score
        drivers = result.get("drivers") or []
        if drivers:
            weak = min(drivers, key=lambda d: float(d.get("score", 0.0) or 0.0))
            if weak and weak.get("name"):
                signals.append(f"weak:{weak.get('name')}")
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
                "summary": {"size": len(result.get("drivers") or [])},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    end_date: Optional[str] = payload.get("end_date")
    org_id: Optional[str] = payload.get("org_id")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        # Placeholder to read statuses from other endpoints if available
        sources.append("/books/v3/reports/status-snapshot")
        _ = get_json(
            f"{api_domain}/books/v3/reports/status?organization_id={org_id}", headers
        )

        drivers = [{"name": d, "score": 0.0} for d in _DRIVERS]
        idx = 0.0
        result = {"as_of": end_date, "drivers": drivers, "index": idx}
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_carri(result)
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
