from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union


@dataclass
class OperateInput:
    org_id: str
    start_date: str
    end_date: str
    headers: Dict[str, str]
    api_domain: str
    query: str


@dataclass
class OperateOutput:
    content: Union[str, Dict[str, Any]]
    meta: Dict[str, Any]
