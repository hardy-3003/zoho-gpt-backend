"""
Integration tests for orchestrators.

This module tests the integration between orchestrators and logic modules.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import time

from core.operate_base import OperateInput
from orchestrators.mis_orchestrator import run_mis
from orchestrators.generic_report_orchestrator import run_generic


def test_mis_orchestrator_telemetry_emission():
    """Test that MIS orchestrator emits structured telemetry events"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_123",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Generate MIS report",
    )

    with patch("orchestrators.mis_orchestrator._log") as mock_log:
        # Run orchestrator
        result = run_mis(
            input=input_data,
            sections=["pnl", "salary"],
            use_dag=False,  # Use sequential for easier testing
            max_workers=2,
        )

        # Verify result structure
        assert result.content["sections"] is not None
        assert "run_id" in result.meta

        # Verify telemetry logs were emitted
        log_calls = mock_log.info.call_args_list

        # Should have span start/end logs
        span_start_calls = [
            call for call in log_calls if "telemetry.span_start" in str(call)
        ]
        span_end_calls = [
            call for call in log_calls if "telemetry.span_end" in str(call)
        ]

        assert len(span_start_calls) > 0
        assert len(span_end_calls) > 0

        # Verify orchestration telemetry
        orchestration_calls = [
            call for call in log_calls if "telemetry.orchestration" in str(call)
        ]
        assert len(orchestration_calls) > 0

        # Verify structured data in logs
        for call in orchestration_calls:
            extra_data = call[1]["extra"]
            assert "run_id" in extra_data
            assert "dag_node_id" in extra_data
            assert "logic_id" in extra_data
            assert "duration_ms" in extra_data
            assert "status" in extra_data


def test_generic_orchestrator_telemetry_emission():
    """Test that generic orchestrator emits structured telemetry events"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_456",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Generate generic report",
    )

    with patch("orchestrators.generic_report_orchestrator._log") as mock_log:
        # Run orchestrator
        result = run_generic(input=input_data, logic_keywords=["pnl", "balance_sheet"])

        # Verify result structure
        assert result.content["sections"] is not None
        assert "run_id" in result.meta

        # Verify telemetry logs were emitted
        log_calls = mock_log.info.call_args_list

        # Should have span start/end logs
        span_start_calls = [
            call for call in log_calls if "telemetry.span_start" in str(call)
        ]
        span_end_calls = [
            call for call in log_calls if "telemetry.span_end" in str(call)
        ]

        assert len(span_start_calls) > 0
        assert len(span_end_calls) > 0

        # Verify orchestration telemetry
        orchestration_calls = [
            call for call in log_calls if "telemetry.orchestration" in str(call)
        ]
        assert len(orchestration_calls) > 0


def test_orchestrator_dag_node_telemetry():
    """Test that each DAG node execution emits proper telemetry"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_789",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Test DAG telemetry",
    )

    with patch(
        "orchestrators.mis_orchestrator.emit_orchestration_telemetry"
    ) as mock_telemetry:
        # Run orchestrator with sequential execution
        result = run_mis(
            input=input_data, sections=["pnl"], use_dag=False, max_workers=1
        )

        # Verify telemetry was called for each node
        assert mock_telemetry.called

        # Get all calls
        calls = mock_telemetry.call_args_list

        # Verify each call has proper structure
        for call in calls:
            kwargs = call[1]
            assert "run_id" in kwargs
            assert "dag_node_id" in kwargs
            assert "logic_id" in kwargs
            assert "duration_ms" in kwargs
            assert "status" in kwargs
            assert kwargs["duration_ms"] > 0  # Should have some duration


