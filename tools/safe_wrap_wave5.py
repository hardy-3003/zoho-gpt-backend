#!/usr/bin/env python3
# Usage:
#   python tools/safe_wrap_wave5.py --range 041-060          # dry-run
#   python tools/safe_wrap_wave5.py --range 041-060 --write  # apply
# Idempotent: if wrapper already present, it skips.

import os, re, argparse, ast, io, sys, textwrap

FILENAME_RE = re.compile(r"^logic_(\d{3})_([a-z0-9_]+)\.py$")

WRAPPER_IMPORTS = [
    "from helpers.learning_hooks import score_confidence",
    "from helpers.history_store import log_with_deltas_and_anomalies",
    "from helpers.rules_engine import validate_accounting",
    "from helpers.provenance import make_provenance",
    "from helpers.schema_registry import validate_output_contract",
]

WRAPPER_FUNC = """
def handle_l4(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Call legacy compute (now handle_impl). It may already return contract-shaped output.
    core_out = handle_impl(payload)

    # If core_out already looks contract-compliant, validate and return as-is.
    if isinstance(core_out, dict) and \
       all(k in core_out for k in ("result","provenance","confidence","alerts")):
        try:
            validate_output_contract(core_out)
        except Exception:
            # If legacy contract is off, fall back to wrapper path below.
            pass
        else:
            return core_out

    # Otherwise, treat core_out as the raw result payload.
    result = core_out if isinstance(core_out, dict) else {"value": core_out}

    # Non-fatal accounting validation
    validations_failed = 0
    try:
        validate_accounting(result)
    except Exception:
        validations_failed += 1

    # Minimal provenance (period-aware)
    prov = make_provenance(
        result={"endpoint": "reports/auto", "ids": [], "filters": {"period": payload.get("period")}}
    )

    # History + Deltas + Anomalies
    logic_id = globals().get("LOGIC_ID")
    alerts_pack = log_with_deltas_and_anomalies(
        logic_id if isinstance(logic_id, str) else "L-XXX",
        payload,
        result,
        prov,
        period_key=payload.get("period"),
    )

    # Confidence scorer (learnable)
    sample_size = 1
    try:
        sample_size = max(1, len(result))  # if dict, len = #keys
    except Exception:
        sample_size = 1

    confidence = score_confidence(
        sample_size=sample_size,
        anomalies=len(alerts_pack.get("anomalies", [])) if isinstance(alerts_pack, dict) else 0,
        validations_failed=validations_failed,
    )

    # Convert string alerts to dict format for schema compliance
    raw_alerts = alerts_pack.get("alerts", []) if isinstance(alerts_pack, dict) else []
    alerts = []
    for alert in raw_alerts:
        if isinstance(alert, str):
            alerts.append({"msg": alert, "level": "info"})
        elif isinstance(alert, dict):
            alerts.append(alert)
        else:
            alerts.append({"msg": str(alert), "level": "info"})
    
    output = {
        "result": result,
        "provenance": prov,
        "confidence": confidence,
        "alerts": alerts,
    }
    validate_output_contract(output)
    return output

# Export wrapper as the official handler
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    return handle_l4(payload)
""".lstrip("\n")


def list_targets(root="logics", r=None):
    for f in sorted(os.listdir(root)):
        if not f.startswith("logic_") or not f.endswith(".py"):
            continue
        m = FILENAME_RE.match(f)
        if not m:
            continue
        num3 = m.group(1)
        if r and not (r[0] <= num3 <= r[1]):
            continue
        yield os.path.join(root, f)


def module_has_wrapper(ast_mod: ast.Module) -> bool:
    # Heuristic: wrapper is present if a top-level name 'handle_l4' exists or the file imports our helpers.
    names = {
        getattr(n, "name", None) for n in ast_mod.body if isinstance(n, ast.FunctionDef)
    }
    if "handle_l4" in names:
        return True
    for n in ast_mod.body:
        if (
            isinstance(n, ast.ImportFrom)
            and n.module
            and n.module.startswith("helpers.")
        ):
            if any(
                alias.name
                in ("provenance", "history_store", "learning_hooks", "schema_registry")
                for alias in n.names
            ):
                return True
    return False


def find_handle_defs(ast_mod: ast.Module):
    handles = []
    for n in ast_mod.body:
        if isinstance(n, ast.FunctionDef) and n.name == "handle":
            handles.append(n)
    return handles


def find_handle_def(ast_mod: ast.Module):
    handles = find_handle_defs(ast_mod)
    return handles[0] if handles else None


def find_logic_id(ast_mod: ast.Module):
    # Look for a simple assignment LOGIC_ID = "L-###"
    for n in ast_mod.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "LOGIC_ID":
                    if isinstance(n.value, ast.Constant) and isinstance(
                        n.value.value, str
                    ):
                        return n.value.value
    return None


