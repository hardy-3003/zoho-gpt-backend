"""
Contract Shape Tests

Tests that verify contract dataclass shapes match expected snapshots.
Fails on any schema drift to enforce cross-phase compatibility.

Task P1.2.1 — Contract dataclasses & schema hash snapshots
"""

import json
import hashlib
import inspect
import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
import sys

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
        pytest.fail(f"Could not generate hash for {contract_class.__name__}: {e}")


def load_snapshot() -> Dict[str, Any]:
    """Load the contract snapshot file"""
    snapshot_path = project_root / "artifacts" / "contract_snapshots.json"

    if not snapshot_path.exists():
        pytest.skip(
            f"Contract snapshot not found at {snapshot_path}. Run 'just contract-snapshots' first."
        )

    try:
        with open(snapshot_path, "r") as f:
            return json.load(f)
    except Exception as e:
        pytest.fail(f"Could not load contract snapshot: {e}")


def test_contract_snapshots_exist():
    """Test that contract snapshots file exists"""
    snapshot_path = project_root / "artifacts" / "contract_snapshots.json"
    assert (
        snapshot_path.exists()
    ), f"Contract snapshot not found at {snapshot_path}. Run 'just contract-snapshots' first."


def test_snapshot_metadata():
    """Test that snapshot has required metadata"""
    snapshot = load_snapshot()

    required_fields = ["generated_at", "generator", "version", "total_contracts"]
    for field in required_fields:
        assert field in snapshot["metadata"], f"Missing metadata field: {field}"

    assert snapshot["metadata"]["generator"] == "tools/gen_contract_snapshots.py"
    assert snapshot["metadata"]["version"] == "1.0"
    assert isinstance(snapshot["metadata"]["total_contracts"], int)
    assert snapshot["metadata"]["total_contracts"] > 0


def test_all_contracts_in_snapshot():
    """Test that all current contracts are in the snapshot"""
    contracts = get_all_contract_classes()
    snapshot = load_snapshot()

    snapshot_contracts = snapshot.get("contracts", {})

    for contract_name in contracts:
        assert (
            contract_name in snapshot_contracts
        ), f"Contract {contract_name} not found in snapshot"


def test_no_extra_contracts_in_snapshot():
    """Test that snapshot doesn't contain contracts that no longer exist"""
    contracts = get_all_contract_classes()
    snapshot = load_snapshot()

    snapshot_contracts = snapshot.get("contracts", {})

    for contract_name in snapshot_contracts:
        assert (
            contract_name in contracts
        ), f"Snapshot contains non-existent contract: {contract_name}"


def test_contract_hashes_match():
    """Test that all contract hashes match the snapshot"""
    contracts = get_all_contract_classes()
    snapshot = load_snapshot()

    snapshot_contracts = snapshot.get("contracts", {})

    for contract_name, contract_class in contracts.items():
        if contract_name not in snapshot_contracts:
            pytest.fail(f"Contract {contract_name} not found in snapshot")

        expected_hash = snapshot_contracts[contract_name]["hash"]
        actual_hash = generate_contract_hash(contract_class)

        assert actual_hash == expected_hash, (
            f"Contract {contract_name} hash mismatch:\n"
            f"  Expected: {expected_hash}\n"
            f"  Actual:   {actual_hash}\n"
            f"  This indicates the contract structure has changed."
        )


def test_contract_field_counts_match():
    """Test that contract field counts match the snapshot"""
    contracts = get_all_contract_classes()
    snapshot = load_snapshot()

    snapshot_contracts = snapshot.get("contracts", {})

    for contract_name, contract_class in contracts.items():
        if contract_name not in snapshot_contracts:
            continue

        expected_fields = set(snapshot_contracts[contract_name]["fields"])
        actual_fields = set(contract_class.__dataclass_fields__.keys())

        assert actual_fields == expected_fields, (
            f"Contract {contract_name} field mismatch:\n"
            f"  Expected: {sorted(expected_fields)}\n"
            f"  Actual:   {sorted(actual_fields)}\n"
            f"  Missing:  {sorted(expected_fields - actual_fields)}\n"
            f"  Extra:    {sorted(actual_fields - expected_fields)}"
        )


