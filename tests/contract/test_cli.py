"""
Contract Tests for CLI Interface

Task P1.2.5 — /cli runner (contract-only)
Verifies CLI contract compliance: exit codes, output parsing, determinism.
"""

import pytest
import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from surfaces.contracts import (
    ExecuteRequest,
    ExecuteResponse,
    LogicOutput,
    validate_contract_structure,
)


class TestCLIContract:
    """Test contract compliance for CLI interface"""

    def test_cli_help_exit_code(self):
        """Test that CLI help returns exit code 0"""
        result = subprocess.run(
            ["python3", "-m", "cli", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "zgpt" in result.stdout
        assert "execute" in result.stdout

    def test_cli_execute_help_exit_code(self):
        """Test that CLI execute help returns exit code 0"""
        result = subprocess.run(
            ["python3", "-m", "cli", "execute", "--help"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert "execute" in result.stdout
        assert "--plan" in result.stdout
        assert "--logic-id" in result.stdout

    def test_cli_execute_with_flags_exit_code_0(self):
        """Test that CLI execute with valid flags returns exit code 0"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--logic-id",
                "logic_001_profit_loss",
                "--org-id",
                "60020606976",
                "--period",
                "2025-01",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0
        assert result.stdout.strip()

    def test_cli_execute_missing_logic_id_exit_code_non_zero(self):
        """Test that CLI execute without logic-id returns non-zero exit code"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--org-id",
                "60020606976",
                "--period",
                "2025-01",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode != 0
        assert "Error" in result.stderr

    def test_cli_execute_with_plan_file_exit_code_0(self):
        """Test that CLI execute with valid plan file returns exit code 0"""
        # Create temporary plan file
        plan_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
            "inputs": {"include_details": True},
            "context": {"source": "cli_test"},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(plan_data, f)
            plan_path = f.name

        try:
            result = subprocess.run(
                ["python3", "-m", "cli", "execute", "--plan", plan_path],
                capture_output=True,
                text=True,
                cwd=project_root,
            )
            assert result.returncode == 0
            assert result.stdout.strip()
        finally:
            os.unlink(plan_path)

    def test_cli_execute_invalid_plan_file_exit_code_non_zero(self):
        """Test that CLI execute with invalid plan file returns non-zero exit code"""
        # Create temporary invalid plan file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            plan_path = f.name

        try:
            result = subprocess.run(
                ["python3", "-m", "cli", "execute", "--plan", plan_path],
                capture_output=True,
                text=True,
                cwd=project_root,
            )
            assert result.returncode != 0
            assert "Error" in result.stderr
        finally:
            os.unlink(plan_path)

    def test_cli_execute_nonexistent_plan_file_exit_code_non_zero(self):
        """Test that CLI execute with nonexistent plan file returns non-zero exit code"""
        result = subprocess.run(
            ["python3", "-m", "cli", "execute", "--plan", "nonexistent.json"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode != 0
        assert "Error" in result.stderr
        assert "not found" in result.stderr

    def test_cli_execute_output_parses_as_execute_response(self):
        """Test that CLI output parses as ExecuteResponse shape"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--logic-id",
                "logic_001_profit_loss",
                "--org-id",
                "60020606976",
                "--period",
                "2025-01",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0

        # Parse output as JSON
        try:
            output_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail("CLI output is not valid JSON")

        # Validate ExecuteResponse structure
        assert "logic_output" in output_data
        assert "execution_time_ms" in output_data
        assert "cache_hit" in output_data
        assert "metadata" in output_data

        # Validate logic_output structure
        logic_output = output_data["logic_output"]
        assert "result" in logic_output
        assert "provenance" in logic_output
        assert "confidence" in logic_output
        assert "alerts" in logic_output
        assert "applied_rule_set" in logic_output
        assert "explanation" in logic_output

    def test_cli_execute_deterministic_same_input(self):
        """Test that CLI produces same output for same input (determinism)"""
        cmd = [
            "python3",
            "-m",
            "cli",
            "execute",
            "--logic-id",
            "logic_001_profit_loss",
            "--org-id",
            "60020606976",
            "--period",
            "2025-01",
        ]

        # Run twice with same input
        result1 = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        result2 = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

        assert result1.returncode == 0
        assert result2.returncode == 0
        assert result1.stdout == result2.stdout

    def test_cli_execute_with_inputs_and_context(self):
        """Test that CLI handles inputs and context JSON correctly"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--logic-id",
                "logic_001_profit_loss",
                "--inputs",
                '{"include_details": true, "format": "summary"}',
                "--context",
                '{"source": "cli_test", "user": "test_user"}',
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0

        # Parse output
        output_data = json.loads(result.stdout)

        # Verify inputs and context are reflected in response
        result_data = output_data["logic_output"]["result"]
        assert result_data["logic_id"] == "logic_001_profit_loss"
        assert result_data["org_id"] == "60020606976"  # Default
        assert result_data["period"] == "2025-01"  # Default

    def test_cli_execute_invalid_json_inputs_exit_code_non_zero(self):
        """Test that CLI with invalid JSON inputs returns non-zero exit code"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--logic-id",
                "logic_001_profit_loss",
                "--inputs",
                '{"invalid": json}',
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode != 0
        assert "Error" in result.stderr

    def test_cli_execute_invalid_json_context_exit_code_non_zero(self):
        """Test that CLI with invalid JSON context returns non-zero exit code"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--logic-id",
                "logic_001_profit_loss",
                "--context",
                '{"invalid": json}',
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode != 0
        assert "Error" in result.stderr

    def test_cli_execute_unknown_command_exit_code_non_zero(self):
        """Test that CLI with unknown command returns non-zero exit code"""
        result = subprocess.run(
            ["python3", "-m", "cli", "unknown_command"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr

    def test_cli_execute_response_contract_structure(self):
        """Test that CLI response matches ExecuteResponse contract structure"""
        result = subprocess.run(
            [
                "python3",
                "-m",
                "cli",
                "execute",
                "--logic-id",
                "logic_001_profit_loss",
                "--org-id",
                "60020606976",
                "--period",
                "2025-01",
            ],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0

        # Parse and validate contract structure
        output_data = json.loads(result.stdout)

        # Create ExecuteResponse instance to validate structure
        response = ExecuteResponse(**output_data)

        # Verify contract validation passes
        assert validate_contract_structure(response, ExecuteResponse)

        # Verify specific contract requirements
        assert isinstance(
            response.logic_output, dict
        )  # CLI outputs dict, not LogicOutput instance
        assert isinstance(response.execution_time_ms, (int, float))
        assert isinstance(response.cache_hit, bool)
        assert isinstance(response.metadata, dict)

        # Verify logic_output contract requirements
        lo = response.logic_output
        assert isinstance(lo, dict)
        assert "result" in lo
        assert "provenance" in lo
        assert "confidence" in lo
        assert "alerts" in lo
        assert "applied_rule_set" in lo
        assert "explanation" in lo
        assert isinstance(lo["result"], dict)
        assert isinstance(lo["provenance"], dict)
        assert isinstance(lo["confidence"], (int, float))
        assert isinstance(lo["alerts"], list)
        assert isinstance(lo["applied_rule_set"], dict)
        assert lo["explanation"] is None or isinstance(lo["explanation"], str)
