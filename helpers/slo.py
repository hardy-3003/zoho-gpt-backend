"""
Service Level Objectives (SLO) Library

Provides SLO evaluation, error budget calculation, burn rate analysis,
and breach detection for production monitoring.
"""

import time
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

from .sli import sli_snapshot, sli_quantiles, sli_rate, sli_availability


class SLOType(Enum):
    """Types of SLOs supported."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    ANOMALY_RATE = "anomaly_rate"


class Severity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SLOSpec:
    """SLO specification with targets and configuration."""

    id: str
    name: str
    description: str
    slo_type: SLOType
    target: float  # Target value (e.g., 99.5 for 99.5% availability)
    window_days: int = 30  # Rolling window in days
    org_id: Optional[str] = None  # Organization-specific SLO
    dimensions: Optional[Dict[str, str]] = None  # Filter dimensions
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ErrorBudget:
    """Error budget calculation results."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    error_budget_remaining: float  # Percentage remaining
    error_budget_consumed: float  # Percentage consumed
    time_to_breach_days: Optional[float] = None  # Days until breach at current rate


@dataclass
class BurnRate:
    """Burn rate analysis results."""

    current_burn_rate: float  # Current error budget consumption rate
    average_burn_rate: float  # Average burn rate over window
    burn_rate_trend: str  # "increasing", "decreasing", "stable"
    severity: Severity
    time_to_breach_days: Optional[float] = None


@dataclass
class SLOResult:
    """Complete SLO evaluation result."""

    spec: SLOSpec
    timestamp: float
    current_value: float
    target_value: float
    is_breached: bool
    error_budget: ErrorBudget
    burn_rate: BurnRate
    recommendations: List[str]
    metadata: Dict[str, Any]


