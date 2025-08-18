#!/usr/bin/env python3
"""
Repo Inventory Scanner — Task P1.5.2

Scans `logics/` for files matching `logic_{id}_{slug}.py` and produces:
- artifacts/repo_logics.json
- artifacts/master_vs_repo_report.json

Exit codes:
- 0: inventories match (no diffs)
- 3: mismatches detected (any diff list non-empty)
- 2: parsing/determinism errors

Deterministic output: stable sorting, normalized paths, sorted keys.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
LOGICS_DIR = ROOT / "logics"
ARTIFACTS_DIR = ROOT / "artifacts"
MASTER_INDEX_PATH = ARTIFACTS_DIR / "master_index.json"
DEFAULT_REPO_INVENTORY = ARTIFACTS_DIR / "repo_logics.json"
DEFAULT_REPORT = ARTIFACTS_DIR / "master_vs_repo_report.json"


LOGIC_FILENAME_RE = re.compile(r"^logic_(\d{3})_([a-z0-9_]+)\.py$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def snake_to_kebab(name: str) -> str:
    return name.replace("_", "-")


@dataclass(frozen=True)
class RepoLogic:
    id: int
    slug: str
    path: str
    present: bool


def scan_repo_logics(base: Path) -> Tuple[List[RepoLogic], Dict[int, List[str]]]:
    entries: List[RepoLogic] = []
    id_to_paths: Dict[int, List[str]] = {}

    for child in sorted(base.iterdir(), key=lambda p: p.name):
        if not child.is_file():
            continue
        m = LOGIC_FILENAME_RE.match(child.name)
        if not m:
            continue
        id_str, slug_snake = m.groups()
        try:
            logic_id = int(id_str)
        except ValueError:
            raise ValueError(f"Invalid ID in filename: {child.name}")
        slug = snake_to_kebab(slug_snake)
        if not KEBAB_RE.match(slug):
            raise ValueError(f"Derived slug not kebab-case: {slug} from {child.name}")
        rel_path = child.relative_to(ROOT).as_posix()
        entries.append(RepoLogic(id=logic_id, slug=slug, path=rel_path, present=True))
        id_to_paths.setdefault(logic_id, []).append(rel_path)

    # Deterministic sorting by id then slug
    entries.sort(key=lambda e: (e.id, e.slug))
    return entries, id_to_paths


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stable formatting: sorted keys, newline at EOF
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
        f.write("\n")


def build_report(
    master_index: List[dict],
    repo_entries: List[RepoLogic],
    id_to_paths: Dict[int, List[str]],
):
    master_by_id: Dict[int, dict] = {int(x["id"]): x for x in master_index}
    repo_by_id: Dict[int, RepoLogic] = {e.id: e for e in repo_entries}

    # missing_in_repo: present in MASTER, absent in repo
    missing_in_repo: List[dict] = []
    for mid in sorted(master_by_id.keys()):
        if mid not in repo_by_id:
            m = master_by_id[mid]
            missing_in_repo.append(
                {
                    "id": mid,
                    "slug": m["slug"],
                    "expected_path": m["path"],
                }
            )

    # extra_in_repo: present in repo, not in MASTER
    extra_in_repo: List[dict] = []
    for rid in sorted(repo_by_id.keys()):
        if rid not in master_by_id:
            r = repo_by_id[rid]
            extra_in_repo.append({"id": rid, "slug": r.slug, "path": r.path})

    # slug_mismatches and path_mismatches
    slug_mismatches: List[dict] = []
    path_mismatches: List[dict] = []
    for cid in sorted(set(master_by_id.keys()).intersection(repo_by_id.keys())):
        m = master_by_id[cid]
        r = repo_by_id[cid]
        if m.get("slug") != r.slug:
            slug_mismatches.append(
                {
                    "id": cid,
                    "expected_slug": m.get("slug"),
                    "repo_slug": r.slug,
                    "expected_path": m.get("path"),
                    "repo_path": r.path,
                }
            )
        if m.get("path") != r.path:
            path_mismatches.append(
                {
                    "id": cid,
                    "expected_path": m.get("path"),
                    "repo_path": r.path,
                }
            )

    # duplicate_ids
    duplicate_ids: List[dict] = []
    for did in sorted(id_to_paths.keys()):
        paths = sorted(id_to_paths[did])
        if len(paths) > 1:
            duplicate_ids.append({"id": did, "paths": paths})

    # Deterministic sort for object lists
    missing_in_repo.sort(key=lambda x: (x["id"], x["slug"]))
    extra_in_repo.sort(key=lambda x: (x["id"], x["slug"]))
    slug_mismatches.sort(key=lambda x: (x["id"], x["expected_slug"], x["repo_slug"]))
    path_mismatches.sort(key=lambda x: (x["id"], x["expected_path"], x["repo_path"]))
    duplicate_ids.sort(key=lambda x: x["id"])  # paths already sorted

    report = {
        "missing_in_repo": missing_in_repo,
        "extra_in_repo": extra_in_repo,
        "slug_mismatches": slug_mismatches,
        "path_mismatches": path_mismatches,
        "duplicate_ids": duplicate_ids,
    }
    return report


def summarize(report: dict) -> str:
    counts = {
        k: len(report.get(k, []))
        for k in [
            "missing_in_repo",
            "extra_in_repo",
            "slug_mismatches",
            "path_mismatches",
            "duplicate_ids",
        ]
    }
    return (
        "Repo Inventory Summary: "
        f"missing={counts['missing_in_repo']} "
        f"extra={counts['extra_in_repo']} "
        f"slug_mismatch={counts['slug_mismatches']} "
        f"path_mismatch={counts['path_mismatches']} "
        f"duplicate_ids={counts['duplicate_ids']}"
    )


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan repo logics and compare with MASTER index"
    )
    parser.add_argument(
        "--output-inventory",
        type=Path,
        default=DEFAULT_REPO_INVENTORY,
        help="Path to write repo_logics.json",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=DEFAULT_REPORT,
        help="Path to write master_vs_repo_report.json",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print human-readable summary counts",
    )

    args = parser.parse_args(argv)

    try:
        repo_entries, id_to_paths = scan_repo_logics(LOGICS_DIR)
        # Convert to plain dicts for JSON emission
        repo_json = [asdict(e) for e in repo_entries]
        write_json(args.output_inventory, repo_json)

        master_index = read_json(MASTER_INDEX_PATH)
        report = build_report(master_index, repo_entries, id_to_paths)
        write_json(args.output_report, report)

        if args.summary:
            print(summarize(report))

        has_diffs = any(len(report[k]) > 0 for k in report.keys())
        return 3 if has_diffs else 0
    except Exception as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
