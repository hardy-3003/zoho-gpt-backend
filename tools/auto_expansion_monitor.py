#!/usr/bin/env python3
"""
Auto-Expansion Monitor Tool

This tool provides comprehensive monitoring, validation, and guardrails for
the auto-expansion capabilities of the Zoho GPT Backend.

Features:
- Real-time monitoring of auto-expansion activities
- Quality assessment and validation
- Performance monitoring and resource limits
- Safety checks and rollback mechanisms
- Human review and approval workflows
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from helpers.pattern_detector import get_pattern_detector, RequestPattern
from helpers.usage_tracker import get_usage_tracker
from helpers.logic_generator import get_logic_generator, GeneratedLogic
from helpers.test_generator import get_test_generator, GeneratedTest
from helpers.history_store import write_event

logger = logging.getLogger(__name__)


class AutoExpansionMonitor:
    """Comprehensive monitoring and validation system for auto-expansion."""

    def __init__(self):
        self.pattern_detector = get_pattern_detector()
        self.usage_tracker = get_usage_tracker()
        self.logic_generator = get_logic_generator()
        self.test_generator = get_test_generator()

        # Configuration
        self.max_generated_logics = 50
        self.quality_threshold = 0.7
        self.performance_threshold = 5.0  # seconds
        self.memory_threshold = 100 * 1024 * 1024  # 100MB
        self.rollback_threshold = 0.3  # quality score for rollback

        # Monitoring state
        self.monitoring_active = False
        self.alerts = []
        self.metrics = {}

    def start_monitoring(self) -> None:
        """Start real-time monitoring of auto-expansion activities."""
        self.monitoring_active = True
        logger.info("Auto-expansion monitoring started")

        try:
            while self.monitoring_active:
                self._collect_metrics()
                self._check_alerts()
                self._validate_system_health()
                time.sleep(30)  # Check every 30 seconds

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            self.stop_monitoring()

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self.monitoring_active = False
        logger.info("Auto-expansion monitoring stopped")

    def _collect_metrics(self) -> None:
        """Collect current system metrics."""
        try:
            # Pattern detection metrics
            pattern_stats = self.pattern_detector.get_statistics()

            # Usage tracking metrics
            usage_stats = self.usage_tracker.get_statistics()

            # Logic generation metrics
            logic_stats = self.logic_generator.get_statistics()

            # Test generation metrics
            test_stats = self.test_generator.get_statistics()

            self.metrics = {
                "timestamp": datetime.now().isoformat(),
                "pattern_detection": pattern_stats,
                "usage_tracking": usage_stats,
                "logic_generation": logic_stats,
                "test_generation": test_stats,
                "system_health": self._assess_system_health(),
            }

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    def _check_alerts(self) -> None:
        """Check for alerts and issues."""
        alerts = []

        # Check logic generation limits
        total_generated = self.metrics.get("logic_generation", {}).get(
            "total_generated", 0
        )
        if total_generated >= self.max_generated_logics:
            alerts.append(
                {
                    "type": "limit_reached",
                    "severity": "high",
                    "message": f"Maximum generated logics limit reached: {total_generated}/{self.max_generated_logics}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check quality scores
        logic_stats = self.metrics.get("logic_generation", {})
        success_rate = logic_stats.get("success_rate", 0.0)
        if success_rate < self.quality_threshold:
            alerts.append(
                {
                    "type": "low_quality",
                    "severity": "medium",
                    "message": f"Low logic generation success rate: {success_rate:.2f}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check test coverage
        test_stats = self.metrics.get("test_generation", {})
        avg_coverage = test_stats.get("average_coverage", 0.0)
        if avg_coverage < 0.6:
            alerts.append(
                {
                    "type": "low_test_coverage",
                    "severity": "medium",
                    "message": f"Low average test coverage: {avg_coverage:.2f}",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check for anomalies
        pattern_stats = self.metrics.get("pattern_detection", {})
        recent_activity = pattern_stats.get("recent_activity", 0)
        if recent_activity > 100:  # High activity threshold
            alerts.append(
                {
                    "type": "high_activity",
                    "severity": "low",
                    "message": f"High pattern detection activity: {recent_activity} patterns",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        self.alerts = alerts

        # Log alerts
        for alert in alerts:
            logger.warning(f"Alert: {alert['message']}")
            write_event("auto_expansion_alert", alert)

    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health."""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())

            health = {
                "cpu_usage": process.cpu_percent(),
                "memory_usage": process.memory_info().rss,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": psutil.disk_usage("/").percent,
                "load_average": psutil.getloadavg(),
                "status": "healthy",
            }

            # Determine health status
            if health["cpu_usage"] > 80:
                health["status"] = "warning"
            if health["memory_usage"] > self.memory_threshold:
                health["status"] = "warning"
            if health["disk_usage"] > 90:
                health["status"] = "critical"

            return health

        except Exception as e:
            logger.error(f"Error assessing system health: {e}")
            return {"status": "unknown", "error": str(e)}

    def _validate_system_health(self) -> None:
        """Validate system health and take action if needed."""
        health = self.metrics.get("system_health", {})

        if health.get("status") == "critical":
            logger.critical("System health is critical - stopping auto-expansion")
            self._emergency_stop()
        elif health.get("status") == "warning":
            logger.warning("System health warning - reducing auto-expansion activity")
            self._reduce_activity()

    def _emergency_stop(self) -> None:
        """Emergency stop of auto-expansion activities."""
        logger.critical(
            "EMERGENCY STOP: Disabling auto-expansion due to system health issues"
        )

        # Disable pattern detection
        self.pattern_detector.similarity_threshold = 1.0  # Effectively disable

        # Disable logic generation
        self.logic_generator.quality_threshold = 1.0  # Effectively disable

        # Record emergency stop
        write_event(
            "auto_expansion_emergency_stop",
            {
                "timestamp": datetime.now().isoformat(),
                "reason": "system_health_critical",
                "metrics": self.metrics,
            },
        )

    def _reduce_activity(self) -> None:
        """Reduce auto-expansion activity due to system warnings."""
        logger.warning("Reducing auto-expansion activity due to system warnings")

        # Increase thresholds to reduce activity
        self.pattern_detector.similarity_threshold = min(
            1.0, self.pattern_detector.similarity_threshold + 0.1
        )
        self.logic_generator.quality_threshold = min(
            1.0, self.logic_generator.quality_threshold + 0.1
        )

        # Record activity reduction
        write_event(
            "auto_expansion_reduced_activity",
            {
                "timestamp": datetime.now().isoformat(),
                "reason": "system_health_warning",
                "new_thresholds": {
                    "similarity_threshold": self.pattern_detector.similarity_threshold,
                    "quality_threshold": self.logic_generator.quality_threshold,
                },
            },
        )

    def validate_generated_logic(self, logic: GeneratedLogic) -> Dict[str, Any]:
        """Validate a generated logic and provide recommendations."""
        validation_result = {
            "logic_id": logic.logic_id,
            "validation_passed": True,
            "quality_score": logic.quality_score,
            "complexity_score": logic.complexity_score,
            "issues": [],
            "recommendations": [],
            "requires_human_review": False,
        }

        # Check quality threshold
        if logic.quality_score < self.quality_threshold:
            validation_result["validation_passed"] = False
            validation_result["issues"].append(
                f"Quality score below threshold: {logic.quality_score:.2f}"
            )
            validation_result["requires_human_review"] = True

        # Check complexity
        if logic.complexity_score > 0.8:
            validation_result["issues"].append(
                f"High complexity: {logic.complexity_score:.2f}"
            )
            validation_result["recommendations"].append(
                "Consider simplifying the logic"
            )

        # Check for rollback
        if logic.quality_score < self.rollback_threshold:
            validation_result["issues"].append("Quality score below rollback threshold")
            validation_result["recommendations"].append(
                "Consider rolling back this logic"
            )

        # Check validation results
        validation_alerts = logic.validation_results.get("alerts", [])
        if validation_alerts:
            validation_result["issues"].extend(validation_alerts)
            validation_result["requires_human_review"] = True

        # Generate recommendations
        if logic.quality_score < 0.5:
            validation_result["recommendations"].append(
                "Consider manual review and refinement"
            )

        if logic.complexity_score > 0.7:
            validation_result["recommendations"].append(
                "Consider breaking down into smaller functions"
            )

        return validation_result

    def approve_generated_logic(
        self, logic_id: str, approved_by: str, comments: str = ""
    ) -> bool:
        """Approve a generated logic for activation."""
        try:
            # Find the logic
            generated_logics = self.logic_generator.get_generated_logics()
            logic = next((l for l in generated_logics if l.logic_id == logic_id), None)

            if not logic:
                logger.error(f"Logic {logic_id} not found")
                return False

            # Validate before approval
            validation = self.validate_generated_logic(logic)
            if not validation["validation_passed"]:
                logger.warning(
                    f"Logic {logic_id} failed validation but proceeding with approval"
                )

            # Update status
            logic.status = "active"

            # Record approval
            write_event(
                "logic_approved",
                {
                    "logic_id": logic_id,
                    "approved_by": approved_by,
                    "comments": comments,
                    "validation_result": validation,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f"Logic {logic_id} approved by {approved_by}")
            return True

        except Exception as e:
            logger.error(f"Error approving logic {logic_id}: {e}")
            return False

    def rollback_generated_logic(
        self, logic_id: str, reason: str, rolled_back_by: str
    ) -> bool:
        """Rollback a generated logic."""
        try:
            # Find the logic
            generated_logics = self.logic_generator.get_generated_logics()
            logic = next((l for l in generated_logics if l.logic_id == logic_id), None)

            if not logic:
                logger.error(f"Logic {logic_id} not found")
                return False

            # Update status
            logic.status = "deprecated"

            # Record rollback
            write_event(
                "logic_rolled_back",
                {
                    "logic_id": logic_id,
                    "reason": reason,
                    "rolled_back_by": rolled_back_by,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f"Logic {logic_id} rolled back by {rolled_back_by}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Error rolling back logic {logic_id}: {e}")
            return False

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for monitoring interface."""
        return {
            "metrics": self.metrics,
            "alerts": self.alerts,
            "generated_logics": [
                {
                    "logic_id": logic.logic_id,
                    "logic_name": logic.logic_name,
                    "quality_score": logic.quality_score,
                    "status": logic.status,
                    "creation_date": logic.creation_date.isoformat(),
                }
                for logic in self.logic_generator.get_generated_logics()
            ],
            "pending_approvals": [
                {
                    "logic_id": logic.logic_id,
                    "logic_name": logic.logic_name,
                    "quality_score": logic.quality_score,
                    "creation_date": logic.creation_date.isoformat(),
                }
                for logic in self.logic_generator.get_generated_logics("validated")
            ],
            "system_status": {
                "monitoring_active": self.monitoring_active,
                "health_status": self.metrics.get("system_health", {}).get(
                    "status", "unknown"
                ),
                "total_alerts": len(self.alerts),
            },
        }

    def generate_report(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate a comprehensive report of auto-expansion activities."""
        report = {
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "details": {},
        }

        if report_type == "comprehensive":
            # Pattern detection summary
            pattern_stats = self.pattern_detector.get_statistics()
            report["summary"]["pattern_detection"] = {
                "total_patterns": pattern_stats.get("total_patterns", 0),
                "recent_activity": pattern_stats.get("recent_activity", 0),
                "average_confidence": pattern_stats.get("average_confidence", 0.0),
            }

            # Usage tracking summary
            usage_stats = self.usage_tracker.get_statistics()
            report["summary"]["usage_tracking"] = {
                "total_logics": usage_stats.get("total_logics", 0),
                "total_calls": usage_stats.get("total_calls", 0),
                "success_rate": usage_stats.get("success_rate", 0.0),
            }

            # Logic generation summary
            logic_stats = self.logic_generator.get_statistics()
            report["summary"]["logic_generation"] = {
                "total_generated": logic_stats.get("total_generated", 0),
                "success_rate": logic_stats.get("success_rate", 0.0),
                "status_distribution": logic_stats.get("status_distribution", {}),
            }

            # Test generation summary
            test_stats = self.test_generator.get_statistics()
            report["summary"]["test_generation"] = {
                "total_generated": test_stats.get("total_generated", 0),
                "success_rate": test_stats.get("success_rate", 0.0),
                "average_coverage": test_stats.get("average_coverage", 0.0),
            }

            # System health
            report["summary"]["system_health"] = self.metrics.get("system_health", {})

            # Recent alerts
            report["summary"]["recent_alerts"] = (
                self.alerts[-10:] if self.alerts else []
            )

        elif report_type == "alerts":
            report["summary"]["alerts"] = self.alerts
            report["summary"]["alert_count"] = len(self.alerts)

        elif report_type == "performance":
            report["summary"]["performance_metrics"] = {
                "system_health": self.metrics.get("system_health", {}),
                "generation_stats": {
                    "logic_generation": self.logic_generator.get_statistics(),
                    "test_generation": self.test_generator.get_statistics(),
                },
            }

        return report


def main():
    """Main CLI interface for the auto-expansion monitor."""
    parser = argparse.ArgumentParser(description="Auto-Expansion Monitor Tool")
    parser.add_argument(
        "command",
        choices=["monitor", "validate", "approve", "rollback", "dashboard", "report"],
        help="Command to execute",
    )
    parser.add_argument("--logic-id", help="Logic ID for approve/rollback commands")
    parser.add_argument("--reason", help="Reason for rollback")
    parser.add_argument("--user", help="User performing the action")
    parser.add_argument("--comments", help="Comments for approval")
    parser.add_argument(
        "--report-type",
        choices=["comprehensive", "alerts", "performance"],
        default="comprehensive",
        help="Report type",
    )
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    monitor = AutoExpansionMonitor()

    try:
        if args.command == "monitor":
            print("Starting auto-expansion monitoring...")
            monitor.start_monitoring()

        elif args.command == "validate":
            if not args.logic_id:
                print("Error: --logic-id required for validate command")
                sys.exit(1)

            generated_logics = monitor.logic_generator.get_generated_logics()
            logic = next(
                (l for l in generated_logics if l.logic_id == args.logic_id), None
            )

            if not logic:
                print(f"Error: Logic {args.logic_id} not found")
                sys.exit(1)

            validation = monitor.validate_generated_logic(logic)
            print(json.dumps(validation, indent=2))

        elif args.command == "approve":
            if not args.logic_id or not args.user:
                print("Error: --logic-id and --user required for approve command")
                sys.exit(1)

            success = monitor.approve_generated_logic(
                args.logic_id, args.user, args.comments or ""
            )
            if success:
                print(f"Logic {args.logic_id} approved successfully")
            else:
                print(f"Failed to approve logic {args.logic_id}")
                sys.exit(1)

        elif args.command == "rollback":
            if not args.logic_id or not args.reason or not args.user:
                print(
                    "Error: --logic-id, --reason, and --user required for rollback command"
                )
                sys.exit(1)

            success = monitor.rollback_generated_logic(
                args.logic_id, args.reason, args.user
            )
            if success:
                print(f"Logic {args.logic_id} rolled back successfully")
            else:
                print(f"Failed to rollback logic {args.logic_id}")
                sys.exit(1)

        elif args.command == "dashboard":
            dashboard_data = monitor.get_dashboard_data()
            print(json.dumps(dashboard_data, indent=2))

        elif args.command == "report":
            report = monitor.generate_report(args.report_type)

            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report, f, indent=2)
                print(f"Report saved to {args.output}")
            else:
                print(json.dumps(report, indent=2))

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
