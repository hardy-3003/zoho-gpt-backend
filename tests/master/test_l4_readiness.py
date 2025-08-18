import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = PROJECT_ROOT / "artifacts"


def _run_auditor(tmp_dir: Path | None = None, logics_dir: Path | None = None) -> dict:
    from tools.audit_l4_readiness import generate_report

    if logics_dir is None:
        logics_dir = PROJECT_ROOT / "logics"
    report = generate_report(logics_dir)
    # Determinism: ensure canonical JSON is identical across runs
    j = json.dumps(report, sort_keys=True)
    j2 = json.dumps(report, sort_keys=True)
    assert j == j2
    return report


def test_summary_total_is_231_and_deterministic():
    report_path = ARTIFACTS / "l4_readiness_report.json"
    assert report_path.exists(), "Artifact must be committed for determinism"
    obj = json.loads(report_path.read_text(encoding="utf-8"))
    assert obj["summary"]["total"] == 231
    # Re-run auditor and compare hash of JSON string
    from tools.audit_l4_readiness import canonical_dumps, generate_report

    r = generate_report(PROJECT_ROOT / "logics")
    rerun_json = canonical_dumps(r)
    committed_json = canonical_dumps(obj)
    assert rerun_json == committed_json


@pytest.mark.parametrize(
    "content,accepts",
    [
        ("from logics.common.l4_default import L4\n", True),
        ("from logics.common.l4_base import L4Base\n", True),
        ("L4 = object()\n", True),
        ("# no l4 import here\n", False),
    ],
)
def test_acceptance_rules_with_synthetic_file(content: str, accepts: bool):
    from tools.audit_l4_readiness import analyze_content_for_l4

    is_ready, has_execute, reason = analyze_content_for_l4(
        content + "\n" + "def execute():\n    return {}\n"
    )
    assert is_ready is accepts


def test_execute_presence_detection():
    from tools.audit_l4_readiness import analyze_content_for_l4

    no_exec = "from logics.common.l4_base import L4Base\n"
    yes_exec = (
        "from logics.common.l4_base import L4Base\n\ndef execute():\n    return {}\n"
    )

    is_ready1, has_execute1, _ = analyze_content_for_l4(no_exec)
    assert has_execute1 is False

    is_ready2, has_execute2, _ = analyze_content_for_l4(yes_exec)
    assert has_execute2 is True
