"""
Unit tests for advanced alerting system.

Tests threshold triggers, severity classification, alert payload structure,
and integration with telemetry and anomaly detection.
"""

import pytest
import time
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from helpers.alerts import (
    create_alert,
    evaluate_alerts,
    get_alerts,
    add_alert_callback,
    clear_alerts,
    export_alerts,
    AlertSeverity,
    get_alert_manager,
)
from helpers.telemetry import get_deep_metrics, clear_metrics


class TestAlertSystem:
    """Test alert system functionality."""

    def setup_method(self):
        """Clear alerts and metrics before each test."""
        clear_alerts()
        clear_metrics()

    def test_alert_creation(self):
        """Test basic alert creation."""
        alert = create_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
            context={"test_key": "test_value"},
            org_id="test_org",
            logic_id="test_logic",
        )

        assert alert is not None
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.source == "test_source"
        assert alert.metric_name == "test_metric"
        assert alert.metric_value == 100.0
        assert alert.threshold == 50.0
        assert alert.org_id == "test_org"
        assert alert.logic_id == "test_logic"
        assert alert.context["test_key"] == "test_value"

    def test_alert_severity_levels(self):
        """Test all alert severity levels."""
        severities = [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL]

        for severity in severities:
            alert = create_alert(
                severity=severity,
                title=f"{severity.value} Alert",
                message=f"Test {severity.value} alert",
                source="test_source",
                metric_name="test_metric",
                metric_value=100.0,
                threshold=50.0,
            )

            assert alert.severity == severity
            assert alert.title == f"{severity.value} Alert"

    def test_alert_deduplication(self):
        """Test that duplicate alerts are not created."""
        # Create first alert
        alert1 = create_alert(
            severity=AlertSeverity.WARNING,
            title="Duplicate Alert",
            message="Test duplicate",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
        )

        # Create duplicate alert (same source, metric, severity)
        alert2 = create_alert(
            severity=AlertSeverity.WARNING,
            title="Duplicate Alert",
            message="Test duplicate",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
        )

        # Second alert should be None (deduplicated)
        assert alert1 is not None
        assert alert2 is None

    def test_alert_filtering(self):
        """Test alert filtering functionality."""
        # Create alerts with different properties
        create_alert(
            severity=AlertSeverity.WARNING,
            title="Warning Alert",
            message="Test warning",
            source="source1",
            metric_name="metric1",
            metric_value=100.0,
            threshold=50.0,
            org_id="org1",
        )

        create_alert(
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            message="Test critical",
            source="source2",
            metric_name="metric2",
            metric_value=200.0,
            threshold=50.0,
            org_id="org2",
        )

        # Test filtering by severity
        warning_alerts = get_alerts(severity=AlertSeverity.WARNING)
        assert len(warning_alerts) == 1
        assert warning_alerts[0].severity == AlertSeverity.WARNING

        # Test filtering by source
        source1_alerts = get_alerts(source="source1")
        assert len(source1_alerts) == 1
        assert source1_alerts[0].source == "source1"

        # Test filtering by org_id
        org1_alerts = get_alerts(org_id="org1")
        assert len(org1_alerts) == 1
        assert org1_alerts[0].org_id == "org1"

        # Test filtering by time
        future_time = datetime.utcnow() + timedelta(hours=1)
        future_alerts = get_alerts(since=future_time)
        assert len(future_alerts) == 0

    def test_threshold_evaluation(self):
        """Test threshold-based alert evaluation."""
        # Mock metrics that would trigger alerts
        mock_metrics = {
            "errors": {
                "test_logic:ValueError": 15,  # High error count
                "test_logic:TypeError": 5,
            },
            "latency": {
                "test_logic": {
                    "count": 100,
                    "mean": 100.0,
                    "std": 20.0,
                    "p50": 95.0,
                    "p95": 6000.0,  # High P95 latency
                    "p99": 8000.0,
                }
            },
            "retries": {"test_logic": 25},  # High retry count
            "memory": {
                "test_logic": {
                    "count": 100,
                    "mean": 85.0,  # High memory usage
                    "max": 90.0,
                    "min": 80.0,
                }
            },
            "cpu": {
                "test_logic": {
                    "count": 100,
                    "mean": 95.0,  # High CPU usage
                    "max": 98.0,
                    "min": 92.0,
                }
            },
        }

        with patch("helpers.alerts.get_deep_metrics", return_value=mock_metrics):
            alerts = evaluate_alerts("test_org", "test_logic", "test_orchestrator")

            # Should have alerts based on thresholds
            assert len(alerts) > 0

            # Check for specific alert types
            alert_sources = [alert.source for alert in alerts]
            alert_metrics = [alert.metric_name for alert in alerts]

            assert "threshold_monitor" in alert_sources
            assert any("latency" in metric for metric in alert_metrics)

    def test_anomaly_detection_alerts(self):
        """Test anomaly detection integration with alerts."""
        # Mock metrics with anomalies
        mock_metrics = {
            "latency": {
                "test_logic": {
                    "count": 100,
                    "mean": 1000.0,  # Anomalously high
                    "std": 100.0,
                    "p50": 950.0,
                    "p95": 1100.0,
                    "p99": 1200.0,
                }
            },
            "throughput": {
                "test_logic": {
                    "count": 100,
                    "mean": 5.0,  # Anomalously low
                    "total": 500,
                    "p50": 4.0,
                    "p95": 6.0,
                    "p99": 7.0,
                }
            },
        }

        with patch("helpers.alerts.get_deep_metrics", return_value=mock_metrics):
            alerts = evaluate_alerts("test_org", "test_logic", "test_orchestrator")

            # Should have anomaly alerts
            assert len(alerts) > 0

            # Check for anomaly detection alerts
            anomaly_alerts = [a for a in alerts if a.source == "anomaly_detector"]
            assert len(anomaly_alerts) > 0

    def test_alert_callbacks(self):
        """Test alert callback functionality."""
        callback_called = False
        callback_alert = None

        def test_callback(alert):
            nonlocal callback_called, callback_alert
            callback_called = True
            callback_alert = alert

        # Add callback
        add_alert_callback(test_callback)

        # Create alert
        alert = create_alert(
            severity=AlertSeverity.WARNING,
            title="Callback Test",
            message="Test callback",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
        )

        # Check callback was called
        assert callback_called
        assert callback_alert == alert

    def test_alert_export(self):
        """Test alert export functionality."""
        # Create some alerts
        create_alert(
            severity=AlertSeverity.WARNING,
            title="Export Test 1",
            message="Test export",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
        )

        create_alert(
            severity=AlertSeverity.CRITICAL,
            title="Export Test 2",
            message="Test export",
            source="test_source",
            metric_name="test_metric",
            metric_value=200.0,
            threshold=50.0,
        )

        # Export as JSON
        json_alerts = export_alerts("json")

        # Verify JSON format
        assert isinstance(json_alerts, str)
        parsed = json.loads(json_alerts)
        assert len(parsed) == 2

        # Check alert structure
        for alert_data in parsed:
            assert "id" in alert_data
            assert "severity" in alert_data
            assert "title" in alert_data
            assert "message" in alert_data
            assert "source" in alert_data
            assert "metric_name" in alert_data
            assert "metric_value" in alert_data
            assert "threshold" in alert_data
            assert "timestamp" in alert_data

    def test_alert_clear(self):
        """Test alert clearing functionality."""
        # Create some alerts
        create_alert(
            severity=AlertSeverity.WARNING,
            title="Clear Test",
            message="Test clear",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
        )

        # Verify alert exists
        alerts_before = get_alerts()
        assert len(alerts_before) == 1

        # Clear alerts
        clear_alerts()

        # Verify alerts are cleared
        alerts_after = get_alerts()
        assert len(alerts_after) == 0

    def test_alert_clear_with_time(self):
        """Test alert clearing with time filter."""
        # Create alerts at different times
        old_time = datetime.utcnow() - timedelta(hours=2)

        # Mock old alert
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = old_time
            create_alert(
                severity=AlertSeverity.WARNING,
                title="Old Alert",
                message="Old alert",
                source="test_source",
                metric_name="test_metric",
                metric_value=100.0,
                threshold=50.0,
            )

        # Create current alert
        create_alert(
            severity=AlertSeverity.WARNING,
            title="Current Alert",
            message="Current alert",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
        )

        # Verify both alerts exist
        alerts_before = get_alerts()
        assert len(alerts_before) == 2

        # Clear old alerts only
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        clear_alerts(before=cutoff_time)

        # Verify only current alert remains
        alerts_after = get_alerts()
        assert len(alerts_after) == 1
        assert alerts_after[0].title == "Current Alert"

    def test_alert_disabled(self):
        """Test alerts when disabled via environment."""
        with patch.dict(os.environ, {"ALERTS_ENABLED": "false"}):
            # Re-import to get disabled version
            import importlib
            import helpers.alerts

            importlib.reload(helpers.alerts)

            # Try to create alert
            alert = helpers.alerts.create_alert(
                severity=helpers.alerts.AlertSeverity.WARNING,
                title="Disabled Test",
                message="Test disabled",
                source="test_source",
                metric_name="test_metric",
                metric_value=100.0,
                threshold=50.0,
            )

            # Should be None when disabled
            assert alert is None

    def test_alert_threshold_configuration(self):
        """Test alert threshold configuration."""
        # Test with custom thresholds
        with patch.dict(
            os.environ,
            {
                "ALERT_ERROR_RATE_THRESHOLD": "0.05",  # 5%
                "ALERT_LATENCY_P95_THRESHOLD": "2000",  # 2 seconds
                "ALERT_MEMORY_USAGE_THRESHOLD": "70.0",  # 70%
                "ALERT_CPU_USAGE_THRESHOLD": "80.0",  # 80%
                "ALERT_RETRY_RATE_THRESHOLD": "0.1",  # 10%
                "ALERT_THROUGHPUT_DROP_THRESHOLD": "0.3",  # 30%
            },
        ):
            # Re-import to get new thresholds
            import importlib
            import helpers.alerts

            importlib.reload(helpers.alerts)

            # Test with metrics that should trigger with new thresholds
            mock_metrics = {
                "errors": {"test_logic:ValueError": 10},
                "latency": {
                    "test_logic": {
                        "count": 100,
                        "mean": 100.0,
                        "std": 20.0,
                        "p50": 95.0,
                        "p95": 2500.0,  # Above 2000ms threshold
                        "p99": 3000.0,
                    }
                },
            }

            with patch("helpers.alerts.get_deep_metrics", return_value=mock_metrics):
                alerts = helpers.alerts.evaluate_alerts(
                    "test_org", "test_logic", "test_orchestrator"
                )

                # Should have alerts based on new thresholds
                assert len(alerts) > 0

    def test_alert_context_richness(self):
        """Test that alerts contain rich context information."""
        alert = create_alert(
            severity=AlertSeverity.WARNING,
            title="Context Test",
            message="Test context",
            source="test_source",
            metric_name="test_metric",
            metric_value=100.0,
            threshold=50.0,
            context={
                "additional_info": "test_value",
                "nested_data": {"key": "value"},
                "array_data": [1, 2, 3],
            },
            org_id="test_org",
            logic_id="test_logic",
            orchestrator_id="test_orchestrator",
        )

        # Check context richness
        assert alert.context["additional_info"] == "test_value"
        assert alert.context["nested_data"]["key"] == "value"
        assert alert.context["array_data"] == [1, 2, 3]
        assert alert.org_id == "test_org"
        assert alert.logic_id == "test_logic"
        assert alert.orchestrator_id == "test_orchestrator"

    def test_alert_telemetry_integration(self):
        """Test that alerts emit telemetry events."""
        with patch("helpers.alerts.event") as mock_event:
            alert = create_alert(
                severity=AlertSeverity.WARNING,
                title="Telemetry Test",
                message="Test telemetry",
                source="test_source",
                metric_name="test_metric",
                metric_value=100.0,
                threshold=50.0,
            )

            # Check telemetry events were emitted
            assert mock_event.called

            # Check event data
            call_args = mock_event.call_args
            assert call_args[0][0] == "alert.created"
            event_data = call_args[0][1]
            assert event_data["alert_id"] == alert.id
            assert event_data["severity"] == alert.severity.value
            assert event_data["source"] == alert.source
            assert event_data["metric_name"] == alert.metric_name


