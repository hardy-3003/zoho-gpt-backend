"""
Tests for the DAG Execution Engine (Phase 3.2.1)

Tests the comprehensive DAG execution engine with:
- Topological sorting and cycle detection
- Parallel execution where dependencies allow
- Execution state tracking and progress reporting
- Node dependency management
- Execution metrics and performance monitoring
- Retry logic and graceful degradation
- Partial failure tolerance
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from helpers.execution_engine import (
    DAGExecutionEngine,
    NodeSpec,
    NodeStatus,
    ExecutionResult,
    ExecutionError,
    run_dag,
)


class TestDAGExecutionEngine:
    """Test cases for DAGExecutionEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = DAGExecutionEngine(max_workers=2)
        self.sample_payload = {
            "org_id": "test_org",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
        }

    def test_add_node(self):
        """Test adding nodes to the DAG."""
        node = NodeSpec(
            id="test_node", import_path="test.module", retries=2, backoff_s=1.0
        )

        self.engine.add_node(node)

        assert "test_node" in self.engine.nodes
        assert self.engine.node_status["test_node"] == NodeStatus.PENDING
        assert self.engine.nodes["test_node"] == node

    def test_add_edge(self):
        """Test adding edges between nodes."""
        node1 = NodeSpec(id="node1", import_path="test.module1")
        node2 = NodeSpec(id="node2", import_path="test.module2")

        self.engine.add_node(node1)
        self.engine.add_node(node2)
        self.engine.add_edge("node1", "node2")

        assert ("node1", "node2") in self.engine.edges

    def test_add_edge_invalid_nodes(self):
        """Test adding edge with invalid nodes raises error."""
        with pytest.raises(ExecutionError, match="Invalid edge"):
            self.engine.add_edge("nonexistent1", "nonexistent2")

    def test_detect_cycles_no_cycles(self):
        """Test cycle detection with no cycles."""
        # Create a simple linear DAG: A -> B -> C
        nodes = [
            NodeSpec(id="A", import_path="test.A"),
            NodeSpec(id="B", import_path="test.B"),
            NodeSpec(id="C", import_path="test.C"),
        ]

        for node in nodes:
            self.engine.add_node(node)

        self.engine.add_edge("A", "B")
        self.engine.add_edge("B", "C")

        cycles = self.engine._detect_cycles()
        assert cycles == []

    def test_detect_cycles_with_cycle(self):
        """Test cycle detection with cycles."""
        # Create a cycle: A -> B -> C -> A
        nodes = [
            NodeSpec(id="A", import_path="test.A"),
            NodeSpec(id="B", import_path="test.B"),
            NodeSpec(id="C", import_path="test.C"),
        ]

        for node in nodes:
            self.engine.add_node(node)

        self.engine.add_edge("A", "B")
        self.engine.add_edge("B", "C")
        self.engine.add_edge("C", "A")

        cycles = self.engine._detect_cycles()
        assert len(cycles) > 0

    def test_topological_sort(self):
        """Test topological sorting."""
        # Create a DAG: A -> B -> C, A -> D
        nodes = [
            NodeSpec(id="A", import_path="test.A"),
            NodeSpec(id="B", import_path="test.B"),
            NodeSpec(id="C", import_path="test.C"),
            NodeSpec(id="D", import_path="test.D"),
        ]

        for node in nodes:
            self.engine.add_node(node)

        self.engine.add_edge("A", "B")
        self.engine.add_edge("B", "C")
        self.engine.add_edge("A", "D")

        order = self.engine._topological_sort()

        # A should come before B and D
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("D")
        # B should come before C
        assert order.index("B") < order.index("C")

    def test_topological_sort_with_cycle(self):
        """Test topological sort with cycle raises error."""
        # Create a cycle: A -> B -> A
        nodes = [
            NodeSpec(id="A", import_path="test.A"),
            NodeSpec(id="B", import_path="test.B"),
        ]

        for node in nodes:
            self.engine.add_node(node)

        self.engine.add_edge("A", "B")
        self.engine.add_edge("B", "A")

        with pytest.raises(ExecutionError, match="DAG contains cycles"):
            self.engine._topological_sort()

    def test_get_ready_nodes(self):
        """Test getting ready nodes."""
        # Create a DAG: A -> B -> C
        nodes = [
            NodeSpec(id="A", import_path="test.A"),
            NodeSpec(id="B", import_path="test.B"),
            NodeSpec(id="C", import_path="test.C"),
        ]

        for node in nodes:
            self.engine.add_node(node)

        self.engine.add_edge("A", "B")
        self.engine.add_edge("B", "C")

        # Initially, only A should be ready
        ready = self.engine._get_ready_nodes(set())
        assert ready == ["A"]

        # After A is completed, B should be ready
        ready = self.engine._get_ready_nodes({"A"})
        assert ready == ["B"]

        # After A and B are completed, C should be ready
        ready = self.engine._get_ready_nodes({"A", "B"})
        assert ready == ["C"]

    @patch("builtins.__import__")
    def test_import_handler_success(self, mock_import):
        """Test successful handler import."""
        mock_module = Mock()
        mock_handler = Mock()
        mock_module.handle = mock_handler
        mock_import.return_value = mock_module

        handler = self.engine._import_handler("test.module")
        assert handler == mock_handler

    @patch("builtins.__import__")
    def test_import_handler_failure(self, mock_import):
        """Test handler import failure returns degraded handler."""
        mock_import.side_effect = ImportError("Module not found")

        handler = self.engine._import_handler("test.module")

        # Should return a degraded handler
        assert callable(handler)

        # Degraded handler should raise an error when called
        with pytest.raises(RuntimeError, match="Module test.module not found"):
            handler({})

    @patch("builtins.__import__")
    def test_execute_node_success(self, mock_import):
        """Test successful node execution."""
        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.return_value = {"result": "success", "confidence": 0.9}
        mock_module.handle = mock_handler
        mock_import.return_value = mock_module

        node = NodeSpec(id="test_node", import_path="test.module")

        result = self.engine._execute_node(node, self.sample_payload)

        assert result.node_id == "test_node"
        assert result.status == NodeStatus.COMPLETED
        assert result.result == {"result": "success", "confidence": 0.9}
        assert result.error is None
        assert result.retry_count == 0
        assert result.execution_time > 0

    @patch("builtins.__import__")
    def test_execute_node_with_retry(self, mock_import):
        """Test node execution with retry logic."""
        mock_module = Mock()
        mock_handler = Mock()
        # First call fails, second call succeeds
        mock_handler.side_effect = [Exception("Temporary error"), {"result": "success"}]
        mock_module.handle = mock_handler
        mock_import.return_value = mock_module

        node = NodeSpec(id="test_node", import_path="test.module", retries=1)

        result = self.engine._execute_node(node, self.sample_payload)

        assert result.status == NodeStatus.COMPLETED
        assert result.retry_count == 1
        assert mock_handler.call_count == 2

    @patch("builtins.__import__")
    def test_execute_node_with_fallback(self, mock_import):
        """Test node execution with fallback logic."""
        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.side_effect = Exception("Permanent error")
        mock_module.handle = mock_handler

        mock_fallback_module = Mock()
        mock_fallback_handler = Mock()
        mock_fallback_handler.return_value = {"result": "fallback_success"}
        mock_fallback_module.handle = mock_fallback_handler

        # Mock import to return different modules for different paths
        def mock_import_side_effect(module_name, fromlist=None):
            if module_name == "test.module":
                return mock_module
            elif module_name == "fallback.module":
                return mock_fallback_module
            raise ImportError(f"Module {module_name} not found")

        mock_import.side_effect = mock_import_side_effect

        node = NodeSpec(
            id="test_node",
            import_path="test.module",
            retries=0,
            fallback_logic="fallback.module",
        )

        result = self.engine._execute_node(node, self.sample_payload)

        assert result.status == NodeStatus.DEGRADED
        assert result.result == {"result": "fallback_success"}
        assert "fallback_logic" in result.metadata

    @patch("builtins.__import__")
    def test_execute_node_final_failure(self, mock_import):
        """Test node execution with final failure."""
        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.side_effect = Exception("Permanent error")
        mock_module.handle = mock_handler
        mock_import.return_value = mock_module

        node = NodeSpec(id="test_node", import_path="test.module", retries=0)

        result = self.engine._execute_node(node, self.sample_payload)

        assert result.status == NodeStatus.FAILED
        assert result.error == "Permanent error"
        assert result.result["degraded"] is True
        assert result.result["reason"] == "retries_exhausted"

    def test_execute_empty_dag(self):
        """Test executing empty DAG raises error."""
        with pytest.raises(ExecutionError, match="No nodes in DAG"):
            self.engine.execute(self.sample_payload)

    def test_execute_dag_with_cycle(self):
        """Test executing DAG with cycle raises error."""
        # Create a cycle
        node1 = NodeSpec(id="A", import_path="test.A")
        node2 = NodeSpec(id="B", import_path="test.B")

        self.engine.add_node(node1)
        self.engine.add_node(node2)
        self.engine.add_edge("A", "B")
        self.engine.add_edge("B", "A")

        with pytest.raises(ExecutionError, match="DAG contains cycles"):
            self.engine.execute(self.sample_payload)

    def test_execute_simple_dag(self):
        """Test executing a simple DAG."""
        # Create a simple linear DAG: A -> B
        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.return_value = {"result": "success"}
        mock_module.handle = mock_handler

        with patch("builtins.__import__", return_value=mock_module):
            node1 = NodeSpec(id="A", import_path="test.A")
            node2 = NodeSpec(id="B", import_path="test.B")

            self.engine.add_node(node1)
            self.engine.add_node(node2)
            self.engine.add_edge("A", "B")

            result = self.engine.execute(self.sample_payload)

            assert "nodes" in result
            assert "edges" in result
            assert "execution_order" in result
            assert "results" in result
            assert "metrics" in result
            assert "status" in result

            assert result["nodes"] == ["A", "B"]
            assert result["edges"] == [("A", "B")]
            assert result["execution_order"] == ["A", "B"]
            assert result["status"]["completed"] == 2
            assert result["status"]["failed"] == 0
            assert result["status"]["success_rate"] == 1.0

    def test_execute_dag_with_partial_failure(self):
        """Test executing DAG with partial failures."""
        # Create a DAG where one node fails
        mock_module_a = Mock()
        mock_handler_a = Mock()
        mock_handler_a.return_value = {"result": "success"}
        mock_module_a.handle = mock_handler_a

        mock_module_b = Mock()
        mock_handler_b = Mock()
        mock_handler_b.side_effect = Exception("Node B failed")
        mock_module_b.handle = mock_handler_b

        def mock_import_side_effect(module_name, fromlist=None):
            if module_name == "test.A":
                return mock_module_a
            elif module_name == "test.B":
                return mock_module_b
            raise ImportError(f"Module {module_name} not found")

        with patch("builtins.__import__", side_effect=mock_import_side_effect):
            node1 = NodeSpec(id="A", import_path="test.A", retries=0)
            node2 = NodeSpec(id="B", import_path="test.B", retries=0)

            self.engine.add_node(node1)
            self.engine.add_node(node2)
            self.engine.add_edge("A", "B")

            result = self.engine.execute(self.sample_payload)

            assert result["status"]["completed"] == 1
            assert result["status"]["failed"] == 1
            assert result["status"]["success_rate"] == 0.5

    def test_progress_callback(self):
        """Test progress callback functionality."""
        progress_events = []

        def progress_callback(event):
            progress_events.append(event)

        # Create a simple DAG
        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.return_value = {"result": "success"}
        mock_module.handle = mock_handler

        with patch("builtins.__import__", return_value=mock_module):
            node = NodeSpec(id="A", import_path="test.A")
            self.engine.add_node(node)

            self.engine.execute(self.sample_payload, progress_callback)

            # Should have at least start and end events
            assert len(progress_events) >= 2
            assert any(event.get("stage") == "start" for event in progress_events)
            assert any(event.get("stage") == "end" for event in progress_events)