def test_contract_field_types_match():
    """Test that contract field types match the snapshot"""
    contracts = get_all_contract_classes()
    snapshot = load_snapshot()

    snapshot_contracts = snapshot.get("contracts", {})

    for contract_name, contract_class in contracts.items():
        if contract_name not in snapshot_contracts:
            continue

        expected_types = snapshot_contracts[contract_name]["field_types"]
        actual_types = {
            field_name: str(field_info.type)
            for field_name, field_info in contract_class.__dataclass_fields__.items()
        }

        for field_name, expected_type in expected_types.items():
            if field_name in actual_types:
                actual_type = actual_types[field_name]
                # Normalize type strings for comparison
                expected_normalized = expected_type.replace("typing.", "").replace(
                    "surfaces.contracts.", ""
                )
                actual_normalized = actual_type.replace("typing.", "").replace(
                    "surfaces.contracts.", ""
                )

                assert actual_normalized == expected_normalized, (
                    f"Contract {contract_name}.{field_name} type mismatch:\n"
                    f"  Expected: {expected_type}\n"
                    f"  Actual:   {actual_type}"
                )


def test_contract_instantiation():
    """Test that all contracts can be instantiated with required values"""
    contracts = get_all_contract_classes()

    # Define minimal required values for contracts that need them
    required_values = {
        "Alert": {
            "code": "TEST_001",
            "severity": AlertSeverity.INFO,
            "message": "Test alert",
        },
        "LogicOutput": {"result": {"test": "data"}},
        "LogicMetadata": {"title": "Test Logic", "logic_id": "L-TEST"},
        "ExecuteRequest": {
            "logic_id": "L-TEST",
            "org_id": "test-org",
            "period": "2025-01",
        },
        "ExecuteResponse": {
            "logic_output": LogicOutput(result={"test": "data"}),
            "execution_time_ms": 100.0,
        },
        "OrchestratorPlanItem": {"logic_id": "L-TEST"},
        "OrchestratorPlan": {"plan_id": "test-plan"},
        "MCPSearchRequest": {
            "query": "test query",
            "org_id": "test-org",
            "period": "2025-01",
        },
        "MCPSearchResponse": {"plan": OrchestratorPlan(plan_id="test-plan")},
        "MCPFetchRequest": {"plan": OrchestratorPlan(plan_id="test-plan")},
        "MCPFetchResponse": {"result": OrchestratorOutput()},
        "SSEEvent": {"event_type": "test", "data": {"test": "data"}},
        "WebhookPayload": {
            "event_type": "test",
            "org_id": "test-org",
            "timestamp": datetime.utcnow(),
        },
        "CLICommand": {"command": "test"},
        "CLIResponse": {"success": True, "output": "test output"},
        "EvidenceNode": {"id": "test-id", "hash": "test-hash", "source": "test-source"},
        "RulePack": {"pack_id": "test-pack", "effective_from": "2025-01-01"},
        "ConsentObject": {
            "subject": "test-subject",
            "purpose": "test-purpose",
            "expires_at": datetime.utcnow(),
            "retention_days": 365,
        },
        "JournalEntryLine": {"account": "1000"},
        "JournalEntry": {"date": "2025-01-27"},
        "RatioImpactRequest": {
            "org_id": "test-org",
            "period": "2025-01",
            "proposed_entry": JournalEntry(date="2025-01-27"),
        },
        "RatioBreach": {"ratio": "test-ratio", "threshold": 1.0, "after": 0.8},
        "RatioSuggestion": {"title": "Test suggestion", "rationale": "Test rationale"},
        "RatioImpactReport": {
            # No required fields
        },
        "RatioImpactOutput": {"impact_report": RatioImpactReport()},
    }

    for contract_name, contract_class in contracts.items():
        try:
            if contract_name in required_values:
                # Use required values for contracts that need them
                instance = contract_class(**required_values[contract_name])
            else:
                # Try to instantiate with no arguments (using defaults)
                instance = contract_class()

            assert isinstance(
                instance, contract_class
            ), f"Failed to instantiate {contract_name}"
        except Exception as e:
            pytest.fail(f"Could not instantiate contract {contract_name}: {e}")