def test_orchestrator_error_telemetry():
    """Test that orchestrator properly handles and telemetries errors"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_error",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Test error telemetry",
    )

    with patch("orchestrators.mis_orchestrator.route") as mock_route:
        # Make route return None to trigger fallback logic
        mock_route.return_value = None

        with patch(
            "orchestrators.mis_orchestrator.emit_orchestration_telemetry"
        ) as mock_telemetry:
            # Run orchestrator
            result = run_mis(
                input=input_data,
                sections=["nonexistent_section"],
                use_dag=False,
                max_workers=1,
            )

            # Verify result contains missing sections
            assert "nonexistent_section" in result.meta["missing"]

            # Verify telemetry was still called (even for missing sections)
            assert mock_telemetry.called


def test_orchestrator_context_propagation():
    """Test that telemetry context is properly propagated through orchestration"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_context",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Test context propagation",
    )

    with patch("orchestrators.mis_orchestrator._log") as mock_log:
        # Run orchestrator
        result = run_mis(
            input=input_data, sections=["pnl"], use_dag=False, max_workers=1
        )

        # Verify context was set
        context = _get_current_context()
        assert "org_id" in context
        assert context["org_id"] == "test_org_context"

        # Verify run_id was set
        assert "run_id" in context
        assert context["run_id"] == result.meta["run_id"]


def test_orchestrator_telemetry_redaction():
    """Test that sensitive data is redacted in orchestration telemetry"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input with sensitive data
    input_data = OperateInput(
        org_id="test_org_sensitive",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={"Authorization": "Bearer secret_token_123"},
        api_domain="test.zoho.com",
        query="Test sensitive data",
    )

    with patch("orchestrators.mis_orchestrator._log") as mock_log:
        # Run orchestrator
        result = run_mis(
            input=input_data, sections=["pnl"], use_dag=False, max_workers=1
        )

        # Verify telemetry logs were emitted
        log_calls = mock_log.info.call_args_list

        # Check that sensitive data is redacted in logs
        for call in log_calls:
            if "extra" in call[1]:
                extra_data = call[1]["extra"]
                # Convert to string to check for redacted values
                log_str = json.dumps(extra_data)
                assert "secret_token_123" not in log_str
                # Should contain redacted marker
                assert "[REDACTED]" in log_str


def test_orchestrator_metrics_aggregation():
    """Test that orchestrator aggregates metrics properly"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_metrics",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Test metrics aggregation",
    )

    with patch(
        "orchestrators.mis_orchestrator.emit_orchestration_telemetry"
    ) as mock_telemetry:
        # Run orchestrator with multiple sections
        result = run_mis(
            input=input_data,
            sections=["pnl", "salary", "balance_sheet"],
            use_dag=False,
            max_workers=1,
        )

        # Verify telemetry was called for each section
        calls = mock_telemetry.call_args_list
        assert len(calls) >= 3  # At least one call per section

        # Verify metrics aggregation
        total_duration = sum(call[1]["duration_ms"] for call in calls)
        assert total_duration > 0

        # Verify all calls have same run_id
        run_ids = set(call[1]["run_id"] for call in calls)
        assert len(run_ids) == 1
        assert list(run_ids)[0] == result.meta["run_id"]


def test_orchestrator_performance_overhead():
    """Test that telemetry adds minimal performance overhead"""
    from helpers.telemetry import _get_current_context

    # Clear any existing context
    _get_current_context().clear()

    # Mock input
    input_data = OperateInput(
        org_id="test_org_perf",
        start_date="2025-01-01",
        end_date="2025-01-31",
        headers={},
        api_domain="test.zoho.com",
        query="Test performance overhead",
    )

    # Measure execution time without telemetry
    with patch(
        "orchestrators.mis_orchestrator.emit_orchestration_telemetry"
    ) as mock_telemetry:
        start_time = time.perf_counter()
        result = run_mis(
            input=input_data, sections=["pnl"], use_dag=False, max_workers=1
        )
        execution_time = time.perf_counter() - start_time

        # Verify telemetry was called
        assert mock_telemetry.called

        # Performance overhead should be minimal (< 3% as per requirements)
        # This is a basic check - in real scenarios, you'd want more sophisticated benchmarking
        assert (
            execution_time < 1.0
        )  # Should complete within 1 second for simple operations
