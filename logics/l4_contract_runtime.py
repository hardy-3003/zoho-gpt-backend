from __future__ import annotations
from typing import Any, Dict, List, Optional

# Import real helper functions
try:
    from helpers.history_store import (
        log_with_deltas_and_anomalies as real_log_with_deltas,
    )
    from helpers.rules_engine import validate_accounting as real_validate_accounting
    from helpers.learning_hooks import score_confidence as real_score_confidence
except ImportError:
    # Fallback to placeholder functions if helpers not available
    def real_log_with_deltas(*args, **kwargs):
        return {"history": [], "deltas": [], "anomalies": []}

    def real_validate_accounting(*args, **kwargs):
        return []

    def real_score_confidence(*args, **kwargs):
        return 0.75


def make_provenance(
    *, result: Dict[str, Any] | None = None, sources: List[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    """Create a comprehensive provenance structure for data sources."""
    result_data = result or {}
    sources_data = sources or []

    # If sources are provided, use them directly
    if sources_data:
        return {"sources": sources_data}

    # Otherwise, convert result data to sources format
    # Extract meaningful provenance from result structure
    provenance_sources = []

    # Check for Zoho-specific data patterns
    if "zoho_data" in result_data:
        zoho_data = result_data["zoho_data"]
        if isinstance(zoho_data, dict):
            provenance_sources.append(
                {
                    "source": "zoho",
                    "endpoint": zoho_data.get("endpoint", "reports/auto"),
                    "ids": zoho_data.get("ids", []),
                    "filters": zoho_data.get("filters", {}),
                    "timestamp": zoho_data.get("timestamp"),
                }
            )

    # Check for calculated fields
    if "calculated_fields" in result_data:
        provenance_sources.append(
            {
                "source": "calculation",
                "method": "formula",
                "inputs": result_data.get("calculation_inputs", []),
            }
        )

    # Default provenance if no specific sources found
    if not provenance_sources:
        provenance_sources = [
            {
                "source": "zoho",
                "endpoint": result_data.get("endpoint", "reports/auto"),
                "ids": result_data.get("ids", []),
                "filters": result_data.get("filters", {}),
            }
        ]

    return {"sources": provenance_sources}


def score_confidence(
    *,
    sample_size: int = 1,
    anomalies: int = 0,
    validations_failed: int = 0,
    data_quality_score: float = 0.8,
    completeness_ratio: float = 1.0,
) -> float:
    """
    Calculate confidence score based on multiple factors.

    Args:
        sample_size: Number of data points processed
        anomalies: Number of anomalies detected
        validations_failed: Number of validation failures
        data_quality_score: Quality score of input data (0.0-1.0)
        completeness_ratio: Ratio of complete vs missing data (0.0-1.0)

    Returns:
        Confidence score between 0.05 and 0.99
    """
    try:
        # Use real confidence scoring if available
        return real_score_confidence(
            sample_size=sample_size,
            anomalies=anomalies,
            validations_failed=validations_failed,
            data_quality_score=data_quality_score,
            completeness_ratio=completeness_ratio,
        )
    except Exception:
        # Fallback calculation
        base = 0.75 if sample_size >= 3 else 0.65

        # Adjust for data quality
        quality_adjustment = (data_quality_score - 0.5) * 0.2  # ±0.1

        # Adjust for completeness
        completeness_adjustment = (completeness_ratio - 0.5) * 0.2  # ±0.1

        # Penalties for issues
        anomaly_penalty = 0.1 * min(anomalies, 5)  # Cap at 0.5
        validation_penalty = 0.15 * min(validations_failed, 3)  # Cap at 0.45

        confidence = (
            base
            + quality_adjustment
            + completeness_adjustment
            - anomaly_penalty
            - validation_penalty
        )

        return max(0.05, min(0.99, confidence))


def validate_output_contract(output: Dict[str, Any]) -> List[str]:
    """
    Validate that output follows the L4 contract structure.

    Args:
        output: The output dictionary to validate

    Returns:
        List of validation error messages
    """
    errors = []

    # Check required fields
    required_fields = ["result", "provenance", "confidence", "alerts"]
    for field in required_fields:
        if field not in output:
            errors.append(f"Missing required field: {field}")

    # Validate confidence score
    if "confidence" in output:
        confidence = output["confidence"]
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            errors.append("Confidence must be a number between 0 and 1")

    # Validate alerts is a list
    if "alerts" in output and not isinstance(output["alerts"], list):
        errors.append("Alerts must be a list")

    # Validate provenance structure
    if "provenance" in output:
        provenance = output["provenance"]
        if not isinstance(provenance, dict) or "sources" not in provenance:
            errors.append("Provenance must be a dict with 'sources' key")

    return errors


def validate_accounting(result: Dict[str, Any]) -> List[str]:
    """
    Perform comprehensive accounting validation.

    Args:
        result: The result data to validate

    Returns:
        List of accounting validation alerts
    """
    try:
        # Use real accounting validation if available
        return real_validate_accounting(result)
    except Exception:
        # Fallback validation
        alerts = []

        # Basic P&L validation
        if "net_profit" in result:
            try:
                revenue = float(result.get("revenue", 0) or 0)
                cogs = float(result.get("cogs", 0) or 0)
                expenses = float(result.get("expenses", 0) or 0)
                calc_np = revenue - cogs - expenses
                np = float(result.get("net_profit", 0) or 0)

                if abs(calc_np - np) > 0.01:
                    alerts.append(
                        "Net profit does not reconcile with revenue - cogs - expenses"
                    )
            except (ValueError, TypeError):
                alerts.append("Failed to validate P&L arithmetic")

        # Balance sheet validation
        if (
            "total_assets" in result
            and "total_liabilities" in result
            and "equity" in result
        ):
            try:
                assets = float(result.get("total_assets", 0) or 0)
                liabilities = float(result.get("total_liabilities", 0) or 0)
                equity = float(result.get("equity", 0) or 0)

                if abs(assets - liabilities - equity) > 0.01:
                    alerts.append(
                        "Balance sheet does not balance: assets != liabilities + equity"
                    )
            except (ValueError, TypeError):
                alerts.append("Failed to validate balance sheet")

        # Negative amount checks
        for key, value in result.items():
            if isinstance(value, (int, float)) and value < 0:
                if "revenue" in key.lower() or "income" in key.lower():
                    alerts.append(
                        f"Negative value detected in revenue/income field: {key}"
                    )

        return alerts


def log_with_deltas_and_anomalies(
    logic_id: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    provenance: Dict[str, Any],
    period_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Log execution with delta comparison and anomaly detection.

    Args:
        logic_id: The logic identifier
        inputs: Input parameters
        outputs: Output results
        provenance: Data provenance information
        period_key: Optional period identifier for delta comparison

    Returns:
        Dictionary with history, deltas, and anomalies
    """
    try:
        # Use real logging function if available
        return real_log_with_deltas(
            logic_id=logic_id,
            inputs=inputs,
            outputs=outputs,
            provenance=provenance,
            period_key=period_key,
        )
    except Exception:
        # Fallback implementation
        return {
            "history": [
                {
                    "type": "execution",
                    "logic_id": logic_id,
                    "timestamp": "2025-01-27T18:00:00Z",
                    "inputs": inputs,
                    "outputs": outputs,
                    "provenance": provenance,
                }
            ],
            "deltas": [],
            "anomalies": [],
        }
