from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import json

try:
    import jsonschema
except Exception as exc:  # pragma: no cover - import error surfaced in tests
    jsonschema = None  # type: ignore


@dataclass(frozen=True)
class PackVersion:
    effective_from: date
    effective_to: Optional[date]
    data: Dict[str, Any]


SCHEMA_PATH = Path(__file__).parent / "schema" / "rule_pack.schema.json"


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid ISO date: {value}") from e


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_with_schema(payload: Dict[str, Any], schema_path: Path) -> None:
    if jsonschema is None:
        raise RuntimeError(
            "jsonschema is required for regulatory pack validation. Install it in requirements."
        )
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(instance=payload, schema=schema)


def _normalize_versions(raw: Dict[str, Any]) -> List[PackVersion]:
    versions: List[PackVersion] = []
    for v in raw.get("versions", []):
        eff_from = _parse_date(v["effective_from"])  # required by schema
        eff_to = _parse_date(v["effective_to"]) if v.get("effective_to") else None
        versions.append(
            PackVersion(effective_from=eff_from, effective_to=eff_to, data=v["data"])
        )
    # Deterministic ordering: sort by effective_from ASC, then effective_to (None last)
    versions.sort(key=lambda x: (x.effective_from, x.effective_to or date.max))
    return versions


def _check_semantic_rules(pack_path: Path, versions: List[PackVersion]) -> None:
    # 1) No overlapping effective windows; contiguous or gapped windows allowed
    # Window is [from, to] inclusive of from, exclusive of next.from; if to is None, open-ended
    for i in range(len(versions)):
        a = versions[i]
        for j in range(i + 1, len(versions)):
            b = versions[j]
            a_to = a.effective_to or date.max
            # overlap if starts before other's end and ends after other's start
            if (
                a.effective_from <= (b.effective_to or date.max)
                and a_to >= b.effective_from
            ):
                # Allow adjacency where a_to < b_from strictly; overlap if a_to >= b_from
                if a_to >= b.effective_from:
                    raise ValueError(
                        f"Overlapping effective windows in pack '{pack_path}': "
                        f"[{a.effective_from} .. {a.effective_to or '∞'}] vs "
                        f"[{b.effective_from} .. {b.effective_to or '∞'}]"
                    )


def validate_pack(path: str | Path) -> None:
    """Validate a rule pack file against schema and semantic constraints.

    Raises ValueError/RuntimeError on failure.
    """
    pack_path = Path(path)
    payload = _load_json(pack_path)
    _validate_with_schema(payload, SCHEMA_PATH)
    versions = _normalize_versions(payload)
    if not versions:
        raise ValueError(f"Pack '{pack_path}' must contain at least one version")
    _check_semantic_rules(pack_path, versions)


def _select_version(versions: List[PackVersion], on_date: date) -> PackVersion:
    candidates: List[Tuple[date, PackVersion]] = []
    for v in versions:
        start = v.effective_from
        end = v.effective_to or date.max
        if start <= on_date <= end:
            candidates.append((start, v))
    # Deterministic selection: if multiple candidates (should not happen post-validation), pick latest start
    if len(candidates) == 0:
        raise LookupError("No active version for the provided date")
    if len(candidates) > 1:
        # Fail-closed per spec when overlapping detected
        raise ValueError(
            "Multiple active versions found for date; pack must not overlap"
        )
    # Single candidate
    return sorted(candidates, key=lambda t: t[0])[-1][1]


def _pack_name_from_file(file_path: Path) -> str:
    # e.g., gst.json -> gst
    return file_path.stem


def load_active(packs_dir: str | Path, country: str, date_iso: str) -> Dict[str, Any]:
    """Load all active packs for a given country and date.

    packs_dir: directory containing rule_packs/<country>/
    country: ISO 2-letter code like 'in'
    date_iso: YYYY-MM-DD

    Returns a deterministic dict: {"packs": {<name>: {"version": "<name>@YYYY-MM", "data": {...}, "effective": {from,to}}}}
    """
    on_date = _parse_date(date_iso)
    base = Path(packs_dir) / country
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(
            f"Packs directory not found for country '{country}': {base}"
        )

    result: Dict[str, Any] = {"packs": {}, "effective_date": date_iso}
    # Iterate files deterministically
    files = sorted(
        [p for p in base.glob("*.json") if p.is_file()], key=lambda p: p.name
    )
    for fp in files:
        raw = _load_json(fp)
        _validate_with_schema(raw, SCHEMA_PATH)
        versions = _normalize_versions(raw)
        _check_semantic_rules(fp, versions)
        selected = _select_version(versions, on_date)
        pack_name = _pack_name_from_file(fp)
        version_label = f"{pack_name}@{selected.effective_from.strftime('%Y-%m')}"
        result["packs"][pack_name] = {
            "version": version_label,
            "effective": {
                "from": selected.effective_from.strftime("%Y-%m-%d"),
                "to": (
                    selected.effective_to.strftime("%Y-%m-%d")
                    if selected.effective_to
                    else None
                ),
            },
            "data": selected.data,
        }

    return result


def list_packs(packs_dir: str | Path) -> List[str]:
    """List available packs as identifiers '<country>/<name>' deterministically."""
    base = Path(packs_dir)
    if not base.exists():
        return []
    out: List[str] = []
    for country_dir in sorted(
        [d for d in base.iterdir() if d.is_dir()], key=lambda p: p.name
    ):
        for fp in sorted(
            [p for p in country_dir.glob("*.json") if p.is_file()], key=lambda p: p.name
        ):
            out.append(f"{country_dir.name}/{_pack_name_from_file(fp)}")
    return out
