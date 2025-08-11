from __future__ import annotations
import os, re, ast
from typing import Dict, List, Tuple

FILENAME_RE = re.compile(r"^logic_(\d{3})_([a-z0-9_]+)\.py$")
ID_LINE_RE = re.compile(r"^ID:\s*L-(\d{3})\s*$", re.IGNORECASE)


def scan_logic_docstring_id(src: str) -> str | None:
    """
    Parse the top-level docstring and extract the ID line "ID: L-###".
    Returns the 3-digit string or None.
    """
    try:
        mod = ast.parse(src)
        if (
            isinstance(mod.body[0], ast.Expr)
            and isinstance(mod.body[0].value, ast.Constant)
            and isinstance(mod.body[0].value.value, str)
        ):
            doc = mod.body[0].value.value
            for line in doc.splitlines():
                m = ID_LINE_RE.match(line.strip())
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def list_logic_files(root: str = "logics") -> List[str]:
    return [
        os.path.join(root, f)
        for f in os.listdir(root)
        if f.startswith("logic_") and f.endswith(".py")
    ]


def check_consistency(root: str = "logics") -> List[Dict[str, str]]:
    """
    Returns list of issues:
      {"file": "...", "issue": "bad_filename|id_mismatch|missing_id|multi_handle"}
    """
    issues = []
    for path in sorted(list_logic_files(root)):
        fname = os.path.basename(path)
        m = FILENAME_RE.match(fname)
        if not m:
            issues.append({"file": path, "issue": "bad_filename"})
            continue
        file_num = m.group(1)
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        logic_id = scan_logic_docstring_id(src)
        if not logic_id:
            issues.append({"file": path, "issue": "missing_id"})
        elif logic_id != file_num:
            issues.append(
                {"file": path, "issue": f"id_mismatch(L-{logic_id} != L-{file_num})"}
            )
        # detect multiple exported handle defs
        try:
            mod = ast.parse(src)
            handles = [
                n
                for n in mod.body
                if isinstance(n, ast.FunctionDef) and n.name == "handle"
            ]
            if len(handles) != 1:
                issues.append({"file": path, "issue": f"multi_handle({len(handles)})"})
        except Exception:
            pass
    return issues


def propose_new_name(path: str) -> str | None:
    """
    If filename is off, propose a corrected snake_case based on docstring Title if present.
    Does not rename. Returns suggestion or None.
    """
    try:
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        mod = ast.parse(src)
        title = None
        if (
            isinstance(mod.body[0], ast.Expr)
            and isinstance(mod.body[0].value, ast.Constant)
            and isinstance(mod.body[0].value.value, str)
        ):
            doc = mod.body[0].value.value
            for line in doc.splitlines():
                if line.strip().lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                    break
        if not title:
            return None
        snake = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        m = FILENAME_RE.match(fname)
        num = m.group(1) if m else "000"
        return f"logic_{num}_{snake}.py"
    except Exception:
        return None
