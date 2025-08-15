from __future__ import annotations
import time
from typing import Any, Dict, List, Optional

# Import real helper functions
try:
    from helpers.history_store import (
        log_with_deltas_and_anomalies as real_log_with_deltas,
    )
    from helpers.rules_engine import validate_accounting as real_validate_accounting
    from helpers.learning_hooks import score_confidence as real_score_confidence
    from helpers.telemetry import (
        emit_logic_telemetry,
        set_logic_context,
        get_deep_metrics,
    )
    from helpers.provenance import create_telemetry_provenance
except ImportError:
    # Fallback to placeholder functions if helpers not available
    def real_log_with_deltas(*args, **kwargs):
        return {"history": [], "deltas": [], "anomalies": []}

    def real_validate_accounting(*args, **kwargs):
        return []

    def real_score_confidence(*args, **kwargs):
        return 0.75

    def emit_logic_telemetry(*args, **kwargs):
        pass

    def set_logic_context(*args, **kwargs):
        pass

    def get_deep_metrics(*args, **kwargs):
        return {}

    def create_telemetry_provenance(*args, **kwargs):
        return {"provenance": {}, "metrics": {}, "keys_count": 0}


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


def handle_l4_with_telemetry(
    logic_id: str, handler_func, payload: Dict[str, Any], org_id: str = None, **kwargs
) -> Dict[str, Any]:
    """
    Execute logic handler with comprehensive telemetry and L4 compliance.

    Args:
        logic_id: The logic identifier
        handler_func: The logic handler function
        payload: Input payload
        org_id: Organization ID for telemetry
        **kwargs: Additional arguments

    Returns:
        L4-compliant result with telemetry
    """
    start_time = time.perf_counter()
    status = "success"
    error_taxonomy = ""
    confidence = 0.0
    alerts_count = 0
    provenance_keys = 0
    inputs_size = len(str(payload))
    outputs_size = 0

    try:
        # Execute the logic handler
        result = handler_func(payload, **kwargs)

        # Extract L4 components
        if isinstance(result, dict):
            # Handle L4 contract format
            logic_result = result.get("result", result)
            provenance = result.get("provenance", {})
            confidence = result.get("confidence", 0.75)
            alerts = result.get("alerts", [])
            alerts_count = len(alerts) if isinstance(alerts, list) else 0

            # Process provenance for telemetry
            telemetry_provenance = create_telemetry_provenance(provenance)
            provenance_keys = telemetry_provenance["keys_count"]

            # Calculate output size
            outputs_size = len(str(logic_result))

            # Validate accounting rules
            validation_alerts = validate_accounting(logic_result)
            if validation_alerts:
                alerts.extend(validation_alerts)
                alerts_count = len(alerts)

            # Log history and deltas
            history_data = log_with_deltas_and_anomalies(
                logic_id=logic_id,
                inputs=payload,
                outputs=logic_result,
                provenance=provenance,
            )

            # Update result with validation alerts
            result["alerts"] = alerts

        else:
            # Handle non-L4 format
            logic_result = result
            provenance = {}
            confidence = 0.75
            alerts = []
            outputs_size = len(str(result))

            # Convert to L4 format
            result = {
                "result": logic_result,
                "provenance": provenance,
                "confidence": confidence,
                "alerts": alerts,
            }

        return result

    except Exception as e:
        status = "error"
        error_taxonomy = type(e).__name__
        confidence = 0.0

        # Return error result in L4 format
        return {
            "result": {"error": str(e)},
            "provenance": {},
            "confidence": confidence,
            "alerts": [f"Execution error: {str(e)}"],
        }

    finally:
        # Emit telemetry
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Set logic context for telemetry
        set_logic_context(logic_id)

        # Detect anomalies for this execution
        from helpers.anomaly_detector import detect_anomaly

        anomaly_result = detect_anomaly(
            f"{logic_id}_latency",
            duration_ms,
            org_id or payload.get("org_id", "unknown"),
            logic_id,
            "",
        )

        emit_logic_telemetry(
            logic_id=logic_id,
            org_id=org_id or payload.get("org_id", "unknown"),
            duration_ms=duration_ms,
            status=status,
            inputs_size=inputs_size,
            outputs_size=outputs_size,
            confidence=confidence,
            alerts_count=alerts_count,
            cache_hit=False,  # TODO: Implement cache detection
            provenance_keys=provenance_keys,
            error_taxonomy=error_taxonomy,
            retry_attempts=0,
            anomaly_score=(
                anomaly_result.overall_score if anomaly_result.is_anomaly else 0.0
            ),
        )