class TestRunDagConvenienceFunction:
    """Test cases for the run_dag convenience function."""

    def test_run_dag_simple(self):
        """Test the run_dag convenience function."""
        sample_payload = {"org_id": "test_org"}

        nodes = [
            NodeSpec(id="A", import_path="test.A"),
            NodeSpec(id="B", import_path="test.B"),
        ]

        edges = [("A", "B")]

        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.return_value = {"result": "success"}
        mock_module.handle = mock_handler

        with patch("builtins.__import__", return_value=mock_module):
            result = run_dag(nodes, edges, sample_payload)

            assert "nodes" in result
            assert "edges" in result
            assert "execution_order" in result
            assert "results" in result
            assert result["nodes"] == ["A", "B"]
            assert result["edges"] == [("A", "B")]

    def test_run_dag_with_progress_callback(self):
        """Test run_dag with progress callback."""
        sample_payload = {"org_id": "test_org"}
        progress_events = []

        def progress_callback(event):
            progress_events.append(event)

        nodes = [NodeSpec(id="A", import_path="test.A")]
        edges = []

        mock_module = Mock()
        mock_handler = Mock()
        mock_handler.return_value = {"result": "success"}
        mock_module.handle = mock_handler

        with patch("builtins.__import__", return_value=mock_module):
            result = run_dag(nodes, edges, sample_payload, progress_callback)

            assert len(progress_events) >= 2
            assert result["status"]["completed"] == 1


