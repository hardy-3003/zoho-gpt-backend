"""
In-process metrics counter registry (P1.4.2).

API:
- inc(name: str, labels: dict[str,str] = {})
- dump() -> dict (stable snapshot)

No external dependencies; pure Python.
"""

from __future__ import annotations

from typing import Dict, Tuple
from threading import Lock
from pathlib import Path
import json, os, tempfile

try:
    import fcntl  # type: ignore
except Exception:  # pragma: no cover
    fcntl = None  # type: ignore


_lock = Lock()
_counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = {}
_PERSIST_PATH = Path("data/metrics/counters.json")
_USE_PERSISTENCE = str(os.getenv("ZOHO_METRICS_PERSIST", "")).lower() in {
    "1",
    "true",
    "yes",
}
_PERSIST_READ_NAMES = {"requests_total", "exec_calls_total"}


def _normalize_labels(labels: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    # Sort for stable keys; cast values to str for consistency
    return tuple(sorted(((str(k), str(v)) for k, v in (labels or {}).items())))


def inc(name: str, labels: Dict[str, str] | None = None) -> None:
    key = (str(name), _normalize_labels(labels or {}))
    with _lock:
        _counters[key] = _counters.get(key, 0) + 1
    _persist_inc(str(name), {k: str(v) for k, v in (labels or {}).items()})


def dump() -> Dict[str, Dict[str, int]]:
    # Emit a stable dict: {name: {"label_kv_serialized": count, ...}, ...}
    snapshot: Dict[str, Dict[str, int]] = {}
    # Start with persisted counts, but only for whitelisted metric names
    for (name, labels_tuple), count in _persist_load().items():
        if name not in _PERSIST_READ_NAMES:
            continue
        label_str = (
            ",".join([f"{k}={v}" for k, v in labels_tuple]) if labels_tuple else ""
        )
        snapshot.setdefault(name, {})[label_str] = (
            snapshot.get(name, {}).get(label_str, 0) + count
        )
    # Add in-memory counts
    with _lock:
        for (name, labels_tuple), count in _counters.items():
            label_str = (
                ",".join([f"{k}={v}" for k, v in labels_tuple]) if labels_tuple else ""
            )
            snapshot.setdefault(name, {})[label_str] = (
                snapshot.get(name, {}).get(label_str, 0) + count
            )
    return snapshot


def _persist_load() -> Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int]:
    # Always attempt to read persisted counters if the file exists,
    # regardless of write persistence setting. This allows other
    # processes (e.g., CLI) to contribute metrics via the shared file.
    try:
        if not _PERSIST_PATH.exists():
            return {}
        data = json.loads(_PERSIST_PATH.read_text())
        out: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = {}
        for name, labels_map in (data or {}).items():
            for label_str, count in (labels_map or {}).items():
                labels_tuple: Tuple[Tuple[str, str], ...] = tuple(
                    tuple(p.split("=", 1)) for p in label_str.split(",") if p
                )
                out[(str(name), labels_tuple)] = int(count)
        return out
    except Exception:
        return {}


def _persist_inc(name: str, labels: Dict[str, str]) -> None:
    if not _USE_PERSISTENCE:
        return
    try:
        _PERSIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        label_str = (
            ",".join([f"{k}={v}" for k, v in sorted(labels.items())]) if labels else ""
        )
        if fcntl is not None:
            with open(_PERSIST_PATH, "a+") as fh:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                except Exception:
                    pass
                try:
                    fh.seek(0)
                    raw = fh.read()
                    data = json.loads(raw) if raw else {}
                except Exception:
                    data = {}
                bucket = data.get(name) or {}
                bucket[label_str] = int(bucket.get(label_str, 0)) + 1
                data[name] = bucket
                tmp_fd, tmp_path = tempfile.mkstemp(
                    dir=str(_PERSIST_PATH.parent), prefix="counters.", suffix=".json"
                )
                os.close(tmp_fd)
                with open(tmp_path, "w") as tf:
                    json.dump(data, tf, separators=(",", ":"))
                    tf.flush()
                    os.fsync(tf.fileno())
                os.replace(tmp_path, _PERSIST_PATH)
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except Exception:
                    pass
        else:
            # Fallback without file locks
            existing = _persist_load()
            snap: Dict[str, Dict[str, int]] = {}
            for (n, lbls), c in existing.items():
                ls = ",".join([f"{k}={v}" for k, v in lbls]) if lbls else ""
                snap.setdefault(n, {})[ls] = c
            snap.setdefault(name, {})[label_str] = (
                int(snap.get(name, {}).get(label_str, 0)) + 1
            )
            with open(_PERSIST_PATH, "w") as fh:
                json.dump(snap, fh, separators=(",", ":"))
                fh.flush()
    except Exception:
        # Best-effort only
        pass
