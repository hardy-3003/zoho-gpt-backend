from __future__ import annotations

import re
from typing import Callable, Dict, Optional, List, Tuple
from difflib import SequenceMatcher

from .operate_base import OperateInput, OperateOutput


_REGISTRY: Dict[str, Callable[[OperateInput], OperateOutput]] = {}
_PATTERN_REGISTRY: Dict[str, Tuple[Callable[[OperateInput], OperateOutput], float]] = {}


def register(keyword: str):
    """Decorator to register an operate function against a keyword.

    The keyword should be a simple lowercased token such as "salary", "pnl",
    etc. Matching is fuzzy: if the keyword appears in the user query, we route
    to the associated function.
    """

    def _inner(func: Callable[[OperateInput], OperateOutput]):
        _REGISTRY[keyword] = func
        return func

    return _inner


def register_pattern(pattern: str, confidence: float = 0.8):
    """Decorator to register an operate function against a regex pattern.

    Args:
        pattern: Regex pattern for matching
        confidence: Confidence score for this pattern match
    """

    def _inner(func: Callable[[OperateInput], OperateOutput]):
        _PATTERN_REGISTRY[pattern] = (func, confidence)
        return func

    return _inner


def route(query: str) -> Optional[Callable[[OperateInput], OperateOutput]]:
    """Enhanced routing with pattern matching and fuzzy matching."""
    query_l = (query or "").lower()

    # First try exact keyword matching
    for k, fn in _REGISTRY.items():
        if k in query_l:
            return fn

    # Then try pattern matching
    best_match = None
    best_confidence = 0.0

    for pattern, (fn, confidence) in _PATTERN_REGISTRY.items():
        try:
            if re.search(pattern, query_l, re.IGNORECASE):
                if confidence > best_confidence:
                    best_match = fn
                    best_confidence = confidence
        except re.error:
            # Skip invalid patterns
            continue

    if best_match and best_confidence >= 0.6:
        return best_match

    # Finally try fuzzy matching
    return _fuzzy_route(query_l)


def _fuzzy_route(query: str) -> Optional[Callable[[OperateInput], OperateOutput]]:
    """Fuzzy matching for routing."""
    best_match = None
    best_ratio = 0.0

    for keyword, func in _REGISTRY.items():
        # Calculate similarity ratio
        ratio = SequenceMatcher(None, query, keyword).ratio()

        # Also check if query contains parts of keyword
        if keyword in query:
            ratio = max(ratio, 0.8)

        if ratio > best_ratio and ratio >= 0.6:  # Minimum threshold
            best_ratio = ratio
            best_match = func

    return best_match


def route_with_confidence(
    query: str,
) -> Tuple[Optional[Callable[[OperateInput], OperateOutput]], float]:
    """Route with confidence scoring."""
    query_l = (query or "").lower()

    # Try exact keyword matching first
    for k, fn in _REGISTRY.items():
        if k in query_l:
            return fn, 1.0

    # Try pattern matching
    best_match = None
    best_confidence = 0.0

    for pattern, (fn, confidence) in _PATTERN_REGISTRY.items():
        try:
            if re.search(pattern, query_l, re.IGNORECASE):
                if confidence > best_confidence:
                    best_match = fn
                    best_confidence = confidence
        except re.error:
            continue

    if best_match and best_confidence >= 0.6:
        return best_match, best_confidence

    # Try fuzzy matching
    best_match = None
    best_ratio = 0.0

    for keyword, func in _REGISTRY.items():
        ratio = SequenceMatcher(None, query_l, keyword).ratio()
        if keyword in query_l:
            ratio = max(ratio, 0.8)

        if ratio > best_ratio and ratio >= 0.6:
            best_ratio = ratio
            best_match = func

    return best_match, best_ratio


def discover_routes(
    query: str, max_results: int = 5
) -> List[Tuple[str, Callable[[OperateInput], OperateOutput], float]]:
    """Discover all possible routes for a query with confidence scores."""
    results = []
    query_l = (query or "").lower()

    # Check all keywords
    for keyword, func in _REGISTRY.items():
        confidence = 0.0

        # Exact match
        if keyword == query_l:
            confidence = 1.0
        # Contains match
        elif keyword in query_l:
            confidence = 0.8
        # Fuzzy match
        else:
            ratio = SequenceMatcher(None, query_l, keyword).ratio()
            if ratio >= 0.6:
                confidence = ratio

        if confidence > 0:
            results.append((keyword, func, confidence))

    # Check patterns
    for pattern, (func, base_confidence) in _PATTERN_REGISTRY.items():
        try:
            if re.search(pattern, query_l, re.IGNORECASE):
                results.append((f"pattern:{pattern}", func, base_confidence))
        except re.error:
            continue

    # Sort by confidence and return top results
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:max_results]


def list_registered_routes() -> Dict[str, List[str]]:
    """List all registered routes."""
    return {
        "keywords": list(_REGISTRY.keys()),
        "patterns": list(_PATTERN_REGISTRY.keys()),
    }


def get_route_stats() -> Dict[str, int]:
    """Get statistics about registered routes."""
    return {
        "total_keywords": len(_REGISTRY),
        "total_patterns": len(_PATTERN_REGISTRY),
        "total_routes": len(_REGISTRY) + len(_PATTERN_REGISTRY),
    }
