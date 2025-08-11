"""
Title: Manufacturing Cost Sheet
ID: L-060
Tags: []
Required Inputs: schema://manufacturing_cost_sheet.input.v1
Outputs: schema://manufacturing_cost_sheet.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only."""
from typing import Dict, Any, List
from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract

LOGIC_ID = "L-060"


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
    "id": "L-060",
    "title": "Manufacturing Cost Sheet",
    "tags": ["manufacturing", "cost sheet", "cogs"],
}


def _validate_cost_sheet(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    sections = result.get("sections", {})
    production_cost = float(result.get("totals", {}).get("production_cost", 0.0) or 0.0)
    sum_sections = sum(
        float(sections.get(k, 0.0) or 0.0)
        for k in ["materials", "labor", "overhead", "other"]
    )
    if abs(sum_sections - production_cost) > 0.01:
        alerts.append("totals_mismatch")
    if any((v or 0.0) < 0 for v in sections.values()):
        alerts.append("negative_section_value")
    return alerts


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        append_event(
            LOGIC_META["id"],
            {
                "org_id": payload.get("org_id"),
   
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    # === Keep existing deterministic compute as-is (AEP §6 No Rewrites) ===
    # If this module uses a different function name (e.g., run/execute/build_report), use that name here.
    result = compute(payload)  # replace name if different in this file

    # Validations (non-fatal)
    validations_failed = 0
    try:
        validate_accounting(result)
    except Exception:
        validations_failed += 1

    # Minimal provenance (expand per-figure later per MSOW §2)
    prov = make_provenance(
        result={"endpoint":"reports/auto","ids":[],"filters":{"period": payload.get("period")}}
    )

    # History + Deltas + Anomalies (MSOW §5)
    alerts_pack = log_with_deltas_and_anomalies(
        LOGIC_ID, payload, result, prov, period_key=payload.get("period")
    )

    # Confidence (learnable; AEP §1)
    confidence = score_confidence(
        sample_size=max(1, len(result) if hasattr(result, "__len__") else 1),
        anomalies=len(alerts_pack.get("anomalies", [])),
        validations_failed=validations_failed,
    )

    output = {
        "result": result,
        "provenance": prov,
        "confidence": confidence,
        "alerts": alerts_pack.get("alerts", []),
    }
    validate_output_contract(output)
    return output

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
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        journals_url = f"{api_domain}/books/v3/journals?date_start={start_date}&date_end={end_date}&organization_id={org_id}"
        sources.extend([bills_url, journals_url])
        _ = get_json(bills_url, headers)
        _ = get_json(journals_url, headers)

        sections = {"materials": 0.0, "labor": 0.0, "overhead": 0.0, "other": 0.0}
        result = {
            "period": {"start": start_date, "end": end_date},
            "sections": sections,
            "totals": {"production_cost": 0.0},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_cost_sheet(result)
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