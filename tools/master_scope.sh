#!/usr/bin/env bash
set -euo pipefail

RANGE="${1:-001-231}"          # e.g. 001-200 or 061-200
TAG="${2:-}"                   # optional git tag name

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# venv + deps (fast if already present)
if [[ ! -d venv ]]; then python -m venv venv; fi
source venv/bin/activate
python -m pip install -U -r requirements-dev.txt >/dev/null

# wrap in 20-file chunks (idempotent; skips already-wrapped)
read L U < <(awk -F- '{print $1" "$2}' <<<"$RANGE")
for S in $(seq "$L" 20 "$U"); do
  E=$((S+19)); (( E>U )) && E="$U"
  python tools/safe_wrap_wave5.py --range "$(printf '%03d-%03d' "$S" "$E")" --write
done

# compile sanity once
python - <<'PY'
import glob, py_compile, sys
files = sorted(glob.glob("logics/logic_0[0-9][0-9]_*.py")
             + glob.glob("logics/logic_1[0-9][0-9]_*.py")
             + glob.glob("logics/logic_200_*.py"))
bad=[]
for p in files:
    try: py_compile.compile(p, doraise=True)
    except Exception as e: bad.append((p,str(e)))
if bad:
    [print("[ERR]",p,"->",e) for p,e in bad]
    sys.exit(2)
print("py_compile ✅ all")
PY

# run tests (includes naming guardrail & contract tests)
export NAMING_ENFORCER_RANGE="001-231"
pytest -q

# optional commit + tag
if [[ -n "$TAG" ]]; then
  git add -A
  git commit -m "master-scope: wrap ${RANGE}; compile + naming + contract tests green."
  git tag -a "$TAG" -m "Master scope: ${RANGE} wrapped & tests green"
fi

echo "✅ Master scope complete for ${RANGE}"; [[ -n "$TAG" ]] && echo "   Tagged: $TAG"
