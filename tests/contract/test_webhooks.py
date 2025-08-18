"""
Contract Tests for Webhooks API
Task P1.2.4 — /webhooks ingress (contract-only)

Tests HMAC verification, replay protection, and response schema validation.
"""

import hashlib
import hmac
import time
import pytest
from fastapi.testclient import TestClient
from app.api.webhooks import (
    verify_hmac_signature,
    check_replay_protection,
    WebhookResponse,
)

# Import the main app to get the webhooks router
from main import app

client = TestClient(app)

# Test configuration
WEBHOOK_SECRET = "webhook-secret-key-change-in-production"
TEST_SOURCE = "test-source"
TEST_PAYLOAD = b'{"test": "data"}'
TEST_MESSAGE_ID = "test-message-123"
TEST_TIMESTAMP = time.time()


def generate_hmac_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC signature for testing"""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


class TestWebhookHMACVerification:
    """Test HMAC signature verification"""

    def test_verify_hmac_signature_valid(self):
        """Test valid HMAC signature verification"""
        signature = generate_hmac_signature(TEST_PAYLOAD, WEBHOOK_SECRET)
        assert verify_hmac_signature(TEST_PAYLOAD, signature, WEBHOOK_SECRET) is True

    def test_verify_hmac_signature_invalid(self):
        """Test invalid HMAC signature verification"""
        invalid_signature = "invalid-signature"
        assert (
            verify_hmac_signature(TEST_PAYLOAD, invalid_signature, WEBHOOK_SECRET)
            is False
        )

    def test_verify_hmac_signature_wrong_payload(self):
        """Test HMAC verification with wrong payload"""
        signature = generate_hmac_signature(TEST_PAYLOAD, WEBHOOK_SECRET)
        wrong_payload = b'{"wrong": "data"}'
        assert verify_hmac_signature(wrong_payload, signature, WEBHOOK_SECRET) is False


class TestWebhookReplayProtection:
    """Test replay protection functionality"""

    def test_check_replay_protection_valid(self):
        """Test valid replay protection check"""
        message_id = f"test-{time.time()}"
        timestamp = time.time()
        assert check_replay_protection(message_id, timestamp) is True

    def test_check_replay_protection_old_message(self):
        """Test replay protection with old timestamp"""
        message_id = f"test-old-{time.time()}"
        old_timestamp = time.time() - 400  # 400 seconds old (beyond 5-minute window)
        assert check_replay_protection(message_id, old_timestamp) is False

    def test_check_replay_protection_duplicate_id(self):
        """Test replay protection with duplicate message ID"""
        message_id = f"test-duplicate-{time.time()}"
        timestamp = time.time()

        # First call should succeed
        assert check_replay_protection(message_id, timestamp) is True

        # Second call with same ID should fail
        assert check_replay_protection(message_id, timestamp) is False


class TestWebhookEndpoint:
    """Test webhook endpoint functionality"""

    def test_webhook_valid_request(self):
        """Test webhook endpoint with valid request"""
        payload = b'{"event": "test", "data": "value"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        message_id = f"test-{time.time()}"
        timestamp = str(time.time())

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert data["status"] == "received"
        assert data["source"] == TEST_SOURCE
        assert data["message_id"] == message_id
        assert data["processing_id"] == "stub-processing-id"
        assert "timestamp" in data

    def test_webhook_missing_signature(self):
        """Test webhook endpoint with missing signature header"""
        payload = b'{"event": "test"}'
        message_id = f"test-{time.time()}"
        timestamp = str(time.time())

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401
        assert "Missing X-Signature header" in response.json()["detail"]

    def test_webhook_invalid_signature(self):
        """Test webhook endpoint with invalid signature"""
        payload = b'{"event": "test"}'
        invalid_signature = "invalid-signature"
        message_id = f"test-{time.time()}"
        timestamp = str(time.time())

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": invalid_signature,
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]

    def test_webhook_missing_message_id(self):
        """Test webhook endpoint with missing message ID"""
        payload = b'{"event": "test"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        timestamp = str(time.time())

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 400
        assert "Missing X-Id header" in response.json()["detail"]

    def test_webhook_missing_timestamp(self):
        """Test webhook endpoint with missing timestamp"""
        payload = b'{"event": "test"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        message_id = f"test-{time.time()}"

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 400
        assert "Missing X-Timestamp header" in response.json()["detail"]

    def test_webhook_invalid_timestamp(self):
        """Test webhook endpoint with invalid timestamp format"""
        payload = b'{"event": "test"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        message_id = f"test-{time.time()}"
        invalid_timestamp = "not-a-number"

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": invalid_timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 400
        assert "Invalid X-Timestamp format" in response.json()["detail"]

    def test_webhook_replay_attack(self):
        """Test webhook endpoint with replay attack"""
        payload = b'{"event": "test"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        message_id = f"test-replay-{time.time()}"
        timestamp = str(time.time())

        # First request should succeed
        response1 = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response1.status_code == 200

        # Second request with same message ID should fail (replay attack)
        response2 = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response2.status_code == 409
        assert "Replay detected" in response2.json()["detail"]

    def test_webhook_old_message(self):
        """Test webhook endpoint with old timestamp"""
        payload = b'{"event": "test"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        message_id = f"test-old-{time.time()}"
        old_timestamp = str(time.time() - 400)  # 400 seconds old

        response = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": old_timestamp,
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 409
        assert "Replay detected or message too old" in response.json()["detail"]

    def test_webhook_health_endpoint(self):
        """Test webhook health endpoint"""
        response = client.get("/webhooks/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "webhooks"
        assert "replay_cache_size" in data


class TestWebhookResponseSchema:
    """Test webhook response schema validation"""

    def test_webhook_response_schema(self):
        """Test WebhookResponse Pydantic model"""
        response = WebhookResponse(
            source="test-source", timestamp=1234567890.0, message_id="test-123"
        )

        assert response.status == "received"
        assert response.source == "test-source"
        assert response.timestamp == 1234567890.0
        assert response.message_id == "test-123"
        assert response.processing_id == "stub-processing-id"

    def test_webhook_response_serialization(self):
        """Test WebhookResponse JSON serialization"""
        response = WebhookResponse(
            source="test-source", timestamp=1234567890.0, message_id="test-123"
        )

        json_data = response.model_dump()

        assert json_data["status"] == "received"
        assert json_data["source"] == "test-source"
        assert json_data["timestamp"] == 1234567890.0
        assert json_data["message_id"] == "test-123"
        assert json_data["processing_id"] == "stub-processing-id"


class TestWebhookContractCompliance:
    """Test webhook contract compliance with deterministic responses"""

    def test_webhook_deterministic_response(self):
        """Test that webhook responses are deterministic for same inputs"""
        payload = b'{"event": "test"}'
        signature = generate_hmac_signature(payload, WEBHOOK_SECRET)
        message_id = f"test-deterministic-{time.time()}"
        timestamp = str(time.time())

        # Make two identical requests
        response1 = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        # Second request with same message ID should fail due to replay protection
        response2 = client.post(
            f"/webhooks/{TEST_SOURCE}",
            content=payload,
            headers={
                "X-Signature": signature,
                "X-Id": message_id,
                "X-Timestamp": timestamp,
                "Content-Type": "application/json",
            },
        )

        # Both should have same response structure (though first succeeds, second fails due to replay)
        assert response1.status_code == 200
        assert response2.status_code == 409

        # But the successful response should have consistent structure
        data1 = response1.json()
        assert data1["status"] == "received"
        assert data1["source"] == TEST_SOURCE
        assert data1["message_id"] == message_id
        assert data1["processing_id"] == "stub-processing-id"
