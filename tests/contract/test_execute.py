"""
Contract Tests for /api/execute Endpoint

Task P1.2.2 — REST /api/execute (contract)
Verifies schema shape parity (request/response) and 200 status.
"""

import pytest
import json
from fastapi.testclient import TestClient
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from main import app
from surfaces.contracts import (
    ExecuteRequest,
    ExecuteResponse,
    LogicOutput,
    validate_contract_structure,
    get_contract_hash,
)

client = TestClient(app)


class TestExecuteEndpointContract:
    """Test contract compliance for /api/execute endpoint"""

    def test_execute_endpoint_exists(self):
        """Test that /api/execute endpoint is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        # Verify endpoint is documented in OpenAPI
        openapi_data = response.json()
        assert "/api/execute" in openapi_data["paths"]

    def test_execute_request_contract_shape(self):
        """Test that request matches ExecuteRequest contract"""
        # Valid request data
        request_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
            "inputs": {"include_details": True},
            "context": {"source": "api"},
        }

        # Create contract instance
        request = ExecuteRequest(**request_data)

        # Validate structure
        assert validate_contract_structure(request, ExecuteRequest)
        assert request.logic_id == "logic_001_profit_loss"
        assert request.org_id == "60020606976"
        assert request.period == "2025-01"

    def test_execute_response_contract_shape(self):
        """Test that response matches ExecuteResponse contract"""
        # Valid request
        request_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        response = client.post("/api/execute", json=request_data)

        # Check status code
        assert response.status_code == 200

        # Parse response
        response_data = response.json()

        # Validate response structure
        assert "logic_output" in response_data
        assert "execution_time_ms" in response_data
        assert "cache_hit" in response_data
        assert "metadata" in response_data

        # Validate logic_output structure
        logic_output = response_data["logic_output"]
        assert "result" in logic_output
        assert "provenance" in logic_output
        assert "confidence" in logic_output
        assert "alerts" in logic_output
        assert "applied_rule_set" in logic_output
        assert "explanation" in logic_output

    def test_execute_deterministic_response(self):
        """Test that responses are deterministic for same inputs"""
        request_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        # Make two identical requests
        response1 = client.post("/api/execute", json=request_data)
        response2 = client.post("/api/execute", json=request_data)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical (deterministic)
        assert data1["logic_output"]["result"] == data2["logic_output"]["result"]
        assert (
            data1["logic_output"]["provenance"] == data2["logic_output"]["provenance"]
        )
        assert (
            data1["logic_output"]["confidence"] == data2["logic_output"]["confidence"]
        )

    def test_execute_logic_001_specific_response(self):
        """Test specific response structure for logic_001"""
        request_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200

        data = response.json()
        result = data["logic_output"]["result"]

        # Check for expected P&L structure
        assert "totals" in result
        assert "sections" in result

        totals = result["totals"]
        assert "revenue" in totals
        assert "cogs" in totals
        assert "gross_profit" in totals
        assert "opex" in totals
        assert "ebit" in totals

        # All values should be numeric
        assert isinstance(totals["revenue"], (int, float))
        assert isinstance(totals["cogs"], (int, float))
        assert isinstance(totals["gross_profit"], (int, float))
        assert isinstance(totals["opex"], (int, float))
        assert isinstance(totals["ebit"], (int, float))

    def test_execute_logic_231_specific_response(self):
        """Test specific response structure for logic_231 (Ratio Impact Advisor)"""
        request_data = {
            "logic_id": "logic_231_ratio_impact_advisor",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200

        data = response.json()
        result = data["logic_output"]["result"]

        # Check for expected ratio impact structure
        assert "impact_report" in result

        impact_report = result["impact_report"]
        assert "before" in impact_report
        assert "after" in impact_report
        assert "deltas" in impact_report
        assert "breaches" in impact_report

        # Check ratio values
        before = impact_report["before"]
        assert "dscr" in before
        assert "icr" in before
        assert "current_ratio" in before
        assert "de_ratio" in before

        # All values should be numeric
        assert isinstance(before["dscr"], (int, float))
        assert isinstance(before["icr"], (int, float))
        assert isinstance(before["current_ratio"], (int, float))
        assert isinstance(before["de_ratio"], (int, float))

    def test_execute_error_handling(self):
        """Test error handling for invalid requests"""
        # Test missing required fields
        invalid_request = {
            "logic_id": "logic_001_profit_loss"
            # Missing org_id and period
        }

        response = client.post("/api/execute", json=invalid_request)
        assert response.status_code == 422  # Validation error

        # Test invalid logic_id
        invalid_logic_request = {
            "logic_id": "invalid_logic",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        response = client.post("/api/execute", json=invalid_logic_request)
        # Should still return 200 with stubbed response
        assert response.status_code == 200

    def test_execute_metadata_structure(self):
        """Test that metadata contains expected fields"""
        request_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200

        data = response.json()
        metadata = data["metadata"]

        assert "logic_id" in metadata
        assert "org_id" in metadata
        assert "period" in metadata
        assert "contract_version" in metadata

        assert metadata["logic_id"] == "logic_001_profit_loss"
        assert metadata["org_id"] == "60020606976"
        assert metadata["period"] == "2025-01"
        assert metadata["contract_version"] == "1.0"

    def test_execute_provenance_structure(self):
        """Test that provenance contains expected evidence nodes"""
        request_data = {
            "logic_id": "logic_001_profit_loss",
            "org_id": "60020606976",
            "period": "2025-01",
        }

        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200

        data = response.json()
        provenance = data["logic_output"]["provenance"]

        assert "source_data" in provenance
        assert "computation" in provenance
        assert "validation" in provenance

        # Check that evidence nodes are lists of strings
        assert isinstance(provenance["source_data"], list)
        assert isinstance(provenance["computation"], list)
        assert isinstance(provenance["validation"], list)

        # Check evidence node format
        for node in provenance["source_data"]:
            assert isinstance(node, str)
            assert node.startswith("evidence://")

    def test_execute_contract_hash_stability(self):
        """Test that contract hashes are stable"""
        # Get contract hashes
        execute_request_hash = get_contract_hash(ExecuteRequest)
        execute_response_hash = get_contract_hash(ExecuteResponse)
        logic_output_hash = get_contract_hash(LogicOutput)

        # Hashes should be deterministic
        assert len(execute_request_hash) == 16
        assert len(execute_response_hash) == 16
        assert len(logic_output_hash) == 16

        # Re-generate hashes to ensure stability
        assert get_contract_hash(ExecuteRequest) == execute_request_hash
        assert get_contract_hash(ExecuteResponse) == execute_response_hash
        assert get_contract_hash(LogicOutput) == logic_output_hash
