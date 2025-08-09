from __future__ import annotations

import importlib
import os
import pkgutil
from typing import Any, Callable, Dict, List, Optional, Tuple


class LogicMeta:
    def __init__(self, logic_id: str, title: str, tags: List[str]) -> None:
        self.logic_id = logic_id
        self.title = title
        self.tags = [t.lower() for t in tags]


# Maps: id -> (handle, meta)
LOGIC_REGISTRY: Dict[
    str, Tuple[Callable[[Dict[str, Any]], Dict[str, Any]], LogicMeta]
] = {}

# Keyword index for search: token -> set(ids)
KEYWORD_INDEX: Dict[str, List[str]] = {}


def _index_keywords(logic_id: str, meta: LogicMeta) -> None:
    tokens = set([*meta.tags, *meta.title.lower().split()])
    for tok in tokens:
        KEYWORD_INDEX.setdefault(tok, []).append(logic_id)


def load_all_logics() -> int:
    """Import all modules under the `logics` package and register those with
    `LOGIC_META` and `handle(payload)`.
    Returns the number of registered logics.
    """
    try:
        import logics  # noqa: F401
    except Exception:
        return 0

    package_path = os.path.dirname(importlib.import_module("logics").__file__)
    count = 0
    loaded_ids: List[str] = []
    for module_info in pkgutil.iter_modules([package_path]):
        if not module_info.ispkg and module_info.name.startswith("logic_"):
            module_name = f"logics.{module_info.name}"
            mod = importlib.import_module(module_name)
            if hasattr(mod, "LOGIC_META") and hasattr(mod, "handle"):
                lm = mod.LOGIC_META
                meta = LogicMeta(
                    logic_id=lm.get("id"),
                    title=lm.get("title"),
                    tags=lm.get("tags", []),
                )
                LOGIC_REGISTRY[meta.logic_id] = (mod.handle, meta)
                _index_keywords(meta.logic_id, meta)
                loaded_ids.append(meta.logic_id)
                count += 1
    # Ensure schemas exist for all loaded logic IDs (defaults where not provided)
    try:
        from helpers.schema_registry import ensure_all_logic_defaults

        ensure_all_logic_defaults(loaded_ids)
    except Exception:
        pass
    return count


def plan_from_query(query: str) -> Dict[str, Any]:
    """Very simple planner: match tokens to logic IDs and build a plan.
    If the query includes 'mis', prefer an orchestrated plan with a few sections.
    """
    ql = (query or "").lower()
    if "mis" in ql:
        sections = []
        if any(t in ql for t in ["pnl", "profit", "loss"]):
            sections.append("pnl")
        if "salary" in ql:
            sections.append("salary")
        return {
            "type": "orchestrator",
            "name": "mis",
            "sections": sections or ["pnl", "salary"],
        }

    # Non-orchestrated: collect matching logic IDs
    matched_ids: List[str] = []
    for token, ids in KEYWORD_INDEX.items():
        if token in ql:
            for i in ids:
                if i not in matched_ids:
                    matched_ids.append(i)
    # fallback to P&L if nothing matched but query seems financial
    if not matched_ids and any(
        t in ql for t in ["pnl", "profit", "loss", "revenue", "expense"]
    ):
        for logic_id, (_h, meta) in LOGIC_REGISTRY.items():
            if "pnl" in meta.tags or "profit" in meta.title.lower():
                matched_ids.append(logic_id)
                break
    return {"type": "logic", "logic_ids": matched_ids[:5]}
