from logics.l4_contract_runtime import make_provenance, score_confidence, validate_output_contract, validate_accounting, log_with_deltas_and_anomalies

"""
Title: Zone Wise Carbon Score
ID: L-146
Tags: []
Required Inputs: schema://zone_wise_carbon_score.input.v1
Outputs: schema://zone_wise_carbon_score.output.v1
Assumptions: 
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""
from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract

from typing import Dict, Any, List, Optional
from typing import Any, Dict
LOGIC_ID = "L-XXX"

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
    "id": "L-146",
    "title": "Zone-wise Carbon Score",
    "tags": ["esg", "zone", "carbon", "scope3"],
}


def _validate_zcs(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    zones = result.get("zones") or []
    totals = result.get("totals") or {}
    try:
        sum_co2 = 0.0
        sum_spend = 0.0
        for z in zones:
            c = float(z.get("co2e_tonnes", 0.0) or 0.0)
            s = float(z.get("spend", 0.0) or 0.0)
            score = float(z.get("score", 0.0) or 0.0)
            if c < 0 or s < 0:
                alerts.append("negatives_present")
            if score < 0 or score > 100:
                alerts.append("score_out_of_bounds")
            sum_co2 += c
            sum_spend += s
        t_co2 = float(totals.get("co2e_tonnes", 0.0) or 0.0)
        t_spend = float(totals.get("spend", 0.0) or 0.0)
        t_avg = float(totals.get("avg_score", 0.0) or 0.0)
        if abs(sum_co2 - t_co2) > 1e-6 or abs(sum_spend - t_spend) > 1e-6:
            alerts.append("totals_mismatch")
        # concentration alert: a single zone >70% co2e
        if sum_co2 > 0:
            shares = [
                (float(z.get("co2e_tonnes", 0.0) or 0.0) / sum_co2) * 100.0
                for z in zones
            ]
            if shares and max(shares) > 70.0:
                alerts.append("co2e_concentration_gt70")
        if t_avg < 0 or t_avg > 100:
            alerts.append("avg_score_out_of_bounds")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    zones = result.get("zones") or []
    try:
        if zones:
            top = max(zones, key=lambda z: float(z.get("co2e_tonnes", 0.0) or 0.0))
            if top and top.get("zone"):
                signals.append(f"top_zone:{top.get('zone')}")
        if any(a.startswith("co2e_concentration") for a in alerts):
            signals.append("co2e_share:>70")
        avg = (result.get("totals") or {}).get("avg_score")
        if isinstance(avg, (int, float)) and avg < 50:
            signals.append("avg_score:<50")
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
                "summary": {"size": len(zones)},
            },
        )
    except Exception:
        pass
    return {"notes": signals[:3]}


def handle_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Optional[str] = payload.get("org_id")
    start_date: Optional[str] = payload.get("start_date")
    end_date: Optional[str] = payload.get("end_date")
    headers: Dict[str, str] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        bills_url = f"{api_domain}/books/v3/bills?date_start={start_date}&date_end={end_date}&organization_id={org_id}&customfield=zone"
        vendors_url = f"{api_domain}/books/v3/vendors?organization_id={org_id}"
        sources.extend([bills_url, vendors_url])

        _ = get_json(bills_url, headers)
        _ = get_json(vendors_url, headers)

        zones: List[Dict[str, Any]] = []
        totals = {"co2e_tonnes": 0.0, "spend": 0.0, "avg_score": 0.0}

        result = {
            "period": {"start": start_date, "end": end_date},
            "zones": zones,
            "totals": totals,
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_zcs(result)
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

def handle_l4(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Call legacy compute (now handle_impl). It may already return contract-shaped output.
    core_out = handle_impl(payload)

    # If core_out already looks contract-compliant, validate and return as-is.
    if isinstance(core_out, dict) and        all(k in core_out for k in ("result","provenance","confidence","alerts")):
        try:
            validate_output_contract(core_out)
        except Exception:
            # If legacy contract is off, fall back to wrapper path below.
            pass
        else:
            return core_out

    # Otherwise, treat core_out as the raw result payload.
    result = core_out if isinstance(core_out, dict) else {"value": core_out}

    # Non-fatal accounting validation
    validations_failed = 0
    try:
        validate_accounting(result)
    except Exception:
        validations_failed += 1

    # Minimal provenance (period-aware)
    prov = make_provenance(
        result={"endpoint": "reports/auto", "ids": [], "filters": {"period": payload.get("period")}}
    )

    # History + Deltas + Anomalies
    logic_id = globals().get("LOGIC_ID")
    alerts_pack = log_with_deltas_and_anomalies(
        logic_id if isinstance(logic_id, str) else "L-XXX",
        payload,
        result,
        prov,
        period_key=payload.get("period"),
    )

    # Confidence scorer (learnable)
    sample_size = 1
    try:
        sample_size = max(1, len(result))  # if dict, len = #keys
    except Exception:
        sample_size = 1

    confidence = score_confidence(
        sample_size=sample_size,
        anomalies=len(alerts_pack.get("anomalies", [])) if isinstance(alerts_pack, dict) else 0,
        validations_failed=validations_failed,
    )

    # Convert string alerts to dict format for schema compliance
    raw_alerts = alerts_pack.get("alerts", []) if isinstance(alerts_pack, dict) else []
    alerts = []
    for alert in raw_alerts:
        if isinstance(alert, str):
            alerts.append({"msg": alert, "level": "info"})
        elif isinstance(alert, dict):
            alerts.append(alert)
        else:
            alerts.append({"msg": str(alert), "level": "info"})
    
    output = {
        "result": result,
        "provenance": prov,
        "confidence": confidence,
        "alerts": alerts,
    
        "meta": {

    
                    **LOGIC_META,

    
                    "strategy": "l4-v0",

    
                    "org_id": payload.get("org_id", "unknown"),

    
                    "query": payload.get("query", ""),

    
                    "notes": [],

    
                },
    }
    validate_output_contract(output)
    return output

# Export wrapper as the official handler
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    return handle_l4(payload)
