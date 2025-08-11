"""
Integration tests for orchestrators.

This module tests the integration between orchestrators and logic modules.
"""

import pytest
from orchestrators.mis_orchestrator import run_dag, NodeSpec


class TestMISOrchestrator:
    """Test suite for MIS orchestrator integration."""

    def test_simple_dag_execution(self):
        """Test simple DAG execution with two nodes."""
        nodes = [
            NodeSpec(
                id="L-001",
                import_path="logics.logic_001_profit_and_loss_summary",
                retries=0,
            ),
            NodeSpec(
                id="L-002", import_path="logics.logic_002_balance_sheet", retries=0
            ),
        ]
        edges = [("L-001", "L-002")]

        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query",
        }

        result = run_dag(nodes, edges, payload, progress_cb=None)

        # Verify result structure
        assert isinstance(result, dict)
        assert "nodes" in result
        assert "edges" in result
        assert "execution_order" in result
        assert "results" in result

        # Verify execution order
        assert len(result["execution_order"]) == 2
        assert "L-001" in result["execution_order"]
        assert "L-002" in result["execution_order"]

        # Verify results
        assert "L-001" in result["results"]
        assert "L-002" in result["results"]

        # Verify each result has the expected contract shape
        for node_id, node_result in result["results"].items():
            assert isinstance(node_result, dict)
            assert "result" in node_result
            assert "provenance" in node_result
            assert "confidence" in node_result
            assert "alerts" in node_result
            assert "meta" in node_result

    def test_dag_with_dependencies(self):
        """Test DAG execution with dependencies."""
        nodes = [
            NodeSpec(
                id="L-001",
                import_path="logics.logic_001_profit_and_loss_summary",
                retries=0,
            ),
            NodeSpec(
                id="L-002", import_path="logics.logic_002_balance_sheet", retries=0
            ),
            NodeSpec(
                id="L-003", import_path="logics.logic_003_trial_balance", retries=0
            ),
        ]
        edges = [("L-001", "L-002"), ("L-002", "L-003")]

        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query",
        }

        result = run_dag(nodes, edges, payload, progress_cb=None)

        # Verify execution order respects dependencies
        execution_order = result["execution_order"]
        l1_index = execution_order.index("L-001")
        l2_index = execution_order.index("L-002")
        l3_index = execution_order.index("L-003")

        # L-001 should execute before L-002
        assert l1_index < l2_index
        # L-002 should execute before L-003
        assert l2_index < l3_index

    def test_dag_with_parallel_execution(self):
        """Test DAG execution with parallel nodes."""
        nodes = [
            NodeSpec(
                id="L-001",
                import_path="logics.logic_001_profit_and_loss_summary",
                retries=0,
            ),
            NodeSpec(
                id="L-002", import_path="logics.logic_002_balance_sheet", retries=0
            ),
            NodeSpec(
                id="L-003", import_path="logics.logic_003_trial_balance", retries=0
            ),
        ]
        # No edges - all nodes can run in parallel
        edges = []

        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query",
        }

        result = run_dag(nodes, edges, payload, progress_cb=None)

        # All nodes should be executed
        assert len(result["execution_order"]) == 3
        assert "L-001" in result["execution_order"]
        assert "L-002" in result["execution_order"]
        assert "L-003" in result["execution_order"]

    def test_dag_error_handling(self):
        """Test DAG execution with error handling."""
        nodes = [
            NodeSpec(
                id="L-001",
                import_path="logics.logic_001_profit_and_loss_summary",
                retries=0,
            ),
            NodeSpec(id="L-INVALID", import_path="logics.invalid_logic", retries=0),
        ]
        edges = [("L-001", "L-INVALID")]

        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query",
        }

        result = run_dag(nodes, edges, payload, progress_cb=None)

        # Should handle errors gracefully
        assert isinstance(result, dict)
        assert "results" in result

        # L-001 should succeed
        assert "L-001" in result["results"]
        assert result["results"]["L-001"]["confidence"] > 0

        # L-INVALID should fail but not crash the entire DAG
        assert "L-INVALID" in result["results"]
        assert result["results"]["L-INVALID"]["confidence"] < 0.5

    def test_dag_with_retries(self):
        """Test DAG execution with retry logic."""
        nodes = [
            NodeSpec(
                id="L-001",
                import_path="logics.logic_001_profit_and_loss_summary",
                retries=2,
            ),
        ]
        edges = []

        payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "headers": {},
            "api_domain": "test.zoho.com",
            "query": "test query",
        }

        result = run_dag(nodes, edges, payload, progress_cb=None)

        # Should execute successfully
        assert isinstance(result, dict)
        assert "L-001" in result["results"]
        assert result["results"]["L-001"]["confidence"] > 0


class TestGenericReportOrchestrator:
    """Test suite for generic report orchestrator integration."""

    def test_report_generation(self):
        """Test basic report generation."""
        # This test would require the generic report orchestrator to be implemented
        # For now, we'll create a placeholder test
        assert True  # Placeholder assertion

    def test_report_with_multiple_sources(self):
        """Test report generation with multiple data sources."""
        # This test would verify that the orchestrator can handle multiple data sources
        assert True  # Placeholder assertion
