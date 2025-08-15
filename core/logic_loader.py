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
    """Enhanced planner with auto-discovery and intelligent logic matching.

    Features:
    - Fuzzy matching with confidence scoring
    - Tag-based clustering and grouping
    - Usage pattern analysis
    - Intelligent fallback selection
    """
    ql = (query or "").lower()

    # Check for orchestrated requests
    if "mis" in ql:
        sections = _discover_mis_sections(ql)
        return {
            "type": "orchestrator",
            "name": "mis",
            "sections": sections,
            "confidence": _calculate_plan_confidence(ql, sections),
            "discovery_method": "orchestrator_pattern",
        }

    # Enhanced logic discovery
    matched_logics = _discover_logics_by_query(ql)

    if matched_logics:
        return {
            "type": "logic",
            "logic_ids": [logic["id"] for logic in matched_logics[:5]],
            "confidence": _calculate_plan_confidence(
                ql, [logic["id"] for logic in matched_logics]
            ),
            "discovery_method": "enhanced_matching",
            "matched_details": matched_logics[:5],
        }

    # Fallback to P&L if nothing matched but query seems financial
    if _is_financial_query(ql):
        fallback_logics = _find_financial_fallbacks(ql)
        return {
            "type": "logic",
            "logic_ids": [logic["id"] for logic in fallback_logics],
            "confidence": 0.6,  # Lower confidence for fallback
            "discovery_method": "financial_fallback",
            "matched_details": fallback_logics,
        }

    return {
        "type": "logic",
        "logic_ids": [],
        "confidence": 0.0,
        "discovery_method": "no_match",
    }


def _discover_mis_sections(query: str) -> List[str]:
    """Discover MIS sections based on query analysis."""
    sections = []

    # Enhanced section detection
    section_patterns = {
        "pnl": ["pnl", "profit", "loss", "revenue", "expense", "income"],
        "salary": ["salary", "payroll", "employee", "staff", "wages"],
        "balance": ["balance", "sheet", "assets", "liabilities", "equity"],
        "cash": ["cash", "flow", "liquidity", "working", "capital"],
        "trial": ["trial", "balance", "ledger", "accounts"],
        "tax": ["tax", "gst", "tds", "compliance", "filing"],
        "inventory": ["inventory", "stock", "goods", "items", "products"],
        "vendor": ["vendor", "supplier", "purchase", "payable"],
        "client": ["client", "customer", "receivable", "sales"],
        "budget": ["budget", "forecast", "planning", "variance"],
    }

    for section, patterns in section_patterns.items():
        if any(pattern in query for pattern in patterns):
            sections.append(section)

    # Default sections if none found
    if not sections:
        sections = ["pnl", "salary"]

    return sections


def _discover_logics_by_query(query: str) -> List[Dict[str, Any]]:
    """Enhanced logic discovery with confidence scoring and fuzzy matching."""
    matched_logics = []

    # Tokenize query
    query_tokens = set(query.split())

    for logic_id, (handler, meta) in LOGIC_REGISTRY.items():
        # Calculate match score
        score = _calculate_logic_match_score(query, query_tokens, meta)

        if score > 0.1:  # Minimum threshold
            matched_logics.append(
                {
                    "id": logic_id,
                    "title": meta.title,
                    "tags": meta.tags,
                    "score": score,
                    "match_reasons": _get_match_reasons(query, meta),
                }
            )

    # Sort by score (highest first)
    matched_logics.sort(key=lambda x: x["score"], reverse=True)

    return matched_logics


def _calculate_logic_match_score(
    query: str, query_tokens: set, meta: LogicMeta
) -> float:
    """Calculate match score for a logic based on query and metadata."""
    score = 0.0

    # Title matching (highest weight)
    title_tokens = set(meta.title.lower().split())
    title_overlap = len(query_tokens & title_tokens)
    if title_overlap > 0:
        score += title_overlap * 0.4

    # Tag matching
    tag_overlap = len(query_tokens & set(meta.tags))
    if tag_overlap > 0:
        score += tag_overlap * 0.3

    # Substring matching
    for token in query_tokens:
        if token in meta.title.lower():
            score += 0.2
        if any(token in tag for tag in meta.tags):
            score += 0.1

    # Exact phrase matching
    if query in meta.title.lower():
        score += 0.5

    # Normalize score
    return min(score, 1.0)


