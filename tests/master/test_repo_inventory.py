import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ART_DIR = ROOT / "artifacts"
REPO_INV = ART_DIR / "repo_logics.json"
REPORT = ART_DIR / "master_vs_repo_report.json"
SCANNER = ROOT / "tools" / "scan_repo_logics.py"


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_scanner_expect(code: int = 0):
    res = subprocess.run(
        ["python3", str(SCANNER), "--summary"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert (
        res.returncode == code
    ), f"Scanner exit {res.returncode} != {code}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert REPO_INV.exists(), "repo_logics.json should be emitted"
    assert REPORT.exists(), "master_vs_repo_report.json should be emitted"
    return res


def test_scanner_emits_and_determinism(tmp_path):
    # First run against committed artifacts; allow mismatches (exit 0 or 3)
    res = subprocess.run(
        ["python3", str(SCANNER), "--summary"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert res.returncode in (0, 3), f"Unexpected scanner exit: {res.returncode}"
    assert REPO_INV.exists() and REPORT.exists()

    # Determinism: re-run to temp outputs and compare bytes
    inv_tmp = tmp_path / "repo_logics.json"
    rep_tmp = tmp_path / "master_vs_repo_report.json"
    res2 = subprocess.run(
        [
            "python3",
            str(SCANNER),
            "--output-inventory",
            str(inv_tmp),
            "--output-report",
            str(rep_tmp),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert res2.returncode in (0, 3)
    assert inv_tmp.exists() and rep_tmp.exists()
    assert (
        inv_tmp.read_bytes() == REPO_INV.read_bytes()
    ), "Inventory JSON not byte-identical"
    assert rep_tmp.read_bytes() == REPORT.read_bytes(), "Report JSON not byte-identical"


def test_inventory_structure_and_sorting():
    inv = read_json(REPO_INV)
    assert isinstance(inv, list)
    # Keys and values
    prev = None
    for item in inv:
        assert set(item.keys()) == {"id", "slug", "path", "present"}
        assert isinstance(item["id"], int)
        assert isinstance(item["slug"], str)
        assert isinstance(item["path"], str) and item["path"].startswith("logics/")
        assert item["present"] is True
        key = (item["id"], item["slug"])  # sort by id then slug
        if prev is not None:
            assert prev <= key, "Inventory not sorted by (id, slug)"
        prev = key


def test_report_shape_and_counts_against_master():
    report = read_json(REPORT)
    # Keys present
    assert set(report.keys()) == {
        "missing_in_repo",
        "extra_in_repo",
        "slug_mismatches",
        "path_mismatches",
        "duplicate_ids",
    }

    # Ensure arrays are lists
    for k in report.keys():
        assert isinstance(report[k], list)

    # If the repository is fully synced with MASTER, expect all lists empty.
    # If this assertion fails, fix gaps in P1.5.3 rather than muting this test.
    assert report["missing_in_repo"] == []
    assert report["extra_in_repo"] == []
    assert report["slug_mismatches"] == []
    assert report["path_mismatches"] == []
    assert report["duplicate_ids"] == []
