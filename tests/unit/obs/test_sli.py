"""
Unit tests for SLI (Service Level Indicators) library.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from helpers.sli import (
    SLIStore,
    SLIMetric,
    SLISnapshot,
    record_sli,
    sli_snapshot,
    sli_quantiles,
    sli_rate,
    sli_count,
    sli_sum,
    sli_availability,
    export_prometheus,
)


class TestSLIMetric:
    """Test SLIMetric dataclass."""

    def test_sli_metric_creation(self):
        """Test creating SLI metric."""
        metric = SLIMetric(
            value=100.5,
            timestamp=time.time(),
            dimensions={"org_id": "test", "logic_id": "L-001"},
            metric_name="latency_ms",
        )

        assert metric.value == 100.5
        assert metric.metric_name == "latency_ms"
        assert metric.dimensions["org_id"] == "test"
        assert metric.dimensions["logic_id"] == "L-001"


class TestSLIStore:
    """Test SLIStore functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.store = SLIStore(
            window_sec=60, bucket_count=6
        )  # 1 minute window, 6 buckets

    def test_record_sli_basic(self):
        """Test basic SLI recording."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})

        snapshot = self.store.get_snapshot()
        assert "test_metric" in snapshot.metrics
        assert len(snapshot.metrics["test_metric"]) == 1
        assert snapshot.metrics["test_metric"][0].value == 100.0

    def test_record_sli_multiple(self):
        """Test recording multiple SLI metrics."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})
        self.store.record_sli("test_metric", 200.0, {"org_id": "test"})
        self.store.record_sli("test_metric", 300.0, {"org_id": "test"})

        snapshot = self.store.get_snapshot()
        assert len(snapshot.metrics["test_metric"]) == 3
        values = [m.value for m in snapshot.metrics["test_metric"]]
        assert values == [100.0, 200.0, 300.0]

    def test_record_sli_with_dimensions(self):
        """Test SLI recording with different dimensions."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "org1"})
        self.store.record_sli("test_metric", 200.0, {"org_id": "org2"})

        # Get metrics for specific org
        org1_metrics = self.store.get_count("test_metric", {"org_id": "org1"})
        org2_metrics = self.store.get_count("test_metric", {"org_id": "org2"})

        assert org1_metrics == 1
        assert org2_metrics == 1

    def test_window_cleanup(self):
        """Test that old metrics are cleaned up after window expires."""
        # Record metrics
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})

        # Simulate time passing beyond window
        with patch("time.time") as mock_time:
            mock_time.return_value = time.time() + 70  # 70 seconds later
            snapshot = self.store.get_snapshot()

        # Metrics should be cleaned up
        assert (
            "test_metric" not in snapshot.metrics
            or len(snapshot.metrics["test_metric"]) == 0
        )

    def test_get_quantiles(self):
        """Test quantile calculation."""
        # Record 10 metrics
        for i in range(1, 11):
            self.store.record_sli("test_metric", float(i), {"org_id": "test"})

        quantiles = self.store.get_quantiles("test_metric", {"org_id": "test"})

        assert quantiles["p50"] == 5.5  # Median
        assert quantiles["p95"] == 9.5  # 95th percentile
        assert quantiles["p99"] == 9.9  # 99th percentile

    def test_get_rate(self):
        """Test rate calculation."""
        # Record 10 metrics over 60 seconds
        for i in range(10):
            self.store.record_sli("test_metric", 1.0, {"org_id": "test"})

        rate = self.store.get_rate("test_metric", {"org_id": "test"})
        # Rate should be approximately 10/60 = 0.167 events per second
        assert 0.15 <= rate <= 0.17

    def test_get_count(self):
        """Test count calculation."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})
        self.store.record_sli("test_metric", 200.0, {"org_id": "test"})

        count = self.store.get_count("test_metric", {"org_id": "test"})
        assert count == 2

    def test_get_sum(self):
        """Test sum calculation."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})
        self.store.record_sli("test_metric", 200.0, {"org_id": "test"})

        total = self.store.get_sum("test_metric", {"org_id": "test"})
        assert total == 300.0

    def test_get_availability(self):
        """Test availability calculation."""
        # Record 8 successes and 2 failures
        for i in range(8):
            self.store.record_sli("success", 1, {"org_id": "test"})
        for i in range(2):
            self.store.record_sli("error", 1, {"org_id": "test"})

        # Record total requests
        for i in range(10):
            self.store.record_sli("total", 1, {"org_id": "test"})

        availability = self.store.get_availability(
            "success", "total", {"org_id": "test"}
        )
        assert availability == 0.8  # 80% availability

    def test_concurrency_safety(self):
        """Test that SLI store is thread-safe."""
        results = []
        errors = []

        def record_metrics():
            try:
                for i in range(100):
                    self.store.record_sli(
                        "concurrent_metric", float(i), {"thread": "test"}
                    )
                results.append("success")
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_metrics)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that all threads succeeded
        assert len(results) == 5
        assert len(errors) == 0

        # Check that all metrics were recorded
        count = self.store.get_count("concurrent_metric", {"thread": "test"})
        assert count == 500  # 5 threads * 100 metrics each

    def test_export_prometheus(self):
        """Test Prometheus export format."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})
        self.store.record_sli("test_metric", 200.0, {"org_id": "test"})

        prometheus_output = self.store.export_prometheus()

        # Check that output contains expected metrics
        assert "sli_test_metric_count" in prometheus_output
        assert "sli_test_metric_total" in prometheus_output
        assert "sli_test_metric_avg" in prometheus_output
        assert 'org_id="test"' in prometheus_output


