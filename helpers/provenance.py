from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProvenanceMapping:
    """Represents a learned mapping from field to Zoho data source."""

    def __init__(
        self,
        field_name: str,
        endpoint: str,
        filters: Dict[str, Any],
        path: List[str],
        confidence: float = 0.0,
        source: str = "learned",
        last_used: Optional[datetime] = None,
        usage_count: int = 0,
    ):
        self.field_name = field_name
        self.endpoint = endpoint
        self.filters = filters
        self.path = path
        self.confidence = confidence
        self.source = source
        self.last_used = last_used or datetime.now()
        self.usage_count = usage_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "endpoint": self.endpoint,
            "filters": self.filters,
            "path": self.path,
            "confidence": self.confidence,
            "source": self.source,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceMapping":
        last_used = None
        if data.get("last_used"):
            try:
                last_used = datetime.fromisoformat(data["last_used"])
            except ValueError:
                pass

        return cls(
            field_name=data["field_name"],
            endpoint=data["endpoint"],
            filters=data.get("filters", {}),
            path=data.get("path", []),
            confidence=data.get("confidence", 0.0),
            source=data.get("source", "learned"),
            last_used=last_used,
            usage_count=data.get("usage_count", 0),
        )


class ProvenanceLearner:
    """Learns and manages field-to-Zoho provenance mappings."""

    def __init__(self, storage_path: str = "data/provenance_mappings.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.mappings: Dict[str, ProvenanceMapping] = {}
        self.load_mappings()

    def load_mappings(self) -> None:
        """Load existing mappings from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for field_name, mapping_data in data.items():
                        self.mappings[field_name] = ProvenanceMapping.from_dict(
                            mapping_data
                        )
                logger.info(f"Loaded {len(self.mappings)} provenance mappings")
        except Exception as e:
            logger.warning(f"Failed to load provenance mappings: {e}")

    def save_mappings(self) -> None:
        """Save mappings to storage."""
        try:
            data = {name: mapping.to_dict() for name, mapping in self.mappings.items()}
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.mappings)} provenance mappings")
        except Exception as e:
            logger.error(f"Failed to save provenance mappings: {e}")

    def learn_mapping(
        self,
        field_name: str,
        endpoint: str,
        filters: Dict[str, Any],
        path: List[str],
        confidence: float = 0.0,
        source: str = "learned",
    ) -> None:
        """Learn a new field-to-Zoho mapping."""
        if field_name in self.mappings:
            # Update existing mapping if new one has higher confidence
            existing = self.mappings[field_name]
            if confidence > existing.confidence:
                self.mappings[field_name] = ProvenanceMapping(
                    field_name,
                    endpoint,
                    filters,
                    path,
                    confidence,
                    source,
                    existing.last_used,
                    existing.usage_count,
                )
                logger.info(
                    f"Updated mapping for {field_name} with confidence {confidence}"
                )
        else:
            # Create new mapping
            self.mappings[field_name] = ProvenanceMapping(
                field_name, endpoint, filters, path, confidence, source
            )
            logger.info(
                f"Learned new mapping for {field_name} with confidence {confidence}"
            )

        self.save_mappings()

    def get_mapping(self, field_name: str) -> Optional[ProvenanceMapping]:
        """Get mapping for a field, updating usage statistics."""
        mapping = self.mappings.get(field_name)
        if mapping:
            mapping.usage_count += 1
            mapping.last_used = datetime.now()
            self.save_mappings()
        return mapping

    def get_mappings_for_fields(
        self, field_names: List[str]
    ) -> Dict[str, ProvenanceMapping]:
        """Get mappings for multiple fields."""
        return {
            name: self.get_mapping(name)
            for name in field_names
            if self.get_mapping(name)
        }

    def suggest_mappings(
        self, field_names: List[str], candidate_maps: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ProvenanceMapping]:
        """Suggest mappings for fields using learned patterns and heuristics."""
        suggestions = {}
        candidate_maps = candidate_maps or {}

        for field_name in field_names:
            # Check existing learned mappings first
            existing = self.get_mapping(field_name)
            if existing:
                suggestions[field_name] = existing
                continue

            # Check candidate maps
            if field_name in candidate_maps:
                candidate = candidate_maps[field_name]
                mapping = ProvenanceMapping(
                    field_name=field_name,
                    endpoint=candidate.get("endpoint", ""),
                    filters=candidate.get("filters", {}),
                    path=candidate.get("path", []),
                    confidence=candidate.get("confidence", 0.5),
                    source="candidate",
                )
                suggestions[field_name] = mapping
                continue

            # Use heuristic matching
            heuristic_mapping = self._heuristic_match(field_name)
            if heuristic_mapping:
                suggestions[field_name] = heuristic_mapping

        return suggestions

    def _heuristic_match(self, field_name: str) -> Optional[ProvenanceMapping]:
        """Use heuristics to suggest a mapping for a field."""
        field_lower = field_name.lower().strip()

        # Enhanced heuristic patterns
        heuristics = [
            # Revenue/Income patterns
            (
                r"revenue|income|sales|turnover",
                "reports/pnl",
                {"section": "income"},
                0.8,
            ),
            (
                r"gross.*revenue|gross.*income",
                "reports/pnl",
                {"section": "income", "type": "gross"},
                0.9,
            ),
            (
                r"net.*revenue|net.*income",
                "reports/pnl",
                {"section": "income", "type": "net"},
                0.9,
            ),
            # Expense patterns
            (r"expense|cost|expenditure", "reports/pnl", {"section": "expense"}, 0.8),
            (
                r"operating.*expense",
                "reports/pnl",
                {"section": "expense", "type": "operating"},
                0.9,
            ),
            (
                r"administrative.*expense",
                "reports/pnl",
                {"section": "expense", "type": "administrative"},
                0.9,
            ),
            # Profit/Loss patterns
            (r"profit|loss", "reports/pnl", {"section": "summary"}, 0.8),
            (
                r"net.*profit|net.*loss",
                "reports/pnl",
                {"section": "summary", "type": "net"},
                0.9,
            ),
            (
                r"gross.*profit|gross.*loss",
                "reports/pnl",
                {"section": "summary", "type": "gross"},
                0.9,
            ),
            # Balance Sheet patterns
            (r"asset", "reports/balance_sheet", {"section": "assets"}, 0.8),
            (
                r"liability|debt",
                "reports/balance_sheet",
                {"section": "liabilities"},
                0.8,
            ),
            (r"equity|capital", "reports/balance_sheet", {"section": "equity"}, 0.8),
            # Period patterns
            (r"period|date|month|year", "common/period", {}, 0.7),
            # Specific financial terms
            (r"ebitda", "reports/pnl", {"section": "summary", "metric": "ebitda"}, 0.9),
            (r"ebit", "reports/pnl", {"section": "summary", "metric": "ebit"}, 0.9),
            (
                r"operating.*income",
                "reports/pnl",
                {"section": "summary", "metric": "operating_income"},
                0.9,
            ),
        ]

        for pattern, endpoint, filters, confidence in heuristics:
            if re.search(pattern, field_lower):
                return ProvenanceMapping(
                    field_name=field_name,
                    endpoint=endpoint,
                    filters=filters,
                    path=[],
                    confidence=confidence,
                    source="heuristic",
                )

        return None

    def validate_mapping(
        self,
        field_name: str,
        actual_value: Any,
        expected_value: Any,
        tolerance: float = 0.1,
    ) -> Dict[str, Any]:
        """Validate a mapping by comparing actual vs expected values."""
        validation = {
            "is_valid": False,
            "confidence_adjustment": 0.0,
            "suggestions": [],
        }

        try:
            # Convert to float for numerical comparison
            actual = float(actual_value) if actual_value is not None else 0.0
            expected = float(expected_value) if expected_value is not None else 0.0

            if expected == 0:
                validation["is_valid"] = actual == 0
            else:
                error_rate = abs(actual - expected) / abs(expected)
                validation["is_valid"] = error_rate <= tolerance

                if validation["is_valid"]:
                    # Boost confidence for accurate mappings
                    validation["confidence_adjustment"] = 0.1
                else:
                    # Reduce confidence for inaccurate mappings
                    validation["confidence_adjustment"] = -0.2
                    validation["suggestions"].append(
                        f"Value mismatch: expected {expected}, got {actual}"
                    )

        except (ValueError, TypeError):
            # Non-numerical comparison
            validation["is_valid"] = str(actual_value) == str(expected_value)
            if not validation["is_valid"]:
                validation["confidence_adjustment"] = -0.1
                validation["suggestions"].append("Type mismatch in validation")

        return validation

    def update_mapping_confidence(
        self, field_name: str, confidence_adjustment: float
    ) -> None:
        """Update the confidence of a mapping based on validation results."""
        if field_name in self.mappings:
            mapping = self.mappings[field_name]
            new_confidence = max(
                0.0, min(1.0, mapping.confidence + confidence_adjustment)
            )
            mapping.confidence = new_confidence
            self.save_mappings()
            logger.info(f"Updated confidence for {field_name} to {new_confidence}")


def make_field_provenance(**field_mappings: Dict[str, Any]) -> Dict[str, Any]:
    """Create a provenance map for multiple fields.

    Args:
        **field_mappings: Dict of field_name -> mapping_data

    Returns:
        Dict with provenance information for each field
    """
    provenance = {
        "fields": {},
        "summary": {
            "total_fields": len(field_mappings),
            "mapped_fields": 0,
            "unmapped_fields": 0,
            "average_confidence": 0.0,
        },
    }

    total_confidence = 0.0
    mapped_count = 0

    for field_name, mapping_data in field_mappings.items():
        if mapping_data and mapping_data.get("endpoint"):
            provenance["fields"][field_name] = {
                "endpoint": mapping_data["endpoint"],
                "filters": mapping_data.get("filters", {}),
                "path": mapping_data.get("path", []),
                "confidence": mapping_data.get("confidence", 0.0),
                "source": mapping_data.get("source", "unknown"),
            }
            total_confidence += mapping_data.get("confidence", 0.0)
            mapped_count += 1
        else:
            provenance["fields"][field_name] = {
                "endpoint": "",
                "filters": {},
                "path": [],
                "confidence": 0.0,
                "source": "unmapped",
            }

    # Update summary
    provenance["summary"]["mapped_fields"] = mapped_count
    provenance["summary"]["unmapped_fields"] = len(field_mappings) - mapped_count
    if mapped_count > 0:
        provenance["summary"]["average_confidence"] = total_confidence / mapped_count

    return provenance


def learn_from_pdf_extraction(
    extraction_result: Dict[str, Any], learner: ProvenanceLearner
) -> Dict[str, Any]:
    """Learn provenance mappings from PDF extraction results."""
    fields = extraction_result.get("fields", {})
    tables = extraction_result.get("tables", [])

    # Extract fields from tables as well
    table_fields = {}
    for table in tables:
        table_name = table.get("name", "unknown")
        for row in table.get("rows", []):
            if isinstance(row, dict) and "name" in row and "value" in row:
                field_name = f"{table_name}_{row['name']}"
                table_fields[field_name] = row["value"]

    # Combine all fields
    all_fields = {**fields, **table_fields}

    # Get suggested mappings
    suggestions = learner.suggest_mappings(list(all_fields.keys()))

    # Learn new mappings
    learned_count = 0
    for field_name, mapping in suggestions.items():
        if mapping.source in ["heuristic", "candidate"]:
            learner.learn_mapping(
                field_name=mapping.field_name,
                endpoint=mapping.endpoint,
                filters=mapping.filters,
                path=mapping.path,
                confidence=mapping.confidence,
                source=mapping.source,
            )
            learned_count += 1

    return {
        "fields_processed": len(all_fields),
        "mappings_learned": learned_count,
        "suggestions": {
            name: mapping.to_dict() for name, mapping in suggestions.items()
        },
        "extraction_confidence": extraction_result.get("meta", {}).get(
            "confidence", 0.0
        ),
    }


# Global learner instance
_global_learner: Optional[ProvenanceLearner] = None


def get_global_learner() -> ProvenanceLearner:
    """Get or create the global provenance learner instance."""
    global _global_learner
    if _global_learner is None:
        _global_learner = ProvenanceLearner()
    return _global_learner


# Backward compatibility functions
def make_provenance(**fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy provenance map for backward compatibility:
    { "sources": [{"source":"zoho", "endpoint":"<api>", "ids":[], "filters":{}}] }
    """
    sources: List[Dict[str, Any]] = []
    for key, value in fields.items():
        if isinstance(value, dict):
            normalized = {
                "source": value.get("source", "zoho"),
                "endpoint": value.get("endpoint", ""),
                "ids": value.get("ids", []),
                "filters": value.get("filters", {}),
            }
        else:
            normalized = {
                "source": "zoho",
                "endpoint": str(value),
                "ids": [],
                "filters": {},
            }
        sources.append(normalized)

    # If no fields provided, return default structure
    if not sources:
        sources = [
            {"source": "zoho", "endpoint": "reports/auto", "ids": [], "filters": {}}
        ]

    return {"sources": sources}


def validate_provenance(prov: Dict[str, Any]) -> None:
    """Legacy provenance validation for backward compatibility."""
    if not isinstance(prov, dict):
        raise TypeError("provenance must be a dict")

    # Support composite provenance with 'figures' and 'sources'
    entries = prov.get("figures") if isinstance(prov.get("figures"), dict) else prov

    for field, entry in entries.items():
        # Skip audit_trail entries which have a different structure
        if field == "audit_trail":
            continue
        # ignore non-dict top-level keys like 'sources'
        if field == "sources":
            continue
        if not isinstance(entry, dict):
            raise TypeError(f"provenance[{field}] must be a dict")

        required_keys = ("source", "endpoint", "ids", "filters")
        for rk in required_keys:
            if rk not in entry:
                raise ValueError(f"provenance[{field}] missing `{rk}`")
        if not isinstance(entry["endpoint"], str):
            raise TypeError(f"provenance[{field}].endpoint must be str")
        if not isinstance(entry["ids"], list):
            raise TypeError(f"provenance[{field}].ids must be list")
        if not isinstance(entry["filters"], dict):
            raise TypeError(f"provenance[{field}].filters must be dict")


# Phase 4.1 Observability Utilities


def standardize_provenance_map(provenance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize provenance map for telemetry and logging.

    Args:
        provenance: Raw provenance map from logic execution

    Returns:
        Standardized provenance map with consistent structure
    """
    if not provenance:
        return {"sources": [], "figures": {}, "keys_count": 0}

    standardized = {"sources": [], "figures": {}, "keys_count": 0}

    # Handle different provenance formats
    if "sources" in provenance:
        standardized["sources"] = provenance["sources"]

    if "figures" in provenance:
        standardized["figures"] = provenance["figures"]
        standardized["keys_count"] = len(provenance["figures"])

    # Count total keys for telemetry
    if isinstance(provenance, dict):
        standardized["keys_count"] = len(provenance.keys())

    return standardized


def redact_pii_from_provenance(provenance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact PII from provenance map for safe logging.

    Args:
        provenance: Raw provenance map

    Returns:
        Provenance map with PII redacted
    """
    if not provenance:
        return provenance

    # PII patterns to redact
    pii_patterns = {
        "gstin",
        "pan",
        "aadhar",
        "ssn",
        "account_number",
        "card_number",
        "phone",
        "email",
        "address",
        "name",
    }

    def redact_value(value):
        if isinstance(value, str):
            value_lower = value.lower()
            if any(pattern in value_lower for pattern in pii_patterns):
                return "[REDACTED]"
        return value

    def redact_dict(data):
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in pii_patterns):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    redact_dict(item) if isinstance(item, dict) else redact_value(item)
                    for item in value
                ]
            else:
                redacted[key] = redact_value(value)

        return redacted

    return redact_dict(provenance)


