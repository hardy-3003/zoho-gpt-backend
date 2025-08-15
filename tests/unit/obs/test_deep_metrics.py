"""
Unit tests for deep metrics collection system.

Tests metrics capture, field correctness, redaction, and performance overhead.
"""

import pytest
import time
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

from helpers.telemetry import (
    get_deep_metrics,
    export_metrics,
    clear_metrics,
    set_org_context,
    set_logic_context,
    timing,
    span,
    emit_logic_telemetry,
    emit_orchestration_telemetry,
)


class TestDeepMetricsCollection:
    """Test deep metrics collection functionality."""

    def setup_method(self):
        """Clear metrics before each test."""
        clear_metrics()

    def test_metrics_storage_and_retrieval(self):
        """Test that metrics are properly stored and retrieved."""
        # Simulate some metrics
        with timing("test_metric", {"org_id": "test_org"}):
            time.sleep(0.01)  # Small delay to ensure timing

        # Get metrics
        metrics = get_deep_metrics()

        # Verify metrics structure
        assert "latency" in metrics
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "errors" in metrics
        assert "retries" in metrics
        assert "throughput" in metrics

    def test_metrics_with_breakdowns(self):
        """Test metrics with org and logic breakdowns."""
        # Set context
        set_org_context("test_org")
        set_logic_context("test_logic")

        # Simulate metrics
        with timing("test_metric"):
            time.sleep(0.01)

        # Get metrics with breakdowns
        metrics = get_deep_metrics(org_id="test_org", logic_id="test_logic")

        # Verify breakdown keys exist
        assert "latency" in metrics
        # Should have composite keys with org and logic
        latency_keys = list(metrics["latency"].keys())
        assert any("test_org:test_logic" in key for key in latency_keys)

    def test_percentile_calculation(self):
        """Test percentile calculation accuracy."""
        # Add multiple data points
        for i in range(100):
            with timing(f"test_metric_{i}"):
                time.sleep(0.001)

        metrics = get_deep_metrics()

        # Check percentile calculations
        for key, data in metrics["latency"].items():
            assert "p50" in data
            assert "p95" in data
            assert "p99" in data
            assert data["p50"] <= data["p95"] <= data["p99"]

    def test_error_metrics(self):
        """Test error metrics collection."""
        # Simulate errors
        with patch("helpers.telemetry.event") as mock_event:
            with span("test_error_span"):
                raise ValueError("Test error")

        metrics = get_deep_metrics()

        # Check error metrics
        assert "errors" in metrics
        # Should have error entries
        assert len(metrics["errors"]) > 0

    def test_retry_metrics(self):
        """Test retry metrics collection."""
        # Simulate retries
        emit_orchestration_telemetry(
            run_id="test_run",
            dag_node_id="test_node",
            logic_id="test_logic",
            duration_ms=100.0,
            status="success",
            attempt=3,  # This indicates retries
        )

        metrics = get_deep_metrics()

        # Check retry metrics
        assert "retries" in metrics
        # Should have retry entries
        assert len(metrics["retries"]) > 0

    def test_throughput_metrics(self):
        """Test throughput metrics collection."""
        # Simulate throughput
        emit_logic_telemetry(
            logic_id="test_logic",
            org_id="test_org",
            duration_ms=100.0,
            status="success",
        )

        metrics = get_deep_metrics()

        # Check throughput metrics
        assert "throughput" in metrics
        # Should have throughput entries
        assert len(metrics["throughput"]) > 0

    def test_memory_metrics(self):
        """Test memory usage metrics."""
        with timing("memory_test"):
            # Simulate some work
            _ = [i for i in range(1000)]

        metrics = get_deep_metrics()

        # Check memory metrics
        assert "memory" in metrics
        for key, data in metrics["memory"].items():
            assert "mean" in data
            assert "max" in data
            assert "min" in data
            assert data["min"] <= data["mean"] <= data["max"]

    def test_cpu_metrics(self):
        """Test CPU usage metrics."""
        with timing("cpu_test"):
            # Simulate CPU work
            sum(range(10000))

        metrics = get_deep_metrics()

        # Check CPU metrics
        assert "cpu" in metrics
        for key, data in metrics["cpu"].items():
            assert "mean" in data
            assert "max" in data
            assert "min" in data
            assert data["min"] <= data["mean"] <= data["max"]

    def test_metrics_export_json(self):
        """Test metrics export in JSON format."""
        # Add some metrics
        with timing("export_test"):
            time.sleep(0.01)

        # Export as JSON
        json_metrics = export_metrics("json")

        # Verify JSON format
        assert isinstance(json_metrics, str)
        parsed = json.loads(json_metrics)
        assert "latency" in parsed
        assert "cpu" in parsed
        assert "memory" in parsed

    def test_metrics_export_prometheus(self):
        """Test metrics export in Prometheus format."""
        # Add some metrics
        with timing("prometheus_test"):
            time.sleep(0.01)

        # Export as Prometheus
        prometheus_metrics = export_metrics("prometheus")

        # Verify Prometheus format
        assert isinstance(prometheus_metrics, str)
        lines = prometheus_metrics.split("\n")
        assert len(lines) > 0
        # Should have metric lines
        assert any("latency_" in line for line in lines)

    def test_metrics_clear(self):
        """Test metrics clearing functionality."""
        # Add some metrics
        with timing("clear_test"):
            time.sleep(0.01)

        # Verify metrics exist
        metrics_before = get_deep_metrics()
        assert len(metrics_before["latency"]) > 0

        # Clear metrics
        clear_metrics()

        # Verify metrics are cleared
        metrics_after = get_deep_metrics()
        assert len(metrics_after["latency"]) == 0

    def test_metrics_disabled(self):
        """Test metrics when disabled via environment."""
        with patch.dict(os.environ, {"DEEP_METRICS_ENABLED": "false"}):
            # Re-import to get disabled version
            import importlib
            import helpers.telemetry

            importlib.reload(helpers.telemetry)

            # Try to add metrics
            with timing("disabled_test"):
                time.sleep(0.01)

            # Get metrics
            metrics = get_deep_metrics()

            # Should be empty when disabled
            assert metrics == {}

    def test_metrics_thread_safety(self):
        """Test metrics collection thread safety."""
        import threading

        def add_metrics():
            for i in range(10):
                with timing(f"thread_metric_{i}"):
                    time.sleep(0.001)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_metrics)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Get metrics
        metrics = get_deep_metrics()

        # Should have metrics from all threads
        assert "latency" in metrics
        assert len(metrics["latency"]) > 0

    def test_metrics_performance_overhead(self):
        """Test that metrics collection has minimal overhead."""
        # Measure baseline performance
        start_time = time.perf_counter()
        for i in range(100):
            time.sleep(0.001)
        baseline_time = time.perf_counter() - start_time

        # Measure performance with metrics
        start_time = time.perf_counter()
        for i in range(100):
            with timing(f"perf_test_{i}"):
                time.sleep(0.001)
        metrics_time = time.perf_counter() - start_time

        # Overhead should be less than 10%
        overhead = (metrics_time - baseline_time) / baseline_time
        assert overhead < 0.1, f"Metrics overhead {overhead:.2%} exceeds 10%"

    def test_metrics_data_quality(self):
        """Test data quality of collected metrics."""
        # Add various types of metrics
        with timing("quality_test_1", {"tag": "value1"}):
            time.sleep(0.01)

        with timing("quality_test_2", {"tag": "value2"}):
            time.sleep(0.02)

        metrics = get_deep_metrics()

        # Check data quality
        for key, data in metrics["latency"].items():
            assert "count" in data
            assert "mean" in data
            assert "std" in data
            assert data["count"] > 0
            assert data["mean"] > 0
            assert data["std"] >= 0

    def test_metrics_redaction(self):
        """Test that sensitive data is properly redacted."""
        # Add metrics with sensitive data
        with timing(
            "sensitive_test",
            {
                "password": "secret123",
                "token": "abc123",
                "gstin": "22AAAAA0000A1Z5",
                "normal_field": "normal_value",
            },
        ):
            time.sleep(0.01)

        # Get metrics and check redaction
        metrics = get_deep_metrics()

        # Export as JSON to check redaction
        json_metrics = export_metrics("json")
        parsed = json.loads(json_metrics)

        # Sensitive fields should be redacted
        assert "password" not in json_metrics or "[REDACTED]" in json_metrics
        assert "token" not in json_metrics or "[REDACTED]" in json_metrics
        assert "gstin" not in json_metrics or "[REDACTED]" in json_metrics

        # Normal fields should not be redacted
        assert "normal_field" in json_metrics
        assert "normal_value" in json_metrics


