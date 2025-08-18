"""
Alert Policies Library

Provides threshold-based alerts, pattern-based anomaly detection,
multi-channel routing, deduplication, and escalation logic.
"""

import time
import os
import re
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

from .sli import sli_snapshot, sli_quantiles, sli_rate
from .slo import SLOResult, burn_rate_alerts


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels."""

    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"


@dataclass
class Threshold:
    """Threshold configuration for alerts."""

    value: float
    duration_sec: int  # Duration the threshold must be exceeded
    severity: AlertSeverity


@dataclass
class Escalation:
    """Escalation configuration."""

    levels: List[str]  # e.g., ["warn->crit->page"]
    cooldown_sec: int = 1800  # 30 minutes default


@dataclass
class AlertPolicy:
    """Alert policy configuration."""

    id: str
    name: str
    description: str
    match: Dict[str, str]  # Match criteria (scope, metric, etc.)
    thresholds: List[Threshold]
    dedup_window_sec: int = 300  # 5 minutes default
    channels: List[str] = None  # e.g., ["slack:#ops", "email:oncall@x"]
    escalation: Optional[Escalation] = None
    quiet_hours: Optional[str] = None  # e.g., "22:00-07:00"
    maintenance_labels: List[str] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AlertEvent:
    """Alert event with all details."""

    id: str
    policy_id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: float
    value: float
    threshold: float
    dimensions: Dict[str, str]
    recommendations: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class AlertState:
    """Alert state for deduplication and escalation."""

    policy_id: str
    current_severity: AlertSeverity
    first_triggered: float
    last_triggered: float
    trigger_count: int
    escalation_level: int = 0
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None


class AlertManager:
    """Manages alert policies, evaluation, and routing."""

    def __init__(self):
        self.policies: Dict[str, AlertPolicy] = {}
        self.alert_states: Dict[str, AlertState] = {}
        self.channel_handlers: Dict[str, Callable] = {}

        # Configuration from environment
        self.default_dedup_window = int(os.getenv("ALERT_DEDUP_WINDOW_SEC", "300"))
        self.escalation_cooldown = int(
            os.getenv("ALERT_ESCALATION_COOLDOWN_SEC", "1800")
        )
        self.quiet_hours = os.getenv("QUIET_HOURS", "22:00-07:00")

        # Register default channel handlers
        self._register_default_handlers()

    def add_policy(self, policy: AlertPolicy) -> None:
        """Add an alert policy."""
        self.policies[policy.id] = policy

    def remove_policy(self, policy_id: str) -> None:
        """Remove an alert policy."""
        if policy_id in self.policies:
            del self.policies[policy_id]
        if policy_id in self.alert_states:
            del self.alert_states[policy_id]

    def evaluate_policies(self, snapshot=None) -> List[AlertEvent]:
        """Evaluate all alert policies and return triggered events."""
        if snapshot is None:
            snapshot = sli_snapshot()

        events = []
        current_time = time.time()

        for policy in self.policies.values():
            if not policy.enabled:
                continue

            # Check if in quiet hours
            if self._is_in_quiet_hours(policy.quiet_hours or self.quiet_hours):
                continue

            # Check if in maintenance window
            if self._is_in_maintenance_window(policy.maintenance_labels or []):
                continue

            # Evaluate policy
            policy_events = self._evaluate_policy(policy, snapshot, current_time)
            events.extend(policy_events)

        return events

    def _evaluate_policy(
        self, policy: AlertPolicy, snapshot, current_time: float
    ) -> List[AlertEvent]:
        """Evaluate a single alert policy."""
        events = []

        # Get current value based on match criteria
        current_value = self._get_current_value(policy.match, snapshot)

        # Check each threshold
        for threshold in policy.thresholds:
            if self._is_threshold_breached(
                policy, threshold, current_value, current_time
            ):
                event = self._create_alert_event(
                    policy, threshold, current_value, current_time
                )
                events.append(event)

        return events

    def _get_current_value(self, match: Dict[str, str], snapshot) -> float:
        """Get current value based on match criteria."""
        scope = match.get("scope", "global")
        metric = match.get("metric", "total")
        dims = {}

        # Extract dimensions from match
        for key, value in match.items():
            if key not in ["scope", "metric"]:
                dims[key] = value

        if metric == "latency_p95_ms":
            quantiles = sli_quantiles("latency_ms", dims, [0.95])
            return quantiles.get("p95", 0.0)

        elif metric == "latency_p99_ms":
            quantiles = sli_quantiles("latency_ms", dims, [0.99])
            return quantiles.get("p99", 0.0)

        elif metric == "error_rate":
            total_rate = sli_rate("total", dims)
            error_rate = sli_rate("error", dims)
            if total_rate == 0:
                return 0.0
            return (error_rate / total_rate) * 100

        elif metric == "availability":
            return sli_availability("success", "total", dims) * 100

        elif metric == "throughput":
            return sli_rate("total", dims)

        elif metric == "anomaly_rate":
            total_rate = sli_rate("total", dims)
            anomaly_rate = sli_rate("anomaly", dims)
            if total_rate == 0:
                return 0.0
            return (anomaly_rate / total_rate) * 100

        else:
            # Default to count
            return sli_count(metric, dims)

    def _is_threshold_breached(
        self,
        policy: AlertPolicy,
        threshold: Threshold,
        current_value: float,
        current_time: float,
    ) -> bool:
        """Check if a threshold is breached."""
        # Get alert state for deduplication
        state_key = f"{policy.id}_{threshold.severity.value}"
        state = self.alert_states.get(state_key)

        # Check if threshold is exceeded
        is_exceeded = False
        if threshold.severity == AlertSeverity.CRITICAL:
            is_exceeded = current_value >= threshold.value
        else:
            is_exceeded = current_value >= threshold.value

        if not is_exceeded:
            # Reset state if threshold is no longer exceeded
            if state:
                del self.alert_states[state_key]
            return False

        # Check duration requirement
        if state:
            duration_exceeded = (
                current_time - state.first_triggered
            ) >= threshold.duration_sec
            if duration_exceeded:
                # Update state
                state.last_triggered = current_time
                state.trigger_count += 1
                return True
            else:
                return False
        else:
            # First time exceeded, create state
            self.alert_states[state_key] = AlertState(
                policy_id=policy.id,
                current_severity=threshold.severity,
                first_triggered=current_time,
                last_triggered=current_time,
                trigger_count=1,
            )
            return True

    def _create_alert_event(
        self,
        policy: AlertPolicy,
        threshold: Threshold,
        current_value: float,
        current_time: float,
    ) -> AlertEvent:
        """Create an alert event."""
        state_key = f"{policy.id}_{threshold.severity.value}"
        state = self.alert_states[state_key]

        # Generate event ID (non-security use); prefer sha256 over md5
        event_id = hashlib.sha256(
            f"{policy.id}_{threshold.severity.value}_{current_time}".encode()
        ).hexdigest()

        # Create title and message
        title = f"{threshold.severity.value.upper()}: {policy.name}"
        message = (
            f"Metric '{policy.match.get('metric', 'unknown')}' is "
            f"{current_value:.2f} (threshold: {threshold.value:.2f})"
        )

        # Add recommendations based on severity
        recommendations = []
        if threshold.severity == AlertSeverity.CRITICAL:
            recommendations.append("Immediate action required")
            recommendations.append("Check system health and resource utilization")
        elif threshold.severity == AlertSeverity.WARNING:
            recommendations.append("Monitor closely")
            recommendations.append("Review recent changes")

        return AlertEvent(
            id=event_id,
            policy_id=policy.id,
            severity=threshold.severity,
            title=title,
            message=message,
            timestamp=current_time,
            value=current_value,
            threshold=threshold.value,
            dimensions=policy.match,
            recommendations=recommendations,
            metadata={
                "trigger_count": state.trigger_count,
                "duration_sec": threshold.duration_sec,
                "dedup_window_sec": policy.dedup_window_sec,
            },
        )

    def _is_in_quiet_hours(self, quiet_hours: str) -> bool:
        """Check if current time is in quiet hours."""
        if not quiet_hours:
            return False

        try:
            start_str, end_str = quiet_hours.split("-")
            current_hour = datetime.now().hour

            start_hour = int(start_str.split(":")[0])
            end_hour = int(end_str.split(":")[0])

            if start_hour <= end_hour:
                return start_hour <= current_hour <= end_hour
            else:
                # Crosses midnight
                return current_hour >= start_hour or current_hour <= end_hour
        except:
            return False

    def _is_in_maintenance_window(self, maintenance_labels: List[str]) -> bool:
        """Check if currently in maintenance window."""
        # Simplified - could check against maintenance calendar
        return False

    def route_alerts(self, events: List[AlertEvent]) -> Dict[str, List[AlertEvent]]:
        """Route alerts to appropriate channels."""
        routed = defaultdict(list)

        for event in events:
            policy = self.policies.get(event.policy_id)
            if not policy or not policy.channels:
                continue

            for channel in policy.channels:
                routed[channel].append(event)

        return dict(routed)

    def send_alerts(self, events: List[AlertEvent]) -> Dict[str, bool]:
        """Send alerts through configured channels."""
        routed = self.route_alerts(events)
        results = {}

        for channel, channel_events in routed.items():
            handler = self._get_channel_handler(channel)
            if handler:
                try:
                    handler(channel_events)
                    results[channel] = True
                except Exception as e:
                    results[channel] = False
            else:
                results[channel] = False

        return results

    def _get_channel_handler(self, channel: str) -> Optional[Callable]:
        """Get handler for a specific channel."""
        # Extract channel type and target
        if ":" in channel:
            channel_type, target = channel.split(":", 1)
        else:
            channel_type, target = channel, ""

        handler_key = f"{channel_type}_{target}"
        return self.channel_handlers.get(handler_key)

    def _register_default_handlers(self):
        """Register default channel handlers."""
        # Slack handler
        self.channel_handlers["slack_#ops"] = self._send_slack_alert
        self.channel_handlers["slack_#alerts"] = self._send_slack_alert

        # Email handler
        self.channel_handlers["email_oncall@x"] = self._send_email_alert
        self.channel_handlers["email_alerts@x"] = self._send_email_alert

        # Webhook handler
        self.channel_handlers["webhook_"] = self._send_webhook_alert

    def _send_slack_alert(self, events: List[AlertEvent]) -> None:
        """Send alert to Slack (placeholder implementation)."""
        for event in events:
            # In a real implementation, this would send to Slack API
            print(f"[SLACK] {event.title}: {event.message}")

    def _send_email_alert(self, events: List[AlertEvent]) -> None:
        """Send alert via email (placeholder implementation)."""
        for event in events:
            # In a real implementation, this would send email
            print(f"[EMAIL] {event.title}: {event.message}")

    def _send_webhook_alert(self, events: List[AlertEvent]) -> None:
        """Send alert via webhook (placeholder implementation)."""
        for event in events:
            # In a real implementation, this would POST to webhook URL
            print(f"[WEBHOOK] {event.title}: {event.message}")

    def create_default_policies(self) -> List[AlertPolicy]:
        """Create default alert policies."""
        policies = [
            AlertPolicy(
                id="latency_p95_high",
                name="High P95 Latency",
                description="Alert when P95 latency exceeds threshold",
                match={"scope": "global", "metric": "latency_p95_ms"},
                thresholds=[
                    Threshold(1500, 300, AlertSeverity.WARNING),  # 1.5s for 5min
                    Threshold(3000, 300, AlertSeverity.CRITICAL),  # 3s for 5min
                ],
                channels=["slack:#ops", "email:oncall@x"],
                escalation=Escalation(["warn->crit->page"], 1800),
            ),
            AlertPolicy(
                id="error_rate_high",
                name="High Error Rate",
                description="Alert when error rate exceeds threshold",
                match={"scope": "global", "metric": "error_rate"},
                thresholds=[
                    Threshold(1.0, 300, AlertSeverity.WARNING),  # 1% for 5min
                    Threshold(5.0, 300, AlertSeverity.CRITICAL),  # 5% for 5min
                ],
                channels=["slack:#ops", "email:oncall@x"],
                escalation=Escalation(["warn->crit->page"], 1800),
            ),
            AlertPolicy(
                id="availability_low",
                name="Low Availability",
                description="Alert when availability drops below threshold",
                match={"scope": "global", "metric": "availability"},
                thresholds=[
                    Threshold(99.0, 300, AlertSeverity.WARNING),  # 99% for 5min
                    Threshold(95.0, 300, AlertSeverity.CRITICAL),  # 95% for 5min
                ],
                channels=["slack:#ops", "email:oncall@x"],
                escalation=Escalation(["warn->crit->page"], 1800),
            ),
            AlertPolicy(
                id="anomaly_rate_high",
                name="High Anomaly Rate",
                description="Alert when anomaly detection rate is high",
                match={"scope": "global", "metric": "anomaly_rate"},
                thresholds=[
                    Threshold(2.0, 300, AlertSeverity.WARNING),  # 2% for 5min
                    Threshold(5.0, 300, AlertSeverity.CRITICAL),  # 5% for 5min
                ],
                channels=["slack:#ops"],
                escalation=Escalation(["warn->crit"], 1800),
            ),
        ]

        return policies


# Global alert manager instance
_alert_manager = AlertManager()


def add_alert_policy(policy: AlertPolicy) -> None:
    """Add an alert policy."""
    _alert_manager.add_policy(policy)


def remove_alert_policy(policy_id: str) -> None:
    """Remove an alert policy."""
    _alert_manager.remove_policy(policy_id)


def evaluate_alert_policies(snapshot=None) -> List[AlertEvent]:
    """Evaluate all alert policies and return triggered events."""
    return _alert_manager.evaluate_policies(snapshot)


def send_alerts(events: List[AlertEvent]) -> Dict[str, bool]:
    """Send alerts through configured channels."""
    return _alert_manager.send_alerts(events)


def create_default_policies() -> List[AlertPolicy]:
    """Create default alert policies."""
    return _alert_manager.create_default_policies()


def evaluate_slo_alerts(slo_results: List[SLOResult]) -> List[AlertEvent]:
    """Evaluate SLO results and generate alerts."""
    events = []

    for result in slo_results:
        # Generate burn rate alerts
        burn_alerts = burn_rate_alerts(result)

        for alert in burn_alerts:
            event = AlertEvent(
                id=hashlib.sha256(
                    f"slo_{result.spec.id}_{alert['severity']}".encode()
                ).hexdigest(),
                policy_id=f"slo_{result.spec.id}",
                severity=AlertSeverity(alert["severity"]),
                title=alert["title"],
                message=alert["message"],
                timestamp=result.timestamp,
                value=result.current_value,
                threshold=result.target_value,
                dimensions=result.spec.dimensions or {},
                recommendations=alert.get("recommendations", []),
                metadata={
                    "slo_id": result.spec.id,
                    "slo_type": result.spec.slo_type.value,
                },
            )
            events.append(event)

    return events
