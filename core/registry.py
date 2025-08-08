from __future__ import annotations

from typing import Callable, Dict, Optional

from .operate_base import OperateInput, OperateOutput


_REGISTRY: Dict[str, Callable[[OperateInput], OperateOutput]] = {}


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


def route(query: str) -> Optional[Callable[[OperateInput], OperateOutput]]:
    query_l = (query or "").lower()
    for k, fn in _REGISTRY.items():
        if k in query_l:
            return fn
    return None