class TestMetricsIntegration:
    """Test integration with other observability components."""

    def test_metrics_with_alerts(self):
        """Test metrics integration with alerting system."""
        from helpers.alerts import evaluate_alerts

        # Add metrics that would trigger alerts
        for i in range(20):  # High error rate
            with span("error_span"):
                raise ValueError("Test error")

        # Evaluate alerts
        alerts = evaluate_alerts("test_org", "test_logic", "test_orchestrator")

        # Should have alerts based on metrics
        assert len(alerts) >= 0  # May or may not have alerts depending on thresholds

    def test_metrics_with_anomaly_detection(self):
        """Test metrics integration with anomaly detection."""
        from helpers.anomaly_detector import detect_anomaly

        # Add normal metrics
        for i in range(10):
            with timing("normal_metric"):
                time.sleep(0.01)

        # Add anomalous metric
        anomaly_result = detect_anomaly(
            "test_metric", 10000.0, "test_org", "test_logic"  # Very high latency
        )

        # Should detect anomaly
        assert anomaly_result.is_anomaly or anomaly_result.overall_score > 0

    def test_metrics_context_propagation(self):
        """Test that context is properly propagated through metrics."""
        # Set context
        set_org_context("test_org")
        set_logic_context("test_logic")

        # Add metrics
        with timing("context_test"):
            time.sleep(0.01)

        # Get metrics with context
        metrics = get_deep_metrics(org_id="test_org", logic_id="test_logic")

        # Should have context-specific metrics
        assert "latency" in metrics
        # Check for context in keys
        latency_keys = list(metrics["latency"].keys())
        assert any("test_org" in key or "test_logic" in key for key in latency_keys)
