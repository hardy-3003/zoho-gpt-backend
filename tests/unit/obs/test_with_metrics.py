import os, glob, json
import pytest
import time
from unittest.mock import patch, MagicMock


def test_with_metrics_does_not_change_output():
    """Test that the decorator doesn't change function outputs"""
    from helpers.obs import with_metrics

    # Test the decorator directly
    @with_metrics("test.metrics")
    def test_function():
        return {"result": "success", "provenance": {}, "alerts": []}

    # Call the function
    out = test_function()
    assert (
        isinstance(out, dict)
        and "result" in out
        and "provenance" in out
        and "alerts" in out
    )
    assert out["result"] == "success"
    assert out["provenance"] == {}
    assert out["alerts"] == []


def test_telemetry_span_context_manager():
    """Test telemetry span context manager functionality"""
    from helpers.telemetry import span, _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    with span("test_span", test_tag="value"):
        context = _get_current_context()
        assert "span_id" in context
        assert "span_name" in context
        assert context["span_name"] == "test_span"
        assert context["test_tag"] == "value"

    # Context should be restored
    context = _get_current_context()
    assert "span_id" not in context
    assert "span_name" not in context


def test_telemetry_redaction():
    """Test that sensitive data is properly redacted"""
    from helpers.telemetry import _redact_sensitive_data

    # Test sensitive field redaction
    data = {
        "normal_field": "value",
        "password": "secret123",
        "auth_token": "abc123",
        "gstin": "27ABCDE1234F1Z5",
        "nested": {"account_number": "1234567890", "safe_field": "ok"},
    }

    redacted = _redact_sensitive_data(data)

    assert redacted["normal_field"] == "value"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["auth_token"] == "[REDACTED]"
    assert redacted["gstin"] == "[REDACTED]"
    assert redacted["nested"]["account_number"] == "[REDACTED]"
    assert redacted["nested"]["safe_field"] == "ok"


def test_telemetry_disabled():
    """Test that telemetry is disabled when TELEMETRY_ENABLED is False"""
    with patch.dict(os.environ, {"TELEMETRY_ENABLED": "false"}):
        # Reload the module to pick up the new environment variable
        import importlib
        import helpers.telemetry

        importlib.reload(helpers.telemetry)

        from helpers.telemetry import emit_logic_telemetry, event, incr

        # These should not raise exceptions when telemetry is disabled
        emit_logic_telemetry("test", "org1", 100.0, "success")
        event("test_event", {"data": "value"})
        incr("test_counter", {"tag": "value"})


def test_provenance_telemetry_utilities():
    """Test provenance telemetry utilities"""
    from helpers.provenance import (
        standardize_provenance_map,
        redact_pii_from_provenance,
        get_provenance_metrics,
        create_telemetry_provenance,
    )

    # Test provenance map
    provenance = {
        "sources": [
            {"source": "zoho", "endpoint": "reports/pnl", "ids": ["123"], "filters": {}}
        ],
        "figures": {
            "revenue": {
                "source": "zoho",
                "endpoint": "reports/pnl",
                "gstin": "27ABCDE1234F1Z5",
            },
            "expenses": {"source": "calculation", "method": "sum"},
        },
    }

    # Test standardization
    std_prov = standardize_provenance_map(provenance)
    assert "sources" in std_prov
    assert "figures" in std_prov
    assert std_prov["keys_count"] > 0

    # Test PII redaction
    redacted = redact_pii_from_provenance(provenance)
    assert redacted["figures"]["revenue"]["gstin"] == "[REDACTED]"
    assert redacted["figures"]["expenses"]["method"] == "sum"  # Not redacted

    # Test metrics extraction
    metrics = get_provenance_metrics(provenance)
    assert metrics["sources_count"] == 1
    assert metrics["figures_count"] == 2
    assert metrics["has_zoho_sources"] == True
    assert metrics["has_calculated_sources"] == True

    # Test telemetry-ready provenance
    telemetry_prov = create_telemetry_provenance(provenance)
    assert "provenance" in telemetry_prov
    assert "metrics" in telemetry_prov
    assert "keys_count" in telemetry_prov


