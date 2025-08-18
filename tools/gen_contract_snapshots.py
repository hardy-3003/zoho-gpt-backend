#!/usr/bin/env python3
"""
Contract Snapshot Generator

Generates deterministic hash snapshots of all contract dataclasses
for cross-phase compatibility enforcement.

Task P1.2.1 — Contract dataclasses & schema hash snapshots
"""

import json
import hashlib
import inspect
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from surfaces.contracts import (
    LogicCategory,
    AlertSeverity,
    Alert,
    AppliedRuleSet,
    LogicOutput,
    LogicMetadata,
    ExecuteRequest,
    ExecuteResponse,
    OrchestratorPlanItem,
    OrchestratorPlan,
    OrchestratorOutput,
    MCPSearchRequest,
    MCPSearchResponse,
    MCPFetchRequest,
    MCPFetchResponse,
    SSEEvent,
    WebhookPayload,
    CLICommand,
    CLIResponse,
    EvidenceNode,
    RulePack,
    ConsentObject,
    JournalEntryLine,
    JournalEntry,
    RatioImpactRequest,
    RatioBreach,
    RatioSuggestion,
    RatioImpactReport,
    RatioImpactOutput,
    get_contract_hash,
)


def get_all_contract_classes() -> Dict[str, type]:
    """Get all contract dataclasses from surfaces.contracts"""
    contracts = {}

    # Import the contracts module
    import surfaces.contracts as contracts_module

    # Find all dataclasses in the module
    for name, obj in inspect.getmembers(contracts_module):
        if inspect.isclass(obj) and hasattr(obj, "__dataclass_fields__"):
            contracts[name] = obj

    return contracts


def generate_contract_hash(contract_class: type) -> str:
    """Generate a deterministic hash for a contract class"""
    try:
        # Get the source code of the class
        source = inspect.getsource(contract_class)

        # Normalize the source (remove comments, normalize whitespace)
        lines = []
        for line in source.split("\n"):
            # Remove comments
            if "#" in line:
                line = line[: line.index("#")]
            # Strip whitespace
            line = line.strip()
            if line:
                lines.append(line)

        normalized_source = "\n".join(lines)

        # Create a hash of the normalized source
        return hashlib.sha256(normalized_source.encode("utf-8")).hexdigest()
    except Exception as e:
        print(f"Warning: Could not generate hash for {contract_class.__name__}: {e}")
        return ""


def generate_snapshot() -> Dict[str, Any]:
    """Generate a complete contract snapshot"""
    contracts = get_all_contract_classes()

    snapshot = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "generator": "tools/gen_contract_snapshots.py",
            "version": "1.0",
            "total_contracts": len(contracts),
        },
        "contracts": {},
    }

    for name, contract_class in contracts.items():
        try:
            hash_value = generate_contract_hash(contract_class)
            if hash_value:
                snapshot["contracts"][name] = {
                    "hash": hash_value,
                    "module": contract_class.__module__,
                    "fields": list(contract_class.__dataclass_fields__.keys()),
                    "field_types": {
                        field_name: str(field_info.type)
                        for field_name, field_info in contract_class.__dataclass_fields__.items()
                    },
                }
        except Exception as e:
            print(f"Error processing contract {name}: {e}")

    return snapshot


def save_snapshot(snapshot: Dict[str, Any], output_path: str) -> None:
    """Save the snapshot to a JSON file"""
    # Ensure the artifacts directory exists
    artifacts_dir = Path(output_path).parent
    artifacts_dir.mkdir(exist_ok=True)

    # Write the snapshot
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)

    print(f"Contract snapshot saved to: {output_path}")
    print(f"Total contracts: {snapshot['metadata']['total_contracts']}")


def load_existing_snapshot(snapshot_path: str) -> Dict[str, Any]:
    """Load an existing snapshot file"""
    if not os.path.exists(snapshot_path):
        return {}

    try:
        with open(snapshot_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load existing snapshot: {e}")
        return {}


def compare_snapshots(
    old_snapshot: Dict[str, Any], new_snapshot: Dict[str, Any]
) -> List[str]:
    """Compare two snapshots and return differences"""
    differences = []

    old_contracts = old_snapshot.get("contracts", {})
    new_contracts = new_snapshot.get("contracts", {})

    # Check for new contracts
    for contract_name in new_contracts:
        if contract_name not in old_contracts:
            differences.append(f"NEW: {contract_name}")
        else:
            old_hash = old_contracts[contract_name]["hash"]
            new_hash = new_contracts[contract_name]["hash"]
            if old_hash != new_hash:
                differences.append(
                    f"CHANGED: {contract_name} (hash: {old_hash[:8]} -> {new_hash[:8]})"
                )

    # Check for removed contracts
    for contract_name in old_contracts:
        if contract_name not in new_contracts:
            differences.append(f"REMOVED: {contract_name}")

    return differences


def main():
    """Main function"""
    output_path = project_root / "artifacts" / "contract_snapshots.json"

    print("Generating contract snapshots...")

    # Generate new snapshot
    new_snapshot = generate_snapshot()

    # Load existing snapshot for comparison
    old_snapshot = load_existing_snapshot(output_path)

    # Compare snapshots
    differences = compare_snapshots(old_snapshot, new_snapshot)

    if differences:
        print("\nContract changes detected:")
        for diff in differences:
            print(f"  - {diff}")
        print("\nThis will cause CI contract tests to fail.")
        print("Review changes and update tests if needed.")
    else:
        print("\nNo contract changes detected.")

    # Save the new snapshot
    save_snapshot(new_snapshot, output_path)

    # Print summary
    print(f"\nSnapshot summary:")
    print(f"  - Total contracts: {new_snapshot['metadata']['total_contracts']}")
    print(f"  - Generated at: {new_snapshot['metadata']['generated_at']}")
    print(f"  - Output file: {output_path}")

    # Exit with error code if there are differences (for CI)
    if differences:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
