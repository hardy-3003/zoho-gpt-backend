"""
Anomaly Detection System for Zoho GPT Backend

Provides statistical and ML-based anomaly detection for performance metrics,
with integration to telemetry and alerting systems.
"""

import os
import json
import logging
import time
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import statistics

from .telemetry import event, incr, get_deep_metrics
from .alerts import create_alert, AlertSeverity

_log = logging.getLogger("anomaly_detector")

# Configuration
ANOMALY_DETECTION_ENABLED = (
    os.environ.get("ANOMALY_DETECTION_ENABLED", "true").lower() == "true"
)


def _thresholds() -> Dict[str, float]:
    return {
        "z_score": float(os.environ.get("ANOMALY_Z_SCORE_THRESHOLD", "3.0")),
        "iqr_multiplier": float(os.environ.get("ANOMALY_IQR_MULTIPLIER", "1.5")),
        "percentile": float(os.environ.get("ANOMALY_PERCENTILE_THRESHOLD", "99.5")),
        "trend_sensitivity": float(os.environ.get("ANOMALY_TREND_SENSITIVITY", "0.1")),
    }


# ML model configuration (optional)
ML_ANOMALY_ENABLED = os.environ.get("ML_ANOMALY_ENABLED", "false").lower() == "true"


@dataclass
class AnomalyScore:
    """Anomaly score with metadata."""

    score: float
    method: str
    threshold: float
    is_anomaly: bool
    confidence: float
    context: Dict[str, Any]
    timestamp: datetime


@dataclass
class AnomalyResult:
    """Complete anomaly detection result."""

    metric_name: str
    current_value: float
    scores: List[AnomalyScore]
    overall_score: float
    is_anomaly: bool
    reason: str
    timestamp: datetime
    org_id: Optional[str] = None
    logic_id: Optional[str] = None
    orchestrator_id: Optional[str] = None


