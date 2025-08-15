import pytest
from unittest.mock import patch, MagicMock
import json

from logics.l4_contract_runtime import handle_l4_with_telemetry


def test_history_telemetry_coexistence():
    """Test that history and telemetry coexist without breaking logic outputs"""

    # Mock handler function that returns L4-compliant output
    def mock_handler(payload):
        return {
            "result": {"revenue": 10000, "expenses": 5000, "net_profit": 5000},
            "provenance": {
                "sources": [
                    {
                        "source": "zoho",
                        "endpoint": "reports/pnl",
                        "ids": ["123"],
                        "filters": {},
                    }
                ],
                "figures": {
                    "revenue": {"source": "zoho", "endpoint": "reports/pnl"},
                    "expenses": {"source": "zoho", "endpoint": "reports/pnl"},
                    "net_profit": {"source": "calculation", "method": "subtraction"},
                },
            },
            "confidence": 0.85,
            "alerts": [],
        }

    # Test payload
    payload = {
        "org_id": "test_org_123",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "test.zoho.com",
        "query": "Generate P&L report",
    }

    # Mock both history and telemetry functions
    with patch("logics.l4_contract_runtime.real_log_with_deltas") as mock_history:
        with patch("logics.l4_contract_runtime.emit_logic_telemetry") as mock_telemetry:
            # Configure history mock to return expected structure
            mock_history.return_value = {
                "history": [
                    {
                        "type": "execution",
                        "logic_id": "L-001",
                        "timestamp": "2025-01-27T18:00:00Z",
                        "inputs": payload,
                        "outputs": {
                            "revenue": 10000,
                            "expenses": 5000,
                            "net_profit": 5000,
                        },
                        "provenance": {
                            "sources": [{"source": "zoho", "endpoint": "reports/pnl"}]
                        },
                    }
                ],
                "deltas": [],
                "anomalies": [],
            }

            # Execute with telemetry wrapper
            result = handle_l4_with_telemetry(
                logic_id="L-001",
                handler_func=mock_handler,
                payload=payload,
                org_id="test_org_123",
            )

            # Verify L4 contract shape is preserved
            assert "result" in result
            assert "provenance" in result
            assert "confidence" in result
            assert "alerts" in result

            # Verify result content is unchanged
            assert result["result"]["revenue"] == 10000
            assert result["result"]["expenses"] == 5000
            assert result["result"]["net_profit"] == 5000
            assert result["confidence"] == 0.85

            # Verify history was called
            mock_history.assert_called_once()
            history_call_args = mock_history.call_args[1]
            assert history_call_args["logic_id"] == "L-001"
            assert history_call_args["inputs"] == payload
            assert "revenue" in history_call_args["outputs"]

            # Verify telemetry was called
            mock_telemetry.assert_called_once()
            telemetry_call_args = mock_telemetry.call_args[1]
            assert telemetry_call_args["logic_id"] == "L-001"
            assert telemetry_call_args["org_id"] == "test_org_123"
            assert telemetry_call_args["status"] == "success"
            assert telemetry_call_args["confidence"] == 0.85


def test_history_telemetry_error_handling():
    """Test that history and telemetry work together during errors"""

    # Mock handler function that raises an exception
    def mock_handler_error(payload):
        raise ValueError("Test error for history and telemetry")

    # Test payload
    payload = {
        "org_id": "test_org_error",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "test.zoho.com",
        "query": "Generate report with error",
    }

    # Mock both history and telemetry functions
    with patch("logics.l4_contract_runtime.real_log_with_deltas") as mock_history:
        with patch("logics.l4_contract_runtime.emit_logic_telemetry") as mock_telemetry:
            # Configure history mock
            mock_history.return_value = {"history": [], "deltas": [], "anomalies": []}

            # Execute with telemetry wrapper
            result = handle_l4_with_telemetry(
                logic_id="L-001",
                handler_func=mock_handler_error,
                payload=payload,
                org_id="test_org_error",
            )

            # Verify error result structure is maintained
            assert "result" in result
            assert "provenance" in result
            assert "confidence" in result
            assert "alerts" in result

            # Verify error is properly captured
            assert "error" in result["result"]
            assert "Test error for history and telemetry" in result["result"]["error"]
            assert result["confidence"] == 0.0
            assert len(result["alerts"]) > 0

            # Verify telemetry was called with error status
            mock_telemetry.assert_called_once()
            telemetry_call_args = mock_telemetry.call_args[1]
            assert telemetry_call_args["logic_id"] == "L-001"
            assert telemetry_call_args["status"] == "error"
            assert telemetry_call_args["error_taxonomy"] == "ValueError"
            assert telemetry_call_args["confidence"] == 0.0