class TestNodeSpec:
    """Test cases for NodeSpec dataclass."""

    def test_node_spec_creation(self):
        """Test NodeSpec creation with default values."""
        node = NodeSpec(id="test", import_path="test.module")

        assert node.id == "test"
        assert node.import_path == "test.module"
        assert node.retries == 1
        assert node.backoff_s == 0.5
        assert node.timeout_s == 30.0
        assert node.priority == 0
        assert node.tags == []
        assert node.dependencies == []
        assert node.fallback_logic is None
        assert node.required is True
        assert node.parallel_group is None

    def test_node_spec_custom_values(self):
        """Test NodeSpec creation with custom values."""
        node = NodeSpec(
            id="test",
            import_path="test.module",
            retries=3,
            backoff_s=2.0,
            timeout_s=60.0,
            priority=5,
            tags=["tag1", "tag2"],
            dependencies=["dep1"],
            fallback_logic="fallback.module",
            required=False,
            parallel_group="group1",
        )

        assert node.retries == 3
        assert node.backoff_s == 2.0
        assert node.timeout_s == 60.0
        assert node.priority == 5
        assert node.tags == ["tag1", "tag2"]
        assert node.dependencies == ["dep1"]
        assert node.fallback_logic == "fallback.module"
        assert node.required is False
        assert node.parallel_group == "group1"


class TestExecutionResult:
    """Test cases for ExecutionResult dataclass."""

    def test_execution_result_creation(self):
        """Test ExecutionResult creation."""
        result = ExecutionResult(
            node_id="test_node",
            status=NodeStatus.COMPLETED,
            result={"data": "success"},
            error=None,
            retry_count=0,
            execution_time=1.5,
            start_time=100.0,
            end_time=101.5,
            metadata={"key": "value"},
        )

        assert result.node_id == "test_node"
        assert result.status == NodeStatus.COMPLETED
        assert result.result == {"data": "success"}
        assert result.error is None
        assert result.retry_count == 0
        assert result.execution_time == 1.5
        assert result.start_time == 100.0
        assert result.end_time == 101.5
        assert result.metadata == {"key": "value"}
