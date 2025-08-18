import os, re, sys, argparse, ast, textwrap

FILENAME_RE = re.compile(r"^logic_(\d{3})_([a-z0-9_]+)\.py$")
ID_LINE_RE = re.compile(r"^ID:\s*L-(\d{3})\s*$", re.IGNORECASE)


def title_from_snake(s: str) -> str:
    return " ".join([p.capitalize() for p in s.split("_") if p])


def find_module_docstring_bounds(src: str):
    """
    Return (start_line_idx, end_line_idx, quote) for the top-level docstring if found, else None.
    Lines are 0-indexed, inclusive bounds.
    """
    # Very small parser: looks for """...""" or '''...''' at the top, skipping blank/comment lines.
    lines = src.splitlines()
    i = 0
    while i < len(lines) and (
        not lines[i].strip() or lines[i].lstrip().startswith("#")
    ):
        i += 1
    if i >= len(lines):
        return None
    line = lines[i].lstrip()
    q = None
    if line.startswith('"""'):
        q = '"""'
    elif line.startswith("'''"):
        q = "'''"
    else:
        return None
    # Single-line docstring?
    if line.count(q) >= 2:
        return (i, i, q)
    # Multi-line: find closing
    j = i + 1
    while j < len(lines):
        if q in lines[j]:
            return (i, j, q)
        j += 1
    return None


def extract_id_from_doc(doc: str):
    for line in doc.splitlines():
        m = ID_LINE_RE.match(line.strip())
        if m:
            return m.group(1)
    return None


def ensure_id_in_doc(doc: str, want3: str) -> str:
    """Insert or correct 'ID: L-###' line inside an existing docstring."""
    lines = doc.splitlines()
    have = extract_id_from_doc(doc)
    if have == want3:
        return doc  # already correct
    # Try to place ID after Title: ... line if present, else append near top.
    inserted = False
    for idx, line in enumerate(lines):
        if line.strip().lower().startswith("title:"):
            lines.insert(idx + 1, f"ID: L-{want3}")
            inserted = True
            break
    if not inserted:
        # Place near top, after any leading blank lines
        k = 0
        while k < len(lines) and not lines[k].strip():
            k += 1
        lines.insert(k, f"ID: L-{want3}")
    return "\n".join(lines)


def new_contract_doc(num3: str, slug: str) -> str:
    title = title_from_snake(slug)
    return textwrap.dedent(
        f'''\
    """
    Title: {title}
    ID: L-{num3}
    Tags: []
    Required Inputs: schema://{slug}.input.v1
    Outputs: schema://{slug}.output.v1
    Assumptions: 
    Evolution Notes: L4 wrapper (provenance, history, confidence); additive only.
    """
    '''
    ).rstrip("\n")


def process_file(path: str, write: bool = False) -> dict:
    fname = os.path.basename(path)
    m = FILENAME_RE.match(fname)
    if not m:
        return {"file": path, "action": "skip_non_matching"}
    num3, slug = m.group(1), m.group(2)

    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    # Locate top-level docstring bounds
    bounds = find_module_docstring_bounds(src)
    if bounds:
        i, j, q = bounds
        lines = src.splitlines()
        doc_raw = "\n".join(lines[i : j + 1])
        # Strip the quotes to edit inside
        head = lines[i]
        tail = lines[j]
        open_idx = head.find(q)
        close_idx = tail.rfind(q)
        inner = head[open_idx + len(q) :] + ("\n" if i != j else "")
        if j > i:
            inner += "\n".join(lines[i + 1 : j])
            inner += "\n" if tail[:close_idx] else ""
            inner += tail[:close_idx]
        inner_fixed = ensure_id_in_doc(inner, num3)
        new_doc = q + inner_fixed + q
        # Replace block
        new_lines = lines[:i] + [new_doc] + lines[j + 1 :]
        new_src = "\n".join(new_lines)
        changed = new_src != src
        if write and changed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_src)
        return {"file": path, "action": "updated_doc_id" if changed else "ok"}
    else:
        # Prepend a new contract header docstring
        header = new_contract_doc(num3, slug)
        new_src = header + "\n" + src
        if write:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_src)
        return {"file": path, "action": "inserted_header"}


def iter_targets(root="logics", r=None):
    for f in sorted(os.listdir(root)):
        if not f.startswith("logic_") or not f.endswith(".py"):
            continue
        m = FILENAME_RE.match(f)
        if not m:
            continue
        num3 = m.group(1)
        if r:
            lo, hi = r
            if not (lo <= num3 <= hi):
                continue
        yield os.path.join(root, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply changes")
    ap.add_argument(
        "--range", type=str, default="", help="numeric range like 001-060 (inclusive)"
    )
    args = ap.parse_args()
    r = None
    if args.range:
        lo, hi = args.range.split("-", 1)
        r = (lo.zfill(3), hi.zfill(3))
    changes = []
    for path in iter_targets(r=r):
        changes.append(process_file(path, write=args.write))
    # Print a compact report
    added = sum(1 for c in changes if c["action"] == "inserted_header")
    updated = sum(1 for c in changes if c["action"] == "updated_doc_id")
    ok = sum(1 for c in changes if c["action"] == "ok")
    print({"files": len(changes), "inserted": added, "updated": updated, "ok": ok})
    for c in changes:
        print(f"{c['action']:>16}  {c['file']}")


if __name__ == "__main__":
    main()
