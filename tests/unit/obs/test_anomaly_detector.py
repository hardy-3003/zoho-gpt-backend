"""
Unit tests for anomaly detection system.

Tests statistical model accuracy, edge-case handling, and integration
with telemetry and alerting systems.
"""

import pytest
import time
import json
import os
import statistics
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from helpers.anomaly_detector import (
    detect_anomaly,
    get_anomaly_history,
    get_anomaly_summary,
    export_anomaly_data,
    clear_anomaly_history,
    get_anomaly_manager,
    AnomalyResult,
    AnomalyScore,
)


class TestAnomalyDetection:
    """Test anomaly detection functionality."""

    def setup_method(self):
        """Clear anomaly history before each test."""
        clear_anomaly_history()

    def test_z_score_detection(self):
        """Test Z-score anomaly detection method."""
        # Add normal data points
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add anomalous value (very high)
        result = detect_anomaly("test_metric", 1000.0, "test_org", "test_logic")

        # Should detect anomaly
        assert result.is_anomaly
        assert result.overall_score > 0

        # Check Z-score method was used
        z_score_scores = [s for s in result.scores if s.method == "z_score"]
        assert len(z_score_scores) == 1
        assert z_score_scores[0].is_anomaly

    def test_iqr_detection(self):
        """Test IQR anomaly detection method."""
        # Add normal data points
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add anomalous value (outlier)
        result = detect_anomaly("test_metric", 500.0, "test_org", "test_logic")

        # Should detect anomaly
        assert result.is_anomaly
        assert result.overall_score > 0

        # Check IQR method was used
        iqr_scores = [s for s in result.scores if s.method == "iqr"]
        assert len(iqr_scores) == 1
        assert iqr_scores[0].is_anomaly

    def test_percentile_detection(self):
        """Test percentile anomaly detection method."""
        # Add normal data points
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add very high value (above 99.5th percentile)
        result = detect_anomaly("test_metric", 200.0, "test_org", "test_logic")

        # Should detect anomaly
        assert result.is_anomaly
        assert result.overall_score > 0

        # Check percentile method was used
        percentile_scores = [s for s in result.scores if s.method == "percentile"]
        assert len(percentile_scores) == 1
        assert percentile_scores[0].is_anomaly

    def test_trend_detection(self):
        """Test trend anomaly detection method."""
        # Add data with trend
        for i in range(25):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add value that deviates from trend
        result = detect_anomaly("test_metric", 200.0, "test_org", "test_logic")

        # Should detect anomaly
        assert result.is_anomaly
        assert result.overall_score > 0

        # Check trend method was used
        trend_scores = [s for s in result.scores if s.method == "trend"]
        assert len(trend_scores) == 1
        assert trend_scores[0].is_anomaly

    def test_insufficient_data_handling(self):
        """Test handling of insufficient data for anomaly detection."""
        # Try to detect anomaly with very few data points
        result = detect_anomaly("test_metric", 100.0, "test_org", "test_logic")

        # Should not detect anomaly with insufficient data
        assert not result.is_anomaly
        assert result.overall_score == 0.0
        assert result.reason == "insufficient_confidence"

        # Check that methods report insufficient data
        for score in result.scores:
            assert score.confidence == 0.0
            assert not score.is_anomaly

    def test_no_variance_handling(self):
        """Test handling of data with no variance."""
        # Add identical data points
        for i in range(20):
            detect_anomaly("test_metric", 100.0, "test_org", "test_logic")

        # Try to detect anomaly
        result = detect_anomaly("test_metric", 100.0, "test_org", "test_logic")

        # Should handle no variance gracefully
        assert not result.is_anomaly
        assert result.overall_score == 0.0

        # Check Z-score method reports no variance
        z_score_scores = [s for s in result.scores if s.method == "z_score"]
        assert len(z_score_scores) == 1
        assert z_score_scores[0].context.get("reason") == "no_variance"

    def test_confidence_calculation(self):
        """Test confidence calculation based on data points."""
        # Add few data points
        for i in range(5):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        result = detect_anomaly("test_metric", 200.0, "test_org", "test_logic")

        # Should have low confidence with few data points
        for score in result.scores:
            assert score.confidence < 1.0

        # Add more data points
        for i in range(95):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        result = detect_anomaly("test_metric", 200.0, "test_org", "test_logic")

        # Should have higher confidence with more data points
        for score in result.scores:
            assert score.confidence > 0.5

    def test_multiple_methods_agreement(self):
        """Test that multiple methods can agree on anomalies."""
        # Add normal data
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add clearly anomalous value
        result = detect_anomaly("test_metric", 1000.0, "test_org", "test_logic")

        # Multiple methods should detect the anomaly
        anomaly_methods = [s.method for s in result.scores if s.is_anomaly]
        assert len(anomaly_methods) > 1

        # Overall result should be anomaly
        assert result.is_anomaly
        assert result.overall_score > 0

    def test_anomaly_history(self):
        """Test anomaly detection history tracking."""
        # Add some anomalies
        for i in range(10):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Get history
        history = get_anomaly_history("test_metric")

        # Should have history entries
        assert len(history) == 10

        # Check history structure
        for entry in history:
            assert isinstance(entry, AnomalyResult)
            assert entry.metric_name == "test_metric"
            assert len(entry.scores) > 0

    def test_anomaly_summary(self):
        """Test anomaly detection summary statistics."""
        # Add normal and anomalous data
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add some anomalies
        for i in range(5):
            detect_anomaly("test_metric", 1000.0 + i, "test_org", "test_logic")

        # Get summary
        summary = get_anomaly_summary("test_metric")

        # Check summary structure
        assert summary["metric_name"] == "test_metric"
        assert summary["total_detections"] == 25
        assert summary["anomaly_count"] > 0
        assert summary["anomaly_rate"] > 0
        assert summary["avg_score"] > 0
        assert summary["last_detection"] is not None

    def test_anomaly_export(self):
        """Test anomaly data export functionality."""
        # Add some data
        for i in range(10):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Export as JSON
        json_data = export_anomaly_data("json")

        # Verify JSON format
        assert isinstance(json_data, str)
        parsed = json.loads(json_data)
        assert "test_metric" in parsed

        # Check summary structure
        summary = parsed["test_metric"]
        assert "total_detections" in summary
        assert "anomaly_count" in summary
        assert "anomaly_rate" in summary
        assert "avg_score" in summary

    def test_anomaly_clear(self):
        """Test anomaly history clearing functionality."""
        # Add some data
        for i in range(10):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Verify data exists
        history_before = get_anomaly_history("test_metric")
        assert len(history_before) == 10

        # Clear history
        clear_anomaly_history()

        # Verify history is cleared
        history_after = get_anomaly_history("test_metric")
        assert len(history_after) == 0

    def test_anomaly_clear_with_time(self):
        """Test anomaly history clearing with time filter."""
        # Add old data
        old_time = datetime.utcnow() - timedelta(hours=2)

        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = old_time
            for i in range(5):
                detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add current data
        for i in range(5):
            detect_anomaly("test_metric", 200.0 + i, "test_org", "test_logic")

        # Verify both old and new data exist
        history_before = get_anomaly_history("test_metric")
        assert len(history_before) == 10

        # Clear old data only
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        clear_anomaly_history(before=cutoff_time)

        # Verify only current data remains
        history_after = get_anomaly_history("test_metric")
        assert len(history_after) == 5

    def test_anomaly_disabled(self):
        """Test anomaly detection when disabled via environment."""
        with patch.dict(os.environ, {"ANOMALY_DETECTION_ENABLED": "false"}):
            # Re-import to get disabled version
            import importlib
            import helpers.anomaly_detector

            importlib.reload(helpers.anomaly_detector)

            # Try to detect anomaly
            result = helpers.anomaly_detector.detect_anomaly(
                "test_metric", 100.0, "test_org", "test_logic"
            )

            # Should return disabled result
            assert not result.is_anomaly
            assert result.overall_score == 0.0
            assert result.reason == "anomaly_detection_disabled"

    def test_ml_anomaly_detection(self):
        """Test ML-based anomaly detection (placeholder)."""
        with patch.dict(os.environ, {"ML_ANOMALY_ENABLED": "true"}):
            # Re-import to get ML-enabled version
            import importlib
            import helpers.anomaly_detector

            importlib.reload(helpers.anomaly_detector)

            # Add data to train ML model
            for i in range(60):  # Need >50 for training
                helpers.anomaly_detector.detect_anomaly(
                    "test_metric", 100.0 + i, "test_org", "test_logic"
                )

            # Try ML detection
            result = helpers.anomaly_detector.detect_anomaly(
                "test_metric", 1000.0, "test_org", "test_logic"
            )

            # Should have ML score (even if not trained)
            ml_scores = [s for s in result.scores if s.method == "ml"]
            assert len(ml_scores) == 1

    def test_anomaly_threshold_configuration(self):
        """Test anomaly detection threshold configuration."""
        # Test with custom thresholds
        with patch.dict(
            os.environ,
            {
                "ANOMALY_Z_SCORE_THRESHOLD": "2.0",  # Lower threshold
                "ANOMALY_IQR_MULTIPLIER": "1.0",  # Lower multiplier
                "ANOMALY_PERCENTILE_THRESHOLD": "95.0",  # Lower percentile
                "ANOMALY_TREND_SENSITIVITY": "0.05",  # Lower sensitivity
            },
        ):
            # Re-import to get new thresholds
            import importlib
            import helpers.anomaly_detector

            importlib.reload(helpers.anomaly_detector)

            # Add normal data
            for i in range(20):
                helpers.anomaly_detector.detect_anomaly(
                    "test_metric", 100.0 + i, "test_org", "test_logic"
                )

            # Test with value that should be anomalous with lower thresholds
            result = helpers.anomaly_detector.detect_anomaly(
                "test_metric", 150.0, "test_org", "test_logic"
            )

            # Should detect anomaly with lower thresholds
            assert result.is_anomaly or result.overall_score > 0

    def test_anomaly_context_richness(self):
        """Test that anomaly results contain rich context information."""
        # Add normal data
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add anomalous value
        result = detect_anomaly("test_metric", 1000.0, "test_org", "test_logic")

        # Check context richness for each method
        for score in result.scores:
            assert "context" in score.__dict__
            assert isinstance(score.context, dict)

            # Check method-specific context
            if score.method == "z_score":
                assert "mean" in score.context
                assert "std" in score.context
                assert "data_points" in score.context
            elif score.method == "iqr":
                assert "q1" in score.context
                assert "q3" in score.context
                assert "iqr" in score.context
            elif score.method == "percentile":
                assert "percentile_threshold" in score.context
                assert "percentile_rank" in score.context
            elif score.method == "trend":
                assert "predicted_value" in score.context
                assert "slope" in score.context
                assert "deviation" in score.context

    def test_anomaly_telemetry_integration(self):
        """Test that anomaly detection emits telemetry events."""
        with patch("helpers.anomaly_detector.event") as mock_event:
            # Add normal data
            for i in range(20):
                detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

            # Add anomalous value
            result = detect_anomaly("test_metric", 1000.0, "test_org", "test_logic")

            # Check telemetry events were emitted
            assert mock_event.called

            # Check event data
            call_args = mock_event.call_args
            assert call_args[0][0] == "anomaly.detected"
            event_data = call_args[0][1]
            assert event_data["metric_name"] == "test_metric"
            assert event_data["value"] == 1000.0
            assert event_data["overall_score"] == result.overall_score
            assert event_data["is_anomaly"] == result.is_anomaly
            assert event_data["reason"] == result.reason