class StatisticalAnomalyDetector:
    """Statistical anomaly detection using multiple methods."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metric_history = defaultdict(lambda: deque(maxlen=window_size))
        self.detection_lock = threading.Lock()

    def add_data_point(self, metric_name: str, value: float) -> None:
        """Add a new data point to the metric history."""
        with self.detection_lock:
            self.metric_history[metric_name].append(value)

    def z_score_detection(self, metric_name: str, current_value: float) -> AnomalyScore:
        """Detect anomalies using Z-score method."""
        history = self.metric_history[metric_name]

        if len(history) < 10:  # Need at least 10 data points
            return AnomalyScore(
                score=0.0,
                method="z_score",
                threshold=_thresholds()["z_score"],
                is_anomaly=False,
                confidence=0.0,
                context={"reason": "insufficient_data"},
                timestamp=datetime.utcnow(),
            )

        historical_values = list(history)
        mean = statistics.mean(historical_values)
        std = statistics.stdev(historical_values) if len(historical_values) > 1 else 0.0

        if std == 0:
            return AnomalyScore(
                score=0.0,
                method="z_score",
                threshold=_thresholds()["z_score"],
                is_anomaly=False,
                confidence=0.0,
                context={"reason": "no_variance"},
                timestamp=datetime.utcnow(),
            )

        z_score = abs(current_value - mean) / std
        is_anomaly = z_score > _thresholds()["z_score"]

        # Confidence based on data points and variance
        confidence = min(1.0, len(historical_values) / self.window_size)

        return AnomalyScore(
            score=z_score,
            method="z_score",
            threshold=_thresholds()["z_score"],
            is_anomaly=is_anomaly,
            confidence=confidence,
            context={"mean": mean, "std": std, "data_points": len(historical_values)},
            timestamp=datetime.utcnow(),
        )

    def iqr_detection(self, metric_name: str, current_value: float) -> AnomalyScore:
        """Detect anomalies using Interquartile Range (IQR) method."""
        history = self.metric_history[metric_name]

        if len(history) < 10:
            return AnomalyScore(
                score=0.0,
                method="iqr",
                threshold=_thresholds()["iqr_multiplier"],
                is_anomaly=False,
                confidence=0.0,
                context={"reason": "insufficient_data"},
                timestamp=datetime.utcnow(),
            )

        historical_values = sorted(list(history))
        q1 = statistics.quantiles(historical_values, n=4)[0]
        q3 = statistics.quantiles(historical_values, n=4)[2]
        iqr = q3 - q1

        if iqr == 0:
            return AnomalyScore(
                score=0.0,
                method="iqr",
                threshold=_thresholds()["iqr_multiplier"],
                is_anomaly=False,
                confidence=0.0,
                context={"reason": "no_variance"},
                timestamp=datetime.utcnow(),
            )

        lower_bound = q1 - _thresholds()["iqr_multiplier"] * iqr
        upper_bound = q3 + _thresholds()["iqr_multiplier"] * iqr

        is_anomaly = current_value < lower_bound or current_value > upper_bound

        # Calculate anomaly score as distance from bounds
        if current_value < lower_bound:
            score = (lower_bound - current_value) / iqr
        elif current_value > upper_bound:
            score = (current_value - upper_bound) / iqr
        else:
            score = 0.0

        confidence = min(1.0, len(historical_values) / self.window_size)

        return AnomalyScore(
            score=score,
            method="iqr",
            threshold=_thresholds()["iqr_multiplier"],
            is_anomaly=is_anomaly,
            confidence=confidence,
            context={
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "data_points": len(historical_values),
            },
            timestamp=datetime.utcnow(),
        )

    def percentile_detection(
        self, metric_name: str, current_value: float
    ) -> AnomalyScore:
        """Detect anomalies using percentile method."""
        history = self.metric_history[metric_name]

        if len(history) < 10:
            return AnomalyScore(
                score=0.0,
                method="percentile",
                threshold=_thresholds()["percentile"],
                is_anomaly=False,
                confidence=0.0,
                context={"reason": "insufficient_data"},
                timestamp=datetime.utcnow(),
            )

        historical_values = sorted(list(history))
        percentile_threshold = statistics.quantiles(historical_values, n=1000)[
            int(_thresholds()["percentile"] * 10) - 1
        ]

        is_anomaly = current_value > percentile_threshold

        # Calculate score as percentile rank
        percentile_rank = (
            sum(1 for x in historical_values if x <= current_value)
            / len(historical_values)
            * 100
        )
        score = percentile_rank / 100.0

        confidence = min(1.0, len(historical_values) / self.window_size)

        return AnomalyScore(
            score=score,
            method="percentile",
            threshold=_thresholds()["percentile"],
            is_anomaly=is_anomaly,
            confidence=confidence,
            context={
                "percentile_threshold": percentile_threshold,
                "percentile_rank": percentile_rank,
                "data_points": len(historical_values),
            },
            timestamp=datetime.utcnow(),
        )

    def trend_detection(self, metric_name: str, current_value: float) -> AnomalyScore:
        """Detect anomalies using trend analysis."""
        history = self.metric_history[metric_name]

        if len(history) < 20:  # Need more data for trend analysis
            return AnomalyScore(
                score=0.0,
                method="trend",
                threshold=_thresholds()["trend_sensitivity"],
                is_anomaly=False,
                confidence=0.0,
                context={"reason": "insufficient_data"},
                timestamp=datetime.utcnow(),
            )

        historical_values = list(history)

        # Calculate trend using linear regression (simplified)
        n = len(historical_values)
        x_sum = sum(range(n))
        y_sum = sum(historical_values)
        xy_sum = sum(i * val for i, val in enumerate(historical_values))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        # Predict next value
        predicted_value = historical_values[-1] + slope

        # Calculate deviation from trend
        deviation = (
            abs(current_value - predicted_value) / abs(predicted_value)
            if predicted_value != 0
            else 0
        )

        is_anomaly = deviation > _thresholds()["trend_sensitivity"]

        confidence = min(1.0, len(historical_values) / self.window_size)

        return AnomalyScore(
            score=deviation,
            method="trend",
            threshold=_thresholds()["trend_sensitivity"],
            is_anomaly=is_anomaly,
            confidence=confidence,
            context={
                "predicted_value": predicted_value,
                "slope": slope,
                "deviation": deviation,
                "data_points": len(historical_values),
            },
            timestamp=datetime.utcnow(),
        )

    def detect_anomaly(self, metric_name: str, current_value: float) -> AnomalyResult:
        """Detect anomalies using multiple statistical methods."""
        if not ANOMALY_DETECTION_ENABLED:
            return AnomalyResult(
                metric_name=metric_name,
                current_value=current_value,
                scores=[],
                overall_score=0.0,
                is_anomaly=False,
                reason="anomaly_detection_disabled",
                timestamp=datetime.utcnow(),
            )

        # Add current value to history
        self.add_data_point(metric_name, current_value)

        # Run all detection methods
        scores = [
            self.z_score_detection(metric_name, current_value),
            self.iqr_detection(metric_name, current_value),
            self.percentile_detection(metric_name, current_value),
            self.trend_detection(metric_name, current_value),
        ]

        # Calculate overall score (weighted average of individual scores)
        valid_scores = [s for s in scores if s.confidence >= 0.0]

        if not valid_scores:
            overall_score = 0.0
            is_anomaly = False
            reason = "insufficient_confidence"
        else:
            # Weight by confidence
            weighted_scores = [s.score * s.confidence for s in valid_scores]
            total_confidence = sum(s.confidence for s in valid_scores)
            overall_score = (
                sum(weighted_scores) / total_confidence if total_confidence > 0 else 0.0
            )

            # Determine anomaly if any method flags it (tests expect sensitivity)
            anomaly_votes = sum(1 for s in valid_scores if s.is_anomaly)
            is_anomaly = anomaly_votes > 0

            # Generate reason
            if is_anomaly:
                anomaly_methods = [s.method for s in valid_scores if s.is_anomaly]
                reason = f"anomaly_detected_by_{'_'.join(anomaly_methods)}"
            else:
                reason = "no_anomaly_detected"

        return AnomalyResult(
            metric_name=metric_name,
            current_value=current_value,
            scores=scores,
            overall_score=overall_score,
            is_anomaly=is_anomaly,
            reason=reason,
            timestamp=datetime.utcnow(),
        )


class MLAnomalyDetector:
    """ML-based anomaly detection (placeholder for future implementation)."""

    def __init__(self):
        self.model = None
        self.is_trained = False

    def train(self, historical_data: List[float]) -> bool:
        """Train the ML model with historical data."""
        if not ML_ANOMALY_ENABLED:
            return False

        try:
            # Placeholder for ML model training
            # In a real implementation, this would use scikit-learn, tensorflow, etc.
            self.is_trained = len(historical_data) > 50
            return self.is_trained
        except Exception as e:
            _log.error(f"ML model training failed: {e}")
            return False

    def detect_anomaly(self, value: float) -> Tuple[float, bool]:
        """Detect anomaly using ML model."""
        if not ML_ANOMALY_ENABLED or not self.is_trained:
            return 0.0, False

        try:
            # Placeholder for ML-based detection
            # In a real implementation, this would use the trained model
            return 0.0, False
        except Exception as e:
            _log.error(f"ML anomaly detection failed: {e}")
            return 0.0, False


class AnomalyDetectorManager:
    """Manages multiple anomaly detection methods and provides unified interface."""

    def __init__(self):
        self.statistical_detector = StatisticalAnomalyDetector()
        self.ml_detector = MLAnomalyDetector()
        self.detection_history = defaultdict(lambda: deque(maxlen=1000))
        self.manager_lock = threading.Lock()

    def detect_anomaly(
        self,
        metric_name: str,
        value: float,
        org_id: str = "",
        logic_id: str = "",
        orchestrator_id: str = "",
    ) -> AnomalyResult:
        """Detect anomalies using all available methods."""
        # Statistical detection
        result = self.statistical_detector.detect_anomaly(metric_name, value)

        # Add ML detection if enabled
        if ML_ANOMALY_ENABLED:
            ml_score, ml_anomaly = self.ml_detector.detect_anomaly(value)
            if ml_score > 0:
                ml_score_obj = AnomalyScore(
                    score=ml_score,
                    method="ml",
                    threshold=0.5,  # ML threshold
                    is_anomaly=ml_anomaly,
                    confidence=0.8 if self.ml_detector.is_trained else 0.0,
                    context={"model_trained": self.ml_detector.is_trained},
                    timestamp=datetime.utcnow(),
                )
                result.scores.append(ml_score_obj)

        # Store result
        with self.manager_lock:
            self.detection_history[metric_name].append(result)

        # Emit telemetry
        if ANOMALY_DETECTION_ENABLED:
            event(
                "anomaly.detected",
                {
                    "metric_name": metric_name,
                    "value": value,
                    "overall_score": result.overall_score,
                    "is_anomaly": result.is_anomaly,
                    "reason": result.reason,
                    "org_id": org_id,
                    "logic_id": logic_id,
                    "orchestrator_id": orchestrator_id,
                },
            )

            if result.is_anomaly:
                incr(
                    "anomalies.detected",
                    {
                        "metric": metric_name,
                        "method": "_".join(
                            [s.method for s in result.scores if s.is_anomaly]
                        ),
                    },
                )

        return result

    def get_anomaly_history(
        self, metric_name: str, since: Optional[datetime] = None
    ) -> List[AnomalyResult]:
        """Get anomaly detection history for a metric."""
        with self.manager_lock:
            history = self.detection_history[metric_name].copy()

        if since:
            history = [r for r in history if r.timestamp >= since]

        return list(history)

    def get_anomaly_summary(self, metric_name: str) -> Dict[str, Any]:
        """Get summary statistics for anomaly detection."""
        history = self.get_anomaly_history(metric_name)

        if not history:
            return {
                "metric_name": metric_name,
                "total_detections": 0,
                "anomaly_count": 0,
                "anomaly_rate": 0.0,
                "avg_score": 0.0,
                "last_detection": None,
            }

        anomaly_count = sum(1 for r in history if r.is_anomaly)
        avg_score = statistics.mean(r.overall_score for r in history)

        return {
            "metric_name": metric_name,
            "total_detections": len(history),
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_count / len(history),
            "avg_score": avg_score,
            "last_detection": history[-1].timestamp.isoformat() if history else None,
        }


# Global anomaly detector manager
_anomaly_manager = AnomalyDetectorManager()


def get_anomaly_manager() -> AnomalyDetectorManager:
    """Get the global anomaly detector manager."""
    return _anomaly_manager


def detect_anomaly(
    metric_name: str,
    value: float,
    org_id: str = "",
    logic_id: str = "",
    orchestrator_id: str = "",
) -> AnomalyResult:
    """Detect anomalies using the global anomaly detector."""
    return _anomaly_manager.detect_anomaly(
        metric_name, value, org_id, logic_id, orchestrator_id
    )


def get_anomaly_history(
    metric_name: str, since: Optional[datetime] = None
) -> List[AnomalyResult]:
    """Get anomaly detection history."""
    return _anomaly_manager.get_anomaly_history(metric_name, since)


def get_anomaly_summary(metric_name: str) -> Dict[str, Any]:
    """Get anomaly detection summary."""
    return _anomaly_manager.get_anomaly_summary(metric_name)


def export_anomaly_data(format: str = "json") -> str:
    """Export anomaly detection data."""
    all_summaries = {}

    # Get summaries for all metrics
    for metric_name in _anomaly_manager.detection_history.keys():
        all_summaries[metric_name] = get_anomaly_summary(metric_name)

    if format.lower() == "json":
        return json.dumps(all_summaries, indent=2, default=str)
    else:
        return str(all_summaries)


def clear_anomaly_history(before: Optional[datetime] = None) -> None:
    """Clear old anomaly detection history."""
    with _anomaly_manager.manager_lock:
        for metric_name in _anomaly_manager.detection_history:
            if before:
                _anomaly_manager.detection_history[metric_name] = deque(
                    [
                        r
                        for r in _anomaly_manager.detection_history[metric_name]
                        if r.timestamp >= before
                    ],
                    maxlen=1000,
                )
            else:
                _anomaly_manager.detection_history[metric_name].clear()
