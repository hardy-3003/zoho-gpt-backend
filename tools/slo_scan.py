#!/usr/bin/env python3
"""
SLO Scanner CLI Tool

Evaluates Service Level Objectives, prints results, and optionally emits alerts.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Add the project root to the path
sys.path.insert(0, ".")

from helpers.sli import sli_snapshot
from helpers.slo import evaluate_slo, create_default_slos, SLOSpec, SLOResult
from helpers.alert_policies import evaluate_slo_alerts, send_alerts


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SLO Scanner - Evaluate Service Level Objectives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all SLOs for the last hour
  python tools/slo_scan.py --since 1h

  # Scan specific organization
  python tools/slo_scan.py --org demo --since 30m

  # Export results in JSON format
  python tools/slo_scan.py --export json --output results.json

  # Emit alerts for breached SLOs
  python tools/slo_scan.py --emit-alerts --dry-run

  # Check specific SLO types
  python tools/slo_scan.py --slo-types availability,latency --since 1h
        """,
    )

    parser.add_argument("--org", "-o", help="Organization ID to scan (default: all)")

    parser.add_argument(
        "--since",
        "-s",
        default="1h",
        help="Time window to scan (e.g., 30m, 1h, 7d) (default: 1h)",
    )

    parser.add_argument(
        "--slo-types",
        help="Comma-separated list of SLO types to scan (availability,latency,error_rate,throughput,anomaly_rate)",
    )

    parser.add_argument(
        "--export",
        "-e",
        choices=["json", "prometheus", "csv"],
        help="Export format for results",
    )

    parser.add_argument("--output", "-f", help="Output file (default: stdout)")

    parser.add_argument(
        "--emit-alerts", action="store_true", help="Emit alerts for breached SLOs"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (don't actually send alerts)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Quiet mode (minimal output)"
    )

    return parser.parse_args()


def parse_time_window(time_str: str) -> timedelta:
    """Parse time window string into timedelta."""
    time_str = time_str.lower()

    if time_str.endswith("m"):
        minutes = int(time_str[:-1])
        return timedelta(minutes=minutes)
    elif time_str.endswith("h"):
        hours = int(time_str[:-1])
        return timedelta(hours=hours)
    elif time_str.endswith("d"):
        days = int(time_str[:-1])
        return timedelta(days=days)
    else:
        # Default to hours
        return timedelta(hours=int(time_str))


def get_slos_to_scan(
    org_id: Optional[str] = None, slo_types: Optional[str] = None
) -> List[SLOSpec]:
    """Get SLOs to scan based on filters."""
    all_slos = create_default_slos(org_id)

    if not slo_types:
        return all_slos

    # Filter by SLO types
    type_list = [t.strip() for t in slo_types.split(",")]
    filtered_slos = []

    for slo in all_slos:
        if slo.slo_type.value in type_list:
            filtered_slos.append(slo)

    return filtered_slos


def evaluate_slos(slos: List[SLOSpec], snapshot=None) -> List[SLOResult]:
    """Evaluate a list of SLOs."""
    results = []

    for slo in slos:
        try:
            result = evaluate_slo(slo, snapshot)
            results.append(result)
        except Exception as e:
            print(f"Error evaluating SLO {slo.id}: {e}", file=sys.stderr)
            continue

    return results


def format_results(results: List[SLOResult], format_type: str = "text") -> str:
    """Format results in the specified format."""
    if format_type == "json":
        return format_json(results)
    elif format_type == "prometheus":
        return format_prometheus(results)
    elif format_type == "csv":
        return format_csv(results)
    else:
        return format_text(results)


def format_text(results: List[SLOResult]) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append("SLO Evaluation Results")
    lines.append("=" * 50)
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append(f"Total SLOs: {len(results)}")
    lines.append("")

    # Summary
    breached_count = sum(1 for r in results if r.is_breached)
    lines.append(
        f"Summary: {breached_count} breached, {len(results) - breached_count} compliant"
    )
    lines.append("")

    # Detailed results
    for result in results:
        status = "❌ BREACHED" if result.is_breached else "✅ COMPLIANT"
        lines.append(f"{result.spec.name} ({result.spec.id})")
        lines.append(f"  Status: {status}")
        lines.append(f"  Current: {result.current_value:.2f}")
        lines.append(f"  Target: {result.target_value:.2f}")
        lines.append(
            f"  Error Budget: {result.error_budget.error_budget_remaining:.1f}% remaining"
        )
        lines.append(f"  Burn Rate: {result.burn_rate.current_burn_rate:.3f}")

        if result.burn_rate.time_to_breach_days:
            lines.append(
                f"  Time to Breach: {result.burn_rate.time_to_breach_days:.1f} days"
            )

        if result.recommendations:
            lines.append("  Recommendations:")
            for rec in result.recommendations[:3]:  # Top 3
                lines.append(f"    - {rec}")

        lines.append("")

    return "\n".join(lines)


def format_json(results: List[SLOResult]) -> str:
    """Format results as JSON."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_slos": len(results),
        "breached_count": sum(1 for r in results if r.is_breached),
        "compliant_count": sum(1 for r in results if not r.is_breached),
        "results": [],
    }

    for result in results:
        result_dict = {
            "slo_id": result.spec.id,
            "slo_name": result.spec.name,
            "slo_type": result.spec.slo_type.value,
            "org_id": result.spec.org_id,
            "is_breached": result.is_breached,
            "current_value": result.current_value,
            "target_value": result.target_value,
            "error_budget": {
                "remaining": result.error_budget.error_budget_remaining,
                "consumed": result.error_budget.error_budget_consumed,
                "total_requests": result.error_budget.total_requests,
                "successful_requests": result.error_budget.successful_requests,
                "failed_requests": result.error_budget.failed_requests,
            },
            "burn_rate": {
                "current": result.burn_rate.current_burn_rate,
                "average": result.burn_rate.average_burn_rate,
                "trend": result.burn_rate.burn_rate_trend,
                "severity": result.burn_rate.severity.value,
                "time_to_breach_days": result.burn_rate.time_to_breach_days,
            },
            "recommendations": result.recommendations,
            "metadata": result.metadata,
        }
        output["results"].append(result_dict)

    return json.dumps(output, indent=2)


def format_prometheus(results: List[SLOResult]) -> str:
    """Format results as Prometheus metrics."""
    lines = []
    timestamp = int(time.time() * 1000)

    for result in results:
        # Basic SLO metrics
        org_label = f'org_id="{result.spec.org_id}"' if result.spec.org_id else ""
        slo_labels = (
            f'slo_id="{result.spec.id}",slo_type="{result.spec.slo_type.value}"'
        )
        if org_label:
            slo_labels = f"{org_label},{slo_labels}"

        lines.append(
            f"slo_current_value{{{slo_labels}}} {result.current_value} {timestamp}"
        )
        lines.append(
            f"slo_target_value{{{slo_labels}}} {result.target_value} {timestamp}"
        )
        lines.append(
            f"slo_is_breached{{{slo_labels}}} {1 if result.is_breached else 0} {timestamp}"
        )

        # Error budget metrics
        lines.append(
            f"slo_error_budget_remaining{{{slo_labels}}} {result.error_budget.error_budget_remaining} {timestamp}"
        )
        lines.append(
            f"slo_error_budget_consumed{{{slo_labels}}} {result.error_budget.error_budget_consumed} {timestamp}"
        )
        lines.append(
            f"slo_total_requests{{{slo_labels}}} {result.error_budget.total_requests} {timestamp}"
        )
        lines.append(
            f"slo_successful_requests{{{slo_labels}}} {result.error_budget.successful_requests} {timestamp}"
        )
        lines.append(
            f"slo_failed_requests{{{slo_labels}}} {result.error_budget.failed_requests} {timestamp}"
        )

        # Burn rate metrics
        lines.append(
            f"slo_burn_rate_current{{{slo_labels}}} {result.burn_rate.current_burn_rate} {timestamp}"
        )
        lines.append(
            f"slo_burn_rate_average{{{slo_labels}}} {result.burn_rate.average_burn_rate} {timestamp}"
        )
        lines.append(
            f"slo_burn_rate_severity{{{slo_labels}}} {result.burn_rate.severity.value} {timestamp}"
        )

        if result.burn_rate.time_to_breach_days:
            lines.append(
                f"slo_time_to_breach_days{{{slo_labels}}} {result.burn_rate.time_to_breach_days} {timestamp}"
            )

    return "\n".join(lines)


def format_csv(results: List[SLOResult]) -> str:
    """Format results as CSV."""
    lines = []

    # Header
    lines.append(
        "slo_id,slo_name,slo_type,org_id,is_breached,current_value,target_value,error_budget_remaining,error_budget_consumed,burn_rate_current,burn_rate_severity,time_to_breach_days"
    )

    # Data rows
    for result in results:
        time_to_breach = result.burn_rate.time_to_breach_days or ""
        org_id = result.spec.org_id or ""

        row = [
            result.spec.id,
            result.spec.name,
            result.spec.slo_type.value,
            org_id,
            "1" if result.is_breached else "0",
            f"{result.current_value:.2f}",
            f"{result.target_value:.2f}",
            f"{result.error_budget.error_budget_remaining:.1f}",
            f"{result.error_budget.error_budget_consumed:.1f}",
            f"{result.burn_rate.current_burn_rate:.3f}",
            result.burn_rate.severity.value,
            f"{time_to_breach:.1f}" if time_to_breach else "",
        ]
        lines.append(",".join(row))

    return "\n".join(lines)


def main():
    """Main function."""
    args = parse_args()

    try:
        # Parse time window
        time_window = parse_time_window(args.since)

        # Get SLOs to scan
        slos = get_slos_to_scan(args.org, args.slo_types)

        if not slos:
            print("No SLOs found matching the specified criteria.", file=sys.stderr)
            sys.exit(1)

        if args.verbose:
            print(
                f"Scanning {len(slos)} SLOs for the last {args.since}...",
                file=sys.stderr,
            )

        # Get SLI snapshot
        snapshot = sli_snapshot()

        # Evaluate SLOs
        results = evaluate_slos(slos, snapshot)

        if not results:
            print("No SLO evaluation results.", file=sys.stderr)
            sys.exit(1)

        # Format and output results
        output = format_results(results, args.export or "text")

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            if not args.quiet:
                print(f"Results written to {args.output}", file=sys.stderr)
        else:
            print(output)

        # Handle alerts
        if args.emit_alerts:
            if args.verbose:
                print("Evaluating SLO alerts...", file=sys.stderr)

            alert_events = evaluate_slo_alerts(results)

            if alert_events:
                if args.verbose:
                    print(f"Found {len(alert_events)} alert events", file=sys.stderr)

                if not args.dry_run:
                    alert_results = send_alerts(alert_events)
                    if args.verbose:
                        for channel, success in alert_results.items():
                            status = "✅" if success else "❌"
                            print(f"{status} {channel}", file=sys.stderr)
                else:
                    if not args.quiet:
                        print("DRY RUN: Would send alerts:", file=sys.stderr)
                        for event in alert_events:
                            print(
                                f"  {event.severity.value}: {event.title}",
                                file=sys.stderr,
                            )
            else:
                if args.verbose:
                    print("No alerts to send", file=sys.stderr)

        # Exit with appropriate code
        breached_count = sum(1 for r in results if r.is_breached)
        if breached_count > 0:
            sys.exit(1)  # Exit with error if any SLOs are breached
        else:
            sys.exit(0)  # Exit successfully if all SLOs are compliant

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
