"""
DAG Execution Engine for Phase 3.2 Orchestration Enhancement

This module provides a comprehensive DAG execution engine with:
- Topological sorting and cycle detection
- Parallel execution where dependencies allow
- Execution state tracking and progress reporting
- Node dependency management
- Execution metrics and performance monitoring
- Retry logic and graceful degradation
- Partial failure tolerance
"""

from __future__ import annotations

import asyncio
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from helpers.obs import with_metrics
from helpers.history_store import log_with_deltas_and_anomalies


logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Node execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEGRADED = "degraded"
    SKIPPED = "skipped"


class ExecutionError(Exception):
    """Custom exception for execution errors."""

    pass


@dataclass
class NodeSpec:
    """Specification for a DAG node."""

    id: str
    import_path: str
    retries: int = 1
    backoff_s: float = 0.5
    timeout_s: float = 30.0
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    fallback_logic: Optional[str] = None
    required: bool = True
    parallel_group: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of node execution."""

    node_id: str
    status: NodeStatus
    result: Dict[str, Any]
    error: Optional[str] = None
    retry_count: int = 0
    execution_time: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Execution metrics and statistics."""

    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    retried_nodes: int = 0
    degraded_nodes: int = 0
    skipped_nodes: int = 0
    total_execution_time: float = 0.0
    parallel_execution_time: float = 0.0
    max_concurrent_nodes: int = 0
    avg_node_execution_time: float = 0.0
    success_rate: float = 0.0
    throughput: float = 0.0  # nodes per second


