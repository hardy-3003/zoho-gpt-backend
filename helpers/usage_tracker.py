"""
Usage Tracking System for Auto-Expansion Capabilities

This module provides comprehensive usage tracking capabilities for monitoring
logic usage patterns, performance metrics, and providing insights for
auto-expansion decisions.

Features:
- Logic usage frequency tracking
- Performance metrics monitoring
- Usage pattern analysis
- Trend detection and forecasting
- Resource utilization tracking
"""

import json
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import logging
import threading

from helpers.history_store import write_event
from helpers.learning_hooks import record_feedback

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Represents usage metrics for a logic module."""

    logic_id: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    average_response_time: float
    total_response_time: float
    last_called: datetime
    first_called: datetime
    peak_usage_time: datetime
    usage_pattern: Dict[str, int]  # hour -> count
    error_types: Dict[str, int]
    performance_trend: str  # 'improving', 'stable', 'degrading'
    resource_usage: Dict[str, float]
    metadata: Dict[str, Any]


@dataclass
class UsagePattern:
    """Represents a usage pattern for analysis."""

    pattern_id: str
    logic_ids: List[str]
    frequency: int
    time_period: str  # 'hourly', 'daily', 'weekly'
    start_time: datetime
    end_time: datetime
    peak_usage: int
    average_usage: float
    trend: str  # 'increasing', 'stable', 'decreasing'
    correlation_score: float
    metadata: Dict[str, Any]


@dataclass
class UsageAnalysis:
    """Results of usage analysis."""

    metrics: Dict[str, UsageMetrics]
    patterns: List[UsagePattern]
    trends: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    performance_alerts: List[Dict[str, Any]]


class UsageTracker:
    """
    Comprehensive usage tracking system for auto-expansion capabilities.

    Tracks:
    - Logic usage frequency and patterns
    - Performance metrics and trends
    - Resource utilization
    - Error patterns and types
    - Usage correlations and dependencies
    """

    def __init__(self, storage_path: str = "data/usage/"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Usage storage
        self.metrics_file = self.storage_path / "metrics.json"
        self.patterns_file = self.storage_path / "patterns.json"
        self.analysis_file = self.storage_path / "analysis.json"

        # Load existing data
        self.metrics: Dict[str, UsageMetrics] = {}
        self.patterns: Dict[str, UsagePattern] = {}
        self._load_data()

        # Configuration
        self.tracking_enabled = True
        self.retention_days = 90
        self.cleanup_interval = 24 * 60 * 60  # 24 hours
        self.last_cleanup = time.time()

        # Thread safety
        self._lock = threading.Lock()

        # Performance tracking
        self.track_start_time = time.time()
        self.total_tracked_calls = 0

    def _load_data(self) -> None:
        """Load existing usage data from storage."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, "r") as f:
                    data = json.load(f)
                    for logic_id, metrics_data in data.get("metrics", {}).items():
                        self.metrics[logic_id] = self._dict_to_metrics(metrics_data)

            if self.patterns_file.exists():
                with open(self.patterns_file, "r") as f:
                    data = json.load(f)
                    for pattern_data in data.get("patterns", []):
                        pattern = self._dict_to_pattern(pattern_data)
                        self.patterns[pattern.pattern_id] = pattern

            logger.info(
                f"Loaded {len(self.metrics)} metrics and {len(self.patterns)} patterns"
            )
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")

    def _save_data(self) -> None:
        """Save usage data to storage."""
        try:
            with self._lock:
                # Save metrics
                metrics_data = {
                    "metrics": {
                        logic_id: asdict(metrics)
                        for logic_id, metrics in self.metrics.items()
                    },
                    "last_updated": datetime.now().isoformat(),
                }
                with open(self.metrics_file, "w") as f:
                    json.dump(metrics_data, f, indent=2, default=str)

                # Save patterns
                patterns_data = {
                    "patterns": [asdict(pattern) for pattern in self.patterns.values()],
                    "last_updated": datetime.now().isoformat(),
                }
                with open(self.patterns_file, "w") as f:
                    json.dump(patterns_data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving usage data: {e}")

    def _dict_to_metrics(self, data: Dict[str, Any]) -> UsageMetrics:
        """Convert dictionary to UsageMetrics."""
        return UsageMetrics(
            logic_id=data["logic_id"],
            total_calls=data["total_calls"],
            successful_calls=data["successful_calls"],
            failed_calls=data["failed_calls"],
            average_response_time=data["average_response_time"],
            total_response_time=data["total_response_time"],
            last_called=datetime.fromisoformat(data["last_called"]),
            first_called=datetime.fromisoformat(data["first_called"]),
            peak_usage_time=datetime.fromisoformat(data["peak_usage_time"]),
            usage_pattern=data["usage_pattern"],
            error_types=data["error_types"],
            performance_trend=data["performance_trend"],
            resource_usage=data["resource_usage"],
            metadata=data["metadata"],
        )

    def _dict_to_pattern(self, data: Dict[str, Any]) -> UsagePattern:
        """Convert dictionary to UsagePattern."""
        return UsagePattern(
            pattern_id=data["pattern_id"],
            logic_ids=data["logic_ids"],
            frequency=data["frequency"],
            time_period=data["time_period"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            peak_usage=data["peak_usage"],
            average_usage=data["average_usage"],
            trend=data["trend"],
            correlation_score=data["correlation_score"],
            metadata=data["metadata"],
        )

    def track_logic_call(
        self,
        logic_id: str,
        start_time: float,
        end_time: float,
        success: bool,
        error_type: str = None,
        resource_usage: Dict[str, float] = None,
    ) -> None:
        """
        Track a logic call with performance metrics.

        Args:
            logic_id: ID of the logic being called
            start_time: Call start timestamp
            end_time: Call end timestamp
            success: Whether the call was successful
            error_type: Type of error if failed
            resource_usage: Resource usage metrics
        """
        if not self.tracking_enabled:
            return

        with self._lock:
            response_time = end_time - start_time
            current_time = datetime.now()

            # Get or create metrics for this logic
            if logic_id not in self.metrics:
                self.metrics[logic_id] = UsageMetrics(
                    logic_id=logic_id,
                    total_calls=0,
                    successful_calls=0,
                    failed_calls=0,
                    average_response_time=0.0,
                    total_response_time=0.0,
                    last_called=current_time,
                    first_called=current_time,
                    peak_usage_time=current_time,
                    usage_pattern={},
                    error_types={},
                    performance_trend="stable",
                    resource_usage={},
                    metadata={"peak_usage": 0},
                )

            metrics = self.metrics[logic_id]

            # Update metrics
            metrics.total_calls += 1
            metrics.last_called = current_time

            if success:
                metrics.successful_calls += 1
            else:
                metrics.failed_calls += 1
                if error_type:
                    metrics.error_types[error_type] = (
                        metrics.error_types.get(error_type, 0) + 1
                    )

            # Update response time metrics
            metrics.total_response_time += response_time
            metrics.average_response_time = (
                metrics.total_response_time / metrics.total_calls
            )

            # Update usage pattern (hourly)
            hour = current_time.strftime("%Y-%m-%d %H:00")
            metrics.usage_pattern[hour] = metrics.usage_pattern.get(hour, 0) + 1

            # Update peak usage
            current_hour_usage = metrics.usage_pattern[hour]
            if current_hour_usage > metrics.metadata.get("peak_usage", 0):
                metrics.metadata["peak_usage"] = current_hour_usage
                metrics.peak_usage_time = current_time

            # Update resource usage
            if resource_usage:
                for resource, usage in resource_usage.items():
                    if resource not in metrics.resource_usage:
                        metrics.resource_usage[resource] = usage
                    else:
                        # Average with existing value
                        metrics.resource_usage[resource] = (
                            metrics.resource_usage[resource] + usage
                        ) / 2

            # Update performance trend
            self._update_performance_trend(metrics)

            # Increment total tracked calls
            self.total_tracked_calls += 1

            # Periodic cleanup
            if time.time() - self.last_cleanup > self.cleanup_interval:
                self._cleanup_old_data()

            # Record event
            write_event(
                "logic_call_tracked",
                {
                    "logic_id": logic_id,
                    "response_time": response_time,
                    "success": success,
                    "error_type": error_type,
                    "total_calls": metrics.total_calls,
                },
            )

    def get_logic_metrics(self, logic_id: str) -> Optional[UsageMetrics]:
        """Get usage metrics for a specific logic."""
        return self.metrics.get(logic_id)

    def get_top_used_logics(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top used logics by call count."""
        sorted_logics = sorted(
            self.metrics.items(), key=lambda x: x[1].total_calls, reverse=True
        )
        return [
            (logic_id, metrics.total_calls)
            for logic_id, metrics in sorted_logics[:limit]
        ]

    def get_performance_alerts(self, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Get performance alerts for logics with high response times."""
        alerts = []

        for logic_id, metrics in self.metrics.items():
            if metrics.average_response_time > threshold:
                alerts.append(
                    {
                        "logic_id": logic_id,
                        "average_response_time": metrics.average_response_time,
                        "total_calls": metrics.total_calls,
                        "success_rate": (
                            metrics.successful_calls / metrics.total_calls
                            if metrics.total_calls > 0
                            else 0
                        ),
                        "severity": (
                            "high" if metrics.average_response_time > 5.0 else "medium"
                        ),
                    }
                )

        return sorted(alerts, key=lambda x: x["average_response_time"], reverse=True)

    def analyze_usage_patterns(self, days: int = 7) -> List[UsagePattern]:
        """Analyze usage patterns over a time period."""
        cutoff_date = datetime.now() - timedelta(days=days)
        patterns = []

        # Group logics by usage patterns
        logic_groups = self._group_logics_by_usage(cutoff_date)

        for group_id, logic_ids in logic_groups.items():
            if len(logic_ids) < 2:  # Skip single logic groups
                continue

            # Analyze group usage pattern
            pattern = self._create_usage_pattern(logic_ids, cutoff_date)
            if pattern:
                patterns.append(pattern)
                self.patterns[pattern.pattern_id] = pattern

        # Save patterns
        self._save_data()

        return patterns

    def detect_usage_trends(self, days: int = 30) -> Dict[str, Any]:
        """Detect usage trends over time."""
        cutoff_date = datetime.now() - timedelta(days=days)

        # Filter recent metrics
        recent_metrics = {
            logic_id: metrics
            for logic_id, metrics in self.metrics.items()
            if metrics.last_called >= cutoff_date
        }

        if not recent_metrics:
            return {
                "total_logics": 0,
                "total_calls": 0,
                "average_response_time": 0,
                "success_rate": 0,
                "trends": {},
            }

        # Calculate overall statistics
        total_calls = sum(m.total_calls for m in recent_metrics.values())
        total_successful = sum(m.successful_calls for m in recent_metrics.values())
        avg_response_time = (
            sum(
                m.average_response_time * m.total_calls for m in recent_metrics.values()
            )
            / total_calls
            if total_calls > 0
            else 0
        )
        success_rate = total_successful / total_calls if total_calls > 0 else 0

        # Analyze trends
        trends = {
            "increasing_usage": len(
                [
                    m
                    for m in recent_metrics.values()
                    if m.performance_trend == "improving"
                ]
            ),
            "stable_usage": len(
                [m for m in recent_metrics.values() if m.performance_trend == "stable"]
            ),
            "decreasing_usage": len(
                [
                    m
                    for m in recent_metrics.values()
                    if m.performance_trend == "degrading"
                ]
            ),
            "high_performance": len(
                [m for m in recent_metrics.values() if m.average_response_time < 1.0]
            ),
            "medium_performance": len(
                [
                    m
                    for m in recent_metrics.values()
                    if 1.0 <= m.average_response_time < 3.0
                ]
            ),
            "low_performance": len(
                [m for m in recent_metrics.values() if m.average_response_time >= 3.0]
            ),
        }

        return {
            "total_logics": len(recent_metrics),
            "total_calls": total_calls,
            "average_response_time": avg_response_time,
            "success_rate": success_rate,
            "trends": trends,
        }

    def get_usage_recommendations(self) -> List[Dict[str, Any]]:
        """Get usage-based recommendations for optimization."""
        recommendations = []

        # Performance recommendations
        performance_alerts = self.get_performance_alerts()
        for alert in performance_alerts[:5]:  # Top 5 performance issues
            recommendations.append(
                {
                    "type": "performance_optimization",
                    "logic_id": alert["logic_id"],
                    "priority": "high" if alert["severity"] == "high" else "medium",
                    "description": f"Logic {alert['logic_id']} has high response time ({alert['average_response_time']:.2f}s)",
                    "suggestions": [
                        "Consider caching frequently accessed data",
                        "Optimize database queries",
                        "Review algorithm complexity",
                    ],
                }
            )

        # Usage pattern recommendations
        low_usage_logics = [
            (logic_id, metrics)
            for logic_id, metrics in self.metrics.items()
            if metrics.total_calls < 5
            and (datetime.now() - metrics.last_called).days > 30
        ]

        for logic_id, metrics in low_usage_logics[:3]:  # Top 3 low usage
            recommendations.append(
                {
                    "type": "low_usage",
                    "logic_id": logic_id,
                    "priority": "low",
                    "description": f"Logic {logic_id} has low usage ({metrics.total_calls} calls)",
                    "suggestions": [
                        "Consider deprecating if no longer needed",
                        "Review if functionality is covered by other logics",
                        "Check if documentation needs updating",
                    ],
                }
            )

        # High error rate recommendations
        high_error_logics = [
            (logic_id, metrics)
            for logic_id, metrics in self.metrics.items()
            if metrics.total_calls > 10
            and metrics.failed_calls / metrics.total_calls > 0.1
        ]

        for logic_id, metrics in high_error_logics[:3]:  # Top 3 high error
            error_rate = metrics.failed_calls / metrics.total_calls
            recommendations.append(
                {
                    "type": "high_error_rate",
                    "logic_id": logic_id,
                    "priority": "high",
                    "description": f"Logic {logic_id} has high error rate ({error_rate:.1%})",
                    "suggestions": [
                        "Review error handling and validation",
                        "Check input data quality",
                        "Consider adding retry logic",
                    ],
                }
            )

        return recommendations

    def _update_performance_trend(self, metrics: UsageMetrics) -> None:
        """Update performance trend based on recent calls."""
        # Simple trend calculation based on recent response times
        # In a real implementation, this would use more sophisticated analysis

        if metrics.total_calls < 10:
            metrics.performance_trend = "stable"
            return

        # Get recent response times (last 10 calls)
        recent_times = metrics.metadata.get("recent_response_times", [])
        if len(recent_times) >= 10:
            recent_avg = sum(recent_times[-10:]) / 10
            overall_avg = metrics.average_response_time

            if recent_avg < overall_avg * 0.9:
                metrics.performance_trend = "improving"
            elif recent_avg > overall_avg * 1.1:
                metrics.performance_trend = "degrading"
            else:
                metrics.performance_trend = "stable"

    def _group_logics_by_usage(self, cutoff_date: datetime) -> Dict[str, List[str]]:
        """Group logics by similar usage patterns."""
        groups = {}
        used_logic_ids = set()

        for logic_id, metrics in self.metrics.items():
            if logic_id in used_logic_ids or metrics.last_called < cutoff_date:
                continue

            # Find logics with similar usage patterns
            similar_logics = [logic_id]
            used_logic_ids.add(logic_id)

            for other_id, other_metrics in self.metrics.items():
                if (
                    other_id in used_logic_ids
                    or other_metrics.last_called < cutoff_date
                ):
                    continue

                # Check if usage patterns are similar
                if self._are_usage_patterns_similar(metrics, other_metrics):
                    similar_logics.append(other_id)
                    used_logic_ids.add(other_id)

            if len(similar_logics) > 1:
                group_id = f"group_{len(groups) + 1}"
                groups[group_id] = similar_logics

        return groups

    def _are_usage_patterns_similar(
        self, metrics1: UsageMetrics, metrics2: UsageMetrics
    ) -> bool:
        """Check if two logics have similar usage patterns."""
        # Compare usage frequency
        freq_ratio = min(metrics1.total_calls, metrics2.total_calls) / max(
            metrics1.total_calls, metrics2.total_calls
        )

        # Compare response times
        time_ratio = min(
            metrics1.average_response_time, metrics2.average_response_time
        ) / max(metrics1.average_response_time, metrics2.average_response_time)

        # Compare success rates
        success1 = (
            metrics1.successful_calls / metrics1.total_calls
            if metrics1.total_calls > 0
            else 0
        )
        success2 = (
            metrics2.successful_calls / metrics2.total_calls
            if metrics2.total_calls > 0
            else 0
        )
        success_ratio = (
            min(success1, success2) / max(success1, success2)
            if max(success1, success2) > 0
            else 1.0
        )

        # Consider similar if all ratios are above 0.7
        return freq_ratio > 0.7 and time_ratio > 0.7 and success_ratio > 0.7

    def _create_usage_pattern(
        self, logic_ids: List[str], start_time: datetime
    ) -> Optional[UsagePattern]:
        """Create a usage pattern from a group of logics."""
        if not logic_ids:
            return None

        # Calculate pattern statistics
        total_frequency = sum(
            self.metrics[logic_id].total_calls for logic_id in logic_ids
        )
        peak_usage = max(
            self.metrics[logic_id].metadata.get("peak_usage", 0)
            for logic_id in logic_ids
        )
        average_usage = total_frequency / len(logic_ids)

        # Calculate correlation score
        correlation_score = self._calculate_correlation_score(logic_ids)

        # Determine trend
        trends = [self.metrics[logic_id].performance_trend for logic_id in logic_ids]
        trend_counts = Counter(trends)
        dominant_trend = trend_counts.most_common(1)[0][0]

        pattern_id = f"pattern_{len(self.patterns) + 1}"

        return UsagePattern(
            pattern_id=pattern_id,
            logic_ids=logic_ids,
            frequency=total_frequency,
            time_period="daily",
            start_time=start_time,
            end_time=datetime.now(),
            peak_usage=peak_usage,
            average_usage=average_usage,
            trend=dominant_trend,
            correlation_score=correlation_score,
            metadata={"logic_count": len(logic_ids)},
        )

    def _calculate_correlation_score(self, logic_ids: List[str]) -> float:
        """Calculate correlation score between logics."""
        if len(logic_ids) < 2:
            return 1.0

        # Simple correlation based on usage timing
        # In a real implementation, this would use more sophisticated correlation analysis

        usage_times = []
        for logic_id in logic_ids:
            metrics = self.metrics[logic_id]
            # Get recent usage times
            recent_hours = sorted(metrics.usage_pattern.keys())[-10:]
            usage_times.extend(recent_hours)

        # Calculate overlap in usage times
        unique_times = set(usage_times)
        overlap = len(usage_times) - len(unique_times)

        return min(1.0, overlap / len(usage_times)) if usage_times else 0.0

    def _cleanup_old_data(self) -> None:
        """Clean up old usage data."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        # Remove old usage pattern entries
        for logic_id, metrics in self.metrics.items():
            old_hours = [
                hour
                for hour in metrics.usage_pattern.keys()
                if datetime.strptime(hour, "%Y-%m-%d %H:00") < cutoff_date
            ]
            for hour in old_hours:
                del metrics.usage_pattern[hour]

        # Remove old patterns
        old_patterns = [
            pattern_id
            for pattern_id, pattern in self.patterns.items()
            if pattern.end_time < cutoff_date
        ]
        for pattern_id in old_patterns:
            del self.patterns[pattern_id]

        self.last_cleanup = time.time()
        logger.info(
            f"Cleaned up {len(old_hours)} old usage entries and {len(old_patterns)} old patterns"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        total_logics = len(self.metrics)

        if total_logics == 0:
            return {
                "total_logics": 0,
                "total_calls": 0,
                "average_response_time": 0,
                "success_rate": 0,
                "tracking_duration": 0,
                "top_used_logics": [],
            }

        # Calculate overall statistics
        total_calls = sum(m.total_calls for m in self.metrics.values())
        total_successful = sum(m.successful_calls for m in self.metrics.values())
        avg_response_time = (
            sum(m.average_response_time * m.total_calls for m in self.metrics.values())
            / total_calls
            if total_calls > 0
            else 0
        )
        success_rate = total_successful / total_calls if total_calls > 0 else 0

        # Get top used logics
        top_used = self.get_top_used_logics(5)

        # Calculate tracking duration
        tracking_duration = time.time() - self.track_start_time

        return {
            "total_logics": total_logics,
            "total_calls": total_calls,
            "average_response_time": avg_response_time,
            "success_rate": success_rate,
            "tracking_duration": tracking_duration,
            "top_used_logics": top_used,
            "total_tracked_calls": self.total_tracked_calls,
        }


# Global instance for easy access
_usage_tracker = None


def get_usage_tracker() -> UsageTracker:
    """Get global usage tracker instance."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


def track_logic_call(
    logic_id: str,
    start_time: float,
    end_time: float,
    success: bool,
    error_type: str = None,
    resource_usage: Dict[str, float] = None,
) -> None:
    """Convenience function to track a logic call."""
    tracker = get_usage_tracker()
    tracker.track_logic_call(
        logic_id, start_time, end_time, success, error_type, resource_usage
    )


def get_usage_statistics() -> Dict[str, Any]:
    """Convenience function to get usage statistics."""
    tracker = get_usage_tracker()
    return tracker.get_statistics()


def get_performance_alerts(threshold: float = 2.0) -> List[Dict[str, Any]]:
    """Convenience function to get performance alerts."""
    tracker = get_usage_tracker()
    return tracker.get_performance_alerts(threshold)
