from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from core.operate_base import OperateInput, OperateOutput
from core.registry import route

from helpers.pdf_extractor import extract_fields, validate_extraction_result
from helpers.schema_registry import (
    save_learned_format,
    validate_learned_format,
    load_learned_format,
    list_learned_formats,
)
from helpers.provenance import (
    get_global_learner,
    learn_from_pdf_extraction,
    make_field_provenance,
)
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.learning_hooks import score_confidence
from helpers.reconciliation import (
    reconcile_totals,
    detect_mismatches,
    cross_field_consistency_check,
)
from helpers.obs import with_metrics
from helpers.telemetry import (
    span,
    emit_orchestration_telemetry,
    set_org_context,
    set_run_context,
    set_logic_context,
    get_deep_metrics,
)
from helpers.alerts import evaluate_alerts, create_alert, AlertSeverity
import logging
from helpers.anomaly_detector import detect_anomaly

_log = logging.getLogger(__name__)
# Route telemetry logs through this module's logger for tests
try:
    from helpers import telemetry as _telemetry

    _telemetry._log = _log
except Exception as e:
    logging.getLogger(__name__).warning("Failed to patch telemetry logger: %s", e)


def run_generic(input: OperateInput, logic_keywords: List[str]) -> OperateOutput:
    run_id = str(uuid.uuid4())

    with span(
        "generic_orchestration",
        run_id=run_id,
        org_id=input.org_id,
        keywords_count=len(logic_keywords),
    ):
        # Route telemetry logs through this module's patched logger during tests
        try:
            from helpers import telemetry as _telemetry

            _telemetry._log = _log
        except Exception as e:
            logging.getLogger(__name__).warning("Failed to patch telemetry logger in run: %s", e)

        # Set telemetry context
        set_org_context(input.org_id)
        set_run_context(run_id)

        records: Dict[str, Any] = {}
        missing: List[str] = []

        for kw in logic_keywords:
            dag_node_id = f"generic_{kw}"

            with span(
                "generic_keyword", run_id=run_id, dag_node_id=dag_node_id, keyword=kw
            ):
                op = route(kw)
                if op is None:
                    missing.append(kw)
                    # Emit telemetry even when missing to keep aggregation consistent
                    emit_orchestration_telemetry(
                        run_id=run_id,
                        dag_node_id=dag_node_id,
                        logic_id=f"operate_{kw}",
                        duration_ms=0.0,
                        status="missing",
                    )
                    continue
                try:
                    start_time = time.perf_counter()
                    out = op(input)
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    records[kw] = out.content

                    # Set logic context for telemetry
                    set_logic_context(f"operate_{kw}")

                    # Detect anomalies for this execution
                    anomaly_result = detect_anomaly(
                        f"operate_{kw}_latency",
                        duration_ms,
                        input.org_id,
                        f"operate_{kw}",
                        dag_node_id,
                    )

                    emit_orchestration_telemetry(
                        run_id=run_id,
                        dag_node_id=dag_node_id,
                        logic_id=f"operate_{kw}",
                        duration_ms=duration_ms,
                        status="success",
                        anomaly_score=(
                            anomaly_result.overall_score
                            if anomaly_result.is_anomaly
                            else 0.0
                        ),
                    )
                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000.0
                    records[kw] = {"error": str(e)}

                    # Set logic context for telemetry
                    set_logic_context(f"operate_{kw}")

                    # Detect anomalies for this execution
                    anomaly_result = detect_anomaly(
                        f"operate_{kw}_latency",
                        duration_ms,
                        input.org_id,
                        f"operate_{kw}",
                        dag_node_id,
                    )

                    emit_orchestration_telemetry(
                        run_id=run_id,
                        dag_node_id=dag_node_id,
                        logic_id=f"operate_{kw}",
                        duration_ms=duration_ms,
                        status="error",
                        error_taxonomy=type(e).__name__,
                        anomaly_score=(
                            anomaly_result.overall_score
                            if anomaly_result.is_anomaly
                            else 0.0
                        ),
                    )

    # Evaluate alerts after execution
    alerts = evaluate_alerts(input.org_id, "", "generic_orchestrator")

    # Add alert information to metadata
    alert_info = {
        "alert_count": len(alerts),
        "critical_alerts": len(
            [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        ),
        "warning_alerts": len(
            [a for a in alerts if a.severity == AlertSeverity.WARNING]
        ),
    }

    meta = {
        "operator": "generic_orchestrator",
        "keywords": logic_keywords,
        "missing": missing,
        "run_id": run_id,
        "alerts": alert_info,
    }
    return OperateOutput(content={"sections": records}, meta=meta)


# Enhanced nomenclature map with confidence scores
ENHANCED_NOMEN_MAP: Dict[str, Dict[str, Any]] = {
    "Revenue": {
        "endpoint": "reports/pnl",
        "filters": {"section": "income"},
        "confidence": 0.9,
    },
    "Income": {
        "endpoint": "reports/pnl",
        "filters": {"section": "income"},
        "confidence": 0.9,
    },
    "Sales": {
        "endpoint": "reports/pnl",
        "filters": {"section": "income"},
        "confidence": 0.8,
    },
    "Turnover": {
        "endpoint": "reports/pnl",
        "filters": {"section": "income"},
        "confidence": 0.8,
    },
    "Expenses": {
        "endpoint": "reports/pnl",
        "filters": {"section": "expense"},
        "confidence": 0.9,
    },
    "Costs": {
        "endpoint": "reports/pnl",
        "filters": {"section": "expense"},
        "confidence": 0.8,
    },
    "Expenditure": {
        "endpoint": "reports/pnl",
        "filters": {"section": "expense"},
        "confidence": 0.8,
    },
    "Net Profit": {
        "endpoint": "reports/pnl",
        "filters": {"section": "summary"},
        "confidence": 0.9,
    },
    "Profit": {
        "endpoint": "reports/pnl",
        "filters": {"section": "summary"},
        "confidence": 0.9,
    },
    "Loss": {
        "endpoint": "reports/pnl",
        "filters": {"section": "summary"},
        "confidence": 0.9,
    },
    "Gross Profit": {
        "endpoint": "reports/pnl",
        "filters": {"section": "summary", "type": "gross"},
        "confidence": 0.8,
    },
    "Operating Profit": {
        "endpoint": "reports/pnl",
        "filters": {"section": "summary", "type": "operating"},
        "confidence": 0.8,
    },
    "Assets": {
        "endpoint": "reports/balance_sheet",
        "filters": {"section": "assets"},
        "confidence": 0.9,
    },
    "Liabilities": {
        "endpoint": "reports/balance_sheet",
        "filters": {"section": "liabilities"},
        "confidence": 0.9,
    },
    "Equity": {
        "endpoint": "reports/balance_sheet",
        "filters": {"section": "equity"},
        "confidence": 0.9,
    },
    "Capital": {
        "endpoint": "reports/balance_sheet",
        "filters": {"section": "equity"},
        "confidence": 0.8,
    },
    "Period": {"endpoint": "common/period", "filters": {}, "confidence": 0.7},
    "Date": {"endpoint": "common/period", "filters": {}, "confidence": 0.7},
    "Month": {"endpoint": "common/period", "filters": {}, "confidence": 0.7},
    "Year": {"endpoint": "common/period", "filters": {}, "confidence": 0.7},
}


@with_metrics("orchestrator.rl.learn_from_pdf")
def learn_from_pdf(pdf_path: str, name: str = "mis_fixture_v1") -> Dict[str, Any]:
    """
    Enhanced PDF learning with comprehensive extraction, validation, and provenance learning.

    Args:
        pdf_path: Path to the PDF file
        name: Name for the learned format

    Returns:
        Dict with learning results including validation and confidence scores
    """
    try:
        # Step 1: Extract fields from PDF
        extraction_result = extract_fields(pdf_path)

        # Step 2: Validate extraction quality
        validation = validate_extraction_result(extraction_result)

        # Step 3: Learn provenance mappings
        learner = get_global_learner()
        learning_result = learn_from_pdf_extraction(extraction_result, learner)

        # Step 4: Create enhanced mapping with confidence scores
        fields = extraction_result.get("fields", {})
        mapping: Dict[str, Any] = {}

        for field_name in fields.keys():
            # Check enhanced nomenclature map
            hint = ENHANCED_NOMEN_MAP.get(field_name)
            if hint:
                mapping[field_name] = {
                    "endpoint": hint["endpoint"],
                    "filters": hint.get("filters", {}),
                    "confidence": hint.get("confidence", 0.8),
                    "source": "enhanced_nomenclature",
                }
            else:
                # Use learned mapping if available
                learned_mapping = learner.get_mapping(field_name)
                if learned_mapping:
                    mapping[field_name] = {
                        "endpoint": learned_mapping.endpoint,
                        "filters": learned_mapping.filters,
                        "confidence": learned_mapping.confidence,
                        "source": learned_mapping.source,
                    }
                else:
                    # Default mapping with low confidence
                    mapping[field_name] = {
                        "endpoint": "",
                        "filters": {},
                        "confidence": 0.1,
                        "source": "default",
                    }

        # Step 5: Save learned format
        path = f"docs/learned_formats/{name}.json"
        save_learned_format(name, mapping, path)

        # Step 6: Validate against learned format
        format_validation = validate_learned_format(fields, name)

        return {
            "meta": extraction_result.get("meta", {}),
            "mapping_path": path,
            "mapping": mapping,
            "extraction_validation": validation,
            "learning_result": learning_result,
            "format_validation": format_validation,
            "summary": {
                "fields_extracted": len(fields),
                "mappings_learned": learning_result.get("mappings_learned", 0),
                "extraction_confidence": extraction_result.get("meta", {}).get(
                    "confidence", 0.0
                ),
                "format_confidence": format_validation.get("confidence", 0.0),
                "overall_quality": (
                    validation.get("score", 0.0) + format_validation.get("score", 0.0)
                )
                / 2,
            },
        }

    except Exception as e:
        return {
            "error": str(e),
            "meta": {
                "file": pdf_path,
                "pages": 1,
                "extraction_methods": ["error"],
                "confidence": 0.0,
            },
            "mapping_path": "",
            "mapping": {},
            "extraction_validation": {
                "is_valid": False,
                "score": 0.0,
                "issues": [str(e)],
            },
            "learning_result": {"fields_processed": 0, "mappings_learned": 0},
            "format_validation": {"is_valid": False, "score": 0.0, "errors": [str(e)]},
            "summary": {
                "fields_extracted": 0,
                "mappings_learned": 0,
                "extraction_confidence": 0.0,
                "format_confidence": 0.0,
                "overall_quality": 0.0,
            },
        }


@with_metrics("orchestrator.rl.generate_from_learned")
def generate_from_learned(
    payload: Dict[str, Any],
    format_name: str,
    validate_output: bool = True,
    auto_correct: bool = False,
) -> Dict[str, Any]:
    """
    Enhanced generation from learned format with validation and auto-correction.

    Args:
        payload: Input payload with source data
        format_name: Name of the learned format to use
        validate_output: Whether to validate the generated output
        auto_correct: Whether to apply automatic corrections

    Returns:
        Dict with generated data, validation results, and confidence scores
    """
    try:
        # Step 1: Load learned format
        learned_format = load_learned_format(format_name)
        if not learned_format:
            return {
                "error": f"Learned format '{format_name}' not found",
                "result": {},
                "provenance": {},
                "confidence": 0.0,
                "alerts": [
                    {"level": "error", "msg": f"Format {format_name} not found"}
                ],
            }

        # Step 2: Generate data using learned mapping
        mapping = learned_format.get("fields", {})
        return _generate_from_mapping(
            payload, mapping, validate_output, auto_correct, format_name
        )

    except Exception as e:
        return {
            "error": str(e),
            "result": {},
            "provenance": {},
            "confidence": 0.0,
            "alerts": [{"level": "error", "msg": f"Generation failed: {str(e)}"}],
        }


def generate_from_learned_mapping(
    payload: Dict[str, Any],
    mapping: Dict[str, Any],
    validate_output: bool = True,
    auto_correct: bool = False,
) -> Dict[str, Any]:
    """
    Generate from learned mapping directly (for backward compatibility).

    Args:
        payload: Input payload with source data
        mapping: Direct mapping dictionary
        validate_output: Whether to validate the generated output
        auto_correct: Whether to apply automatic corrections

    Returns:
        Dict with generated data, validation results, and confidence scores
    """
    try:
        return _generate_from_mapping(
            payload, mapping, validate_output, auto_correct, "direct_mapping"
        )
    except Exception as e:
        return {
            "error": str(e),
            "result": {},
            "provenance": {},
            "confidence": 0.0,
            "alerts": [{"level": "error", "msg": f"Generation failed: {str(e)}"}],
        }


def _generate_from_mapping(
    payload: Dict[str, Any],
    mapping: Dict[str, Any],
    validate_output: bool = True,
    auto_correct: bool = False,
    format_name: str = "unknown",
) -> Dict[str, Any]:
    """
    Internal function to generate from mapping.
    """
    # Step 1: Generate data using learned mapping
    src = payload.get("source_fields", {})
    result: Dict[str, Any] = {}
    prov_map: Dict[str, Any] = {}

    for field_name, field_info in mapping.items():
        if isinstance(field_info, dict):
            value = src.get(field_name)
            result[field_name] = value
            prov_map[field_name] = {
                "endpoint": field_info.get("endpoint", ""),
                "filters": field_info.get("filters", {}),
                "confidence": field_info.get("confidence", 0.0),
                "source": field_info.get("source", "learned"),
            }

    # Step 2: Create provenance
    provenance = make_field_provenance(**prov_map)

    # Step 3: Validate output if requested
    validation_results = {}
    alerts = []

    if validate_output:
        # Validate against learned format
        format_validation = validate_learned_format(result, format_name)
        validation_results["format_validation"] = format_validation

        # Reconcile totals
        reconciliation = reconcile_totals(result)
        validation_results["reconciliation"] = reconciliation

        # Cross-field consistency check
        consistency = cross_field_consistency_check(result)
        validation_results["consistency"] = consistency

        # Generate alerts
        if not format_validation.get("is_valid", True):
            alerts.append(
                {
                    "level": "warning",
                    "msg": f"Format validation failed: {format_validation.get('errors', [])}",
                }
            )

        if not reconciliation.get("reconciliation", {}).get("is_valid", True):
            alerts.append(
                {
                    "level": "warning",
                    "msg": f"Reconciliation issues: {reconciliation.get('reconciliation', {}).get('issues', [])}",
                }
            )

        if not consistency.get("is_consistent", True):
            alerts.append(
                {
                    "level": "warning",
                    "msg": f"Consistency issues: {consistency.get('issues', [])}",
                }
            )

    # Step 4: Auto-correct if requested
    corrections = {}
    if auto_correct and validation_results:
        corrections = _apply_auto_corrections(result, validation_results)
        if corrections:
            result.update(corrections)
            alerts.append(
                {"level": "info", "msg": f"Applied {len(corrections)} auto-corrections"}
            )

    # Step 5: Calculate confidence
    confidence_factors = []

    # Format confidence
    if validation_results.get("format_validation"):
        confidence_factors.append(
            validation_results["format_validation"].get("score", 0.0)
        )

    # Reconciliation confidence
    if validation_results.get("reconciliation"):
        confidence_factors.append(
            validation_results["reconciliation"]["reconciliation"].get("score", 0.0)
        )

    # Consistency confidence
    if validation_results.get("consistency"):
        consistency_score = (
            1.0 if validation_results["consistency"].get("is_consistent", True) else 0.5
        )
        confidence_factors.append(consistency_score)

    # Average confidence
    overall_confidence = (
        sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    )

    # Step 6: Log history and deltas
    alerts_pack = log_with_deltas_and_anomalies(
        "L-RL-001", payload, result, provenance, period_key=payload.get("period")
    )
    alerts.extend(alerts_pack.get("alerts", []))

    return {
        "result": result,
        "provenance": provenance,
        "confidence": overall_confidence,
        "alerts": alerts,
        "enabled": True,  # Default to True when generation succeeds
        "meta": {
            "format_name": format_name,
            "format_version": "1.0",
            "validation_results": validation_results,
            "corrections": corrections,
            "generation_method": "learned_format",
        },
    }


def _apply_auto_corrections(
    data: Dict[str, Any], validation_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply automatic corrections based on validation results."""
    corrections = {}

    # Apply reconciliation corrections
    reconciliation = validation_results.get("reconciliation", {})
    if reconciliation:
        reconciliation_data = reconciliation.get("reconciliation", {})
        corrections.update(reconciliation_data.get("corrections", {}))

    # Apply format validation corrections
    format_validation = validation_results.get("format_validation", {})
    if format_validation and not format_validation.get("is_valid", True):
        # Try to fix missing required fields
        errors = format_validation.get("errors", [])
        for error in errors:
            if "Missing required field" in error:
                field_name = error.split(": ")[-1]
                # Set default value based on field type
                if "revenue" in field_name.lower() or "income" in field_name.lower():
                    corrections[field_name] = 0.0
                elif "expense" in field_name.lower() or "cost" in field_name.lower():
                    corrections[field_name] = 0.0
                elif "profit" in field_name.lower() or "loss" in field_name.lower():
                    corrections[field_name] = 0.0
                else:
                    corrections[field_name] = ""

    return corrections


@with_metrics("orchestrator.rl.compare_formats")
def compare_formats(format1: str, format2: str) -> Dict[str, Any]:
    """Compare two learned formats and identify differences."""
    try:
        format1_data = load_learned_format(format1)
        format2_data = load_learned_format(format2)

        if not format1_data or not format2_data:
            return {
                "error": f"One or both formats not found: {format1}, {format2}",
                "comparison": {},
            }

        fields1 = set(format1_data.get("fields", {}).keys())
        fields2 = set(format2_data.get("fields", {}).keys())

        common_fields = fields1 & fields2
        only_in_format1 = fields1 - fields2
        only_in_format2 = fields2 - fields1

        # Compare common fields
        field_differences = []
        for field in common_fields:
            field1_info = format1_data["fields"][field]
            field2_info = format2_data["fields"][field]

            if field1_info != field2_info:
                field_differences.append(
                    {"field": field, "format1": field1_info, "format2": field2_info}
                )

        return {
            "comparison": {
                "format1": {
                    "name": format1,
                    "version": format1_data.get("version", "1.0"),
                    "field_count": len(fields1),
                },
                "format2": {
                    "name": format2,
                    "version": format2_data.get("version", "1.0"),
                    "field_count": len(fields2),
                },
                "field_analysis": {
                    "common_fields": len(common_fields),
                    "only_in_format1": len(only_in_format1),
                    "only_in_format2": len(only_in_format2),
                    "field_differences": len(field_differences),
                },
                "common_fields": list(common_fields),
                "only_in_format1": list(only_in_format1),
                "only_in_format2": list(only_in_format2),
                "field_differences": field_differences,
            }
        }

    except Exception as e:
        return {"error": str(e), "comparison": {}}


@with_metrics("orchestrator.rl.list_available_formats")
def list_available_formats() -> Dict[str, Any]:
    """List all available learned formats with metadata."""
    try:
        formats = list_learned_formats()

        # Group by source
        by_source = {}
        for fmt in formats:
            source = fmt.get("source", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(fmt)

        # Calculate statistics
        total_formats = len(formats)
        total_fields = sum(fmt.get("field_count", 0) for fmt in formats)
        avg_confidence = (
            sum(fmt.get("confidence", 0.0) for fmt in formats) / total_formats
            if total_formats > 0
            else 0.0
        )

        return {
            "formats": formats,
            "statistics": {
                "total_formats": total_formats,
                "total_fields": total_fields,
                "average_confidence": avg_confidence,
                "by_source": {
                    source: len(formats) for source, formats in by_source.items()
                },
            },
            "grouped_by_source": by_source,
        }

    except Exception as e:
        return {"error": str(e), "formats": [], "statistics": {}}


@with_metrics("orchestrator.rl.validate_pdf_against_format")
def validate_pdf_against_format(pdf_path: str, format_name: str) -> Dict[str, Any]:
    """Validate a PDF against a learned format."""
    try:
        # Extract fields from PDF
        extraction_result = extract_fields(pdf_path)
        fields = extraction_result.get("fields", {})

        # Validate against format
        validation = validate_learned_format(fields, format_name)

        # Detect mismatches if we have expected values
        mismatches = {}
        learned_format = load_learned_format(format_name)
        if learned_format:
            expected_fields = set(learned_format.get("fields", {}).keys())
            actual_fields = set(fields.keys())

            missing_fields = expected_fields - actual_fields
            extra_fields = actual_fields - expected_fields

            if missing_fields:
                mismatches["missing_fields"] = list(missing_fields)
            if extra_fields:
                mismatches["extra_fields"] = list(extra_fields)

        return {
            "pdf_path": pdf_path,
            "format_name": format_name,
            "extraction_result": extraction_result,
            "validation": validation,
            "mismatches": mismatches,
            "summary": {
                "fields_extracted": len(fields),
                "validation_score": validation.get("score", 0.0),
                "is_valid": validation.get("is_valid", False),
                "missing_fields": len(mismatches.get("missing_fields", [])),
                "extra_fields": len(mismatches.get("extra_fields", [])),
            },
        }

    except Exception as e:
        return {
            "error": str(e),
            "pdf_path": pdf_path,
            "format_name": format_name,
            "validation": {"is_valid": False, "score": 0.0, "errors": [str(e)]},
        }
