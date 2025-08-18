from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
ARTIFACTS = ROOT / "artifacts"
REPORT = ARTIFACTS / "master_vs_repo_report.json"
SCaffold = TOOLS / "scaffold_missing_logics.py"
SCANNER = TOOLS / "scan_repo_logics.py"


def _read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_scaffold_missing_idempotent(tmp_path: Path, monkeypatch):
    # Work in repo; scanner writes to artifacts in-place
    report = _read_json(REPORT)
    missing = report.get("missing_in_repo", [])

    if not missing:
        # Nothing to scaffold; ensure running the tool is a no-op and exits 0
        res = subprocess.run(
            ["python3", str(SCaffold), "--dry-run"], cwd=ROOT.as_posix()
        )
        assert res.returncode == 0
        return

    # First run should create exactly these files
    res_yes = subprocess.run(["python3", str(SCaffold), "--yes"], cwd=ROOT.as_posix())
    assert res_yes.returncode == 0

    # Verify files exist with deterministic content header line
    for obj in missing:
        path = ROOT / obj["expected_path"]
        assert path.exists(), f"Expected created: {path}"
        content = path.read_text(encoding="utf-8")
        assert f"Logic ID: {int(obj['id']):03d}" in content
        assert f"\"slug\": \"{obj['slug']}\"" in content

    # Second run must be a no-op and exit 0
    res_again = subprocess.run(["python3", str(SCaffold), "--yes"], cwd=ROOT.as_posix())
    assert res_again.returncode == 0

    # Refresh inventories using scanner and assert no missing remain
    res_scan = subprocess.run(
        ["python3", str(SCANNER), "--summary"], cwd=ROOT.as_posix()
    )
    assert res_scan.returncode in (0, 3)
    report2 = _read_json(REPORT)
    assert report2.get("missing_in_repo", []) == []