def test_history_telemetry_provenance_integration():
    """Test that provenance is properly handled by both history and telemetry"""

    # Mock handler function with complex provenance
    def mock_handler_provenance(payload):
        return {
            "result": {"total": 15000},
            "provenance": {
                "sources": [
                    {
                        "source": "zoho",
                        "endpoint": "reports/pnl",
                        "ids": ["123"],
                        "filters": {},
                    },
                    {
                        "source": "zoho",
                        "endpoint": "reports/balance",
                        "ids": ["456"],
                        "filters": {},
                    },
                ],
                "figures": {
                    "revenue": {
                        "source": "zoho",
                        "endpoint": "reports/pnl",
                        "gstin": "27ABCDE1234F1Z5",
                    },
                    "assets": {
                        "source": "zoho",
                        "endpoint": "reports/balance",
                        "account_number": "1234567890",
                    },
                },
            },
            "confidence": 0.9,
            "alerts": [],
        }

    # Test payload
    payload = {
        "org_id": "test_org_provenance",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "test.zoho.com",
        "query": "Generate report with provenance",
    }

    # Mock both history and telemetry functions
    with patch("logics.l4_contract_runtime.real_log_with_deltas") as mock_history:
        with patch("logics.l4_contract_runtime.emit_logic_telemetry") as mock_telemetry:
            # Configure history mock
            mock_history.return_value = {
                "history": [{"type": "execution", "logic_id": "L-001"}],
                "deltas": [],
                "anomalies": [],
            }

            # Execute with telemetry wrapper
            result = handle_l4_with_telemetry(
                logic_id="L-001",
                handler_func=mock_handler_provenance,
                payload=payload,
                org_id="test_org_provenance",
            )

            # Verify provenance is preserved in result
            assert "provenance" in result
            assert "sources" in result["provenance"]
            assert "figures" in result["provenance"]
            assert len(result["provenance"]["sources"]) == 2
            assert len(result["provenance"]["figures"]) == 2

            # Verify history was called with provenance
            mock_history.assert_called_once()
            history_call_args = mock_history.call_args[1]
            assert "provenance" in history_call_args
            assert (
                history_call_args["provenance"]["sources"]
                == result["provenance"]["sources"]
            )

            # Verify telemetry was called with provenance metrics
            mock_telemetry.assert_called_once()
            telemetry_call_args = mock_telemetry.call_args[1]
            assert (
                telemetry_call_args["provenance_keys"] > 0
            )  # Should count provenance keys


def test_history_telemetry_validation_integration():
    """Test that accounting validation works with both history and telemetry"""

    # Mock handler function that returns data with validation issues
    def mock_handler_validation(payload):
        return {
            "result": {
                "revenue": 10000,
                "expenses": 5000,
                "net_profit": 6000,  # Incorrect: should be 5000
            },
            "provenance": {"sources": [{"source": "zoho", "endpoint": "reports/pnl"}]},
            "confidence": 0.8,
            "alerts": [],
        }

    # Test payload
    payload = {
        "org_id": "test_org_validation",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "test.zoho.com",
        "query": "Generate report with validation",
    }

    # Mock validation function to return alerts
    with patch(
        "logics.l4_contract_runtime.real_validate_accounting"
    ) as mock_validation:
        with patch("logics.l4_contract_runtime.real_log_with_deltas") as mock_history:
            with patch(
                "logics.l4_contract_runtime.emit_logic_telemetry"
            ) as mock_telemetry:
                # Configure validation mock to return alerts
                mock_validation.return_value = [
                    "Net profit does not reconcile with revenue - expenses"
                ]

                # Configure history mock
                mock_history.return_value = {
                    "history": [{"type": "execution", "logic_id": "L-001"}],
                    "deltas": [],
                    "anomalies": [],
                }

                # Execute with telemetry wrapper
                result = handle_l4_with_telemetry(
                    logic_id="L-001",
                    handler_func=mock_handler_validation,
                    payload=payload,
                    org_id="test_org_validation",
                )

                # Verify validation alerts are added to result
                assert "alerts" in result
                assert len(result["alerts"]) == 1
                assert "Net profit does not reconcile" in result["alerts"][0]

                # Verify validation was called
                mock_validation.assert_called_once()

                # Verify telemetry includes alert count
                mock_telemetry.assert_called_once()
                telemetry_call_args = mock_telemetry.call_args[1]
                assert telemetry_call_args["alerts_count"] == 1


def test_history_telemetry_non_l4_format():
    """Test that non-L4 format results are properly converted"""

    # Mock handler function that returns non-L4 format
    def mock_handler_non_l4(payload):
        return {"revenue": 10000, "expenses": 5000, "net_profit": 5000}

    # Test payload
    payload = {
        "org_id": "test_org_non_l4",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "headers": {},
        "api_domain": "test.zoho.com",
        "query": "Generate non-L4 report",
    }

    # Mock both history and telemetry functions
    with patch("logics.l4_contract_runtime.real_log_with_deltas") as mock_history:
        with patch("logics.l4_contract_runtime.emit_logic_telemetry") as mock_telemetry:
            # Configure history mock
            mock_history.return_value = {
                "history": [{"type": "execution", "logic_id": "L-001"}],
                "deltas": [],
                "anomalies": [],
            }

            # Execute with telemetry wrapper
            result = handle_l4_with_telemetry(
                logic_id="L-001",
                handler_func=mock_handler_non_l4,
                payload=payload,
                org_id="test_org_non_l4",
            )

            # Verify result is converted to L4 format
            assert "result" in result
            assert "provenance" in result
            assert "confidence" in result
            assert "alerts" in result

            # Verify original data is preserved in result
            assert result["result"]["revenue"] == 10000
            assert result["result"]["expenses"] == 5000
            assert result["result"]["net_profit"] == 5000

            # Verify default values are set
            assert result["confidence"] == 0.75  # Default confidence
            assert result["alerts"] == []  # Empty alerts list

            # Verify history was called with converted data
            mock_history.assert_called_once()
            history_call_args = mock_history.call_args[1]
            assert history_call_args["outputs"]["revenue"] == 10000

            # Verify telemetry was called
            mock_telemetry.assert_called_once()
            telemetry_call_args = mock_telemetry.call_args[1]
            assert telemetry_call_args["logic_id"] == "L-001"
            assert telemetry_call_args["status"] == "success"
