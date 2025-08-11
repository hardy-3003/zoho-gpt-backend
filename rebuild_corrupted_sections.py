#!/usr/bin/env python3
"""
Rebuild corrupted sections in logic files.
"""

import os
import re
from pathlib import Path


def rebuild_corrupted_sections(file_path: str) -> bool:
    """Rebuild corrupted sections in a single logic file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if file needs rebuilding
        if (
            "except Exception as e:" in content
            and 'violations.append(f"validation_error: {str(e)}")' in content
        ):
            # This section is corrupted, rebuild it
            lines = content.split("\n")
            fixed_lines = []

            for i, line in enumerate(lines):
                # Skip the corrupted section and rebuild it
                if "except Exception as e:" in line:
                    # Find the matching try statement
                    try_line = None
                    for j in range(i - 1, -1, -1):
                        if "try:" in lines[j]:
                            try_line = j
                            break

                    if try_line is not None:
                        # Rebuild the try-except block properly
                        try_indent = len(lines[try_line]) - len(
                            lines[try_line].lstrip()
                        )
                        indent_str = " " * try_indent

                        # Add the proper except block
                        fixed_lines.append(f"{indent_str}    except Exception as e:")
                        fixed_lines.append(
                            f'{indent_str}        violations.append(f"validation_error: {{str(e)}}")'
                        )

                        # Skip the next few lines that are corrupted
                        skip_count = 0
                        for k in range(i + 1, len(lines)):
                            if "return violations" in lines[k]:
                                break
                            skip_count += 1

                        # Add the return statement
                        fixed_lines.append(f"{indent_str}")
                        fixed_lines.append(f"{indent_str}    return violations")

                        # Skip the corrupted lines
                        i += skip_count + 1
                        continue

                fixed_lines.append(line)

            content = "\n".join(fixed_lines)

        # Fix any remaining malformed try blocks
        content = re.sub(r"try:\s*\n\s*try:", "try:", content)
        content = re.sub(
            r"except\s+Exception\s*:\s*\n\s*except\s+Exception\s*:",
            "except Exception:",
            content,
        )

        # Write back if any changes were made
        if "except Exception as e:" in content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Rebuilt corrupted sections: {file_path}")
            return True

        return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Rebuild corrupted sections in all logic files."""
    logics_dir = Path("logics")
    if not logics_dir.exists():
        print("logics directory not found")
        return

    fixed_count = 0
    total_files = 0

    for logic_file in logics_dir.glob("logic_*.py"):
        total_files += 1
        if rebuild_corrupted_sections(str(logic_file)):
            fixed_count += 1

    print(f"\nSummary:")
    print(f"Total logic files checked: {total_files}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files with no issues: {total_files - fixed_count}")


if __name__ == "__main__":
    main()