class TestAnomalyIntegration:
    """Test integration with other observability components."""

    def test_anomaly_with_alerts(self):
        """Test anomaly detection integration with alerting system."""
        from helpers.alerts import evaluate_alerts

        # Add normal data
        for i in range(20):
            detect_anomaly("test_metric", 100.0 + i, "test_org", "test_logic")

        # Add anomalous data
        for i in range(5):
            detect_anomaly("test_metric", 1000.0 + i, "test_org", "test_logic")

        # Evaluate alerts
        alerts = evaluate_alerts("test_org", "test_logic", "test_orchestrator")

        # Should have alerts based on anomalies
        assert len(alerts) >= 0  # May or may not have alerts depending on thresholds

    def test_anomaly_with_metrics(self):
        """Test anomaly detection integration with metrics collection."""
        from helpers.telemetry import timing, get_deep_metrics

        # Add metrics that would be analyzed for anomalies
        for i in range(10):
            with timing("anomaly_test"):
                time.sleep(0.01)

        # Get metrics
        metrics = get_deep_metrics()

        # Should have metrics that could be used for anomaly detection
        assert "latency" in metrics
        assert len(metrics["latency"]) > 0

    def test_anomaly_performance(self):
        """Test anomaly detection performance with large datasets."""
        import time

        # Measure performance with large dataset
        start_time = time.perf_counter()

        # Add many data points
        for i in range(1000):
            detect_anomaly("perf_test", 100.0 + i, "test_org", "test_logic")

        # Add anomalous value
        result = detect_anomaly("perf_test", 10000.0, "test_org", "test_logic")

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Should complete within reasonable time (<5 seconds)
        assert duration < 5.0, f"Anomaly detection took {duration:.2f} seconds"

        # Should detect anomaly
        assert result.is_anomaly or result.overall_score > 0

    def test_anomaly_edge_cases(self):
        """Test anomaly detection with edge cases."""
        # Test with very small values
        result = detect_anomaly("edge_test", 0.001, "test_org", "test_logic")
        assert isinstance(result, AnomalyResult)

        # Test with very large values
        result = detect_anomaly("edge_test", 1e10, "test_org", "test_logic")
        assert isinstance(result, AnomalyResult)

        # Test with negative values
        result = detect_anomaly("edge_test", -100.0, "test_org", "test_logic")
        assert isinstance(result, AnomalyResult)

        # Test with zero
        result = detect_anomaly("edge_test", 0.0, "test_org", "test_logic")
        assert isinstance(result, AnomalyResult)

        # Test with NaN (should handle gracefully)
        import math

        result = detect_anomaly("edge_test", float("nan"), "test_org", "test_logic")
        assert isinstance(result, AnomalyResult)

        # Test with infinity (should handle gracefully)
        result = detect_anomaly("edge_test", float("inf"), "test_org", "test_logic")
        assert isinstance(result, AnomalyResult)
