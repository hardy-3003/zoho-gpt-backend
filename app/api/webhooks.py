"""
Webhooks API Router - Contract-Only Implementation
Task P1.2.4 — /webhooks ingress (contract-only)

Provides HMAC-verified webhook endpoints with replay protection.
Contract-only implementation with deterministic stub responses.
"""

import hashlib
import hmac
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Configuration
WEBHOOK_SECRET = "webhook-secret-key-change-in-production"  # TODO: Move to config
REPLAY_WINDOW_SECONDS = 300  # 5 minutes
REPLAY_CACHE_SIZE = 1000  # In-memory cache size for replay protection

# In-memory replay protection (in production, use Redis/database)
_replay_cache: Dict[str, float] = {}


class WebhookResponse(BaseModel):
    """Deterministic webhook response schema (contract only)"""

    status: str = "received"
    source: str
    timestamp: float
    message_id: str
    processing_id: str = "stub-processing-id"


def verify_hmac_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature against payload"""
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def check_replay_protection(message_id: str, timestamp: float) -> bool:
    """Check for replay attacks using message ID and timestamp"""
    current_time = time.time()

    # Check if message is too old
    if current_time - timestamp > REPLAY_WINDOW_SECONDS:
        return False

    # Check if message ID was already processed
    if message_id in _replay_cache:
        return False

    # Add to replay cache (with cleanup for old entries)
    _replay_cache[message_id] = timestamp

    # Simple cleanup: remove old entries if cache gets too large
    if len(_replay_cache) > REPLAY_CACHE_SIZE:
        cutoff_time = current_time - REPLAY_WINDOW_SECONDS
        _replay_cache.clear()
        # In production, use a proper cache with TTL

    return True


@router.post("/{source}")
async def webhook_handler(
    source: str,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_id: Optional[str] = Header(None, alias="X-Id"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
):
    """
    Webhook endpoint with HMAC verification and replay protection.

    Contract-only implementation that returns deterministic stub responses.
    No business logic side effects.
    """

    # Validate required headers
    if not x_signature:
        raise HTTPException(status_code=401, detail="Missing X-Signature header")

    if not x_id:
        raise HTTPException(status_code=400, detail="Missing X-Id header")

    if not x_timestamp:
        raise HTTPException(status_code=400, detail="Missing X-Timestamp header")

    # Parse timestamp
    try:
        timestamp = float(x_timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Timestamp format")

    # Get request body for HMAC verification
    body = await request.body()

    # Verify HMAC signature
    if not verify_hmac_signature(body, x_signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Check replay protection
    if not check_replay_protection(x_id, timestamp):
        raise HTTPException(
            status_code=409, detail="Replay detected or message too old"
        )

    # Return deterministic stub response (contract only)
    response = WebhookResponse(source=source, timestamp=timestamp, message_id=x_id)

    return response


@router.get("/health")
async def webhook_health():
    """Health check for webhooks endpoint"""
    return {
        "status": "healthy",
        "service": "webhooks",
        "replay_cache_size": len(_replay_cache),
    }