class SLOEvaluator:
    """Evaluates SLOs and calculates error budgets and burn rates."""

    def __init__(self):
        # Default SLO targets from environment
        self.default_targets = {
            SLOType.AVAILABILITY: float(os.getenv("SLO_AVAILABILITY", "99.5")),
            SLOType.LATENCY: float(os.getenv("SLO_LATENCY_P95_MS", "2500")),
            SLOType.ERROR_RATE: float(os.getenv("SLO_ERROR_RATE_MAX", "0.5")),
            SLOType.THROUGHPUT: float(os.getenv("SLO_THROUGHPUT_MIN", "100")),
            SLOType.ANOMALY_RATE: float(os.getenv("SLO_ANOMALY_RATE_MAX", "1.0")),
        }

        # Burn rate thresholds
        self.burn_rate_thresholds = {
            Severity.INFO: 0.5,  # 50% of error budget consumed
            Severity.WARNING: 0.8,  # 80% of error budget consumed
            Severity.CRITICAL: 0.95,  # 95% of error budget consumed
        }

    def evaluate_slo(self, spec: SLOSpec, snapshot=None) -> SLOResult:
        """Evaluate an SLO and return comprehensive results."""
        if snapshot is None:
            snapshot = sli_snapshot()

        # Get current value based on SLO type
        current_value = self._get_current_value(spec, snapshot)

        # Determine if breached
        is_breached = self._is_breached(spec, current_value)

        # Calculate error budget
        error_budget = self._calculate_error_budget(spec, snapshot)

        # Calculate burn rate
        burn_rate = self._calculate_burn_rate(spec, error_budget, snapshot)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            spec, current_value, error_budget, burn_rate
        )

        return SLOResult(
            spec=spec,
            timestamp=time.time(),
            current_value=current_value,
            target_value=spec.target,
            is_breached=is_breached,
            error_budget=error_budget,
            burn_rate=burn_rate,
            recommendations=recommendations,
            metadata={
                "window_days": spec.window_days,
                "org_id": spec.org_id,
                "dimensions": spec.dimensions,
            },
        )

    def _get_current_value(self, spec: SLOSpec, snapshot) -> float:
        """Get current value for the SLO based on its type."""
        dims = spec.dimensions or {}

        if spec.slo_type == SLOType.AVAILABILITY:
            return sli_availability("success", "total", dims) * 100

        elif spec.slo_type == SLOType.LATENCY:
            quantiles = sli_quantiles("latency_ms", dims, [0.95])
            return quantiles.get("p95", 0.0)

        elif spec.slo_type == SLOType.ERROR_RATE:
            total_rate = sli_rate("total", dims)
            error_rate = sli_rate("error", dims)
            if total_rate == 0:
                return 0.0
            return (error_rate / total_rate) * 100

        elif spec.slo_type == SLOType.THROUGHPUT:
            return sli_rate("total", dims)

        elif spec.slo_type == SLOType.ANOMALY_RATE:
            total_rate = sli_rate("total", dims)
            anomaly_rate = sli_rate("anomaly", dims)
            if total_rate == 0:
                return 0.0
            return (anomaly_rate / total_rate) * 100

        return 0.0

    def _is_breached(self, spec: SLOSpec, current_value: float) -> bool:
        """Determine if the SLO is breached based on its type."""
        if spec.slo_type == SLOType.AVAILABILITY:
            return current_value < spec.target

        elif spec.slo_type == SLOType.LATENCY:
            return current_value > spec.target

        elif spec.slo_type == SLOType.ERROR_RATE:
            return current_value > spec.target

        elif spec.slo_type == SLOType.THROUGHPUT:
            return current_value < spec.target

        elif spec.slo_type == SLOType.ANOMALY_RATE:
            return current_value > spec.target

        return False

    def _calculate_error_budget(self, spec: SLOSpec, snapshot) -> ErrorBudget:
        """Calculate error budget for the SLO."""
        dims = spec.dimensions or {}

        if spec.slo_type == SLOType.AVAILABILITY:
            total_requests = sli_count("total", dims)
            successful_requests = sli_count("success", dims)
            failed_requests = total_requests - successful_requests

            # Error budget is the allowed failure percentage
            error_budget_percentage = 100 - spec.target
            allowed_failures = (total_requests * error_budget_percentage) / 100
            remaining_failures = allowed_failures - failed_requests

            error_budget_remaining = (
                (remaining_failures / total_requests * 100)
                if total_requests > 0
                else 100
            )
            error_budget_consumed = (
                (failed_requests / total_requests * 100) if total_requests > 0 else 0
            )

            return ErrorBudget(
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                error_budget_remaining=max(0, error_budget_remaining),
                error_budget_consumed=min(100, error_budget_consumed),
            )

        else:
            # For other SLO types, use a simplified error budget
            total_requests = sli_count("total", dims)
            error_budget_remaining = 100  # Default for non-availability SLOs
            error_budget_consumed = 0

            return ErrorBudget(
                total_requests=total_requests,
                successful_requests=total_requests,  # Simplified
                failed_requests=0,  # Simplified
                error_budget_remaining=error_budget_remaining,
                error_budget_consumed=error_budget_consumed,
            )

    def _calculate_burn_rate(
        self, spec: SLOSpec, error_budget: ErrorBudget, snapshot
    ) -> BurnRate:
        """Calculate burn rate and determine severity."""
        # Calculate current burn rate (simplified)
        current_burn_rate = error_budget.error_budget_consumed / 100.0
        average_burn_rate = current_burn_rate  # Simplified - could use historical data

        # Determine trend (simplified)
        burn_rate_trend = "stable"
        if current_burn_rate > average_burn_rate * 1.1:
            burn_rate_trend = "increasing"
        elif current_burn_rate < average_burn_rate * 0.9:
            burn_rate_trend = "decreasing"

        # Determine severity
        severity = Severity.INFO
        if current_burn_rate >= self.burn_rate_thresholds[Severity.CRITICAL]:
            severity = Severity.CRITICAL
        elif current_burn_rate >= self.burn_rate_thresholds[Severity.WARNING]:
            severity = Severity.WARNING

        # Calculate time to breach (simplified)
        time_to_breach_days = None
        if current_burn_rate > 0 and burn_rate_trend == "increasing":
            remaining_budget = 1.0 - current_burn_rate
            if remaining_budget > 0:
                time_to_breach_days = (
                    remaining_budget / current_burn_rate * spec.window_days
                )

        return BurnRate(
            current_burn_rate=current_burn_rate,
            average_burn_rate=average_burn_rate,
            burn_rate_trend=burn_rate_trend,
            severity=severity,
            time_to_breach_days=time_to_breach_days,
        )

    def _generate_recommendations(
        self,
        spec: SLOSpec,
        current_value: float,
        error_budget: ErrorBudget,
        burn_rate: BurnRate,
    ) -> List[str]:
        """Generate recommendations based on SLO evaluation."""
        recommendations = []

        # Check if breached
        if burn_rate.severity == Severity.CRITICAL:
            recommendations.append(
                "CRITICAL: SLO is severely breached. Immediate action required."
            )
            recommendations.append(
                "Consider rolling back recent deployments or scaling up resources."
            )

        elif burn_rate.severity == Severity.WARNING:
            recommendations.append(
                "WARNING: SLO is approaching breach threshold. Monitor closely."
            )
            recommendations.append(
                "Review recent changes and consider preventive measures."
            )

        # Type-specific recommendations
        if spec.slo_type == SLOType.AVAILABILITY:
            if current_value < spec.target:
                recommendations.append(
                    "Investigate recent failures and error patterns."
                )
                recommendations.append(
                    "Check infrastructure health and resource utilization."
                )

        elif spec.slo_type == SLOType.LATENCY:
            if current_value > spec.target:
                recommendations.append("Investigate performance bottlenecks.")
                recommendations.append(
                    "Consider database optimization or caching improvements."
                )

        elif spec.slo_type == SLOType.ERROR_RATE:
            if current_value > spec.target:
                recommendations.append("Review error logs and fix root causes.")
                recommendations.append("Consider circuit breakers or retry mechanisms.")

        # Time to breach warnings
        if burn_rate.time_to_breach_days is not None:
            if burn_rate.time_to_breach_days < 1:
                recommendations.append(
                    f"URGENT: SLO will breach within {burn_rate.time_to_breach_days:.1f} days at current rate."
                )
            elif burn_rate.time_to_breach_days < 7:
                recommendations.append(
                    f"WARNING: SLO will breach within {burn_rate.time_to_breach_days:.1f} days at current rate."
                )

        return recommendations

    def create_default_slos(self, org_id: Optional[str] = None) -> List[SLOSpec]:
        """Create default SLOs for the system."""
        default_slos = [
            SLOSpec(
                id="availability_global",
                name="Global Availability",
                description="Overall system availability",
                slo_type=SLOType.AVAILABILITY,
                target=self.default_targets[SLOType.AVAILABILITY],
                org_id=org_id,
            ),
            SLOSpec(
                id="latency_p95_global",
                name="Global P95 Latency",
                description="95th percentile response time",
                slo_type=SLOType.LATENCY,
                target=self.default_targets[SLOType.LATENCY],
                org_id=org_id,
            ),
            SLOSpec(
                id="error_rate_global",
                name="Global Error Rate",
                description="Overall error rate",
                slo_type=SLOType.ERROR_RATE,
                target=self.default_targets[SLOType.ERROR_RATE],
                org_id=org_id,
            ),
            SLOSpec(
                id="anomaly_rate_global",
                name="Global Anomaly Rate",
                description="Overall anomaly detection rate",
                slo_type=SLOType.ANOMALY_RATE,
                target=self.default_targets[SLOType.ANOMALY_RATE],
                org_id=org_id,
            ),
        ]

        return default_slos


