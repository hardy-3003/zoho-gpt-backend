"""
Metrics endpoint router for observability baseline (P1.4.2).

GET /metrics.json → returns obs.metrics.dump() as JSON.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from obs import metrics


router = APIRouter(tags=["metrics"])


@router.get("/metrics.json")
async def get_metrics():
    return JSONResponse(content=metrics.dump())
