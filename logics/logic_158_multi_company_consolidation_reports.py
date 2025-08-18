from logics.l4_contract_runtime import (
    make_provenance,
    score_confidence,
    validate_output_contract,
    validate_accounting,
    log_with_deltas_and_anomalies,
)

"""
Title: Multi Company Consolidation Reports
ID: L-158
Tags: []
Required Inputs: schema://multi_company_consolidation_reports.input.v1
Outputs: schema://multi_company_consolidation_reports.output.v1
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

LOGIC_ID = "L-158"

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
    "id": "L-158",
    "title": "Multi-company Consolidation Reports",
    "tags": ["consolidation", "multi-entity"],
}


def _validate_mcc(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        comps = result.get("companies") or []
        sum_rev = sum(float(c.get("revenue", 0.0) or 0.0) for c in comps)
        sum_exp = sum(float(c.get("expense", 0.0) or 0.0) for c in comps)
        sum_prof = sum(float(c.get("profit", 0.0) or 0.0) for c in comps)
        totals = result.get("totals") or {}
        if abs(sum_rev - float(totals.get("revenue", 0.0) or 0.0)) > 1e-6:
            alerts.append("totals_mismatch")
        if abs(sum_exp - float(totals.get("expense", 0.0) or 0.0)) > 1e-6:
            alerts.append("totals_mismatch")
        if abs(sum_prof - float(totals.get("profit", 0.0) or 0.0)) > 1e-6:
            alerts.append("totals_mismatch")
        if result.get("fx_policy") == "none":
            currencies = {c.get("currency") for c in comps if c.get("currency")}
            if len(currencies) > 1:
                alerts.append("mixed_currency_no_fx")
    except Exception:
        alerts.append("validation_error")
    return list(dict.fromkeys(alerts))


def _learn_from_history(
    payload: Dict[str, Any], result: Dict[str, Any], alerts: List[str]
) -> Dict[str, Any]:
    signals: List[str] = ["l4-v0-run", "schema:stable"]
    try:
        signals.append(f"entities:{len(result.get('companies') or [])}")
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
                "summary": {"size": len(result.get("companies") or [])},
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
        tb_url = f"{api_domain}/books/v3/reports/trialbalance?date_start={start_date}&date_end={end_date}&organization_id={org_id}&group_by=company"
        sources.append(tb_url)
        _ = get_json(tb_url, headers)

        companies: List[Dict[str, Any]] = []
        result = {
            "period": {"start": start_date, "end": end_date},
            "companies": companies,
            "totals": {"revenue": 0.0, "expense": 0.0, "profit": 0.0},
            "fx_policy": "none",
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_mcc(result)
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
