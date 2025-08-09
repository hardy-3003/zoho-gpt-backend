from __future__ import annotations

from typing import Any, Dict, List


def extract_fields_from_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """Lightweight placeholder extractor.
    Returns a structure with detected tables and key-value fields.
    """
    # Hook point for future OCR/table parsing (camelot, pdfplumber, layoutparser)
    return {"tables": [], "fields": {}}


def learn_provenance_mapping(
    fields: Dict[str, Any],
    candidate_maps: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Placeholder mapping from field labels to Zoho endpoints/filters/paths.
    Returns a dict keyed by field name with provenance hints.
    """
    candidate_maps = candidate_maps or {}
    mapping: Dict[str, Any] = {}
    for k in fields.keys():
        mapping[k] = candidate_maps.get(k) or {"endpoint": "", "filter": {}, "path": []}
    return mapping
