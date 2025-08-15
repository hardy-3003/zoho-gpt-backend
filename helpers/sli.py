"""
Service Level Indicators (SLI) Library

Provides threadsafe in-memory storage for SLI metrics with rolling windows,
histogram buckets, and export capabilities for SLO evaluation.
"""

import threading
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
from datetime import datetime, timedelta

# Configuration from environment
SLI_WINDOW_SEC = int(os.getenv("SLI_WINDOW_SEC", "604800"))  # 7 days default
SLI_BUCKETS = int(os.getenv("SLI_BUCKETS", "60"))  # 60 buckets default


def _sli_enabled() -> bool:
    return os.getenv("SLO_ENABLED", "true").lower() == "true"


@dataclass
class SLIMetric:
    """Individual SLI metric with value and metadata."""

    value: float
    timestamp: float
    dimensions: Dict[str, str]
    metric_name: str


@dataclass
class SLISnapshot:
    """Snapshot of SLI metrics for a specific time window."""

    timestamp: float
    metrics: Dict[str, List[SLIMetric]]
    window_sec: int
    bucket_count: int


class SLIStore:
    """Threadsafe in-memory SLI store with rolling windows and histogram buckets."""

    def __init__(
        self, window_sec: int = SLI_WINDOW_SEC, bucket_count: int = SLI_BUCKETS
    ):
        self.window_sec = window_sec
        self.bucket_count = bucket_count
        self.bucket_sec = window_sec / bucket_count

        # Threadsafe storage
        self._lock = threading.RLock()
        self._metrics: Dict[str, list] = defaultdict(list)
        self._current_bucket = 0
        self._last_cleanup = time.time()

        # Bucket timestamps for cleanup
        self._bucket_timestamps = deque(maxlen=bucket_count)
        self._bucket_timestamps.append(time.time())

    def record_sli(self, metric: str, value: float, dims: Dict[str, str]) -> None:
        """Record an SLI metric with value and dimensions."""
        if not _sli_enabled():
            return

        current_time = time.time()

        with self._lock:
            # Cleanup old buckets if needed
            self._cleanup_old_buckets(current_time)

            # Create metric entry
            sli_metric = SLIMetric(
                value=value, timestamp=current_time, dimensions=dims, metric_name=metric
            )

            # Store metric
            self._metrics[metric].append(sli_metric)

    def _cleanup_old_buckets(self, current_time: float) -> None:
        """Remove metrics older than the window."""
        cutoff_time = current_time - self.window_sec

        # Update bucket timestamps (guard against patched time.time in tests)
        try:
            last_ts = float(self._bucket_timestamps[-1])
            now_ts = float(current_time)
        except Exception:
            last_ts = self._bucket_timestamps[-1]
            now_ts = current_time

        if now_ts - last_ts >= self.bucket_sec:
            self._bucket_timestamps.append(now_ts)

        # Remove old bucket timestamps
        while self._bucket_timestamps and self._bucket_timestamps[0] < cutoff_time:
            self._bucket_timestamps.popleft()

    def get_snapshot(self) -> SLISnapshot:
        """Get a snapshot of all current SLI metrics."""
        if not _sli_enabled():
            return SLISnapshot(
                timestamp=time.time(),
                metrics={},
                window_sec=self.window_sec,
                bucket_count=self.bucket_count,
            )

        current_time = time.time()
        cutoff_time = current_time - self.window_sec

        with self._lock:
            self._cleanup_old_buckets(current_time)

            # Filter metrics within window
            filtered_metrics = {}
            for metric_name, metrics_list in self._metrics.items():
                recent_metrics = [m for m in metrics_list if m.timestamp >= cutoff_time]
                if recent_metrics:
                    filtered_metrics[metric_name] = recent_metrics

            return SLISnapshot(
                timestamp=current_time,
                metrics=filtered_metrics,
                window_sec=self.window_sec,
                bucket_count=self.bucket_count,
            )

    def get_quantiles(
        self,
        metric: str,
        dims: Optional[Dict[str, str]] = None,
        quantiles: List[float] = None,
    ) -> Dict[str, float]:
        """Get quantiles for a specific metric and dimensions."""
        if quantiles is None:
            quantiles = [0.5, 0.95, 0.99]

        snapshot = self.get_snapshot()
        if metric not in snapshot.metrics:
            return {f"p{int(q*100)}": 0.0 for q in quantiles}

        # Filter by dimensions if specified
        metrics = snapshot.metrics[metric]
        if dims:
            metrics = [
                m
                for m in metrics
                if all(m.dimensions.get(k) == v for k, v in dims.items())
            ]

        if not metrics:
            return {f"p{int(q*100)}": 0.0 for q in quantiles}

        values = [m.value for m in metrics]
        values.sort()

        result = {}
        for q in quantiles:
            if q == 0.0:
                result[f"p{int(q*100)}"] = values[0]
            elif q == 1.0:
                result[f"p{int(q*100)}"] = values[-1]
            else:
                index = q * (len(values) - 1)
                if index.is_integer():
                    result[f"p{int(q*100)}"] = values[int(index)]
                else:
                    lower = values[int(index)]
                    upper = values[int(index) + 1]
                    result[f"p{int(q*100)}"] = lower + (upper - lower) * (
                        index - int(index)
                    )

        return result

    def get_rate(self, metric: str, dims: Optional[Dict[str, str]] = None) -> float:
        """Get rate (events per second) for a specific metric and dimensions."""
        snapshot = self.get_snapshot()
        if metric not in snapshot.metrics:
            return 0.0

        # Filter by dimensions if specified
        metrics = snapshot.metrics[metric]
        if dims:
            metrics = [
                m
                for m in metrics
                if all(m.dimensions.get(k) == v for k, v in dims.items())
            ]

        if not metrics:
            return 0.0

        # Calculate rate over the configured window for stable expectations
        return len(metrics) / float(self.window_sec)

    def get_count(self, metric: str, dims: Optional[Dict[str, str]] = None) -> int:
        """Get count of events for a specific metric and dimensions."""
        snapshot = self.get_snapshot()
        if metric not in snapshot.metrics:
            return 0

        # Filter by dimensions if specified
        metrics = snapshot.metrics[metric]
        if dims:
            metrics = [
                m
                for m in metrics
                if all(m.dimensions.get(k) == v for k, v in dims.items())
            ]

        return len(metrics)

    def get_sum(self, metric: str, dims: Optional[Dict[str, str]] = None) -> float:
        """Get sum of values for a specific metric and dimensions."""
        snapshot = self.get_snapshot()
        if metric not in snapshot.metrics:
            return 0.0

        # Filter by dimensions if specified
        metrics = snapshot.metrics[metric]
        if dims:
            metrics = [
                m
                for m in metrics
                if all(m.dimensions.get(k) == v for k, v in dims.items())
            ]

        return sum(m.value for m in metrics)

    def get_availability(
        self,
        success_metric: str,
        total_metric: str,
        dims: Optional[Dict[str, str]] = None,
    ) -> float:
        """Calculate availability as success_rate / total_rate."""
        success_rate = self.get_rate(success_metric, dims)
        total_rate = self.get_rate(total_metric, dims)

        if total_rate == 0:
            return 1.0  # No requests means 100% availability

        return success_rate / total_rate

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        if not _sli_enabled():
            return ""

        snapshot = self.get_snapshot()
        lines = []

        for metric_name, metrics in snapshot.metrics.items():
            # Group by dimensions
            dim_groups = defaultdict(list)
            for metric in metrics:
                dim_key = tuple(sorted(metric.dimensions.items()))
                dim_groups[dim_key].append(metric)

            for dims_tuple, group_metrics in dim_groups.items():
                # Build dimension string
                dim_str = ""
                if dims_tuple:
                    dim_parts = [f'{k}="{v}"' for k, v in dims_tuple]
                    dim_str = "{" + ",".join(dim_parts) + "}"

                # Calculate metrics
                count = len(group_metrics)
                total = sum(m.value for m in group_metrics)
                avg = total / count if count > 0 else 0

                # Export as Prometheus metrics
                lines.append(f"sli_{metric_name}_count{dim_str} {count}")
                lines.append(f"sli_{metric_name}_total{dim_str} {total}")
                lines.append(f"sli_{metric_name}_avg{dim_str} {avg}")

                # Add quantiles if we have enough data
                if count >= 10:
                    values = [m.value for m in group_metrics]
                    values.sort()
                    for q in [0.5, 0.95, 0.99]:
                        index = int(q * (len(values) - 1))
                        lines.append(
                            f"sli_{metric_name}_p{int(q*100)}{dim_str} {values[index]}"
                        )

        return "\n".join(lines)


