from contextlib import contextmanager
import time
import logging
import json
import os
import threading
from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid
import psutil
import statistics
from collections import defaultdict, deque

# Import SLI collection
try:
    from .sli import record_sli

    SLI_ENABLED = True
except ImportError:
    SLI_ENABLED = False

# Configuration
TELEMETRY_ENABLED = os.environ.get("TELEMETRY_ENABLED", "true").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
DEEP_METRICS_ENABLED = os.environ.get("DEEP_METRICS_ENABLED", "true").lower() == "true"
SLO_ENABLED = os.environ.get("SLO_ENABLED", "true").lower() == "true"

# Thread-local storage for context
_local = threading.local()

_log = logging.getLogger("telemetry")

# Redaction patterns for sensitive data
SENSITIVE_FIELDS = {
    "password",
    "token",
    "secret",
    "key",
    "auth",
    "credential",
    "ssn",
    "pan",
    "aadhar",
    "gstin",
    "account_number",
    "card_number",
}

# Deep metrics storage
_metrics_store = {
    "latency": defaultdict(lambda: deque(maxlen=1000)),  # Store last 1000 measurements
    "errors": defaultdict(int),
    "retries": defaultdict(int),
    "throughput": defaultdict(lambda: deque(maxlen=100)),
    "memory": defaultdict(lambda: deque(maxlen=100)),
    "cpu": defaultdict(lambda: deque(maxlen=100)),
}

# Metrics aggregation lock
_metrics_lock = threading.Lock()


