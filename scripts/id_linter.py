#!/usr/bin/env python3
"""
ID Range/Collision Linter for Zoho GPT Backend

Task P1.1.3 — ID-Range/Collision Linter

This script enforces:
- Every logic file follows the `logic_{id}_{name}.py` pattern
- IDs are sequential (1 → 231), no gaps or duplicates
- No collision of IDs or duplicate filenames
- Clear error messages with non-zero exit codes on violation

Usage:
    python scripts/id_linter.py
    just id-lint
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class LogicFile:
    """Represents a logic file with its metadata."""

    path: Path
    id: int
    name: str
    filename: str


@dataclass
class LinterResult:
    """Result of the linter check."""

    success: bool
    errors: List[str]
    warnings: List[str]
    found_ids: Set[int]
    duplicate_ids: Set[int]
    missing_ids: Set[int]
    invalid_files: List[LogicFile]


class IDLinter:
    """Linter for logic file ID policy enforcement."""

    def __init__(
        self, logics_dir: str = "logics", expected_range: Tuple[int, int] = (1, 231)
    ):
        self.logics_dir = Path(logics_dir)
        self.expected_range = expected_range
        self.expected_ids = set(range(expected_range[0], expected_range[1] + 1))

        # Regex pattern for logic file naming
        self.filename_pattern = re.compile(r"^logic_(\d{3})_(.+)\.py$")

    def scan_logic_files(self) -> List[LogicFile]:
        """Scan the logics directory for logic files."""
        logic_files = []

        if not self.logics_dir.exists():
            raise FileNotFoundError(f"Logics directory not found: {self.logics_dir}")

        for file_path in self.logics_dir.glob("logic_*.py"):
            match = self.filename_pattern.match(file_path.name)
            if match:
                logic_id = int(match.group(1))
                logic_name = match.group(2)
                logic_files.append(
                    LogicFile(
                        path=file_path,
                        id=logic_id,
                        name=logic_name,
                        filename=file_path.name,
                    )
                )
            else:
                # Invalid filename pattern
                logic_files.append(
                    LogicFile(
                        path=file_path,
                        id=-1,  # Invalid ID
                        name="",
                        filename=file_path.name,
                    )
                )

        return logic_files

    def validate_filename_pattern(self, logic_files: List[LogicFile]) -> List[str]:
        """Validate that all files follow the correct naming pattern."""
        errors = []

        for logic_file in logic_files:
            if logic_file.id == -1:  # Invalid pattern
                errors.append(
                    f"Invalid filename pattern: {logic_file.filename} "
                    f"(expected: logic_XXX_name.py where XXX is 3-digit ID)"
                )

        return errors

    def check_id_range_and_duplicates(
        self, logic_files: List[LogicFile]
    ) -> Tuple[Set[int], Set[int], Set[int]]:
        """Check for ID range compliance and duplicates."""
        found_ids = set()
        duplicate_ids = set()

        # Check for duplicates and collect found IDs
        id_counts = defaultdict(list)
        for logic_file in logic_files:
            if logic_file.id != -1:  # Skip invalid files
                id_counts[logic_file.id].append(logic_file)
                found_ids.add(logic_file.id)

        # Find duplicates
        for logic_id, files in id_counts.items():
            if len(files) > 1:
                duplicate_ids.add(logic_id)

        # Find missing IDs
        missing_ids = self.expected_ids - found_ids

        return found_ids, duplicate_ids, missing_ids

    def check_out_of_range_ids(self, logic_files: List[LogicFile]) -> List[str]:
        """Check for IDs outside the expected range."""
        errors = []

        for logic_file in logic_files:
            if logic_file.id != -1:  # Skip invalid files
                if (
                    logic_file.id < self.expected_range[0]
                    or logic_file.id > self.expected_range[1]
                ):
                    errors.append(
                        f"ID out of range: {logic_file.filename} "
                        f"(ID {logic_file.id} not in range {self.expected_range[0]}-{self.expected_range[1]})"
                    )

        return errors

    def check_duplicate_filenames(self, logic_files: List[LogicFile]) -> List[str]:
        """Check for duplicate filenames (case-insensitive)."""
        errors = []
        filename_counts = defaultdict(list)

        for logic_file in logic_files:
            filename_counts[logic_file.filename.lower()].append(logic_file)

        for filename_lower, files in filename_counts.items():
            if len(files) > 1:
                original_filenames = [f.filename for f in files]
                errors.append(
                    f"Duplicate filename detected: {original_filenames} "
                    f"(case-insensitive match: {filename_lower})"
                )

        return errors

    def generate_summary(
        self, found_ids: Set[int], missing_ids: Set[int], duplicate_ids: Set[int]
    ) -> List[str]:
        """Generate a summary of the ID coverage."""
        summary = []

        total_expected = len(self.expected_ids)
        total_found = len(found_ids)
        total_missing = len(missing_ids)
        total_duplicates = len(duplicate_ids)

        summary.append(f"ID Coverage Summary:")
        summary.append(
            f"  Expected IDs: {self.expected_range[0]}-{self.expected_range[1]} ({total_expected} total)"
        )
        summary.append(f"  Found IDs: {total_found}")
        summary.append(f"  Missing IDs: {total_missing}")
        summary.append(f"  Duplicate IDs: {total_duplicates}")

        if missing_ids:
            missing_list = sorted(list(missing_ids))
            summary.append(f"  Missing ID list: {missing_list}")

        if duplicate_ids:
            duplicate_list = sorted(list(duplicate_ids))
            summary.append(f"  Duplicate ID list: {duplicate_list}")

        return summary

    def run(self) -> LinterResult:
        """Run the complete linter check."""
        errors = []
        warnings = []

        try:
            # Scan for logic files
            logic_files = self.scan_logic_files()

            # Validate filename patterns
            pattern_errors = self.validate_filename_pattern(logic_files)
            errors.extend(pattern_errors)

            # Check ID range and duplicates
            found_ids, duplicate_ids, missing_ids = self.check_id_range_and_duplicates(
                logic_files
            )

            # Check for out-of-range IDs
            range_errors = self.check_out_of_range_ids(logic_files)
            errors.extend(range_errors)

            # Check for duplicate filenames
            filename_errors = self.check_duplicate_filenames(logic_files)
            errors.extend(filename_errors)

            # Generate summary
            summary = self.generate_summary(found_ids, missing_ids, duplicate_ids)

            # Add missing/duplicate ID errors
            if missing_ids:
                errors.append(f"Missing logic IDs: {sorted(list(missing_ids))}")

            if duplicate_ids:
                errors.append(f"Duplicate logic IDs: {sorted(list(duplicate_ids))}")

            # Determine success
            success = len(errors) == 0

            # Add summary as warnings if there are issues
            if not success:
                warnings.extend(summary)

            return LinterResult(
                success=success,
                errors=errors,
                warnings=warnings,
                found_ids=found_ids,
                duplicate_ids=duplicate_ids,
                missing_ids=missing_ids,
                invalid_files=[f for f in logic_files if f.id == -1],
            )

        except Exception as e:
            errors.append(f"Linter error: {str(e)}")
            return LinterResult(
                success=False,
                errors=errors,
                warnings=warnings,
                found_ids=set(),
                duplicate_ids=set(),
                missing_ids=set(),
                invalid_files=[],
            )


def main():
    """Main entry point for the ID linter."""
    print("🔍 ID Range/Collision Linter for Zoho GPT Backend")
    print("=" * 60)

    # Initialize linter
    linter = IDLinter()

    # Run linter
    result = linter.run()

    # Display results
    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"   {warning}")

    if result.errors:
        print("\n❌ Errors:")
        for error in result.errors:
            print(f"   {error}")

        print(f"\n❌ Linter failed with {len(result.errors)} error(s)")
        sys.exit(1)
    else:
        print("\n✅ ID policy validation passed!")
        print(f"   Found {len(result.found_ids)} logic files")
        print(
            f"   All IDs in range {linter.expected_range[0]}-{linter.expected_range[1]} are present"
        )
        print(f"   No duplicate IDs or filenames detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
