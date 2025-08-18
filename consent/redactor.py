from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Tuple


DETERMINISTIC_SALT = "zgpt-consent-v1"


def _stable_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash_value(value: Any) -> str:
    data = _stable_json({"v": value, "s": DETERMINISTIC_SALT})
    return "sha256:" + hashlib.sha256(data).hexdigest()


def redact_consent(
    consent: Dict[str, Any],
    *,
    null_fields: Iterable[str] | None = None,
    hash_fields: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """Return a deterministically redacted copy of a consent object.

    - Fields in null_fields are set to None if present.
    - Fields in hash_fields are replaced with sha256 hash of their stable JSON representation.
    - Unknown fields are left intact to preserve forward compatibility.
    - Operation is pure and deterministic.
    """

    null_set = set(null_fields or [])
    hash_set = set(hash_fields or [])

    redacted: Dict[str, Any] = {}
    for key, value in consent.items():
        if key in null_set:
            redacted[key] = None
        elif key in hash_set and value is not None:
            redacted[key] = _hash_value(value)
        elif isinstance(value, dict):
            # Recurse for nested objects; inherit same policy
            redacted[key] = redact_consent(
                value, null_fields=null_set, hash_fields=hash_set
            )
        elif isinstance(value, list):
            new_list = []
            for item in value:
                if isinstance(item, dict):
                    new_list.append(
                        redact_consent(item, null_fields=null_set, hash_fields=hash_set)
                    )
                else:
                    new_list.append(item)
            redacted[key] = new_list
        else:
            redacted[key] = value

    return redacted


def default_consent_redaction_policy() -> Tuple[Iterable[str], Iterable[str]]:
    """Default redaction policy for consent objects.

    - Null out potentially identifying free-text like metadata that may accidentally carry PII.
    - Hash subject to preserve linkability without exposing raw value.
    """

    null_fields = ["metadata"]
    hash_fields = ["subject", "consent_id"]
    return null_fields, hash_fields


def redact_consent_default(consent: Dict[str, Any]) -> Dict[str, Any]:
    null_fields, hash_fields = default_consent_redaction_policy()
    return redact_consent(consent, null_fields=null_fields, hash_fields=hash_fields)
