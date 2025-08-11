from __future__ import annotations
from typing import Any, Dict, List


def make_provenance(
    *, result: Dict[str, Any] | None = None, sources: List[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    # Create a provenance structure that matches the validation requirements
    result_data = result or {}
    return {
        "result": {
            "source": "zoho",
            "endpoint": result_data.get("endpoint", "reports/auto"),
            "ids": result_data.get("ids", []),
            "filters": result_data.get("filters", {}),
        }
    }


def score_confidence(
    *, sample_size: int = 1, anomalies: int = 0, validations_failed: int = 0
) -> float:
    base = 0.75 if sample_size >= 3 else 0.65
    penalty = 0.1 * anomalies + 0.15 * validations_failed
    return max(0.05, min(0.99, base - penalty))


def validate_output_contract(_: Dict[str, Any]) -> None:
    return  # no-op validator for tests


def validate_accounting(_: Dict[str, Any]) -> None:
    return  # no-op; wrapper treats failures as non-fatal anyway


def log_with_deltas_and_anomalies(
    _: str,
    __: Dict[str, Any],
    ___: Dict[str, Any],
    ____: Dict[str, Any],
    period_key: str | None = None,
) -> Dict[str, Any]:
    return {"history": [], "deltas": [], "anomalies": []}
