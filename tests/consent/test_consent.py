import json
from pathlib import Path
from typing import Dict, Any

import pytest


def load_schema() -> Dict[str, Any]:
    schema_path = Path("consent/schema/consent.schema.json")
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.unit
def test_consent_schema_validates_successfully():
    try:
        import jsonschema  # type: ignore
    except Exception:
        pytest.skip("jsonschema not available in environment")

    schema = load_schema()
    payload = {
        "subject": "ORG:60020606976",
        "scope": ["gst.gstr2b.read", "einvoice.irp.read"],
        "purpose": "compliance_reconciliation",
        "created_at": "2025-08-18T00:00:00Z",
        "expires_at": "2026-03-31T23:59:59Z",
        "retention_days": 365,
        "metadata": {"channel": "api"},
    }
    jsonschema.validate(instance=payload, schema=schema)


@pytest.mark.unit
def test_consent_schema_validation_failure():
    try:
        import jsonschema  # type: ignore
    except Exception:
        pytest.skip("jsonschema not available in environment")

    schema = load_schema()
    bad_payload = {
        # missing required fields like scope and purpose
        "subject": "ORG:60020606976",
        "created_at": "2025-08-18T00:00:00Z",
        "expires_at": "2026-03-31T23:59:59Z",
        "retention_days": -1,
    }
    with pytest.raises(Exception):
        import jsonschema  # type: ignore

        jsonschema.validate(instance=bad_payload, schema=schema)


@pytest.mark.unit
def test_redaction_is_deterministic():
    from consent.redactor import redact_consent_default

    payload = {
        "consent_id": "abc-123",
        "subject": "ORG:60020606976",
        "scope": ["gst.gstr2b.read"],
        "purpose": "compliance_reconciliation",
        "created_at": "2025-08-18T00:00:00Z",
        "expires_at": "2026-03-31T23:59:59Z",
        "retention_days": 365,
        "metadata": {"notes": "Alice phone 99999"},
    }

    r1 = redact_consent_default(payload)
    r2 = redact_consent_default(payload)
    assert r1 == r2
    # metadata should be nulled
    assert r1.get("metadata") is None
    # subject should be hashed and prefixed with sha256:
    assert isinstance(r1.get("subject"), str) and r1["subject"].startswith("sha256:")


@pytest.mark.unit
def test_ledger_integration_with_redacted_consent(tmp_path: Path):
    from evidence.ledger import EvidenceLedger
    from consent.redactor import redact_consent_default

    payload = {
        "subject": "ORG:60020606976",
        "scope": ["gst.gstr2b.read"],
        "purpose": "compliance_reconciliation",
        "created_at": "2025-08-18T00:00:00Z",
        "expires_at": "2026-03-31T23:59:59Z",
        "retention_days": 365,
        "metadata": {"notes": "PII risk"},
    }

    redacted = redact_consent_default(payload)
    ledger = EvidenceLedger(tmp_path.as_posix())
    rec1 = ledger.write("consent:ORG:60020606976", redacted)
    rec2 = ledger.write("consent:ORG:60020606976", redacted)

    # Evidence writes should be deterministic and stable
    assert rec1.data_hash == rec2.data_hash
    assert ledger.verify_integrity("consent:ORG:60020606976") is True
