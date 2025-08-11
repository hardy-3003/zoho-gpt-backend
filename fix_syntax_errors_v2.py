#!/usr/bin/env python3
"""
Fix widespread syntax errors in logic files with proper indentation handling.
The issue is malformed "return {}try:" lines that should be proper try-except blocks.
"""

import os
import re
from pathlib import Path


def fix_syntax_error_in_file(file_path: str) -> bool:
    """Fix syntax error in a single logic file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file has the syntax error
        if "return {}try:" not in content:
            return False

        # Fix the malformed line with proper structure
        # Pattern: "return {}try:" should be replaced with proper try-except structure
        # We need to handle the indentation properly

        # First, find the problematic line and its context
        lines = content.split("\n")
        fixed_lines = []

        for i, line in enumerate(lines):
            if "return {}try:" in line:
                # Get the indentation of the current line
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent

                # Replace the malformed line with proper structure
                fixed_lines.append(f"{indent_str}try:")
                fixed_lines.append(
                    f"{indent_str}    from helpers.history_store import append_event"
                )
                fixed_lines.append(f"{indent_str}except Exception:  # pragma: no cover")
                fixed_lines.append(
                    f"{indent_str}    def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore"
                )
                fixed_lines.append(f"{indent_str}        return None")
            else:
                fixed_lines.append(line)

        fixed_content = "\n".join(fixed_lines)

        # Write back the fixed content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)

        print(f"Fixed: {file_path}")
        return True

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix syntax errors in all logic files."""
    logics_dir = Path("logics")
    if not logics_dir.exists():
        print("logics directory not found")
        return

    fixed_count = 0
    total_files = 0

    for logic_file in logics_dir.glob("logic_*.py"):
        total_files += 1
        if fix_syntax_error_in_file(str(logic_file)):
            fixed_count += 1

    print(f"\nSummary:")
    print(f"Total logic files checked: {total_files}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with no issues: {total_files - fixed_count}")


if __name__ == "__main__":
    main()