def test_l4_telemetry_wrapper():
    """Test L4 contract runtime telemetry wrapper"""
    from logics.l4_contract_runtime import handle_l4_with_telemetry

    # Mock handler function
    def mock_handler(payload):
        return {
            "result": {"revenue": 1000, "expenses": 500},
            "provenance": {"sources": [{"source": "zoho", "endpoint": "reports/pnl"}]},
            "confidence": 0.85,
            "alerts": [],
        }

    # Test successful execution
    with patch("logics.l4_contract_runtime.emit_logic_telemetry") as mock_telemetry:
        result = handle_l4_with_telemetry(
            logic_id="L-001",
            handler_func=mock_handler,
            payload={"org_id": "test_org", "start_date": "2025-01-01"},
            org_id="test_org",
        )

        # Verify result structure
        assert "result" in result
        assert "provenance" in result
        assert "confidence" in result
        assert "alerts" in result

        # Verify telemetry was called
        mock_telemetry.assert_called_once()
        call_args = mock_telemetry.call_args[1]
        assert call_args["logic_id"] == "L-001"
        assert call_args["org_id"] == "test_org"
        assert call_args["status"] == "success"
        assert call_args["confidence"] == 0.85


def test_l4_telemetry_wrapper_error():
    """Test L4 contract runtime telemetry wrapper with error handling"""
    from logics.l4_contract_runtime import handle_l4_with_telemetry

    # Mock handler function that raises an exception
    def mock_handler_error(payload):
        raise ValueError("Test error")

    # Test error execution
    with patch("logics.l4_contract_runtime.emit_logic_telemetry") as mock_telemetry:
        result = handle_l4_with_telemetry(
            logic_id="L-001",
            handler_func=mock_handler_error,
            payload={"org_id": "test_org"},
            org_id="test_org",
        )

        # Verify error result structure
        assert "result" in result
        assert "error" in result["result"]
        assert "provenance" in result
        assert "confidence" in result
        assert "alerts" in result

        # Verify telemetry was called with error status
        mock_telemetry.assert_called_once()
        call_args = mock_telemetry.call_args[1]
        assert call_args["logic_id"] == "L-001"
        assert call_args["status"] == "error"
        assert call_args["error_taxonomy"] == "ValueError"
        assert call_args["confidence"] == 0.0


def test_orchestration_telemetry():
    """Test orchestration telemetry emission"""
    from helpers.telemetry import emit_orchestration_telemetry

    with patch("helpers.telemetry._log") as mock_log:
        emit_orchestration_telemetry(
            run_id="test_run_123",
            dag_node_id="node_1",
            logic_id="L-001",
            duration_ms=150.5,
            status="success",
            deps=["node_0"],
            attempt=1,
            retry_backoff_ms=0,
        )

        # Verify log was called
        mock_log.info.assert_called_once()
        call_args = mock_log.info.call_args
        assert call_args[0][0] == "telemetry.orchestration"

        # Verify structured data
        extra_data = call_args[1]["extra"]
        assert extra_data["run_id"] == "test_run_123"
        assert extra_data["dag_node_id"] == "node_1"
        assert extra_data["logic_id"] == "L-001"
        assert extra_data["duration_ms"] == 150.5
        assert extra_data["status"] == "success"


def test_telemetry_context_management():
    """Test telemetry context management functions"""
    from helpers.telemetry import (
        set_org_context,
        set_run_context,
        set_dag_context,
        _get_current_context,
    )

    # Clear context
    _get_current_context().clear()

    # Set contexts
    set_org_context("org_123")
    set_run_context("run_456")
    set_dag_context("node_1", ["node_0"])

    # Verify context
    context = _get_current_context()
    assert context["org_id"] == "org_123"
    assert context["run_id"] == "run_456"
    assert context["dag_node_id"] == "node_1"
    assert context["deps"] == ["node_0"]


def test_telemetry_structured_logging():
    """Test that telemetry emits structured JSON logs"""
    from helpers.telemetry import event, timing, incr

    with patch("helpers.telemetry._log") as mock_log:
        # Test event emission
        event("test_event", {"data": "value"})

        # Verify structured log format
        mock_log.info.assert_called()
        call_args = mock_log.info.call_args
        assert call_args[0][0] == "telemetry.event"

        extra_data = call_args[1]["extra"]
        assert "ts" in extra_data
        assert extra_data["type"] == "event"
        assert extra_data["name"] == "test_event"
        assert extra_data["data"]["data"] == "value"

        # Test timing emission
        with timing("test_timer", {"tag": "value"}):
            time.sleep(0.001)  # Small delay

        # Verify timing log
        timing_calls = [
            call
            for call in mock_log.info.call_args_list
            if call[0][0] == "telemetry.timing"
        ]
        assert len(timing_calls) > 0

        # Test counter emission
        incr("test_counter", {"tag": "value"}, 5)

        # Verify counter log
        counter_calls = [
            call
            for call in mock_log.info.call_args_list
            if call[0][0] == "telemetry.counter"
        ]
        assert len(counter_calls) > 0
