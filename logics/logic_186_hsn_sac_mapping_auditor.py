"""
Title: Hsn Sac Mapping Auditor
ID: L-186
Tags: []
Required Inputs: schema://hsn_sac_mapping_auditor.input.v1
Outputs: schema://hsn_sac_mapping_auditor.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
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
    "id": "L-186",
    "title": "HSN-SAC Mapping Auditor",
    "tags": ["gst", "hsn", "audit"],
}


def _validate_hsn(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    counters = result.get("counters") or {}
    try:
        for k in ["ok", "missing", "mismatch"]:
            v = int(counters.get(k, 0))
            if v < 0:
                alerts.append("negative_counter")
    except Exception:
        alerts.append("invalid_counters")
    for row in result.get("items", []) or []:
        status = row.get("status")
        if status not in {"ok", "missing", "mismatch"}:
            alerts.append("invalid_status")
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
        sources.append(items_url)
        _ = get_json(items_url, headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "items": [],
            "counters": {"ok": 0, "missing": 0, "mismatch": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_hsn(result)
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
