#!/usr/bin/env python3
"""
Comprehensive fix for all syntax and indentation errors in logic files.
"""

import os
import re
from pathlib import Path


def fix_file_comprehensively(file_path: str) -> bool:
    """Fix all syntax and indentation errors in a single logic file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file needs fixing
        needs_fix = False

        # Fix 1: Fix malformed try blocks
        if (
            "try:" in content
            and "from helpers.history_store import append_event" in content
        ):
            # Replace the problematic try-except block with proper structure
            content = re.sub(
                r"try:\s*\n\s*from helpers\.history_store import append_event",
                "try:\n    from helpers.history_store import append_event",
                content,
            )
            needs_fix = True

        # Fix 2: Fix missing indentation after if statements
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            # Check if this line has an if statement followed by a try block
            if line.strip().startswith("if ") and line.strip().endswith(":"):
                # Look ahead to see if the next line is a try block
                if i + 1 < len(lines) and lines[i + 1].strip() == "try:":
                    # Add proper indentation to the try block
                    indent = len(line) - len(line.lstrip())
                    indent_str = " " * (indent + 4)  # Add 4 spaces for the try block
                    fixed_lines.append(line)
                    fixed_lines.append(indent_str + "try:")
                    # Skip the next line since we already added it
                    continue

            fixed_lines.append(line)

        if needs_fix or len(fixed_lines) != len(lines):
            content = "\n".join(fixed_lines)

        # Fix 3: Fix any remaining malformed LOGIC_META lines
        content = re.sub(r"return \{\}LOGIC_META", "LOGIC_META", content)

        # Fix 4: Ensure proper spacing around LOGIC_META
        content = re.sub(r"LOGIC_META\s*=\s*\{", "\nLOGIC_META = {", content)

        # Write back if any changes were made
        if (
            needs_fix
            or "return {}LOGIC_META" in content
            or "try:\n    from helpers.history_store import append_event" in content
        ):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {file_path}")
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
        if fix_file_comprehensively(str(logic_file)):
            fixed_count += 1

    print(f"\nSummary:")
    print(f"Total logic files checked: {total_files}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with no issues: {total_files - fixed_count}")


if __name__ == "__main__":
    main()
