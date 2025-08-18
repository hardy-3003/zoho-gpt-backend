import json
import hashlib
from pathlib import Path
import pytest

from regulatory.loader import validate_pack, load_active, list_packs


FIXTURES_BASE = Path(__file__).resolve().parents[2] / "regulatory" / "rule_packs"


def _sha256(obj) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_schema_validation_happy_path():
    path = FIXTURES_BASE / "in" / "gst.json"
    validate_pack(str(path))


def test_schema_validation_failure(tmp_path: Path):
    # Missing required 'versions'
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception):
        validate_pack(str(bad))


def test_semantic_overlap_failure(tmp_path: Path):
    bad = tmp_path / "overlap.json"
    bad.write_text(
        json.dumps(
            {
                "versions": [
                    {
                        "effective_from": "2024-01-01",
                        "effective_to": "2024-12-31",
                        "data": {},
                    },
                    {"effective_from": "2024-06-01", "effective_to": None, "data": {}},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        validate_pack(str(bad))


def test_effective_date_selection_boundaries():
    base = FIXTURES_BASE
    # 2024-12-31 should pick first version
    out_2024 = load_active(base, "in", "2024-12-31")
    assert out_2024["packs"]["gst"]["version"].endswith("2024-01")
    assert out_2024["packs"]["gst"]["effective"]["to"] == "2024-12-31"

    # 2025-01-01 should pick second version
    out_2025 = load_active(base, "in", "2025-01-01")
    assert out_2025["packs"]["gst"]["version"].endswith("2025-01")
    assert out_2025["packs"]["gst"]["effective"]["to"] is None


def test_fail_closed_when_no_active(tmp_path: Path):
    # Create a pack with a closed window and query outside
    p = tmp_path / "in"
    p.mkdir(parents=True)
    (tmp_path / "out_of_scope.json").write_text("{}", encoding="utf-8")
    bad = p / "x.json"
    bad.write_text(
        json.dumps(
            {
                "versions": [
                    {
                        "effective_from": "2024-01-01",
                        "effective_to": "2024-12-31",
                        "data": {"k": 1},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        load_active(tmp_path, "in", "2025-01-01")


def test_list_packs_deterministic():
    items = list_packs(FIXTURES_BASE)
    assert items == sorted(items)
    assert "in/gst" in items


def test_deterministic_load_hash_repeatable():
    out1 = load_active(FIXTURES_BASE, "in", "2025-02-10")
    out2 = load_active(FIXTURES_BASE, "in", "2025-02-10")
    assert _sha256(out1) == _sha256(out2)
