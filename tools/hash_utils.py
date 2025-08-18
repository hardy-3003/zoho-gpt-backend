"""
Deterministic JSON canonicalization and hashing utilities.

Task P1.3.4 — Evidence Replay “Golden” Runner helpers

Rules:
- Canonical JSON must be deterministic across runs and platforms
- sort_keys=True, separators=(",", ":") to avoid whitespace variance
- Disallow NaN/Inf representations (allow_nan=False)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def _default_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    # Fall back to string representation as a last resort (stable for enums, etc.)
    return str(obj)


def to_canonical_json(data: Any) -> str:
    """Return a deterministic JSON string for the given Python object.

    - Keys are sorted
    - No extraneous whitespace
    - NaN/Inf are not allowed
    """
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_default_serializer,
    )


def sha256_hex(content: bytes | str) -> str:
    """Compute SHA256 hex digest of bytes or string input."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def canonical_sha256_of_obj(obj: Any) -> str:
    """Compute SHA256 hex of the canonical JSON of a Python object."""
    return sha256_hex(to_canonical_json(obj))


def write_pretty_json(path: str, obj: Any) -> None:
    """Write a human-friendly pretty-printed JSON file for debugging/diffs."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
