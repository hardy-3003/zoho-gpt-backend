from contextlib import contextmanager
import time
import logging

_log = logging.getLogger("telemetry")

def incr(counter: str, tags: dict | None = None, n: int = 1) -> None:
    try:
        _log.info("telemetry.incr", extra={"counter": counter, "n": n, "tags": tags or {}})
    except Exception:
        pass

def event(name: str, data: dict | None = None) -> None:
    try:
        _log.info("telemetry.event", extra={"event": name, "data": data or {}})
    except Exception:
        pass

@contextmanager
def timing(metric: str, tags: dict | None = None):
    start = time.perf_counter()
    try:
        yield
    finally:
        dur_ms = (time.perf_counter() - start) * 1000.0
        try:
            _log.info("telemetry.timing", extra={"metric": metric, "ms": round(dur_ms, 3), "tags": tags or {}})
        except Exception:
            pass
