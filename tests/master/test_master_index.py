import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "master_index.json"
EXTRACTOR = ROOT / "tools" / "extract_master_index.py"


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_master_index_length_and_ids():
    index = read_json(ARTIFACT)
    assert isinstance(index, list)
    assert len(index) == 231, f"Expected 231 entries, got {len(index)}"
    ids = [int(x["id"]) for x in index]
    assert ids == list(range(1, 232)), "IDs must be contiguous 1..231 and sorted"


def test_slugs_and_paths():
    index = read_json(ARTIFACT)
    kebab_re = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    path_re = re.compile(r"^logics/logic_(\d{3})_[a-z0-9_]+\.py$")
    for item in index:
        slug = item["slug"]
        assert isinstance(slug, str) and kebab_re.match(slug), f"Invalid slug: {slug}"
        path = item["path"]
        assert isinstance(path, str) and path_re.match(
            path
        ), f"Invalid path pattern: {path}"
        status = item["status"]
        if status == "present":
            assert (ROOT / path).exists(), f"Missing file for present item: {path}"


def test_determinism_rerun_matches_committed(tmp_path):
    out_path = tmp_path / "master_index.json"
    # Run extractor; ensure it exits 0
    res = subprocess.run(
        ["python3", str(EXTRACTOR), "--output", str(out_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Extractor failed: {res.stderr or res.stdout}"
    # Compare byte-for-byte
    expected = (ROOT / "artifacts" / "master_index.json").read_bytes()
    observed = out_path.read_bytes()
    assert (
        observed == expected
    ), "Re-extracted master_index.json differs from committed version"
