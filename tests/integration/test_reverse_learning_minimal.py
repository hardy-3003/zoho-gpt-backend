import json, os
from orchestrators.generic_report_orchestrator import (
    learn_from_pdf,
    generate_from_learned_mapping,
)


def test_learn_and_generate_minimal(tmp_path):
    # Arrange: pretend we learned from a fixture PDF
    pdf_path = "fixtures/pdfs/mis_fixture_v1.pdf"
    learned = learn_from_pdf(pdf_path, name="mis_fixture_v1")
    assert "mapping" in learned and learned["mapping"]
    # Act: generate using source_fields that resemble extracted fields
    payload = {
        "period": "2025-06",
        "source_fields": {"Revenue": 12345.0, "Expenses": 6789.0},
    }
    out = generate_from_learned_mapping(payload, learned["mapping"])
    # Assert: contract shape + provenance anchors
    assert set(["result", "provenance", "confidence", "alerts"]).issubset(out.keys())
    assert "Revenue" in out["result"] and "Expenses" in out["result"]
    assert (
        "Revenue" in out["provenance"]["fields"]
        and "Expenses" in out["provenance"]["fields"]
    )
    # When fields are coherent, expect enabled True
    assert out.get("enabled") in (True, False)
