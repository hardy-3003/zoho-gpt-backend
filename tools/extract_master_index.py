#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple


MASTER_PATH = os.path.join(os.getcwd(), "MASTER_SCOPE_OF_WORK.md")
LOGICS_DIR = os.path.join(os.getcwd(), "logics")
OUTPUT_PATH = os.path.join(os.getcwd(), "artifacts", "master_index.json")


NUM_AUTHORITY = 231


@dataclass(frozen=True)
class MasterEntry:
    id: int
    title: str


FILENAME_RE = re.compile(r"^logic_(\d{3})_([a-z0-9_]+)\.py$")


def slugify_kebab(text: str) -> str:
    # Normalize whitespace and punctuation → kebab-case
    lowered = text.strip().lower()
    # Replace all non-alphanumeric with '-'
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    slug = slug.strip("-")
    # Collapse multiple '-'
    slug = re.sub(r"-+", "-", slug)
    return slug


def kebab_to_snake(kebab: str) -> str:
    return kebab.replace("-", "_")


def parse_master_entries(master_md: str) -> List[MasterEntry]:
    # Find section 12) Master Logic Index
    start_idx = master_md.find("12) Master Logic Index")
    if start_idx == -1:
        raise RuntimeError(
            "Could not find '12) Master Logic Index' section in MASTER_SCOPE_OF_WORK.md"
        )
    tail = master_md[start_idx:]
    # End before section 13)
    end_marker = "13) DevEx"
    end_idx = tail.find(end_marker)
    if end_idx != -1:
        section = tail[:end_idx]
    else:
        section = tail

    entries: List[MasterEntry] = []
    # Match enumerated lines like: '123. Title ...'
    line_re = re.compile(r"^\s*(\d{1,3})\.\s+(.+?)\s*$")
    for raw_line in section.splitlines():
        m = line_re.match(raw_line)
        if not m:
            continue
        logic_id = int(m.group(1))
        title_raw = m.group(2)
        # Remove trailing commentary like two spaces or nothing; keep meaningful content
        # Drop trailing bullets starting from '  - ' lines (handled by not matching them)
        # Remove surrounding quotes/backticks
        title = title_raw.strip().strip("`")
        entries.append(MasterEntry(id=logic_id, title=title))

    # Basic validations
    if not entries:
        raise RuntimeError("No enumerated entries found in MASTER scope section 12")
    # Sort by id to be safe (though they are ordered)
    entries.sort(key=lambda e: e.id)
    return entries


def scan_existing_logic_files(directory: str) -> Dict[int, str]:
    id_to_filename: Dict[int, str] = {}
    for fname in os.listdir(directory):
        m = FILENAME_RE.match(fname)
        if not m:
            continue
        num = int(m.group(1))
        # Prefer lexicographically smallest if duplicates (should not happen)
        if num not in id_to_filename or fname < id_to_filename[num]:
            id_to_filename[num] = fname
    return id_to_filename


def build_master_index(
    entries: List[MasterEntry], id_to_filename: Dict[int, str]
) -> List[Dict[str, object]]:
    result: List[Dict[str, object]] = []
    for e in entries:
        filename = id_to_filename.get(e.id)
        if filename:
            # Use the actual filename to derive slug
            m = FILENAME_RE.match(filename)
            suffix_snake = m.group(2) if m else ""
            slug = (
                slugify_kebab(suffix_snake.replace("_", "-"))
                if suffix_snake
                else slugify_kebab(e.title)
            )
            status = "present"
            path = os.path.join("logics", filename)
        else:
            slug = slugify_kebab(e.title)
            status = "planned"
            path = os.path.join("logics", f"logic_{e.id:03d}_{kebab_to_snake(slug)}.py")

        # Preserve dict key order for deterministic JSON
        item = {
            "id": e.id,
            "slug": slug,
            "title": e.title,
            "phase": "P1",
            "status": status,
            "path": path,
        }
        result.append(item)

    # Deterministic sort by id
    result.sort(key=lambda d: int(d["id"]))
    return result


def validate_index(index: List[Dict[str, object]]) -> Tuple[bool, str]:
    ids = [int(x["id"]) for x in index]
    if len(index) != NUM_AUTHORITY:
        return False, f"Count mismatch: expected {NUM_AUTHORITY}, got {len(index)}"
    expected_ids = list(range(1, NUM_AUTHORITY + 1))
    if ids != expected_ids:
        return False, "IDs are not contiguous 1..231 or not sorted"
    return True, "ok"


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Extract canonical MASTER index from MASTER_SCOPE_OF_WORK.md"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_PATH,
        help="Path to write artifacts/master_index.json",
    )
    parser.add_argument(
        "--no-write", action="store_true", help="Do not write file; just validate"
    )
    parser.add_argument("--summary", action="store_true", help="Print a human summary")
    args = parser.parse_args(argv)

    try:
        with open(MASTER_PATH, "r", encoding="utf-8") as f:
            master_md = f.read()
    except FileNotFoundError:
        print(f"MASTER file not found: {MASTER_PATH}", file=sys.stderr)
        return 2

    entries = parse_master_entries(master_md)
    # Trim entries to exactly 1..231; ignore any stray numbering outside range
    entries = [e for e in entries if 1 <= e.id <= NUM_AUTHORITY]

    id_to_filename = scan_existing_logic_files(LOGICS_DIR)
    index = build_master_index(entries, id_to_filename)

    ok, msg = validate_index(index)
    if not ok:
        print(f"Validation failed: {msg}", file=sys.stderr)
        return 3

    if not args.no_write:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        # Deterministic JSON output
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            f.write("\n")

    if args.summary:
        present = sum(1 for x in index if x.get("status") == "present")
        planned = len(index) - present
        print(
            f"MASTER index: {len(index)} items (present={present}, planned={planned}) → {args.output}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
