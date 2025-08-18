"""
Server-Sent Events (SSE) Endpoint

Task P1.2.3 — Non-MCP /sse (contract-only)
Exposes GET /sse that streams progress events with deterministic behavior.
Mirrors /mcp/fetch event model: progress → section → done.
"""

import asyncio
import json
import time
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

# Import contracts from surfaces
from surfaces.contracts import (
    SSEEvent,
    ExecuteResponse,
    LogicOutput,
    Alert,
    AlertSeverity,
    AppliedRuleSet,
    validate_contract_structure,
)

from obs import log as obs_log
from obs import metrics as obs_metrics

router = APIRouter(tags=["sse"])


@router.get("/sse")
async def sse_stream(
    cursor: Optional[str] = Query(None, description="Resume cursor for resumability")
):
    """
    Server-Sent Events stream endpoint.

    Streams deterministic progress events:
    - event: progress - {percent: int} (0→100)
    - event: section - minimal deterministic stub
    - event: done - final JSON identical to /api/execute ExecuteResponse

    Supports resumability via ?cursor= parameter (echoed back).
    """

    try:
        obs_metrics.inc("requests_total", {"surface": "sse"})
        obs_log.info("sse_start", attrs={"has_cursor": bool(cursor)})
    except Exception:
        pass

    async def event_generator():
        """Generate SSE events with deterministic timing"""

        # Echo back cursor for resumability (no real storage in contract phase)
        if cursor:
            yield f"event: cursor\ndata: {json.dumps({'cursor': cursor})}\n\n"

        # Progress events (0→100)
        for percent in range(0, 101, 25):  # 0, 25, 50, 75, 100
            progress_event = SSEEvent(
                event_type="progress",
                data={"percent": percent},
                event_id=f"progress_{percent}",
            )
            yield f"event: {progress_event.event_type}\ndata: {json.dumps(progress_event.data)}\n\n"

            # Small delay for realistic streaming
            await asyncio.sleep(0.1)

        # Section event (minimal deterministic stub)
        section_event = SSEEvent(
            event_type="section",
            data={
                "section_id": "contract_stub",
                "title": "Contract Phase Stub",
                "status": "completed",
                "result": {"message": "Deterministic stub section"},
            },
            event_id="section_001",
        )
        yield f"event: {section_event.event_type}\ndata: {json.dumps(section_event.data)}\n\n"

        await asyncio.sleep(0.1)

        # Done event with final JSON identical to /api/execute ExecuteResponse
        final_response = _generate_final_response()
        done_event = SSEEvent(
            event_type="done", data=final_response, event_id="done_001"
        )
        yield f"event: {done_event.event_type}\ndata: {json.dumps(done_event.data)}\n\n"
        try:
            obs_log.info("sse_done", attrs={"events": 7})
        except Exception:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


def _generate_final_response() -> dict:
    """
    Generate final response identical to /api/execute ExecuteResponse.

    This provides deterministic, contract-compliant output for SSE streams.
    """
    start_time = time.time()

    # Generate stubbed logic output (deterministic)
    logic_output = _generate_stubbed_logic_output()

    execution_time_ms = (time.time() - start_time) * 1000

    # Create ExecuteResponse-compatible structure
    response = {
        "logic_output": {
            "result": logic_output["result"],
            "provenance": logic_output["provenance"],
            "confidence": logic_output["confidence"],
            "alerts": logic_output["alerts"],
            "applied_rule_set": logic_output["applied_rule_set"],
            "explanation": logic_output["explanation"],
        },
        "execution_time_ms": execution_time_ms,
        "cache_hit": False,  # Stubbed - no actual caching in contract phase
        "metadata": {
            "source": "sse_stream",
            "contract_version": "1.0",
            "stream_completed": True,
        },
    }

    return response


def _generate_stubbed_logic_output() -> dict:
    """
    Generate stubbed/deterministic logic output for SSE stream.

    Returns the same structure as /api/execute but with SSE-specific metadata.
    """

    # Deterministic result based on SSE context
    result = {
        "stream_result": {
            "total_events": 7,  # progress(5) + section(1) + done(1)
            "progress_events": 5,
            "section_events": 1,
            "done_events": 1,
            "stream_duration_ms": 500,  # Approximate
            "deterministic": True,
        },
        "sse_metadata": {
            "event_types": ["progress", "section", "done"],
            "resumability_supported": True,
            "contract_compliant": True,
        },
    }

    # Generate deterministic provenance
    provenance = {
        "source_data": ["evidence://sse/stream/contract/stubbed"],
        "computation": ["evidence://compute/sse/deterministic"],
        "validation": ["evidence://validate/sse/contract"],
        "stream_events": [
            "evidence://events/progress",
            "evidence://events/section",
            "evidence://events/done",
        ],
    }

    # Generate deterministic alerts (none for contract phase)
    alerts = []

    # Generate deterministic confidence score
    confidence = 0.95  # High confidence for stubbed responses

    # Generate applied rule set (empty for contract phase)
    applied_rule_set = {"packs": {}, "effective_date_window": None}

    # Generate explanation
    explanation = "Contract-phase SSE stream with deterministic events and final JSON identical to /api/execute"

    return {
        "result": result,
        "provenance": provenance,
        "confidence": confidence,
        "alerts": alerts,
        "applied_rule_set": applied_rule_set,
        "explanation": explanation,
    }