def _get_match_reasons(query: str, meta: LogicMeta) -> List[str]:
    """Get reasons why a logic matched the query."""
    reasons = []
    query_lower = query.lower()

    if query_lower in meta.title.lower():
        reasons.append("exact_title_match")

    for tag in meta.tags:
        if tag in query_lower:
            reasons.append(f"tag_match:{tag}")

    return reasons


def _is_financial_query(query: str) -> bool:
    """Check if query is financial in nature."""
    financial_terms = [
        "pnl",
        "profit",
        "loss",
        "revenue",
        "expense",
        "income",
        "balance",
        "sheet",
        "cash",
        "flow",
        "trial",
        "ledger",
        "account",
        "financial",
        "money",
        "cost",
        "price",
        "value",
    ]

    return any(term in query for term in financial_terms)


def _find_financial_fallbacks(query: str) -> List[Dict[str, Any]]:
    """Find fallback logics for financial queries."""
    fallbacks = []

    # Priority order for financial fallbacks
    priority_patterns = [
        ("pnl", ["profit", "loss", "revenue", "expense"]),
        ("balance", ["balance", "sheet", "assets", "liabilities"]),
        ("cash", ["cash", "flow", "liquidity"]),
        ("trial", ["trial", "balance", "ledger"]),
    ]

    for pattern, terms in priority_patterns:
        if any(term in query for term in terms):
            # Find best matching logic for this pattern
            for logic_id, (handler, meta) in LOGIC_REGISTRY.items():
                if pattern in meta.tags or pattern in meta.title.lower():
                    fallbacks.append(
                        {
                            "id": logic_id,
                            "title": meta.title,
                            "tags": meta.tags,
                            "score": 0.6,
                            "match_reasons": [f"financial_fallback:{pattern}"],
                        }
                    )
                    break

    return fallbacks


def _calculate_plan_confidence(query: str, selected_items: List[str]) -> float:
    """Calculate confidence score for a plan."""
    if not selected_items:
        return 0.0

    # Base confidence
    confidence = 0.5

    # Boost for exact matches
    query_lower = query.lower()
    exact_matches = sum(1 for item in selected_items if item.lower() in query_lower)
    if exact_matches > 0:
        confidence += 0.3 * (exact_matches / len(selected_items))

    # Boost for multiple matches
    if len(selected_items) > 1:
        confidence += 0.1

    return min(confidence, 1.0)


def discover_logics_by_tags(
    tags: List[str], min_confidence: float = 0.3
) -> List[Dict[str, Any]]:
    """Discover logics by tag matching with confidence scoring."""
    discovered = []

    for logic_id, (handler, meta) in LOGIC_REGISTRY.items():
        # Calculate tag overlap
        common_tags = set(tags) & set(meta.tags)
        if common_tags:
            confidence = len(common_tags) / len(set(tags) | set(meta.tags))

            if confidence >= min_confidence:
                discovered.append(
                    {
                        "id": logic_id,
                        "title": meta.title,
                        "tags": meta.tags,
                        "confidence": confidence,
                        "common_tags": list(common_tags),
                    }
                )

    # Sort by confidence
    discovered.sort(key=lambda x: x["confidence"], reverse=True)
    return discovered


def discover_logics_by_pattern(
    pattern: str, fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """Discover logics by pattern matching with optional fuzzy matching."""
    discovered = []
    pattern_lower = pattern.lower()

    for logic_id, (handler, meta) in LOGIC_REGISTRY.items():
        # Exact matching
        if pattern_lower in meta.title.lower() or pattern_lower in meta.tags:
            discovered.append(
                {
                    "id": logic_id,
                    "title": meta.title,
                    "tags": meta.tags,
                    "confidence": 0.9,
                    "match_type": "exact",
                }
            )
        elif fuzzy:
            # Fuzzy matching (simple implementation)
            title_words = meta.title.lower().split()
            tag_words = [tag.lower() for tag in meta.tags]

            # Check for partial matches
            for word in title_words + tag_words:
                if pattern_lower in word or word in pattern_lower:
                    discovered.append(
                        {
                            "id": logic_id,
                            "title": meta.title,
                            "tags": meta.tags,
                            "confidence": 0.6,
                            "match_type": "fuzzy",
                        }
                    )
                    break

    # Remove duplicates and sort
    seen = set()
    unique_discovered = []
    for item in discovered:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique_discovered.append(item)

    unique_discovered.sort(key=lambda x: x["confidence"], reverse=True)
    return unique_discovered
