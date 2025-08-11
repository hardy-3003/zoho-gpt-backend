"""
Title: Anomaly Detection Report
ID: L-076
Tags: []
Required Inputs: schema://anomaly_detection_report.input.v1
Outputs: schema://anomaly_detection_report.output.v1
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
    "id": "L-076",
    "title": "Anomaly Detection",
    "tags": ["anomaly", "outlier", "stats"],
}


def _validate_anomaly(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    anomalies = result.get("anomalies", [])
    for a in anomalies:
        z = float(a.get("zscore", 0.0) or 0.0)
        val = float(a.get("value", 0.0) or 0.0)
        if z < -20 or z > 20:
            alerts.append("zscore_out_of_bounds")
        if abs(z) > 3:
            alerts.append("significant_outlier")
        if val < 0:
            alerts.append("negative_value")
    totals = result.get("totals", {})
    if int(totals.get("count", 0) or 0) != len(anomalies):
        alerts.append("count_mismatch")
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
        sources.append(f"{api_domain}/books/v3/journals?organization_id={org_id}")
        _ = get_json(sources[-1], headers)

        result = {
            "period": {"start": start_date, "end": end_date},
            "anomalies": [],
            "totals": {"count": 0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_anomaly(result)
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
