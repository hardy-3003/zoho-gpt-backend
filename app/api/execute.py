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


@router.post("/execute", response_model=ExecuteResponse)
async def execute_logic(request: ExecuteRequest) -> ExecuteResponse:
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
        obs_metrics.inc("exec_calls_total", {"logic": request.logic_id})
        trace_id = (
            request.context.get("trace_id")
            if isinstance(request.context, dict)
            else None
        )
        obs_log.info(
            "execute_start",
            attrs={
                "logic_id": request.logic_id,
                "org_id": request.org_id,
                "period": request.period,
            },
            trace_id=trace_id,
        )
    except Exception:
        pass

    try:
        # Validate request structure
        if not validate_contract_structure(request, ExecuteRequest):
            raise HTTPException(status_code=400, detail="Invalid request structure")

        # Stubbed/deterministic response based on logic_id
        logic_output = _generate_stubbed_output(
            request.logic_id, request.org_id, request.period
        )

        # Deterministic execution time for contract-only phase
        execution_time_ms = 0.0

        response = ExecuteResponse(
            logic_output=logic_output,
            execution_time_ms=execution_time_ms,
            cache_hit=False,  # Stubbed - no actual caching in contract phase
            metadata={
                "logic_id": request.logic_id,
                "org_id": request.org_id,
                "period": request.period,
                "contract_version": "1.0",
            },
        )

        try:
            obs_log.info(
                "execute_ok",
                attrs={"status_code": 200, "logic_id": request.logic_id},
                trace_id=(
                    request.context.get("trace_id")
                    if isinstance(request.context, dict)
                    else None
                ),
            )
        except Exception:
            pass
        return response

    except HTTPException as e:
        try:
            obs_metrics.inc("errors_total", {"surface": "rest"})
            obs_log.warn(
                "execute_error",
                attrs={"status_code": e.status_code, "detail": e.detail},
                trace_id=(
                    request.context.get("trace_id")
                    if isinstance(request.context, dict)
                    else None
                ),
            )
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            obs_metrics.inc("errors_total", {"surface": "rest"})
            obs_log.error("execute_error", attrs={"error": str(e)})
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
