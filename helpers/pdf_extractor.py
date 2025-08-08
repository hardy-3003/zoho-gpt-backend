from __future__ import annotations

from typing import Any, Dict, List


def extract_fields_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Placeholder PDF extractor.
    Returns a structure with detected tables and key-value fields.
    """
    # TODO: integrate real OCR/table parsing (camelot, pdfplumber, layoutparser)
    return {"tables": [], "fields": {}}
