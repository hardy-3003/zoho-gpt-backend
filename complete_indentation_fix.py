#!/usr/bin/env python3
"""
Complete indentation fix for all logic files.
"""

import os
import re
from pathlib import Path


def fix_indentation_completely(file_path: str) -> bool:
    """Fix all indentation issues in a single logic file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file needs fixing
        needs_fix = False

        # Fix 1: Fix missing indentation after try statements
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            # Check if this line is a try statement that needs proper indentation
            if line.strip() == "try:" and i > 0:
                # Get the indentation of the previous line
                prev_line = lines[i - 1]
                if prev_line.strip().endswith(":"):
                    # This try should be indented under the previous line
                    prev_indent = len(prev_line) - len(prev_line.lstrip())
                    new_indent = " " * (prev_indent + 4)
                    fixed_lines.append(new_indent + "try:")
                    needs_fix = True
                    continue

            # Check if this line is an except statement that needs proper indentation
            if line.strip().startswith("except") and i > 0:
                # Find the matching try statement
                try_indent = None
                for j in range(i - 1, -1, -1):
                    if lines[j].strip() == "try:":
                        try_indent = len(lines[j]) - len(lines[j].lstrip())
                        break

                if try_indent is not None:
                    fixed_lines.append(" " * try_indent + line.strip())
                    needs_fix = True
                    continue

            fixed_lines.append(line)

        if needs_fix:
            content = "\n".join(fixed_lines)

        # Fix 2: Fix any remaining malformed blocks
        # Replace any remaining problematic patterns
        content = re.sub(r"(\s+)try:\s*\n\s*try:", r"\1try:", content)
        content = re.sub(
            r"(\s+)except\s+Exception\s*:\s*\n\s*except\s+Exception\s*:",
            r"\1except Exception:",
            content,
        )

        # Write back if any changes were made
        if needs_fix or "try:\ntry:" in content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed indentation: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix all logic files comprehensively."""
    logics_dir = Path("logics")
    if not logics_dir.exists():
        print("logics directory not found")
        return

    fixed_count = 0
    total_files = 0

    for logic_file in logics_dir.glob("logic_*.py"):
        total_files += 1
        if fix_indentation_completely(str(logic_file)):
            fixed_count += 1

    print(f"\nSummary:")
    print(f"Total logic files checked: {total_files}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with no issues: {total_files - fixed_count}")


if __name__ == "__main__":
    main()