class TestSLIFunctions:
    """Test global SLI functions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear any existing metrics
        from helpers.sli import _sli_store

        _sli_store._metrics.clear()
        _sli_store._bucket_timestamps.clear()
        _sli_store._bucket_timestamps.append(time.time())

    def test_record_sli_function(self):
        """Test global record_sli function."""
        record_sli("test_metric", 100.0, {"org_id": "test"})

        snapshot = sli_snapshot()
        assert "test_metric" in snapshot.metrics
        assert len(snapshot.metrics["test_metric"]) == 1

    def test_sli_quantiles_function(self):
        """Test global sli_quantiles function."""
        for i in range(1, 11):
            record_sli("test_metric", float(i), {"org_id": "test"})

        quantiles = sli_quantiles("test_metric", {"org_id": "test"})
        assert quantiles["p50"] == 5.5

    def test_sli_rate_function(self):
        """Test global sli_rate function."""
        for i in range(10):
            record_sli("test_metric", 1.0, {"org_id": "test"})

        rate = sli_rate("test_metric", {"org_id": "test"})
        assert rate > 0

    def test_sli_count_function(self):
        """Test global sli_count function."""
        record_sli("test_metric", 100.0, {"org_id": "test"})
        record_sli("test_metric", 200.0, {"org_id": "test"})

        count = sli_count("test_metric", {"org_id": "test"})
        assert count == 2

    def test_sli_sum_function(self):
        """Test global sli_sum function."""
        record_sli("test_metric", 100.0, {"org_id": "test"})
        record_sli("test_metric", 200.0, {"org_id": "test"})

        total = sli_sum("test_metric", {"org_id": "test"})
        assert total == 300.0

    def test_sli_availability_function(self):
        """Test global sli_availability function."""
        for i in range(8):
            record_sli("success", 1, {"org_id": "test"})
        for i in range(2):
            record_sli("error", 1, {"org_id": "test"})
        for i in range(10):
            record_sli("total", 1, {"org_id": "test"})

        availability = sli_availability("success", "total", {"org_id": "test"})
        assert availability == 0.8

    def test_export_prometheus_function(self):
        """Test global export_prometheus function."""
        record_sli("test_metric", 100.0, {"org_id": "test"})

        prometheus_output = export_prometheus()
        assert "sli_test_metric" in prometheus_output


class TestSLIDisabled:
    """Test SLI functionality when disabled."""

    @patch.dict("os.environ", {"SLO_ENABLED": "false"})
    def test_sli_disabled(self):
        """Test that SLI recording is disabled when SLO_ENABLED=false."""
        # Re-import to get updated environment
        import importlib
        import helpers.sli

        importlib.reload(helpers.sli)

        # Record metrics
        helpers.sli.record_sli("test_metric", 100.0, {"org_id": "test"})

        # Get snapshot
        snapshot = helpers.sli.sli_snapshot()

        # Should be empty when disabled
        assert len(snapshot.metrics) == 0


class TestSLIEdgeCases:
    """Test SLI edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.store = SLIStore(window_sec=60, bucket_count=6)

    def test_empty_quantiles(self):
        """Test quantile calculation with no data."""
        quantiles = self.store.get_quantiles("nonexistent_metric")
        assert quantiles["p50"] == 0.0
        assert quantiles["p95"] == 0.0
        assert quantiles["p99"] == 0.0

    def test_single_value_quantiles(self):
        """Test quantile calculation with single value."""
        self.store.record_sli("test_metric", 100.0, {"org_id": "test"})

        quantiles = self.store.get_quantiles("test_metric", {"org_id": "test"})
        assert quantiles["p50"] == 100.0
        assert quantiles["p95"] == 100.0
        assert quantiles["p99"] == 100.0

    def test_zero_rate(self):
        """Test rate calculation with no data."""
        rate = self.store.get_rate("nonexistent_metric")
        assert rate == 0.0

    def test_zero_availability(self):
        """Test availability calculation with no requests."""
        availability = self.store.get_availability(
            "success", "total", {"org_id": "test"}
        )
        assert availability == 1.0  # No requests means 100% availability

    def test_negative_values(self):
        """Test handling of negative values."""
        self.store.record_sli("test_metric", -100.0, {"org_id": "test"})

        total = self.store.get_sum("test_metric", {"org_id": "test"})
        assert total == -100.0

    def test_large_values(self):
        """Test handling of large values."""
        large_value = 1e9
        self.store.record_sli("test_metric", large_value, {"org_id": "test"})

        total = self.store.get_sum("test_metric", {"org_id": "test"})
        assert total == large_value
