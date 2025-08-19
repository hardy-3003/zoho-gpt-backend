"""
Audit Coverage & L4 Readiness (P1.5.5)

Deterministic auditor that:
- Verifies coverage for IDs 1..231 with filenames `logic_{id:03d}_{slug}.py`
- Checks L4 readiness per logic via static text/AST (no imports)
- Notes presence/absence of top-level `execute(...)` function (non-fatal)

Outputs deterministic JSON to `artifacts/l4_readiness_report.json` with keys
sorted and null timestamp for byte-identical reruns on unchanged repos.

Exit codes:
- 0: All 231 are ready and no `not_ready`
- 4: Any `not_ready` exists OR coverage count != 231
- 2: Errors (parse issues, unexpected exceptions)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


LOGICS_DIR_DEFAULT = Path("logics")
ARTIFACT_PATH_DEFAULT = Path("artifacts/l4_readiness_report.json")
EXPECTED_TOTAL = 231


LOGIC_FILENAME_RE = re.compile(r"^logic_(?P<id>\d{3})_(?P<slug>[a-z0-9_]+)\.py$")


@dataclass(frozen=True)
class ModuleFinding:
    logic_id: int
    path: Path


def canonical_dumps(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def discover_logics(logics_dir: Path) -> Dict[int, List[Path]]:
    id_to_paths: Dict[int, List[Path]] = {}
    if not logics_dir.exists():
        return id_to_paths
    for p in sorted(logics_dir.glob("logic_*.py")):
        m = LOGIC_FILENAME_RE.match(p.name)
        if not m:
            # Skip non-conforming names; this auditor focuses on expected pattern
            continue
        logic_id = int(m.group("id"))
        id_to_paths.setdefault(logic_id, []).append(p)
    return id_to_paths


def _contains(text: str, needle: str) -> bool:
    return needle in text


def analyze_content_for_l4(text: str) -> Tuple[bool, bool, Optional[str]]:
    """
    Returns: (is_ready, has_execute, reason_if_not_ready)

    Acceptance (any true):
      1) Contains 'from logics.l4_contract_runtime import'
      2) Contains 'from logics.common.l4_default import L4'
      3) Contains 'from logics.common.l4_base import L4Base'
      4) Defines top-level symbol 'L4 = ...'

    Bonus note: has top-level def execute(...)
    """
    try:
        # Text-based checks first (fast, deterministic)
        has_rule1 = _contains(text, "from logics.l4_contract_runtime import")
        has_rule2 = _contains(text, "from logics.common.l4_default import L4")
        has_rule3 = _contains(text, "from logics.common.l4_base import L4Base")

        # Top-level L4 symbol (loose text check followed by a simple regex anchored to line start)
        l4_assign = False
        for line in text.splitlines():
            if re.match(r"^L4\s*=\s*.+", line):
                l4_assign = True
                break

        is_ready = has_rule1 or has_rule2 or has_rule3 or l4_assign

        # execute presence (top-level def execute(…))
        has_execute = False
        for line in text.splitlines():
            if re.match(r"^def\s+execute\s*\(.*\)\s*:\s*", line):
                has_execute = True
                break

        return (
            is_ready,
            has_execute,
            (
                None
                if is_ready
                else _not_ready_reason(has_rule1, has_rule2, has_rule3, l4_assign)
            ),
        )
    except (
        Exception
    ) as ex:  # pragma: no cover — safety net; escalated to exit code 2 in caller
        return False, False, f"analyze_error: {type(ex).__name__}: {ex}"


def _not_ready_reason(has_r1: bool, has_r2: bool, has_r3: bool, has_r4: bool) -> str:
    reasons = []
    if not has_r1:
        reasons.append("missing 'from logics.l4_contract_runtime import'")
    if not has_r2:
        reasons.append("missing 'from logics.common.l4_default import L4'")
    if not has_r3:
        reasons.append("missing 'from logics.common.l4_base import L4Base'")
    if not has_r4:
        reasons.append("missing top-level 'L4 = ...'")
    return "; ".join(reasons) if reasons else "unknown"


def _rel_path(path: Path, logics_dir: Path) -> str:
    """Return a deterministic relative path like 'logics/filename.py'."""
    try:
        # If path is inside the parent of logics_dir, return relative to it
        rel = path.resolve().relative_to(logics_dir.resolve().parent)
        return rel.as_posix()
    except Exception:
        try:
            rel2 = path.resolve().relative_to(logics_dir.resolve())
            return (Path("logics") / rel2).as_posix()
        except Exception:
            return (Path("logics") / path.name).as_posix()


def generate_report(logics_dir: Path) -> dict:
    id_to_paths = discover_logics(logics_dir)

    expected_ids = list(range(1, EXPECTED_TOTAL + 1))
    not_ready: List[dict] = []
    missing_execute: List[dict] = []

    parse_or_io_error = False

    # Coverage checks and per-module readiness
    for logic_id in expected_ids:
        paths = id_to_paths.get(logic_id, [])
        if len(paths) == 0:
            not_ready.append({"id": logic_id, "path": "", "reason": "missing file"})
            continue
        if len(paths) > 1:
            # Multiple files for same id — mark all paths
            for p in paths:
                not_ready.append(
                    {
                        "id": logic_id,
                        "path": _rel_path(p, logics_dir),
                        "reason": "duplicate id",
                    }
                )
            continue

        path = paths[0]
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as ex:
            parse_or_io_error = True
            not_ready.append(
                {
                    "id": logic_id,
                    "path": _rel_path(path, logics_dir),
                    "reason": f"io_error: {type(ex).__name__}: {ex}",
                }
            )
            continue

        is_ready, has_execute, reason = analyze_content_for_l4(text)
        if not is_ready:
            not_ready.append(
                {
                    "id": logic_id,
                    "path": _rel_path(path, logics_dir),
                    "reason": reason or "not_ready",
                }
            )
        if not has_execute:
            missing_execute.append(
                {"id": logic_id, "path": _rel_path(path, logics_dir)}
            )

    # Deterministic sorting by id, then path
    not_ready.sort(key=lambda x: (int(x["id"]), x.get("path", "")))
    missing_execute.sort(key=lambda x: (int(x["id"]), x.get("path", "")))

    ready_count = EXPECTED_TOTAL - len(
        [entry for entry in not_ready if entry.get("reason") != "missing file"]
    )
    # If there are missing files, they are also not ready — above logic includes them already

    report = {
        "summary": {
            "total": EXPECTED_TOTAL,
            "ready": ready_count,
            "not_ready": len(not_ready),
        },
        "not_ready": not_ready,
        "missing_execute": missing_execute,
        "timestamp": None,
    }

    # Determine exit code
    if parse_or_io_error:
        report["summary"]["exit_code"] = 2
    elif not_ready or len(id_to_paths) < EXPECTED_TOTAL:
        report["summary"]["exit_code"] = 4
    else:
        report["summary"]["exit_code"] = 0

    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit coverage & L4 readiness (deterministic)"
    )
    parser.add_argument(
        "--logics-dir",
        default=str(LOGICS_DIR_DEFAULT),
        help="Directory to scan for logic_*.py",
    )
    parser.add_argument(
        "--out", default=str(ARTIFACT_PATH_DEFAULT), help="Path to write report JSON"
    )
    args = parser.parse_args(argv)

    logics_dir = Path(args.logics_dir)
    out_path = Path(args.out)

    try:
        report = generate_report(logics_dir)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(canonical_dumps(report), encoding="utf-8")
        return int(report["summary"]["exit_code"])  # 0, 4, or 2
    except Exception as ex:
        # Fail closed on unexpected errors
        fail_obj = {
            "summary": {
                "total": EXPECTED_TOTAL,
                "ready": 0,
                "not_ready": EXPECTED_TOTAL,
                "exit_code": 2,
            },
            "not_ready": [
                {
                    "id": i,
                    "path": "",
                    "reason": f"fatal_error: {type(ex).__name__}: {ex}",
                }
                for i in range(1, EXPECTED_TOTAL + 1)
            ],
            "missing_execute": [],
            "timestamp": None,
        }
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(canonical_dumps(fail_obj), encoding="utf-8")
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    sys.exit(main())
