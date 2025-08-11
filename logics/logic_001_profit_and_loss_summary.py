from logics.l4_contract_runtime import (
    make_provenance,
    score_confidence,
    validate_output_contract,
    validate_accounting,
    log_with_deltas_and_anomalies,
)

"""
Title: Profit And Loss Summary
ID: L-001
Tags: []
Required Inputs: schema://profit_and_loss_summary.input.v1
Outputs: schema://profit_and_loss_summary.output.v1
Assumptions:
Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
"""

from helpers.rules_engine import validate_accounting
from helpers.schema_registry import validate_output_contract

from typing import Dict, Any, List
from typing import Any, Dict

LOGIC_ID = "L-XXX"

# Prefer using helpers if available; define safe fallbacks to keep imports clean
try:  # noqa: F401 - imported for side-effect/use when present
    from helpers.zoho_client import get_json  # type: ignore
except Exception:  # pragma: no cover

    def get_json(_url: str, headers: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {}


try:
    from helpers.history_store import append_event  # type: ignore
except Exception:  # pragma: no cover
    try:
        from helpers.history_store import write_event as _write_event  # type: ignore

        def append_event(logic_id: str, data: Dict[str, Any]) -> None:  # type: ignore
            _write_event(f"logic_{logic_id}", data)

    except Exception:  # pragma: no cover

        def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore
            return None


try:
    from helpers.obs import with_metrics  # type: ignore
except Exception:  # pragma: no cover

    def with_metrics(name: str):  # type: ignore
        def deco(fn):
            return fn

        return deco


LOGIC_META = {
    "id": "L-001",
    "title": "Profit & Loss Summary",
    "tags": ["pnl", "profit", "loss", "summary", "income", "expense", "finance"],
}


def _validate_pnl_summary(result: Dict[str, Any]) -> List[str]:
    alerts: List[str] = []
    try:
        totals = result.get("totals", {})
        income_total = float(totals.get("income_total", 0) or 0)
        expense_total = float(totals.get("expense_total", 0) or 0)
        profit = float(totals.get("profit", 0) or 0)
        if abs(income_total - expense_total - profit) > 0.01:
            alerts.append("unbalanced: income - expense != profit")
        breakdown = result.get("breakdown", {}) or {}
        income_lines = breakdown.get("Income", []) or []
        expense_lines = breakdown.get("Expenses", []) or []
        if not income_lines and not expense_lines:
            alerts.append("empty breakdown")
        for line in income_lines + expense_lines:
            amt = float(line.get("amount", 0) or 0)
            if amt < 0:
                alerts.append("negative amount detected")
                break
    except Exception:
        alerts.append("validation error")
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


@with_metrics("logic.L-001.handle")
def handle_impl(payload: Dict[str, Any]) -> Dict[str, Any]:
    org_id: Any = payload.get("org_id")
    start_date: Any = payload.get("start_date")
    end_date: Any = payload.get("end_date")
    headers: Dict[str, Any] = payload.get("headers", {})
    api_domain: str = payload.get("api_domain", "")
    query: str = payload.get("query", "")

    sources: List[str] = []
    result: Dict[str, Any] = {}

    try:
        # Deterministic placeholder without external calls
        # Document intended sources
        sources.append("/books/v3/invoices?date_start=&date_end=")
        sources.append("/books/v3/bills?date_start=&date_end=")

        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "totals": {"income_total": 0.0, "expense_total": 0.0, "profit": 0.0},
            "breakdown": {"Income": [], "Expenses": []},
        }
    except Exception as e:
        return {
            "result": {},
            "provenance": {"sources": sources},
            "confidence": 0.2,
            "alerts": [f"error: {str(e)}"],
            "meta": {"strategy": "l4-v0", "org_id": org_id, "query": query},
        }

    alerts = _validate_pnl_summary(result)
    learn = _learn_from_history(payload, result)

    conf = 0.6
    if any(a.startswith("unbalanced") for a in alerts):
        conf -= 0.15
    if "empty breakdown" in alerts:
        conf -= 0.10
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


# ---- L4 wrapper glue (safe, additive) ----------------------------------------
try:
    from helpers.logic_contract import l4_compliant
except Exception:  # fallback if import fails

    def l4_compliant(*_a, **_k):
        def _wrap(f):
            return f

        return _wrap


# Resolve the underlying implementation once, in this order
_handle_impl = None
for _name in ("handle_impl", "handle_core", "handle"):
    if _name in globals() and callable(globals()[_name]):
        _handle_impl = globals()[_name]
        break


@l4_compliant(validate=True, logic_id="L-001")
def handle_impl(payload):
    if _handle_impl is None:
        # Standard error envelope if the file had no implementation
        return {
            "result": None,
            "provenance": {"source": "internal", "path": None},
            "confidence": 0.2,
            "alerts": [
                {
                    "level": "error",
                    "message": "No underlying handle implementation found",
                }
            ],
            "meta": {"logic": "L-001"},
        }
    out = _handle_impl(payload)
    try:
        # Standardize provenance per-key and log deltas/anomalies
        from helpers.provenance import make_provenance
        from helpers.history_store import log_with_deltas_and_anomalies
        from helpers.learning_hooks import score_confidence as _score

        prov = out.get("provenance") or {}
        prov.setdefault("sources", prov.get("sources", []))
        prov.setdefault("figures", {})
        totals = ((out or {}).get("result") or {}).get("totals", {})
        period = {
            "start": payload.get("start_date"),
            "end": payload.get("end_date"),
        }
        figure_map = {}
        if "income_total" in totals:
            figure_map["income_total"] = {
                "endpoint": "reports/pnl",
                "filters": {"section": "income", "period": period},
            }
        if "expense_total" in totals:
            figure_map["expense_total"] = {
                "endpoint": "reports/pnl",
                "filters": {"section": "expense", "period": period},
            }
        if "profit" in totals:
            figure_map["profit"] = {
                "endpoint": "reports/pnl",
                "filters": {"section": "summary", "period": period},
            }
        prov["figures"].update(make_provenance(**figure_map))
        out["provenance"] = prov

        pack = log_with_deltas_and_anomalies(
            "L-001", payload, out.get("result") or {}, prov
        )
        extra_alerts = pack.get("alerts", [])
        if extra_alerts:
            out["alerts"] = list(out.get("alerts", [])) + extra_alerts

        validations_failed = (
            1
            if any(
                isinstance(a, str) and "unbalanced" in a.lower()
                for a in out.get("alerts", [])
            )
            else 0
        )
        new_conf = _score(
            sample_size=int(payload.get("sample_size", 1) or 1),
            anomalies=len(pack.get("anomalies", []) or []),
            validations_failed=validations_failed,
        )
        try:
            out["confidence"] = max(float(out.get("confidence", 0.0)), float(new_conf))
        except Exception:
            out["confidence"] = float(new_conf)
    except Exception:
        # Non-fatal; keep original output
        pass
    return out


# ------------------------------------------------------------------------------


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
