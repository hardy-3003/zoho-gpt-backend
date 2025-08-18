#!/usr/bin/env python3
"""
CLI Entrypoint for Zoho GPT Backend

Task P1.2.5 — /cli runner (contract-only)
Provides a Python CLI entrypoint `zgpt` with execute command for contract testing.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from surfaces.contracts import (
    ExecuteRequest,
    ExecuteResponse,
    LogicOutput,
    Alert,
    AlertSeverity,
    AppliedRuleSet,
)

from obs import metrics as obs_metrics
from obs import log as obs_log


def load_execute_request_from_json(plan_path: str) -> ExecuteRequest:
    """Load ExecuteRequest from JSON file"""
    try:
        with open(plan_path, "r") as f:
            data = json.load(f)
        return ExecuteRequest(**data)
    except FileNotFoundError:
        print(f"Error: Plan file '{plan_path}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in plan file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to load plan file: {e}", file=sys.stderr)
        sys.exit(1)


def build_execute_request_from_flags(
    logic_id: str,
    org_id: Optional[str] = None,
    period: Optional[str] = None,
    inputs: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> ExecuteRequest:
    """Build ExecuteRequest from command line flags"""
    if not org_id:
        org_id = "60020606976"  # Default test org ID
    if not period:
        period = "2025-01"  # Default test period

    return ExecuteRequest(
        logic_id=logic_id,
        org_id=org_id,
        period=period,
        inputs=inputs or {},
        context=context or {},
    )


def create_stubbed_response(request: ExecuteRequest) -> ExecuteResponse:
    """Create a stubbed ExecuteResponse for contract testing"""
    # Create a deterministic stub response
    logic_output = LogicOutput(
        result={
            "status": "stubbed",
            "logic_id": request.logic_id,
            "org_id": request.org_id,
            "period": request.period,
            "message": "CLI contract test response - no business logic executed",
        },
        provenance={
            "source": ["cli_contract_test"],
            "inputs": [
                f"logic_id={request.logic_id}",
                f"org_id={request.org_id}",
                f"period={request.period}",
            ],
        },
        confidence=1.0,
        alerts=[
            Alert(
                code="CLI_STUB",
                severity=AlertSeverity.INFO,
                message="This is a contract test response from CLI",
                evidence=["cli_execution", "contract_only"],
            )
        ],
        applied_rule_set=AppliedRuleSet(),
        explanation="CLI contract test - deterministic stub response",
    )

    return ExecuteResponse(
        logic_output=logic_output,
        execution_time_ms=0.1,  # Deterministic stub time
        cache_hit=False,
        metadata={"source": "cli", "contract_test": True, "deterministic": True},
    )


def execute_command(args: argparse.Namespace) -> None:
    """Handle the execute command"""
    try:
        # Configure CLI log sink to stderr to avoid polluting stdout JSON
        def _cli_sink(payload: Dict[str, Any]) -> None:
            print(
                json.dumps(payload, separators=(",", ":")), file=sys.stderr, flush=True
            )

        obs_log.set_sink(_cli_sink)

        # Load or build ExecuteRequest
        if args.plan:
            request = load_execute_request_from_json(args.plan)
        else:
            if not args.logic_id:
                print(
                    "Error: --logic-id is required when not using --plan",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Parse inputs and context if provided
            inputs = {}
            if args.inputs:
                try:
                    inputs = json.loads(args.inputs)
                except json.JSONDecodeError:
                    print("Error: --inputs must be valid JSON", file=sys.stderr)
                    sys.exit(1)

            context = {}
            if args.context:
                try:
                    context = json.loads(args.context)
                except json.JSONDecodeError:
                    print("Error: --context must be valid JSON", file=sys.stderr)
                    sys.exit(1)

            request = build_execute_request_from_flags(
                logic_id=args.logic_id,
                org_id=args.org_id,
                period=args.period,
                inputs=inputs,
                context=context,
            )

        # Create stubbed response
        response = create_stubbed_response(request)

        # Output as JSON
        # Convert dataclass to dict properly
        response_dict = {
            "logic_output": {
                "result": response.logic_output.result,
                "provenance": response.logic_output.provenance,
                "confidence": response.logic_output.confidence,
                "alerts": [
                    {
                        "code": alert.code,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "evidence": alert.evidence,
                        "metadata": alert.metadata,
                    }
                    for alert in response.logic_output.alerts
                ],
                "applied_rule_set": {
                    "packs": response.logic_output.applied_rule_set.packs,
                    "effective_date_window": response.logic_output.applied_rule_set.effective_date_window,
                },
                "explanation": response.logic_output.explanation,
            },
            "execution_time_ms": response.execution_time_ms,
            "cache_hit": response.cache_hit,
            "metadata": response.metadata,
        }
        print(json.dumps(response_dict, indent=2))

        try:
            obs_metrics.inc("requests_total", {"surface": "cli"})
            obs_metrics.inc("exec_calls_total", {"logic": request.logic_id})
            obs_log.info(
                "cli_run_ok",
                attrs={"logic_id": request.logic_id},
                trace_id=(
                    request.context.get("trace_id")
                    if isinstance(request.context, dict)
                    else None
                ),
            )
        except Exception:
            pass

    except Exception as e:
        try:
            obs_metrics.inc("errors_total", {"surface": "cli"})
            obs_log.error("cli_run_error", attrs={"error": str(e)})
        except Exception:
            pass
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entrypoint"""
    parser = argparse.ArgumentParser(
        prog="zgpt",
        description="Zoho GPT Backend CLI - Contract Testing Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute with plan file
  zgpt execute --plan plan.json
  
  # Execute with flags
  zgpt execute --logic-id logic_001_profit_loss --org-id 60020606976 --period 2025-01
  
  # Execute with inputs and context
  zgpt execute --logic-id logic_001_profit_loss --inputs '{"include_details": true}' --context '{"source": "cli"}'
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Execute command
    execute_parser = subparsers.add_parser(
        "execute", help="Execute a logic module (contract testing only)"
    )

    # Plan file option
    execute_parser.add_argument(
        "--plan", type=str, help="Path to JSON file containing ExecuteRequest"
    )

    # Individual parameters (used when not using --plan)
    execute_parser.add_argument(
        "--logic-id", type=str, help="Logic module ID to execute"
    )
    execute_parser.add_argument(
        "--org-id", type=str, help="Organization ID (default: 60020606976)"
    )
    execute_parser.add_argument(
        "--period", type=str, help="Period in YYYY-MM format (default: 2025-01)"
    )
    execute_parser.add_argument(
        "--inputs", type=str, help="JSON string of inputs to pass to logic module"
    )
    execute_parser.add_argument(
        "--context", type=str, help="JSON string of context to pass to logic module"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "execute":
        execute_command(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
