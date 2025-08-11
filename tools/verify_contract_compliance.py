#!/usr/bin/env python3
"""
Verify logic module contract compliance.

This script checks that all logic modules follow the standardized contract.
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Any


def extract_docstring_info(logic_file: Path) -> Dict[str, Any]:
    """Extract docstring information from a logic file."""
    with open(logic_file, "r") as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        module_docstring = ast.get_docstring(tree)
    except:
        module_docstring = None

    return {
        "has_docstring": module_docstring is not None,
        "docstring": module_docstring,
        "docstring_length": len(module_docstring) if module_docstring else 0,
    }


def extract_logic_meta_info(logic_file: Path) -> Dict[str, Any]:
    """Extract LOGIC_META information from a logic file."""
    with open(logic_file, "r") as f:
        content = f.read()

    # Look for LOGIC_META
    meta_match = re.search(r"LOGIC_META\s*=\s*{([^}]+)}", content)
    if not meta_match:
        return {"has_meta": False}

    meta_content = meta_match.group(1)

    # Extract fields
    id_match = re.search(r'"id":\s*"([^"]+)"', meta_content)
    title_match = re.search(r'"title":\s*"([^"]+)"', meta_content)
    tags_match = re.search(r'"tags":\s*\[([^\]]+)\]', meta_content)

    return {
        "has_meta": True,
        "has_id": id_match is not None,
        "has_title": title_match is not None,
        "has_tags": tags_match is not None,
        "id": id_match.group(1) if id_match else None,
        "title": title_match.group(1) if title_match else None,
        "tags": tags_match.group(1) if tags_match else None,
    }


def extract_function_info(logic_file: Path) -> Dict[str, Any]:
    """Extract function information from a logic file."""
    with open(logic_file, "r") as f:
        content = f.read()

    # Check for required functions
    has_handle = "def handle(" in content
    has_handle_l4 = "def handle_l4(" in content
    has_handle_impl = "def handle_impl(" in content

    return {
        "has_handle": has_handle,
        "has_handle_l4": has_handle_l4,
        "has_handle_impl": has_handle_impl,
    }


def extract_import_info(logic_file: Path) -> Dict[str, Any]:
    """Extract import information from a logic file."""
    with open(logic_file, "r") as f:
        content = f.read()

    # Check for required imports
    has_l4_runtime = "from logics.l4_contract_runtime import" in content
    has_typing = "from typing import" in content or "import typing" in content

    return {"has_l4_runtime": has_l4_runtime, "has_typing": has_typing}


def verify_contract_compliance(logic_file: Path) -> Dict[str, Any]:
    """Verify contract compliance for a single logic file."""
    docstring_info = extract_docstring_info(logic_file)
    meta_info = extract_logic_meta_info(logic_file)
    function_info = extract_function_info(logic_file)
    import_info = extract_import_info(logic_file)

    # Define compliance rules
    compliance_issues = []

    # Docstring requirements
    if not docstring_info["has_docstring"]:
        compliance_issues.append("missing_docstring")
    elif docstring_info["docstring_length"] < 50:
        compliance_issues.append("docstring_too_short")

    # LOGIC_META requirements
    if not meta_info["has_meta"]:
        compliance_issues.append("missing_logic_meta")
    else:
        if not meta_info["has_id"]:
            compliance_issues.append("missing_meta_id")
        if not meta_info["has_title"]:
            compliance_issues.append("missing_meta_title")
        if not meta_info["has_tags"]:
            compliance_issues.append("missing_meta_tags")

    # Function requirements
    if not function_info["has_handle"]:
        compliance_issues.append("missing_handle_function")
    if not function_info["has_handle_l4"]:
        compliance_issues.append("missing_handle_l4_function")

    # Import requirements
    if not import_info["has_l4_runtime"]:
        compliance_issues.append("missing_l4_runtime_import")
    if not import_info["has_typing"]:
        compliance_issues.append("missing_typing_import")

    return {
        "file": str(logic_file),
        "compliant": len(compliance_issues) == 0,
        "issues": compliance_issues,
        "docstring_info": docstring_info,
        "meta_info": meta_info,
        "function_info": function_info,
        "import_info": import_info,
    }


def generate_compliance_report(logics_dir: Path) -> Dict[str, Any]:
    """Generate a comprehensive compliance report."""
    logic_files = sorted(logics_dir.glob("logic_*.py"))

    compliance_results = []
    total_files = len(logic_files)
    compliant_files = 0

    for logic_file in logic_files:
        result = verify_contract_compliance(logic_file)
        compliance_results.append(result)
        if result["compliant"]:
            compliant_files += 1

    # Calculate statistics
    compliance_rate = (compliant_files / total_files) * 100 if total_files > 0 else 0

    # Group issues by type
    issue_counts = {}
    for result in compliance_results:
        for issue in result["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    return {
        "total_files": total_files,
        "compliant_files": compliant_files,
        "non_compliant_files": total_files - compliant_files,
        "compliance_rate": compliance_rate,
        "issue_counts": issue_counts,
        "results": compliance_results,
    }


def main():
    """Main function to run compliance verification."""
    logics_dir = Path("logics")

    if not logics_dir.exists():
        print("Error: logics directory not found")
        return

    print("Verifying logic module contract compliance...")
    report = generate_compliance_report(logics_dir)

    # Print summary
    print(f"\n=== COMPLIANCE REPORT ===")
    print(f"Total files: {report['total_files']}")
    print(f"Compliant files: {report['compliant_files']}")
    print(f"Non-compliant files: {report['non_compliant_files']}")
    print(f"Compliance rate: {report['compliance_rate']:.1f}%")

    # Print issue breakdown
    if report["issue_counts"]:
        print(f"\n=== ISSUE BREAKDOWN ===")
        for issue, count in sorted(report["issue_counts"].items()):
            print(f"{issue}: {count} files")

    # Print non-compliant files
    non_compliant = [r for r in report["results"] if not r["compliant"]]
    if non_compliant:
        print(f"\n=== NON-COMPLIANT FILES ===")
        for result in non_compliant[:10]:  # Show first 10
            print(f"{result['file']}: {', '.join(result['issues'])}")

        if len(non_compliant) > 10:
            print(f"... and {len(non_compliant) - 10} more files")

    # Print recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    if report["compliance_rate"] < 80:
        print(
            "⚠️  Low compliance rate. Focus on fixing missing LOGIC_META and docstrings."
        )
    elif report["compliance_rate"] < 95:
        print(
            "⚠️  Moderate compliance rate. Address remaining issues for production readiness."
        )
    else:
        print("✅ High compliance rate. System is ready for production.")

    if report["issue_counts"].get("missing_logic_meta", 0) > 0:
        print("🔧 Priority: Add LOGIC_META to all logic files")
    if report["issue_counts"].get("missing_docstring", 0) > 0:
        print("🔧 Priority: Add docstrings to all logic files")
    if report["issue_counts"].get("missing_handle_function", 0) > 0:
        print("🔧 Priority: Ensure all logic files have handle() function")


if __name__ == "__main__":
    main()