def _redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields from telemetry data."""
    if not data:
        return data

    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        is_sensitive = any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS)

        if is_sensitive:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = _redact_sensitive_data(value)
        elif isinstance(value, list):
            redacted[key] = [
                _redact_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value

    return redacted


def _get_current_context() -> Dict[str, Any]:
    """Get current telemetry context from thread-local storage."""
    if not hasattr(_local, "context"):
        _local.context = {}
    return _local.context


def _set_context(**kwargs) -> None:
    """Set telemetry context for current thread."""
    if not hasattr(_local, "context"):
        _local.context = {}
    _local.context.update(kwargs)


def _clear_context() -> None:
    """Clear telemetry context for current thread."""
    if hasattr(_local, "context"):
        _local.context.clear()


def _get_system_metrics() -> Dict[str, float]:
    """Get current system metrics."""
    try:
        process = psutil.Process()
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
        }
    except Exception:
        return {"cpu_percent": 0.0, "memory_mb": 0.0, "memory_percent": 0.0}


def _calculate_percentiles(
    values: List[float], percentiles: List[float] = [50, 95, 99]
) -> Dict[str, float]:
    """Calculate percentiles from a list of values."""
    if not values:
        return {f"p{p}": 0.0 for p in percentiles}

    sorted_values = sorted(values)
    result = {}
    for p in percentiles:
        if p == 100:
            result[f"p{p}"] = sorted_values[-1]
        else:
            index = (p / 100) * (len(sorted_values) - 1)
            if index.is_integer():
                result[f"p{p}"] = sorted_values[int(index)]
            else:
                lower = sorted_values[int(index)]
                upper = sorted_values[int(index) + 1]
                result[f"p{p}"] = lower + (upper - lower) * (index - int(index))

    return result


def _store_deep_metric(
    metric_type: str, key: str, value: float, org_id: str = "", logic_id: str = ""
) -> None:
    """Store a deep metric for aggregation."""
    if not DEEP_METRICS_ENABLED:
        return

    try:
        with _metrics_lock:
            # Create composite key for breakdown
            composite_key = f"{org_id}:{logic_id}:{key}" if org_id and logic_id else key
            _metrics_store[metric_type][composite_key].append(value)
    except Exception:
        pass


def get_deep_metrics(
    org_id: str = "", logic_id: str = "", orchestrator_id: str = ""
) -> Dict[str, Any]:
    """Get aggregated deep metrics with breakdowns."""
    if not DEEP_METRICS_ENABLED:
        return {}

    try:
        with _metrics_lock:
            metrics = {}

            # Latency metrics with percentiles
            latency_metrics = {}
            for key, values in _metrics_store["latency"].items():
                if values:
                    latency_metrics[key] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                        **_calculate_percentiles(list(values)),
                    }
            metrics["latency"] = latency_metrics

            # Error taxonomy counts
            error_metrics = {}
            for key, count in _metrics_store["errors"].items():
                error_metrics[key] = count
            metrics["errors"] = error_metrics

            # Retry attempts
            retry_metrics = {}
            for key, count in _metrics_store["retries"].items():
                retry_metrics[key] = count
            metrics["retries"] = retry_metrics

            # Throughput metrics
            throughput_metrics = {}
            for key, values in _metrics_store["throughput"].items():
                if values:
                    throughput_metrics[key] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "total": sum(values),
                        **_calculate_percentiles(list(values)),
                    }
            metrics["throughput"] = throughput_metrics

            # Memory usage
            memory_metrics = {}
            for key, values in _metrics_store["memory"].items():
                if values:
                    memory_metrics[key] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "max": max(values),
                        "min": min(values),
                        **_calculate_percentiles(list(values)),
                    }
            metrics["memory"] = memory_metrics

            # CPU usage
            cpu_metrics = {}
            for key, values in _metrics_store["cpu"].items():
                if values:
                    cpu_metrics[key] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "max": max(values),
                        "min": min(values),
                        **_calculate_percentiles(list(values)),
                    }
            metrics["cpu"] = cpu_metrics

            return metrics
    except Exception:
        return {}


def incr(counter: str, tags: dict | None = None, n: int = 1) -> None:
    """Increment a counter metric."""
    if not TELEMETRY_ENABLED:
        return

    try:
        context = _get_current_context()
        event_data = {
            "ts": datetime.utcnow().isoformat(),
            "type": "counter",
            "name": counter,
            "value": n,
            "tags": _redact_sensitive_data(tags or {}),
            **context,
        }
        _log.info("telemetry.counter", extra=event_data)
    except Exception:
        pass


def event(name: str, data: dict | None = None) -> None:
    """Emit a structured event."""
    if not TELEMETRY_ENABLED:
        return

    try:
        context = _get_current_context()
        event_data = {
            "ts": datetime.utcnow().isoformat(),
            "type": "event",
            "name": name,
            "data": _redact_sensitive_data(data or {}),
            **context,
        }
        _log.info("telemetry.event", extra=event_data)
    except Exception:
        pass


@contextmanager
def timing(metric: str, tags: dict | None = None):
    """Context manager for timing metrics."""
    if not TELEMETRY_ENABLED:
        yield
        return

    start = time.perf_counter()
    system_start = _get_system_metrics()

    try:
        yield
    finally:
        dur_ms = (time.perf_counter() - start) * 1000.0
        system_end = _get_system_metrics()

        try:
            context = _get_current_context()
            org_id = context.get("org_id", "")
            logic_id = context.get("logic_id", "")

            # Store deep metrics
            _store_deep_metric("latency", metric, dur_ms, org_id, logic_id)
            _store_deep_metric(
                "cpu",
                metric,
                system_end["cpu_percent"] - system_start["cpu_percent"],
                org_id,
                logic_id,
            )
            _store_deep_metric(
                "memory",
                metric,
                system_end["memory_mb"] - system_start["memory_mb"],
                org_id,
                logic_id,
            )

            # Record SLI metrics if enabled
            if SLI_ENABLED and SLI_ENABLED:
                try:
                    dims = {"org_id": org_id, "logic_id": logic_id, "metric": metric}
                    record_sli("latency_ms", dur_ms, dims)
                    record_sli("success", 1, dims)
                    record_sli("total", 1, dims)
                except Exception:
                    pass  # Don't let SLI recording break telemetry

            event_data = {
                "ts": datetime.utcnow().isoformat(),
                "type": "timer",
                "name": metric,
                "duration_ms": round(dur_ms, 3),
                "tags": _redact_sensitive_data(tags or {}),
                **context,
            }
            _log.info("telemetry.timing", extra=event_data)
        except Exception:
            pass


@contextmanager
def span(span_name: str, **span_tags):
    """Context manager for telemetry spans with structured logging."""
    if not TELEMETRY_ENABLED:
        yield
        return

    span_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    start_perf = time.perf_counter()
    system_start = _get_system_metrics()

    # Set span context
    old_context = _get_current_context().copy()
    _set_context(span_id=span_id, span_name=span_name, **span_tags)

    try:
        # Log span start
        event_data = {
            "ts": start_time.isoformat(),
            "type": "span_start",
            "span_id": span_id,
            "span_name": span_name,
            "tags": _redact_sensitive_data(span_tags),
            **old_context,
        }
        _log.info("telemetry.span_start", extra=event_data)

        yield

        # Log span success
        end_time = datetime.utcnow()
        dur_ms = (time.perf_counter() - start_perf) * 1000.0
        system_end = _get_system_metrics()

        # Store deep metrics for span
        context = _get_current_context()
        org_id = context.get("org_id", "")
        logic_id = context.get("logic_id", "")
        _store_deep_metric("latency", span_name, dur_ms, org_id, logic_id)
        _store_deep_metric(
            "cpu",
            span_name,
            system_end["cpu_percent"] - system_start["cpu_percent"],
            org_id,
            logic_id,
        )
        _store_deep_metric(
            "memory",
            span_name,
            system_end["memory_mb"] - system_start["memory_mb"],
            org_id,
            logic_id,
        )

        # Record SLI metrics if enabled
        if SLI_ENABLED and SLI_ENABLED:
            try:
                dims = {"org_id": org_id, "logic_id": logic_id, "span_name": span_name}
                record_sli("latency_ms", dur_ms, dims)
                record_sli("success", 1, dims)
                record_sli("total", 1, dims)
            except Exception:
                pass  # Don't let SLI recording break telemetry

        event_data = {
            "ts": end_time.isoformat(),
            "type": "span_end",
            "span_id": span_id,
            "span_name": span_name,
            "duration_ms": round(dur_ms, 3),
            "status": "success",
            "tags": _redact_sensitive_data(span_tags),
            **old_context,
        }
        _log.info("telemetry.span_end", extra=event_data)

    except Exception as e:
        # Log span error
        end_time = datetime.utcnow()
        dur_ms = (time.perf_counter() - start_perf) * 1000.0
        system_end = _get_system_metrics()

        # Store error metrics
        context = _get_current_context()
        org_id = context.get("org_id", "")
        logic_id = context.get("logic_id", "")
        error_key = f"{span_name}:{type(e).__name__}"
        _store_deep_metric("errors", error_key, 1, org_id, logic_id)

        # Record SLI error metrics if enabled
        if SLI_ENABLED and SLI_ENABLED:
            try:
                dims = {"org_id": org_id, "logic_id": logic_id, "span_name": span_name}
                record_sli("error", 1, dims)
                record_sli("total", 1, dims)
            except Exception:
                pass  # Don't let SLI recording break telemetry

        event_data = {
            "ts": end_time.isoformat(),
            "type": "span_end",
            "span_id": span_id,
            "span_name": span_name,
            "duration_ms": round(dur_ms, 3),
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "tags": _redact_sensitive_data(span_tags),
            **old_context,
        }
        _log.error("telemetry.span_error", extra=event_data)
        raise
    finally:
        # Restore old context
        _clear_context()
        _set_context(**old_context)


def emit_logic_telemetry(
    logic_id: str,
    org_id: str,
    duration_ms: float,
    status: str,
    inputs_size: int = 0,
    outputs_size: int = 0,
    confidence: float = 0.0,
    alerts_count: int = 0,
    cache_hit: bool = False,
    provenance_keys: int = 0,
    error_taxonomy: str = "",
    retry_attempts: int = 0,
    **kwargs,
) -> None:
    """Emit structured telemetry for logic execution."""
    if not TELEMETRY_ENABLED:
        return

    try:
        context = _get_current_context()

        # Store deep metrics
        _store_deep_metric(
            "latency", f"logic:{logic_id}", duration_ms, org_id, logic_id
        )
        _store_deep_metric("throughput", f"logic:{logic_id}", 1, org_id, logic_id)

        if retry_attempts > 0:
            _store_deep_metric(
                "retries", f"logic:{logic_id}", retry_attempts, org_id, logic_id
            )

        if error_taxonomy:
            _store_deep_metric(
                "errors", f"logic:{logic_id}:{error_taxonomy}", 1, org_id, logic_id
            )

        event_data = {
            "ts": datetime.utcnow().isoformat(),
            "type": "logic_execution",
            "logic_id": logic_id,
            "org_id": org_id,
            "duration_ms": round(duration_ms, 3),
            "status": status,
            "inputs_size": inputs_size,
            "outputs_size": outputs_size,
            "confidence": round(confidence, 3),
            "alerts_count": alerts_count,
            "cache_hit": cache_hit,
            "provenance_keys": provenance_keys,
            "error_taxonomy": error_taxonomy,
            "retry_attempts": retry_attempts,
            **context,
            **kwargs,
        }
        _log.info("telemetry.logic", extra=event_data)
    except Exception:
        pass


def emit_orchestration_telemetry(
    run_id: str,
    dag_node_id: str,
    logic_id: str,
    duration_ms: float,
    status: str,
    deps: List[str] = None,
    attempt: int = 1,
    retry_backoff_ms: int = 0,
    **kwargs,
) -> None:
    """Emit structured telemetry for orchestration node execution."""
    if not TELEMETRY_ENABLED:
        return

    try:
        context = _get_current_context()
        org_id = context.get("org_id", "")

        # Store deep metrics
        _store_deep_metric(
            "latency", f"orchestrator:{dag_node_id}", duration_ms, org_id, logic_id
        )
        _store_deep_metric(
            "throughput", f"orchestrator:{dag_node_id}", 1, org_id, logic_id
        )

        if attempt > 1:
            _store_deep_metric(
                "retries", f"orchestrator:{dag_node_id}", attempt - 1, org_id, logic_id
            )

        event_data = {
            "ts": datetime.utcnow().isoformat(),
            "type": "orchestration_node",
            "run_id": run_id,
            "dag_node_id": dag_node_id,
            "logic_id": logic_id,
            "duration_ms": round(duration_ms, 3),
            "status": status,
            "deps": deps or [],
            "attempt": attempt,
            "retry_backoff_ms": retry_backoff_ms,
            **context,
            **kwargs,
        }
        _log.info("telemetry.orchestration", extra=event_data)
    except Exception:
        pass


def set_org_context(org_id: str) -> None:
    """Set organization context for telemetry."""
    _set_context(org_id=org_id)


def set_run_context(run_id: str) -> None:
    """Set run context for telemetry."""
    _set_context(run_id=run_id)


def set_dag_context(dag_node_id: str, deps: List[str] = None) -> None:
    """Set DAG context for telemetry."""
    _set_context(dag_node_id=dag_node_id, deps=deps or [])


def set_logic_context(logic_id: str) -> None:
    """Set logic context for telemetry."""
    _set_context(logic_id=logic_id)


def export_metrics(format: str = "json") -> str:
    """Export metrics in specified format."""
    if not DEEP_METRICS_ENABLED:
        return ""

    metrics = get_deep_metrics()

    if format.lower() == "json":
        return json.dumps(metrics, indent=2)
    elif format.lower() == "prometheus":
        # Convert to Prometheus format
        prometheus_lines = []
        for metric_type, metric_data in metrics.items():
            for key, values in metric_data.items():
                if isinstance(values, dict):
                    for stat, value in values.items():
                        prometheus_lines.append(
                            f'{metric_type}_{stat}{{key="{key}"}} {value}'
                        )
                else:
                    prometheus_lines.append(f'{metric_type}{{key="{key}"}} {values}')
        return "\n".join(prometheus_lines)
    else:
        return str(metrics)


def clear_metrics() -> None:
    """Clear all stored metrics."""
    if not DEEP_METRICS_ENABLED:
        return

    try:
        with _metrics_lock:
            for metric_type in _metrics_store:
                _metrics_store[metric_type].clear()
    except Exception:
        pass
