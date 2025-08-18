from logics.l4_contract_runtime import (
    make_provenance,
    score_confidence,
    validate_output_contract,
    validate_accounting,
    log_with_deltas_and_anomalies,
)

"""
Title: Government Scheme Utilization Tracker
ID: L-170
Tags: []
Required Inputs: schema://government_scheme_utilization_tracker.input.v1
Outputs: schema://government_scheme_utilization_tracker.output.v1
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

LOGIC_ID = "L-170"

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


def handle_l4(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Call legacy compute (now handle_impl). It may already return contract-shaped output.
    core_out = handle_impl(payload)

    # If core_out already looks contract-compliant, validate and return as-is.
    if isinstance(core_out, dict) and all(
        k in core_out for k in ("result", "provenance", "confidence", "alerts")
    ):
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
        result={
            "endpoint": "reports/auto",
            "ids": [],
            "filters": {"period": payload.get("period")},
        }
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
        anomalies=(
            len(alerts_pack.get("anomalies", []))
            if isinstance(alerts_pack, dict)
            else 0
        ),
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