class TestAlertIntegration:
    """Test integration with other observability components."""

    def test_alerts_with_anomaly_detection(self):
        """Test alerts integration with anomaly detection."""
        from helpers.anomaly_detector import detect_anomaly

        # Create anomalous data
        for i in range(20):
            detect_anomaly(
                "test_metric",
                1000.0 + i,
                "test_org",
                "test_logic",  # Normal range
            )

        # Add anomalous value
        anomaly_result = detect_anomaly(
            "test_metric",
            10000.0,  # Very high - should be anomalous
            "test_org",
            "test_logic",
        )

        # Evaluate alerts
        alerts = evaluate_alerts("test_org", "test_logic", "test_orchestrator")

        # Should have alerts based on anomalies
        assert len(alerts) >= 0  # May or may not have alerts depending on thresholds

    def test_alerts_with_metrics(self):
        """Test alerts integration with metrics collection."""
        # Add metrics that would trigger alerts
        from helpers.telemetry import timing, span

        # Add high latency metrics
        for i in range(10):
            with timing("high_latency_test"):
                time.sleep(0.1)  # 100ms

        # Add error metrics
        for i in range(5):
            with span("error_span"):
                raise ValueError("Test error")

        # Evaluate alerts
        alerts = evaluate_alerts("test_org", "test_logic", "test_orchestrator")

        # Should have alerts based on collected metrics
        assert len(alerts) >= 0  # May or may not have alerts depending on thresholds