def ensure_imports(src: str) -> str:
    # Insert any missing imports after the first non-docstring, non-comment line of code.
    missing = [imp for imp in WRAPPER_IMPORTS if imp not in src]
    if not missing:
        return src
    lines = src.splitlines()
    # Find insertion point: after module docstring block and initial imports/comments.
    i = 0
    # Skip shebang and encoding
    while i < len(lines) and (
        lines[i].startswith("#!") or lines[i].startswith("# -*-")
    ):
        i += 1
    # Skip blank/comments
    while i < len(lines) and (
        not lines[i].strip() or lines[i].lstrip().startswith("#")
    ):
        i += 1
    # If docstring, skip its block
    if i < len(lines) and (
        lines[i].lstrip().startswith('"""') or lines[i].lstrip().startswith("'''")
    ):
        q = '"""' if lines[i].lstrip().startswith('"""') else "'''"
        if lines[i].count(q) >= 2:
            i += 1
        else:
            j = i + 1
            while j < len(lines) and q not in lines[j]:
                j += 1
            i = min(j + 1, len(lines))
        # Skip trailing blank/comment lines after docstring
        while i < len(lines) and (
            not lines[i].strip() or lines[i].lstrip().startswith("#")
        ):
            i += 1
    # Insert imports here
    ins = missing + [""]
    new = lines[:i] + ins + lines[i:]
    return "\n".join(new)


def rename_handle_to_impl(src: str, handle_nodes: list[ast.FunctionDef]) -> str:
    lines = src.splitlines()
    # Sort by line number in descending order to avoid line number shifts
    handle_nodes = sorted(handle_nodes, key=lambda x: x.lineno, reverse=True)

    for handle_node in handle_nodes:
        # `lineno` is 1-based; find the exact line where 'def handle(' starts.
        ln = handle_node.lineno - 1
        # Handle decorators above? If present, the ast lineno points to the 'def' line, not decorators.
        def_line = lines[ln]
        # Replace only the function name token on this line.
        new_def_line = re.sub(r"\bdef\s+handle\s*\(", "def handle_impl(", def_line)
        if new_def_line == def_line:
            # Very defensive: try replacing first 'def handle' occurrence across file
            for idx in range(len(lines)):
                if re.search(r"^\s*def\s+handle\s*\(", lines[idx]):
                    lines[idx] = re.sub(
                        r"\bdef\s+handle\s*\(", "def handle_impl(", lines[idx]
                    )
                    break
        else:
            lines[ln] = new_def_line
    return "\n".join(lines)


def append_wrapper(src: str) -> str:
    # Ensure we have typing imports needed by the signature
    need_typing = "from typing import Any, Dict"
    if need_typing not in src:
        # Prefer to add at top after other imports
        lines = src.splitlines()
        ins_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                ins_idx = i + 1
        lines.insert(ins_idx, need_typing)
        src = "\n".join(lines)
    # Append wrapper function at EOF (with a separating newline)
    if not src.endswith("\n"):
        src += "\n"
    return src + "\n" + WRAPPER_FUNC


def process_file(path: str, write: bool) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    try:
        mod = ast.parse(src)
    except SyntaxError as e:
        return {"file": path, "action": f"skip_syntax_error({e})"}

    if module_has_wrapper(mod):
        return {"file": path, "action": "skip_already_wrapped"}

    handle_nodes = find_handle_defs(mod)
    if not handle_nodes:
        return {"file": path, "action": "skip_no_handle"}

    # Step 1: rename existing handle → handle_impl
    updated = rename_handle_to_impl(src, handle_nodes)

    # Step 2: ensure imports for wrapper
    updated = ensure_imports(updated)

    # Step 3: ensure LOGIC_ID exists; if not, add a conservative default near top
    if find_logic_id(mod) is None and "LOGIC_ID" not in updated:
        # Add LOGIC_ID after imports
        lines = updated.splitlines()
        ins_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                ins_idx = i + 1
        lines.insert(ins_idx, 'LOGIC_ID = "L-XXX"')
        updated = "\n".join(lines)

    # Step 4: append wrapper and export handle = handle_l4
    updated = append_wrapper(updated)

    if not write:
        return {"file": path, "action": "would_write"}
    # Backup then write
    bak = path + ".bak"
    try:
        if not os.path.exists(bak):
            with open(bak, "w", encoding="utf-8") as bf:
                bf.write(src)
    except Exception:
        pass
    with open(path, "w", encoding="utf-8") as f:
        f.write(updated)
    return {"file": path, "action": "wrapped"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--range", type=str, default="041-060", help="numeric range, e.g., 041-060"
    )
    ap.add_argument("--write", action="store_true", help="apply changes")
    args = ap.parse_args()
    lo, hi = args.range.split("-", 1)
    r = (lo.zfill(3), hi.zfill(3))
    results = []
    for path in list_targets(r=r):
        res = process_file(path, write=args.write)
        results.append(res)
        print(res)
    # Exit non-zero if any syntax_error to be explicit
    if any("syntax_error" in (r["action"] or "") for r in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