def get_provenance_metrics(provenance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metrics from provenance map for telemetry.

    Args:
        provenance: Raw provenance map

    Returns:
        Dictionary with provenance metrics
    """
    if not provenance:
        return {
            "sources_count": 0,
            "figures_count": 0,
            "total_keys": 0,
            "has_zoho_sources": False,
            "has_calculated_sources": False,
        }

    metrics = {
        "sources_count": 0,
        "figures_count": 0,
        "total_keys": len(provenance.keys()),
        "has_zoho_sources": False,
        "has_calculated_sources": False,
    }

    # Count sources
    if "sources" in provenance and isinstance(provenance["sources"], list):
        metrics["sources_count"] = len(provenance["sources"])
        for source in provenance["sources"]:
            if isinstance(source, dict):
                source_type = source.get("source", "").lower()
                if "zoho" in source_type:
                    metrics["has_zoho_sources"] = True
                elif "calculat" in source_type:
                    metrics["has_calculated_sources"] = True

    # Count figures
    if "figures" in provenance and isinstance(provenance["figures"], dict):
        metrics["figures_count"] = len(provenance["figures"])

    return metrics


def create_telemetry_provenance(provenance: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create telemetry-ready provenance map with redaction and metrics.

    Args:
        provenance: Raw provenance map

    Returns:
        Telemetry-ready provenance map
    """
    # Standardize the provenance
    std_provenance = standardize_provenance_map(provenance)

    # Redact PII
    redacted_provenance = redact_pii_from_provenance(std_provenance)

    # Get metrics
    metrics = get_provenance_metrics(provenance)

    return {
        "provenance": redacted_provenance,
        "metrics": metrics,
        "keys_count": metrics["total_keys"],
    }
