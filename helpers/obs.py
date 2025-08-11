from __future__ import annotations
import os, time, json, threading
from typing import Any, Dict, Callable

_LOCK = threading.Lock()
_ROOT = os.environ.get("DATA_DIR") or os.path.join(
    os.path.dirname(__file__), "..", "data"
)
_METRICS_DIR = os.path.join(_ROOT, "metrics")
os.makedirs(_METRICS_DIR, exist_ok=True)
_LOGS_DIR = os.path.join(_ROOT, "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)


def _metrics_path(name: str) -> str:
    return os.path.join(_METRICS_DIR, f"{name}.jsonl")


def _logs_path(name: str) -> str:
    return os.path.join(_LOGS_DIR, f"{name}.jsonl")


def emit_metric(stream: str, payload: Dict[str, Any]) -> None:
    with _LOCK, open(_metrics_path(stream), "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), **payload}, ensure_ascii=False) + "\n")


def emit_log(stream: str, payload: Dict[str, Any]) -> None:
    with _LOCK, open(_logs_path(stream), "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), **payload}, ensure_ascii=False) + "\n")


def with_metrics(name: str) -> Callable:
    """
    Decorator to capture runtime, exceptions, anomaly counts (if present),
    and basic success/failure taxonomy. Additive; doesn't alter outputs.
    """

    def deco(fn: Callable) -> Callable:
        def wrapped(*args, **kwargs):
            t0 = time.time()
            status = "ok"
            exc = None
            alerts_n = None
            try:
                out = fn(*args, **kwargs)
                if (
                    isinstance(out, dict)
                    and "alerts" in out
                    and isinstance(out["alerts"], list)
                ):
                    alerts_n = len(out["alerts"])
                return out
            except Exception as e:
                status = "error"
                exc = repr(e)
                raise
            finally:
                dt = time.time() - t0
                emit_metric(
                    "runtime",
                    {
                        "name": name,
                        "duration_s": round(dt, 6),
                        "status": status,
                        "alerts": alerts_n,
                    },
                )
                if exc:
                    emit_log("errors", {"name": name, "error": exc})

        return wrapped

    return deco
