"""
REST API Execute Endpoint

Task P1.2.2 — REST /api/execute (contract)
Exposes POST /api/execute that accepts the canonical contract request
and returns the canonical contract response (stubbed values, deterministic).
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time
import json

# Import contracts from surfaces
from surfaces.contracts import (
    ExecuteRequest,
    ExecuteResponse,
    LogicOutput,
    Alert,
    AlertSeverity,
    AppliedRuleSet,
    validate_contract_structure,
)

from obs import log as obs_log
from obs import metrics as obs_metrics

router = APIRouter(prefix="/api", tags=["execute"])


@router.post("/execute")
async def execute_logic(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a logic module with the given inputs.

    This endpoint accepts a canonical contract request and returns
    a canonical contract response with stubbed/deterministic values.
    """
    # Deterministic contract-only stub: avoid wall-clock variance
    start_time = 0.0

    # Observability entry
    try:
        obs_metrics.inc("requests_total", {"surface": "rest"})
    except Exception:
        pass

    try:
        # Support two shapes:
        # 1) Canonical contract: {logic_id, org_id, period, inputs, context}
        # 2) Parity smoke shape: {plan: [{logic, inputs}]} (org/period optional)

        is_plan_mode = "plan" in payload and isinstance(payload.get("plan"), list)
        if is_plan_mode:
            first = payload["plan"][0] if payload["plan"] else {}
            logic_str = first.get("logic", "logic_001_profit_and_loss_summary")
            logic_id = logic_str
            inputs = first.get("inputs", {}) if isinstance(first, dict) else {}
            org_id = payload.get("org_id", "60020606976")
            period = inputs.get("period") or payload.get("period", "2025-01")
            context = payload.get("context", {})
        else:
            # Manual validation to return 422 on missing required fields (contract phase)
            missing = [k for k in ["logic_id", "org_id", "period"] if k not in payload]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail=f"Missing required field(s): {', '.join(missing)}",
                )
            req = ExecuteRequest(**payload)
            logic_id = req.logic_id
            org_id = req.org_id
            period = req.period
            context = req.context

        try:
            obs_metrics.inc("exec_calls_total", {"logic": logic_id})
        except Exception:
            pass

        logic_output = _generate_stubbed_output(logic_id, org_id, period)

        # Deterministic execution time for contract-only phase
        execution_time_ms = 0.0

        response: Dict[str, Any] = {
            "logic_output": {
                "result": logic_output.result,
                "provenance": logic_output.provenance,
                "confidence": logic_output.confidence,
                "alerts": [
                    {
                        "code": a.code,
                        "severity": getattr(a.severity, "value", str(a.severity)),
                        "message": a.message,
                        "evidence": a.evidence,
                        "metadata": a.metadata,
                    }
                    for a in logic_output.alerts
                ],
                "applied_rule_set": {
                    "packs": logic_output.applied_rule_set.packs,
                    "effective_date_window": logic_output.applied_rule_set.effective_date_window,
                },
                "explanation": logic_output.explanation,
            },
            "execution_time_ms": execution_time_ms,
            "cache_hit": False,
            "metadata": {
                "logic_id": logic_id,
                "org_id": org_id,
                "period": period,
                "contract_version": "1.0",
            },
        }

        # Extra top-level mirror ONLY for plan-mode to satisfy parity tests
        if is_plan_mode:
            response["result"] = logic_output.result

        try:
            obs_log.info(
                "execute_ok",
                attrs={"status_code": 200, "logic_id": logic_id},
                trace_id=(
                    context.get("trace_id") if isinstance(context, dict) else None
                ),
            )
        except Exception:
            pass
        return response

    except HTTPException as e:
        try:
            if int(e.status_code) >= 500:
                obs_metrics.inc("errors_total", {"surface": "rest"})
            obs_log.warn(
                "execute_error",
                attrs={"status_code": e.status_code, "detail": e.detail},
                trace_id=(
                    context.get("trace_id") if isinstance(context, dict) else None
                ),
            )
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            obs_metrics.inc("errors_total", {"surface": "rest"})
            obs_log.error(
                "execute_error",
                attrs={"error": str(e)},
                trace_id=(
                    context.get("trace_id") if isinstance(context, dict) else None
                ),
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


def _generate_stubbed_output(logic_id: str, org_id: str, period: str) -> LogicOutput:
    """
    Generate stubbed/deterministic output based on logic_id.

    This function provides deterministic responses for contract testing
    without requiring actual business logic implementation.
    """

    # Generate stubbed result based on logic_id pattern (deterministic, no py-hash)
    if logic_id.startswith("logic_001"):
        result = {
            "totals": {
                "revenue": 1000000,
                "cogs": 600000,
                "gross_profit": 400000,
                "opex": 200000,
                "ebit": 200000,
            },
            "sections": {
                "sales": {"amount": 1000000},
                "expenses": {"amount": 800000},
            },
        }
    elif logic_id.startswith("logic_231"):  # Ratio Impact Advisor
        result = {
            "impact_report": {
                "before": {
                    "dscr": 1.65,
                    "icr": 3.4,
                    "current_ratio": 1.8,
                    "de_ratio": 0.9,
                },
                "after": {
                    "dscr": 1.48,
                    "icr": 3.1,
                    "current_ratio": 1.55,
                    "de_ratio": 0.92,
                },
                "deltas": {
                    "dscr": -0.17,
                    "icr": -0.3,
                    "current_ratio": -0.25,
                    "de_ratio": 0.02,
                },
                "breaches": [],
            },
            "suggestions": [],
        }
    else:
        # Generic stubbed result for other logics
        result = {
            "data": f"Stubbed data for {logic_id}",
            "count": 123,
            "period": period,
            "org_id": org_id,
        }

    # Generate deterministic provenance
    provenance = {
        "source_data": [f"evidence://{logic_id}/{org_id}/{period}/stubbed"],
        "computation": ["evidence://compute/contract/stubbed"],
        "validation": [f"evidence://validate/{logic_id}/contract"],
    }

    # Generate deterministic alerts (none for contract phase)
    alerts = []

    # Generate deterministic confidence score
    confidence = 0.95  # High confidence for stubbed responses

    # Generate applied rule set (empty for contract phase)
    applied_rule_set = AppliedRuleSet(packs={}, effective_date_window=None)

    # Generate explanation
    explanation = f"Contract-phase stubbed response for {logic_id}"

    return LogicOutput(
        result=result,
        provenance=provenance,
        confidence=confidence,
        alerts=alerts,
        applied_rule_set=applied_rule_set,
        explanation=explanation,
    )