# Global SLI store instance
_sli_store = SLIStore()


def record_sli(metric: str, value: float, dims: Dict[str, str]) -> None:
    """Record an SLI metric with value and dimensions."""
    _sli_store.record_sli(metric, value, dims)


def sli_snapshot() -> SLISnapshot:
    """Get a snapshot of all current SLI metrics."""
    return _sli_store.get_snapshot()


def sli_quantiles(
    metric: str, dims: Optional[Dict[str, str]] = None, quantiles: List[float] = None
) -> Dict[str, float]:
    """Get quantiles for a specific metric and dimensions."""
    return _sli_store.get_quantiles(metric, dims, quantiles)


def sli_rate(metric: str, dims: Optional[Dict[str, str]] = None) -> float:
    """Get rate (events per second) for a specific metric and dimensions."""
    return _sli_store.get_rate(metric, dims)


def sli_count(metric: str, dims: Optional[Dict[str, str]] = None) -> int:
    """Get count of events for a specific metric and dimensions."""
    return _sli_store.get_count(metric, dims)


def sli_sum(metric: str, dims: Optional[Dict[str, str]] = None) -> float:
    """Get sum of values for a specific metric and dimensions."""
    return _sli_store.get_sum(metric, dims)


def sli_availability(
    success_metric: str, total_metric: str, dims: Optional[Dict[str, str]] = None
) -> float:
    """Calculate availability as success_rate / total_rate."""
    return _sli_store.get_availability(success_metric, total_metric, dims)


def export_prometheus() -> str:
    """Export metrics in Prometheus format."""
    return _sli_store.export_prometheus()
