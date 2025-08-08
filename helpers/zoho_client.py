from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests


class ZohoClient:
    """Thin Zoho Books HTTP client with basic retries and rate limiting.

    This is intentionally minimal; expand with caching, backoff, and error taxonomies.
    """

    def __init__(
        self,
        api_domain: str,
        access_token: str,
        organization_id: str,
        rate_limit_per_sec: float = 5.0,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ) -> None:
        self.api_domain = api_domain.rstrip("/")
        self.access_token = access_token
        self.organization_id = organization_id
        self.rate_limit_per_sec = rate_limit_per_sec
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._last_call_ts = 0.0

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Zoho-oauthtoken {self.access_token}"}

    def _rate_limit(self) -> None:
        if self.rate_limit_per_sec <= 0:
            return
        min_interval = 1.0 / self.rate_limit_per_sec
        elapsed = time.time() - self._last_call_ts
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_call_ts = time.time()

    def _request(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.api_domain}{path}"
        params = params or {}
        params.setdefault("organization_id", self.organization_id)
        attempt = 0
        while True:
            attempt += 1
            self._rate_limit()
            resp = requests.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 429 and attempt <= self.max_retries:
                # simple backoff
                time.sleep(0.5 * attempt)
                continue
            if resp.status_code >= 400:
                raise Exception(f"Zoho API error {resp.status_code}: {resp.text}")
            return resp.json()

    # Convenience endpoints (extend as needed)
    def list_invoices(self, date_start: str, date_end: str) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/books/v3/invoices",
            {"date_start": date_start, "date_end": date_end, "status": "all"},
        )

    def list_bills(self, date_start: str, date_end: str) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/books/v3/bills",
            {"date_start": date_start, "date_end": date_end, "status": "all"},
        )
