#!/usr/bin/env python3
import os
import re
import sys


def apply_l4_wrapper_to_file(filepath: str, logic_id: str):
    """Apply additive L4 wrapper to a logic file."""

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already has L4 wrapper
    if "from helpers.learning_hooks import score_confidence" in content:
        print(f"  {filepath}: already has L4 wrapper")
        return False

    # Find the existing handle function
    handle_match = re.search(r"def handle\([^)]*\)[^:]*:\s*", content)
    if not handle_match:
        print(f"  {filepath}: no handle function found")
        return False

    # Extract the function name that the existing handle calls (if any)
    # Look for patterns like: result = compute(payload) or similar
    compute_match = re.search(r"result\s*=\s*(\w+)\(payload\)", content)
    compute_func = compute_match.group(1) if compute_match else "compute"

    # Create the L4 wrapper imports
    imports = """from helpers.learning_hooks import score_confidence
from helpers.history_store import log_with_deltas_and_anomalies
from helpers.rules_engine import validate_accounting
from helpers.provenance import make_provenance
from helpers.schema_registry import validate_output_contract

LOGIC_ID = "{}"
""".format(
        logic_id
    )

    # Create the L4 wrapper function
    wrapper = """
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    # === Keep existing deterministic compute as-is (AEP §6 No Rewrites) ===
    # If this module uses a different function name (e.g., run/execute/build_report), use that name here.
    result = {}(payload)  # replace name if different in this file

    # Validations (non-fatal)
    validations_failed = 0
    try:
        validate_accounting(result)
    except Exception:
        validations_failed += 1

    # Minimal provenance (expand per-figure later per MSOW §2)
    prov = make_provenance(
        result={{"endpoint":"reports/auto","ids":[],"filters":{{"period": payload.get("period")}}}}
    )

    # History + Deltas + Anomalies (MSOW §5)
    alerts_pack = log_with_deltas_and_anomalies(
        LOGIC_ID, payload, result, prov, period_key=payload.get("period")
    )

    # Confidence (learnable; AEP §1)
    confidence = score_confidence(
        sample_size=max(1, len(result) if hasattr(result, "__len__") else 1),
        anomalies=len(alerts_pack.get("anomalies", [])),
        validations_failed=validations_failed,
    )

    output = {{
        "result": result,
        "provenance": prov,
        "confidence": confidence,
        "alerts": alerts_pack.get("alerts", []),
    }}
    validate_output_contract(output)
    return output
""".format(
        compute_func
    )

    # Insert imports after existing imports
    import_pattern = r"(from typing import[^\n]*\n)"
    import_match = re.search(import_pattern, content)
    if import_match:
        new_content = content.replace(
            import_match.group(1), import_match.group(1) + imports + "\n"
        )
    else:
        # If no typing import, add after the docstring
        docstring_end = content.find('"""', content.find('"""') + 3) + 3
        new_content = content[:docstring_end] + "\n" + imports + content[docstring_end:]

    # Replace the existing handle function with the wrapper
    handle_start = handle_match.start()
    # Find the end of the handle function (look for the next function or end of file)
    lines = new_content[handle_start:].split("\n")
    indent_level = len(lines[0]) - len(lines[0].lstrip())
    end_idx = 0
    for i, line in enumerate(lines[1:], 1):
        if (
            line.strip()
            and not line.startswith(" " * (indent_level + 1))
            and line.strip().startswith("def ")
        ):
            end_idx = i
            break
    if end_idx == 0:
        end_idx = len(lines)

    # Replace the handle function
    before_handle = new_content[:handle_start]
    after_handle = new_content[handle_start:].split("\n")[end_idx:]
    after_handle = "\n".join(after_handle) if after_handle else ""

    new_content = before_handle + wrapper + "\n" + after_handle

    # Write the updated content
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  {filepath}: applied L4 wrapper")
    return True


def main():
    # Apply to files 041-060
    for i in range(41, 61):
        logic_id = f"L-{i:03d}"
        pattern = f"logics/logic_{i:03d}_*.py"

        # Find matching files
        for filename in os.listdir("logics"):
            if filename.startswith(f"logic_{i:03d}_") and filename.endswith(".py"):
                filepath = os.path.join("logics", filename)
                apply_l4_wrapper_to_file(filepath, logic_id)
                break


if __name__ == "__main__":
    main()