# Global SLO evaluator instance
_slo_evaluator = SLOEvaluator()


def evaluate_slo(spec: SLOSpec, snapshot=None) -> SLOResult:
    """Evaluate an SLO and return comprehensive results."""
    return _slo_evaluator.evaluate_slo(spec, snapshot)


def create_default_slos(org_id: Optional[str] = None) -> List[SLOSpec]:
    """Create default SLOs for the system."""
    return _slo_evaluator.create_default_slos(org_id)


def burn_rate_alerts(result: SLOResult) -> List[Dict[str, Any]]:
    """Generate alerts based on burn rate analysis."""
    alerts = []

    # Critical alerts
    if result.burn_rate.severity == Severity.CRITICAL:
        alerts.append(
            {
                "severity": "critical",
                "title": f"Critical SLO Breach: {result.spec.name}",
                "message": f"SLO {result.spec.name} is critically breached. Current value: {result.current_value:.2f}, Target: {result.target:.2f}",
                "recommendations": result.recommendations[:3],  # Top 3 recommendations
            }
        )

    # Warning alerts
    elif result.burn_rate.severity == Severity.WARNING:
        alerts.append(
            {
                "severity": "warning",
                "title": f"SLO Warning: {result.spec.name}",
                "message": f"SLO {result.spec.name} is approaching breach threshold. Current value: {result.current_value:.2f}, Target: {result.target:.2f}",
                "recommendations": result.recommendations[:2],  # Top 2 recommendations
            }
        )

    # Time to breach alerts
    if result.burn_rate.time_to_breach_days is not None:
        if result.burn_rate.time_to_breach_days < 1:
            alerts.append(
                {
                    "severity": "critical",
                    "title": f"Immediate SLO Breach Risk: {result.spec.name}",
                    "message": f"SLO {result.spec.name} will breach within {result.burn_rate.time_to_breach_days:.1f} days at current rate",
                    "recommendations": ["Immediate action required to prevent breach"],
                }
            )
        elif result.burn_rate.time_to_breach_days < 7:
            alerts.append(
                {
                    "severity": "warning",
                    "title": f"SLO Breach Risk: {result.spec.name}",
                    "message": f"SLO {result.spec.name} will breach within {result.burn_rate.time_to_breach_days:.1f} days at current rate",
                    "recommendations": ["Monitor closely and take preventive action"],
                }
            )

    return alerts