class DAGExecutionEngine:
    """
    Advanced DAG execution engine with comprehensive features.

    Features:
    - Topological sorting with cycle detection
    - Parallel execution with dependency management
    - Retry logic with exponential backoff
    - Graceful degradation and fallback logic
    - Execution state tracking and progress reporting
    - Performance monitoring and metrics collection
    - Partial failure tolerance
    """

    def __init__(
        self,
        max_workers: int = 4,
        enable_parallel: bool = True,
        enable_metrics: bool = True,
        enable_history: bool = True,
    ):
        self.max_workers = max_workers
        self.enable_parallel = enable_parallel
        self.enable_metrics = enable_metrics
        self.enable_history = enable_history

        # Execution state
        self.nodes: Dict[str, NodeSpec] = {}
        self.edges: List[Tuple[str, str]] = []
        self.node_status: Dict[str, NodeStatus] = {}
        self.node_results: Dict[str, ExecutionResult] = {}
        self.execution_order: List[str] = []

        # Performance tracking
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.metrics = ExecutionMetrics()

        # Threading
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None

        # Progress callback
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def add_node(self, node: NodeSpec) -> None:
        """Add a node to the DAG."""
        self.nodes[node.id] = node
        self.node_status[node.id] = NodeStatus.PENDING

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a dependency edge between nodes."""
        if from_node not in self.nodes or to_node not in self.nodes:
            raise ExecutionError(f"Invalid edge: {from_node} -> {to_node}")
        self.edges.append((from_node, to_node))

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set progress callback for execution updates."""
        self.progress_callback = callback

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the DAG using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []

        # Build adjacency list
        adj_list = defaultdict(list)
        for from_node, to_node in self.edges:
            adj_list[from_node].append(to_node)

        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Visit all neighbors
            for neighbor in adj_list[node]:
                dfs(neighbor, path.copy())

            rec_stack.remove(node)
            path.pop()

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    def _topological_sort(self) -> List[str]:
        """Perform topological sort of nodes."""
        # Build adjacency list and in-degree count
        adj_list = defaultdict(list)
        in_degree = {node_id: 0 for node_id in self.nodes}

        for from_node, to_node in self.edges:
            adj_list[from_node].append(to_node)
            in_degree[to_node] += 1

        # Kahn's algorithm
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            for neighbor in adj_list[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            raise ExecutionError("DAG contains cycles or disconnected nodes")

        return result

    def _get_ready_nodes(self, completed_nodes: Set[str]) -> List[str]:
        """Get nodes that are ready to execute (all dependencies satisfied)."""
        ready = []

        for node_id, node in self.nodes.items():
            if node_id in completed_nodes:
                continue

            if self.node_status[node_id] in [NodeStatus.PENDING, NodeStatus.RETRYING]:
                # Check if all dependencies are completed
                dependencies_satisfied = True
                for from_node, to_node in self.edges:
                    if to_node == node_id and from_node not in completed_nodes:
                        dependencies_satisfied = False
                        break

                if dependencies_satisfied:
                    ready.append(node_id)

        return ready

    def _import_handler(
        self, import_path: str
    ) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        """Import and return a handler function."""
        try:
            module_name = import_path
            module = __import__(module_name, fromlist=["handle"])
            return getattr(module, "handle")
        except (ModuleNotFoundError, ImportError, AttributeError) as e:
            error_msg = str(e)
            logger.error(f"Failed to import handler from {import_path}: {error_msg}")

            # Return a degraded handler
            def degraded_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
                raise RuntimeError(f"Module {import_path} not found: {error_msg}")

            return degraded_handler

    def _execute_node(
        self, node: NodeSpec, payload: Dict[str, Any], retry_count: int = 0
    ) -> ExecutionResult:
        """Execute a single node with retry logic."""
        start_time = time.time()
        node_id = node.id

        # Update status
        with self._lock:
            self.node_status[node_id] = NodeStatus.RUNNING

        if self.progress_callback:
            self.progress_callback(
                {"stage": "start", "node": node_id, "retry_count": retry_count}
            )

        try:
            # Import and execute handler
            handler = self._import_handler(node.import_path)
            result = handler(payload)

            end_time = time.time()
            execution_time = end_time - start_time

            # Success
            execution_result = ExecutionResult(
                node_id=node_id,
                status=NodeStatus.COMPLETED,
                result=result,
                retry_count=retry_count,
                execution_time=execution_time,
                start_time=start_time,
                end_time=end_time,
                metadata={"import_path": node.import_path},
            )

            with self._lock:
                self.node_status[node_id] = NodeStatus.COMPLETED

            if self.progress_callback:
                self.progress_callback(
                    {
                        "stage": "end",
                        "node": node_id,
                        "status": "completed",
                        "execution_time": execution_time,
                    }
                )

            return execution_result

        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            error_msg = str(e)

            # Check if we should retry
            if retry_count < node.retries:
                # Exponential backoff
                backoff_time = node.backoff_s * (2**retry_count)
                logger.warning(
                    f"Node {node_id} failed, retrying in {backoff_time}s: {error_msg}"
                )

                with self._lock:
                    self.node_status[node_id] = NodeStatus.RETRYING

                if self.progress_callback:
                    self.progress_callback(
                        {
                            "stage": "retry",
                            "node": node_id,
                            "retry_count": retry_count + 1,
                            "backoff_time": backoff_time,
                        }
                    )

                time.sleep(backoff_time)
                return self._execute_node(node, payload, retry_count + 1)

            # Check if we have fallback logic
            if node.fallback_logic:
                logger.info(
                    f"Node {node_id} failed, trying fallback logic: {node.fallback_logic}"
                )
                try:
                    fallback_handler = self._import_handler(node.fallback_logic)
                    result = fallback_handler(payload)

                    execution_result = ExecutionResult(
                        node_id=node_id,
                        status=NodeStatus.DEGRADED,
                        result=result,
                        error=error_msg,
                        retry_count=retry_count,
                        execution_time=execution_time,
                        start_time=start_time,
                        end_time=end_time,
                        metadata={
                            "import_path": node.import_path,
                            "fallback_logic": node.fallback_logic,
                            "degraded": True,
                        },
                    )

                    with self._lock:
                        self.node_status[node_id] = NodeStatus.DEGRADED

                    if self.progress_callback:
                        self.progress_callback(
                            {
                                "stage": "end",
                                "node": node_id,
                                "status": "degraded",
                                "fallback_logic": node.fallback_logic,
                            }
                        )

                    return execution_result

                except Exception as fallback_error:
                    logger.error(
                        f"Fallback logic also failed for {node_id}: {fallback_error}"
                    )

            # Final failure
            execution_result = ExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                result={
                    "result": {},
                    "provenance": {},
                    "confidence": 0.0,
                    "alerts": [
                        {"level": "error", "msg": f"{node_id} failed: {error_msg}"}
                    ],
                    "degraded": True,
                    "reason": "retries_exhausted",
                },
                error=error_msg,
                retry_count=retry_count,
                execution_time=execution_time,
                start_time=start_time,
                end_time=end_time,
                metadata={"import_path": node.import_path},
            )

            with self._lock:
                self.node_status[node_id] = NodeStatus.FAILED

            if self.progress_callback:
                self.progress_callback(
                    {
                        "stage": "end",
                        "node": node_id,
                        "status": "failed",
                        "error": error_msg,
                    }
                )

            return execution_result

    def _execute_parallel(
        self, ready_nodes: List[str], payload: Dict[str, Any]
    ) -> List[ExecutionResult]:
        """Execute nodes in parallel."""
        if not self.enable_parallel or len(ready_nodes) == 1:
            # Sequential execution
            results = []
            for node_id in ready_nodes:
                node = self.nodes[node_id]
                result = self._execute_node(node, payload)
                results.append(result)
            return results

        # Parallel execution
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for node_id in ready_nodes:
                node = self.nodes[node_id]
                future = executor.submit(self._execute_node, node, payload)
                futures[future] = node_id

            results = []
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    node_id = futures[future]
                    logger.error(
                        f"Unexpected error in parallel execution for {node_id}: {e}"
                    )
                    # Create failed result
                    failed_result = ExecutionResult(
                        node_id=node_id,
                        status=NodeStatus.FAILED,
                        result={
                            "result": {},
                            "provenance": {},
                            "confidence": 0.0,
                            "alerts": [
                                {"level": "error", "msg": f"Unexpected error: {str(e)}"}
                            ],
                            "degraded": True,
                            "reason": "unexpected_error",
                        },
                        error=str(e),
                    )
                    results.append(failed_result)

        return results

    @with_metrics("execution_engine.execute_dag")
    def execute(
        self,
        payload: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the DAG with comprehensive features.

        Args:
            payload: Input payload for all nodes
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with execution results, metrics, and status
        """
        if progress_callback:
            self.set_progress_callback(progress_callback)

        self.start_time = time.time()

        try:
            # Validate DAG
            if not self.nodes:
                raise ExecutionError("No nodes in DAG")

            # Detect cycles
            cycles = self._detect_cycles()
            if cycles:
                raise ExecutionError(f"DAG contains cycles: {cycles}")

            # Topological sort
            self.execution_order = self._topological_sort()

            # Initialize metrics
            self.metrics.total_nodes = len(self.nodes)

            # Execute nodes
            completed_nodes = set()
            failed_nodes = set()

            while len(completed_nodes) + len(failed_nodes) < len(self.nodes):
                ready_nodes = self._get_ready_nodes(completed_nodes)

                if not ready_nodes:
                    # Check for deadlock
                    remaining_nodes = (
                        set(self.nodes.keys()) - completed_nodes - failed_nodes
                    )
                    if remaining_nodes:
                        logger.warning(
                            f"Deadlock detected, remaining nodes: {remaining_nodes}"
                        )
                        # Mark non-required nodes as skipped
                        for node_id in remaining_nodes:
                            node = self.nodes[node_id]
                            if not node.required:
                                self.node_status[node_id] = NodeStatus.SKIPPED
                                self.node_results[node_id] = ExecutionResult(
                                    node_id=node_id,
                                    status=NodeStatus.SKIPPED,
                                    result={
                                        "result": {},
                                        "provenance": {},
                                        "confidence": 0.0,
                                        "alerts": [
                                            {
                                                "level": "warning",
                                                "msg": f"{node_id} skipped due to deadlock",
                                            }
                                        ],
                                        "degraded": True,
                                        "reason": "deadlock_skip",
                                    },
                                )
                                failed_nodes.add(node_id)
                            else:
                                # Mark as failed
                                self.node_status[node_id] = NodeStatus.FAILED
                                self.node_results[node_id] = ExecutionResult(
                                    node_id=node_id,
                                    status=NodeStatus.FAILED,
                                    result={
                                        "result": {},
                                        "provenance": {},
                                        "confidence": 0.0,
                                        "alerts": [
                                            {
                                                "level": "error",
                                                "msg": f"{node_id} failed due to deadlock",
                                            }
                                        ],
                                        "degraded": True,
                                        "reason": "deadlock_failure",
                                    },
                                )
                                failed_nodes.add(node_id)
                    break

                # Execute ready nodes
                results = self._execute_parallel(ready_nodes, payload)

                # Process results
                for result in results:
                    self.node_results[result.node_id] = result

                    if result.status == NodeStatus.COMPLETED:
                        completed_nodes.add(result.node_id)
                        self.metrics.completed_nodes += 1
                    elif result.status == NodeStatus.DEGRADED:
                        completed_nodes.add(result.node_id)
                        self.metrics.degraded_nodes += 1
                    elif result.status == NodeStatus.FAILED:
                        failed_nodes.add(result.node_id)
                        self.metrics.failed_nodes += 1
                    elif result.status == NodeStatus.SKIPPED:
                        failed_nodes.add(result.node_id)
                        self.metrics.skipped_nodes += 1

                    if result.retry_count > 0:
                        self.metrics.retried_nodes += 1

                # Update max concurrent nodes
                self.metrics.max_concurrent_nodes = max(
                    self.metrics.max_concurrent_nodes, len(ready_nodes)
                )

            # Calculate final metrics
            self.end_time = time.time()
            self.metrics.total_execution_time = self.end_time - self.start_time

            if self.metrics.completed_nodes > 0:
                total_time = sum(r.execution_time for r in self.node_results.values())
                self.metrics.avg_node_execution_time = (
                    total_time / self.metrics.completed_nodes
                )

            self.metrics.success_rate = (
                self.metrics.completed_nodes + self.metrics.degraded_nodes
            ) / self.metrics.total_nodes

            if self.metrics.total_execution_time > 0:
                self.metrics.throughput = (
                    self.metrics.total_nodes / self.metrics.total_execution_time
                )

            # Log execution history if enabled
            if self.enable_history:
                self._log_execution_history(payload)

            return {
                "nodes": list(self.nodes.keys()),
                "edges": self.edges,
                "execution_order": self.execution_order,
                "results": {
                    node_id: result.__dict__
                    for node_id, result in self.node_results.items()
                },
                "metrics": self.metrics.__dict__,
                "status": {
                    "completed": len(completed_nodes),
                    "failed": len(failed_nodes),
                    "total": len(self.nodes),
                    "success_rate": self.metrics.success_rate,
                },
            }

        except Exception as e:
            self.end_time = time.time()
            logger.error(f"DAG execution failed: {e}")
            raise ExecutionError(f"DAG execution failed: {e}")

    def _log_execution_history(self, payload: Dict[str, Any]) -> None:
        """Log execution history for analysis."""
        try:
            execution_summary = {
                "total_nodes": self.metrics.total_nodes,
                "completed_nodes": self.metrics.completed_nodes,
                "failed_nodes": self.metrics.failed_nodes,
                "success_rate": self.metrics.success_rate,
                "total_execution_time": self.metrics.total_execution_time,
                "execution_order": self.execution_order,
            }

            log_with_deltas_and_anomalies(
                "L-DAG-001",
                payload,
                execution_summary,
                {"engine": "dag_execution_engine"},
                period_key=payload.get("period"),
            )
        except Exception as e:
            logger.warning(f"Failed to log execution history: {e}")


# Convenience functions for backward compatibility
def run_dag(
    nodes: List[NodeSpec],
    edges: List[Tuple[str, str]],
    payload: Dict[str, Any],
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    Convenience function for running a DAG (backward compatibility).

    Args:
        nodes: List of node specifications
        edges: List of dependency edges
        payload: Input payload
        progress_cb: Progress callback
        max_workers: Maximum parallel workers

    Returns:
        Execution results
    """
    engine = DAGExecutionEngine(max_workers=max_workers)

    # Add nodes and edges
    for node in nodes:
        engine.add_node(node)

    for from_node, to_node in edges:
        engine.add_edge(from_node, to_node)

    # Execute
    return engine.execute(payload, progress_cb)
