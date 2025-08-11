"""
Title: Auto Fill For Common Journal Entries Ai Trained On History
ID: L-152
Tags: []
Required Inputs: schema://auto_fill_for_common_journal_entries_ai_trained_on_history.input.v1
Outputs: schema://auto_fill_for_common_journal_entries_ai_trained_on_history.output.v1
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
    "id": "L-152",
    "title": "Auto-Fill Common Journal Entries",
    "tags": ["je", "auto", "learn"],
}


def _validate_afje(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        templates = result.get("templates") or []
        for t in templates:
            if not isinstance(t.get("suggested_entry"), dict) or not t.get(
                "suggested_entry"
            ):
                alerts.append("empty_entry")
            cp = float(t.get("confidence_pct", 0.0) or 0.0)
            if cp < 0 or cp > 100:
                alerts.append("confidence_out_of_bounds")
        if (result.get("totals") or {}).get("templates", 0) != len(templates):
            alerts.append("totals_mismatch")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        templates = result.get("templates") or []
        signals.append(f"templates:{len(templates)}")
        if any((float(t.get("confidence_pct", 0.0) or 0.0) > 80.0) for t in templates):
            signals.append("top_conf:>80")
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
                "summary": {"size": len(result.get("templates") or [])},
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
        jrnl_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.append(jrnl_url)
        _ = get_json(jrnl_url, headers)

        templates: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "templates": templates,
            "totals": {"templates": len(templates)},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_afje(result)
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
