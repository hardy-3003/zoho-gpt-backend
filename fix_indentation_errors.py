#!/usr/bin/env python3
"""
Fix indentation errors in logic files.
The issue is malformed indentation after the first fix.
"""

import os
import re
from pathlib import Path


def fix_indentation_in_file(file_path: str) -> bool:
    """Fix indentation error in a single logic file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file has the indentation error pattern
        if (
            "            try:" in content
            and "    from helpers.history_store import append_event" in content
        ):
            # Fix the malformed indentation
            lines = content.split("\n")
            fixed_lines = []

            for i, line in enumerate(lines):
                if line.strip() == "try:":
                    # Fix the try block indentation
                    fixed_lines.append("try:")
                elif line.strip() == "from helpers.history_store import append_event":
                    # Fix the import indentation
                    fixed_lines.append(
                        "    from helpers.history_store import append_event"
                    )
                elif line.strip() == "except Exception:  # pragma: no cover":
                    # Fix the except block indentation
                    fixed_lines.append("except Exception:  # pragma: no cover")
                elif (
                    line.strip()
                    == "def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore"
                ):
                    # Fix the function definition indentation
                    fixed_lines.append(
                        "    def append_event(_logic_id: str, _data: Dict[str, Any]) -> None:  # type: ignore"
                    )
                elif line.strip() == "return None":
                    # Fix the return statement indentation
                    fixed_lines.append("        return None")
                elif "return {}LOGIC_META" in line:
                    # Fix the LOGIC_META line
                    indent = len(line) - len(line.lstrip())
                    indent_str = " " * indent
                    fixed_lines.append(f"{indent_str}LOGIC_META = {{")
                else:
                    fixed_lines.append(line)

            fixed_content = "\n".join(fixed_lines)

            # Write back the fixed content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)

            print(f"Fixed indentation: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix indentation errors in all logic files."""
    logics_dir = Path("logics")
    if not logics_dir.exists():
        print("logics directory not found")
        return

    fixed_count = 0
    total_files = 0

    for logic_file in logics_dir.glob("logic_*.py"):
        total_files += 1
        if fix_indentation_in_file(str(logic_file)):
            fixed_count += 1

    print(f"\nSummary:")
    print(f"Total logic files checked: {total_files}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with no issues: {total_files - fixed_count}")


if __name__ == "__main__":
    main()