def test_contract_validation():
    """Test that contract validation helpers work"""
    from surfaces.contracts import validate_contract_structure

    # Test with a simple contract
    alert = Alert(code="TEST_001", severity=AlertSeverity.INFO, message="Test alert")

    assert validate_contract_structure(alert, Alert)
    assert not validate_contract_structure(alert, LogicOutput)


def test_contract_hash_deterministic():
    """Test that contract hashes are deterministic"""
    contracts = get_all_contract_classes()

    for contract_name, contract_class in contracts.items():
        hash1 = generate_contract_hash(contract_class)
        hash2 = generate_contract_hash(contract_class)

        assert hash1 == hash2, f"Contract {contract_name} hash is not deterministic"


def test_specific_contract_structures():
    """Test specific important contract structures"""

    # Test LogicOutput structure
    logic_output = LogicOutput(
        result={"test": "data"},
        provenance={"test": ["evidence://test"]},
        confidence=0.95,
        alerts=[],
        applied_rule_set=AppliedRuleSet(),
        explanation="Test explanation",
    )

    assert logic_output.result == {"test": "data"}
    assert logic_output.confidence == 0.95
    assert len(logic_output.alerts) == 0

    # Test Alert structure
    alert = Alert(
        code="TEST_ALERT",
        severity=AlertSeverity.WARN,
        message="Test warning",
        evidence=["evidence://test"],
        metadata={"source": "test"},
    )

    assert alert.code == "TEST_ALERT"
    assert alert.severity == AlertSeverity.WARN
    assert len(alert.evidence) == 1

    # Test JournalEntry structure
    je_line = JournalEntryLine(
        account="1000", dr=100.0, cr=0.0, meta={"vendor": "test"}
    )

    je = JournalEntry(
        date="2025-01-27", lines=[je_line], notes="Test entry", source="api"
    )

    assert je.date == "2025-01-27"
    assert len(je.lines) == 1
    assert je.lines[0].account == "1000"
    assert je.lines[0].dr == 100.0


def test_enum_values():
    """Test that enum values are as expected"""
    assert LogicCategory.STATIC.value == "Static"
    assert LogicCategory.DYNAMIC_REGULATION.value == "Dynamic(Regulation)"
    assert LogicCategory.DYNAMIC_PATTERNS.value == "Dynamic(Patterns)"
    assert LogicCategory.DYNAMIC_GROWTH.value == "Dynamic(Growth)"
    assert LogicCategory.DYNAMIC_BEHAVIOR.value == "Dynamic(Behavior)"

    assert AlertSeverity.INFO.value == "info"
    assert AlertSeverity.WARN.value == "warn"
    assert AlertSeverity.ERROR.value == "error"


def test_contract_imports():
    """Test that all contracts can be imported correctly"""
    # This test ensures that the __all__ export list is correct
    import surfaces.contracts as contracts_module

    expected_exports = [
        "LogicCategory",
        "AlertSeverity",
        "Alert",
        "AppliedRuleSet",
        "LogicOutput",
        "LogicMetadata",
        "ExecuteRequest",
        "ExecuteResponse",
        "OrchestratorPlanItem",
        "OrchestratorPlan",
        "OrchestratorOutput",
        "MCPSearchRequest",
        "MCPSearchResponse",
        "MCPFetchRequest",
        "MCPFetchResponse",
        "SSEEvent",
        "WebhookPayload",
        "CLICommand",
        "CLIResponse",
        "EvidenceNode",
        "RulePack",
        "ConsentObject",
        "JournalEntryLine",
        "JournalEntry",
        "RatioImpactRequest",
        "RatioBreach",
        "RatioSuggestion",
        "RatioImpactReport",
        "RatioImpactOutput",
        "validate_contract_structure",
        "get_contract_hash",
    ]

    for export_name in expected_exports:
        assert hasattr(contracts_module, export_name), f"Missing export: {export_name}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
