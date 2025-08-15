"""
Shared anomaly datatypes kept in a stable module to preserve class identity
across any reloads of the main anomaly detector module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import datetime as _dt


@dataclass
class AnomalyScore:
    """Anomaly score with metadata."""

    score: float
    method: str
    threshold: float
    is_anomaly: bool
    confidence: float
    context: Dict[str, Any]
    timestamp: _dt.datetime


@dataclass
class AnomalyResult:
    """Complete anomaly detection result."""

    metric_name: str
    current_value: float
    scores: List[AnomalyScore]
    overall_score: float
    is_anomaly: bool
    reason: str
    timestamp: _dt.datetime
    org_id: Optional[str] = None
    logic_id: Optional[str] = None
    orchestrator_id: Optional[str] = None


__all__ = ["AnomalyScore", "AnomalyResult"]
