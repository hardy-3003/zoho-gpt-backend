from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from helpers.provenance import validate_provenance

logger = logging.getLogger(__name__)

# Minimal per-logic schema registry with sensible defaults
_BASE_INPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "org_id": {"type": "string"},
        "start_date": {"type": "string", "format": "date"},
        "end_date": {"type": "string", "format": "date"},
        "headers": {"type": "object"},
        "api_domain": {"type": "string"},
        "query": {"type": "string"},
    },
    "required": ["org_id", "start_date", "end_date"],
    "additionalProperties": True,
}

_BASE_OUTPUT: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "result": {"type": "object"},
        "provenance": {"type": "object"},
        "confidence": {"type": "number"},
        "alerts": {"type": "array", "items": {"type": "string"}},
        "meta": {"type": "object"},
    },
    "required": ["result", "provenance", "confidence", "alerts", "meta"],
}

_INPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {"L-001": _BASE_INPUT}
_OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {"L-001": _BASE_OUTPUT}

# Format learning storage
_FORMAT_SCHEMAS: Dict[str, Dict[str, Any]] = {}
_FORMAT_VERSIONS: Dict[str, List[str]] = {}


class FormatSchema:
    """Represents a learned format schema with versioning."""

    def __init__(
        self,
        name: str,
        fields: Dict[str, Any],
        version: str = "1.0",
        confidence: float = 0.0,
        source: str = "learned",
        created_at: Optional[datetime] = None,
    ):
        self.name = name
        self.fields = fields
        self.version = version
        self.confidence = confidence
        self.source = source
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fields": self.fields,
            "version": self.version,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "schema": self._generate_json_schema(),
        }

    def _generate_json_schema(self) -> Dict[str, Any]:
        """Generate JSON Schema from field definitions."""
        properties = {}
        required = []

        for field_name, field_info in self.fields.items():
            field_type = field_info.get("type", "string")
            properties[field_name] = {
                "type": field_type,
                "description": field_info.get("description", f"Field: {field_name}"),
            }

            if field_info.get("required", False):
                required.append(field_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormatSchema":
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass

        return cls(
            name=data["name"],
            fields=data["fields"],
            version=data.get("version", "1.0"),
            confidence=data.get("confidence", 0.0),
            source=data.get("source", "learned"),
            created_at=created_at,
        )


class FormatRegistry:
    """Registry for managing learned format schemas."""

    def __init__(self, storage_path: str = "data/format_schemas.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.formats: Dict[str, FormatSchema] = {}
        self.load_formats()

    def load_formats(self) -> None:
        """Load existing format schemas from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for format_name, format_data in data.items():
                        self.formats[format_name] = FormatSchema.from_dict(format_data)
                logger.info(f"Loaded {len(self.formats)} format schemas")
        except Exception as e:
            logger.warning(f"Failed to load format schemas: {e}")

    def save_formats(self) -> None:
        """Save format schemas to storage."""
        try:
            data = {
                name: format_schema.to_dict()
                for name, format_schema in self.formats.items()
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.formats)} format schemas")
        except Exception as e:
            logger.error(f"Failed to save format schemas: {e}")

    def register_format(
        self,
        name: str,
        fields: Dict[str, Any],
        confidence: float = 0.0,
        source: str = "learned",
    ) -> str:
        """Register a new format schema."""
        # Generate version
        existing_versions = [f.version for f in self.formats.values() if f.name == name]
        if existing_versions:
            # Increment version
            latest_version = max(
                existing_versions, key=lambda v: [int(x) for x in v.split(".")]
            )
            major, minor = latest_version.split(".")
            new_version = f"{major}.{int(minor) + 1}"
        else:
            new_version = "1.0"

        format_schema = FormatSchema(name, fields, new_version, confidence, source)
        self.formats[name] = format_schema
        self.save_formats()

        logger.info(
            f"Registered format {name} version {new_version} with confidence {confidence}"
        )
        return new_version

    def get_format(
        self, name: str, version: Optional[str] = None
    ) -> Optional[FormatSchema]:
        """Get a format schema by name and optional version."""
        if name not in self.formats:
            return None

        format_schema = self.formats[name]
        if version and format_schema.version != version:
            # Look for specific version
            for fmt in self.formats.values():
                if fmt.name == name and fmt.version == version:
                    return fmt
            return None

        return format_schema

    def list_formats(self) -> List[Dict[str, Any]]:
        """List all available formats."""
        return [
            {
                "name": fmt.name,
                "version": fmt.version,
                "confidence": fmt.confidence,
                "source": fmt.source,
                "created_at": fmt.created_at.isoformat(),
                "field_count": len(fmt.fields),
            }
            for fmt in self.formats.values()
        ]

    def validate_data_against_format(
        self, data: Dict[str, Any], format_name: str
    ) -> Dict[str, Any]:
        """Validate data against a learned format."""
        format_schema = self.get_format(format_name)
        if not format_schema:
            return {
                "is_valid": False,
                "errors": [f"Format {format_name} not found"],
                "score": 0.0,
            }

        schema = format_schema._generate_json_schema()
        validation_result = self._validate_json_schema(data, schema)

        # Calculate score based on validation
        total_fields = len(format_schema.fields)
        valid_fields = sum(1 for field in format_schema.fields if field in data)
        score = valid_fields / total_fields if total_fields > 0 else 0.0

        return {
            "is_valid": validation_result["is_valid"],
            "errors": validation_result["errors"],
            "score": score,
            "format_version": format_schema.version,
            "confidence": format_schema.confidence,
        }

    def _validate_json_schema(
        self, data: Dict[str, Any], schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simple JSON Schema validation."""
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check field types
        properties = schema.get("properties", {})
        for field_name, field_value in data.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type", "string")
                if expected_type == "number" and not isinstance(
                    field_value, (int, float)
                ):
                    errors.append(
                        f"Field {field_name} should be number, got {type(field_value)}"
                    )
                elif expected_type == "string" and not isinstance(field_value, str):
                    errors.append(
                        f"Field {field_name} should be string, got {type(field_value)}"
                    )

        return {"is_valid": len(errors) == 0, "errors": errors}


# Global format registry instance
_global_format_registry: Optional[FormatRegistry] = None


def get_global_format_registry() -> FormatRegistry:
    """Get or create the global format registry instance."""
    global _global_format_registry
    if _global_format_registry is None:
        _global_format_registry = FormatRegistry()
    return _global_format_registry


def register_logic_schema(
    logic_id: str,
    input_schema: Dict[str, Any] | None = None,
    output_schema: Dict[str, Any] | None = None,
) -> None:
    if not logic_id:
        return
    _INPUT_SCHEMAS[logic_id] = input_schema or _BASE_INPUT
    _OUTPUT_SCHEMAS[logic_id] = output_schema or _BASE_OUTPUT


def get_input_schema(logic_id: str) -> Dict[str, Any]:
    return _INPUT_SCHEMAS.get(logic_id, _BASE_INPUT)


def get_output_schema(logic_id: str) -> Dict[str, Any]:
    return _OUTPUT_SCHEMAS.get(logic_id, _BASE_OUTPUT)


def ensure_all_logic_defaults(ids: list[str]) -> None:
    for lid in ids:
        _INPUT_SCHEMAS.setdefault(lid, _BASE_INPUT)
        _OUTPUT_SCHEMAS.setdefault(lid, _BASE_OUTPUT)


# --- Additive contract validation helpers ---
_OUTPUT_REQUIREMENTS = {
    "provenance": dict,
    "confidence": (int, float),
    "result": dict,
    "alerts": list,
}


def validate_output_contract(payload: Dict[str, Any]) -> None:
    for field, typ in _OUTPUT_REQUIREMENTS.items():
        if field not in payload:
            raise ValueError(f"Missing required output field: {field}")
        if not isinstance(payload[field], typ):
            raise TypeError(
                f"Field `{field}` must be {typ}, got {type(payload[field])}"
            )
    # Deep checks
    validate_provenance(payload["provenance"])
    _validate_alerts(payload["alerts"])


def _validate_alerts(alerts: Any) -> None:
    if not isinstance(alerts, list):
        raise TypeError("alerts must be a list")
    for i, a in enumerate(alerts):
        if not isinstance(a, dict):
            raise TypeError(f"alerts[{i}] must be dict")
        # relaxed minimum: require 'level' and 'msg' where present; allow 'msg'-only
        if "msg" not in a:
            raise ValueError(f"alerts[{i}] missing 'msg'")
        if "level" in a and not isinstance(a["level"], (str,)):
            raise TypeError(f"alerts[{i}].level must be str")
        if not isinstance(a.get("msg", ""), (str,)):
            raise TypeError(f"alerts[{i}].msg must be str")


def register_schema(
    name: str,
    schema: Dict[str, Any],
    version: str = "1.0",
    description: str = "",
) -> None:
    """Register a new schema with versioning."""
    # Store in format registry
    registry = get_global_format_registry()

    # Convert schema to field definitions
    fields = {}
    if "properties" in schema:
        for field_name, field_schema in schema["properties"].items():
            fields[field_name] = {
                "type": field_schema.get("type", "string"),
                "description": field_schema.get("description", ""),
                "required": field_name in schema.get("required", []),
            }

    registry.register_format(name, fields, 0.8, "manual")


def save_learned_format(name: str, mapping: Dict[str, Any], path: str) -> None:
    """Save a learned format mapping to storage."""
    try:
        # Convert mapping to field definitions
        fields = {}
        for field_name, field_info in mapping.items():
            if isinstance(field_info, dict):
                fields[field_name] = {
                    "type": "number",  # Default to number for financial data
                    "description": f"Learned field: {field_name}",
                    "required": True,
                    "endpoint": field_info.get("endpoint", ""),
                    "filters": field_info.get("filters", {}),
                }
            else:
                fields[field_name] = {
                    "type": "string",
                    "description": f"Learned field: {field_name}",
                    "required": True,
                }

        # Register in format registry
        registry = get_global_format_registry()
        version = registry.register_format(name, fields, 0.7, "learned")

        # Also save to legacy path for backward compatibility
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(
                {
                    "name": name,
                    "version": version,
                    "mapping": mapping,
                    "fields": fields,
                    "created_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

        logger.info(f"Saved learned format {name} version {version} to {path}")

    except Exception as e:
        logger.error(f"Failed to save learned format {name}: {e}")


def load_learned_format(name: str) -> Optional[Dict[str, Any]]:
    """Load a learned format by name."""
    registry = get_global_format_registry()
    format_schema = registry.get_format(name)

    if format_schema:
        return {
            "name": format_schema.name,
            "version": format_schema.version,
            "fields": format_schema.fields,
            "confidence": format_schema.confidence,
            "source": format_schema.source,
            "created_at": format_schema.created_at.isoformat(),
        }

    return None


def validate_learned_format(data: Dict[str, Any], format_name: str) -> Dict[str, Any]:
    """Validate data against a learned format."""
    registry = get_global_format_registry()
    return registry.validate_data_against_format(data, format_name)


def list_learned_formats() -> List[Dict[str, Any]]:
    """List all learned formats."""
    registry = get_global_format_registry()
    return registry.list_formats()


def migrate_format_version(format_name: str, target_version: str) -> bool:
    """Migrate a format to a new version."""
    registry = get_global_format_registry()
    current_format = registry.get_format(format_name)

    if not current_format:
        return False

    # Create new version with updated fields
    new_fields = current_format.fields.copy()
    # Add migration logic here as needed

    registry.register_format(
        format_name, new_fields, current_format.confidence, "migrated"
    )
    return True
