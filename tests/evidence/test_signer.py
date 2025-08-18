"""
Unit tests for evidence signer.

Tests deterministic signing, verification, tamper detection,
and pluggable signer functionality.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from evidence.signer import (
    EvidenceSigner,
    HMACSigner,
    DeterministicSigner,
    SignatureResult,
    Signer,
)


class TestHMACSigner:
    """Test HMAC signer functionality."""

    @pytest.fixture
    def keys(self):
        """Create test keys."""
        return {
            "key1": b"secret-key-1-for-testing",
            "key2": b"secret-key-2-for-testing",
            "default": b"default-secret-key",
        }

    @pytest.fixture
    def signer(self, keys):
        """Create HMAC signer instance."""
        return HMACSigner(keys)

    def test_sign_bytes(self, signer):
        """Test signing bytes data."""
        data = b"test data for signing"
        signature_result = signer.sign(data, "key1")

        assert isinstance(signature_result, SignatureResult)
        assert signature_result.algorithm == "sha256-hmac"
        assert signature_result.key_id == "key1"
        assert signature_result.signature is not None
        assert signature_result.timestamp is not None
        assert signature_result.metadata == {}

    def test_sign_string(self, signer):
        """Test signing string data."""
        data = "test string data"
        signature_result = signer.sign(data, "key2")

        assert signature_result.algorithm == "sha256-hmac"
        assert signature_result.key_id == "key2"

    def test_sign_dict(self, signer):
        """Test signing dictionary data."""
        data = {"test": "value", "number": 42}
        signature_result = signer.sign(data, "default")

        assert signature_result.algorithm == "sha256-hmac"
        assert signature_result.key_id == "default"

    def test_sign_with_metadata(self, signer):
        """Test signing with metadata."""
        data = "test data"
        metadata = {"source": "test", "version": "1.0"}
        signature_result = signer.sign(data, "key1", metadata=metadata)

        assert signature_result.metadata == metadata

    def test_verify_valid_signature(self, signer):
        """Test verifying valid signature."""
        data = "test data for verification"
        signature_result = signer.sign(data, "key1")

        assert signer.verify(data, signature_result) is True

    def test_verify_invalid_signature(self, signer):
        """Test verifying invalid signature."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        # Tamper with data
        tampered_data = "tampered data"
        assert signer.verify(tampered_data, signature_result) is False

    def test_verify_wrong_key(self, signer):
        """Test verifying with wrong key."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        # Try to verify with different key
        wrong_signer = HMACSigner({"wrong_key": b"wrong-secret"})
        assert wrong_signer.verify(data, signature_result) is False

    def test_verify_wrong_algorithm(self, signer):
        """Test verifying with wrong algorithm."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        # Create signature result with wrong algorithm
        wrong_signature = SignatureResult(
            signature=signature_result.signature,
            algorithm="wrong-algorithm",
            key_id=signature_result.key_id,
            timestamp=signature_result.timestamp,
            metadata=signature_result.metadata,
        )

        assert signer.verify(data, wrong_signature) is False

    def test_sign_nonexistent_key(self, signer):
        """Test signing with nonexistent key."""
        data = "test data"

        with pytest.raises(KeyError, match="Key ID not found"):
            signer.sign(data, "nonexistent_key")

    def test_verify_nonexistent_key(self, signer):
        """Test verifying with nonexistent key."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        # Create signer without the key
        other_signer = HMACSigner({"other_key": b"other-secret"})
        assert other_signer.verify(data, signature_result) is False

    def test_deterministic_json(self, signer):
        """Test that JSON serialization is deterministic."""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "b": 2, "a": 1}  # Same data, different key order

        sig1 = signer.sign(data1, "key1")
        sig2 = signer.sign(data2, "key1")

        # Should produce same signature due to sorted keys
        assert sig1.signature == sig2.signature

    def test_different_data_different_signature(self, signer):
        """Test that different data produces different signatures."""
        data1 = "test data 1"
        data2 = "test data 2"

        sig1 = signer.sign(data1, "key1")
        sig2 = signer.sign(data2, "key1")

        assert sig1.signature != sig2.signature

    def test_different_keys_different_signature(self, signer):
        """Test that different keys produce different signatures."""
        data = "test data"

        sig1 = signer.sign(data, "key1")
        sig2 = signer.sign(data, "key2")

        assert sig1.signature != sig2.signature

    def test_get_algorithm(self, signer):
        """Test getting algorithm identifier."""
        assert signer.get_algorithm() == "sha256-hmac"

    def test_unsupported_data_type(self, signer):
        """Test signing unsupported data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            signer.sign(123, "key1")  # int is not supported


class TestDeterministicSigner:
    """Test deterministic signer functionality."""

    @pytest.fixture
    def master_key(self):
        """Create master key for testing."""
        return b"master-key-for-deterministic-testing"

    @pytest.fixture
    def signer(self, master_key):
        """Create deterministic signer instance."""
        return DeterministicSigner(master_key, "2025-01-01T00:00:00Z")

    def test_sign_deterministic(self, signer):
        """Test that signing is deterministic."""
        data = "test data"

        sig1 = signer.sign(data, "key1")
        sig2 = signer.sign(data, "key1")

        # Should produce identical signatures
        assert sig1.signature == sig2.signature
        assert sig1.timestamp == sig2.timestamp
        assert sig1.algorithm == sig2.algorithm

    def test_verify_deterministic(self, signer):
        """Test verifying deterministic signature."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        assert signer.verify(data, signature_result) is True

    def test_different_keys_different_signatures(self, signer):
        """Test that different keys produce different signatures."""
        data = "test data"

        sig1 = signer.sign(data, "key1")
        sig2 = signer.sign(data, "key2")

        assert sig1.signature != sig2.signature

    def test_key_derivation(self, signer):
        """Test that key derivation is deterministic."""
        data = "test data"

        # Same key should produce same signature
        sig1 = signer.sign(data, "key1")
        sig2 = signer.sign(data, "key1")

        assert sig1.signature == sig2.signature

    def test_get_algorithm(self, signer):
        """Test getting algorithm identifier."""
        assert signer.get_algorithm() == "sha256-hmac-deterministic"

    def test_fixed_timestamp(self, signer):
        """Test that timestamp is fixed."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        assert signature_result.timestamp == "2025-01-01T00:00:00Z"

    def test_verify_invalid_signature(self, signer):
        """Test verifying invalid signature."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        # Tamper with data
        tampered_data = "tampered data"
        assert signer.verify(tampered_data, signature_result) is False

    def test_verify_wrong_algorithm(self, signer):
        """Test verifying with wrong algorithm."""
        data = "test data"
        signature_result = signer.sign(data, "key1")

        # Create signature result with wrong algorithm
        wrong_signature = SignatureResult(
            signature=signature_result.signature,
            algorithm="wrong-algorithm",
            key_id=signature_result.key_id,
            timestamp=signature_result.timestamp,
            metadata=signature_result.metadata,
        )

        assert signer.verify(data, wrong_signature) is False


class TestEvidenceSigner:
    """Test evidence signer functionality."""

    @pytest.fixture
    def keys(self):
        """Create test keys."""
        return {"key1": b"secret-key-1", "key2": b"secret-key-2"}

    def test_default_signer(self):
        """Test default signer creation."""
        signer = EvidenceSigner()

        assert signer.get_algorithm() == "sha256-hmac"

        # Should be able to sign with default key
        data = "test data"
        signature_result = signer.sign(data)
        assert signature_result.key_id == "default"

    def test_custom_hmac_signer(self, keys):
        """Test custom HMAC signer."""
        hmac_signer = HMACSigner(keys)
        signer = EvidenceSigner(hmac_signer)

        assert signer.get_algorithm() == "sha256-hmac"

        data = "test data"
        signature_result = signer.sign(data, "key1")
        assert signature_result.key_id == "key1"

    def test_custom_deterministic_signer(self):
        """Test custom deterministic signer."""
        master_key = b"master-key"
        deterministic_signer = DeterministicSigner(master_key)
        signer = EvidenceSigner(deterministic_signer)

        assert signer.get_algorithm() == "sha256-hmac-deterministic"

        data = "test data"
        signature_result = signer.sign(data, "key1")
        assert signature_result.key_id == "key1"

    def test_sign_and_verify(self, keys):
        """Test sign and verify operations."""
        hmac_signer = HMACSigner(keys)
        signer = EvidenceSigner(hmac_signer)

        data = "test data"
        signature_result = signer.sign(data, "key1")

        assert signer.verify(data, signature_result) is True

        # Tamper with data
        tampered_data = "tampered data"
        assert signer.verify(tampered_data, signature_result) is False

    def test_create_hmac_signer(self, keys):
        """Test creating HMAC signer."""
        signer = EvidenceSigner()
        hmac_signer = signer.create_hmac_signer(keys)

        assert isinstance(hmac_signer, EvidenceSigner)
        assert hmac_signer.get_algorithm() == "sha256-hmac"

        data = "test data"
        signature_result = hmac_signer.sign(data, "key1")
        assert signature_result.key_id == "key1"

    def test_create_deterministic_signer(self):
        """Test creating deterministic signer."""
        signer = EvidenceSigner()
        master_key = b"master-key"
        deterministic_signer = signer.create_deterministic_signer(
            master_key, "2025-01-01T00:00:00Z"
        )

        assert isinstance(deterministic_signer, EvidenceSigner)
        assert deterministic_signer.get_algorithm() == "sha256-hmac-deterministic"

        data = "test data"
        signature_result = deterministic_signer.sign(data, "key1")
        assert signature_result.key_id == "key1"
        assert signature_result.timestamp == "2025-01-01T00:00:00Z"

    def test_deterministic_replay(self):
        """Test deterministic replay capability."""
        master_key = b"master-key-for-replay"
        signer = EvidenceSigner()
        deterministic_signer = signer.create_deterministic_signer(
            master_key, "2025-01-01T00:00:00Z"
        )

        data = "test data for replay"

        # Sign multiple times
        sig1 = deterministic_signer.sign(data, "key1")
        sig2 = deterministic_signer.sign(data, "key1")
        sig3 = deterministic_signer.sign(data, "key1")

        # All signatures should be identical
        assert sig1.signature == sig2.signature
        assert sig2.signature == sig3.signature
        assert sig1.timestamp == sig2.timestamp
        assert sig2.timestamp == sig3.timestamp


class TestSignatureResult:
    """Test SignatureResult validation."""

    def test_valid_signature_result(self):
        """Test creating valid signature result."""
        signature_result = SignatureResult(
            signature="base64-encoded-signature",
            algorithm="sha256-hmac",
            key_id="test-key",
            timestamp="2025-01-01T00:00:00Z",
            metadata={"test": "value"},
        )

        assert signature_result.signature == "base64-encoded-signature"
        assert signature_result.algorithm == "sha256-hmac"
        assert signature_result.key_id == "test-key"
        assert signature_result.timestamp == "2025-01-01T00:00:00Z"
        assert signature_result.metadata == {"test": "value"}

    def test_empty_signature(self):
        """Test empty signature."""
        with pytest.raises(ValueError, match="Signature cannot be empty"):
            SignatureResult(
                signature="",
                algorithm="sha256-hmac",
                key_id="test-key",
                timestamp="2025-01-01T00:00:00Z",
                metadata={},
            )

    def test_empty_algorithm(self):
        """Test empty algorithm."""
        with pytest.raises(ValueError, match="Algorithm cannot be empty"):
            SignatureResult(
                signature="base64-encoded-signature",
                algorithm="",
                key_id="test-key",
                timestamp="2025-01-01T00:00:00Z",
                metadata={},
            )

    def test_empty_key_id(self):
        """Test empty key ID."""
        with pytest.raises(ValueError, match="Key ID cannot be empty"):
            SignatureResult(
                signature="base64-encoded-signature",
                algorithm="sha256-hmac",
                key_id="",
                timestamp="2025-01-01T00:00:00Z",
                metadata={},
            )

    def test_empty_timestamp(self):
        """Test empty timestamp."""
        with pytest.raises(ValueError, match="Timestamp cannot be empty"):
            SignatureResult(
                signature="base64-encoded-signature",
                algorithm="sha256-hmac",
                key_id="test-key",
                timestamp="",
                metadata={},
            )

    def test_immutable(self):
        """Test that SignatureResult is immutable."""
        signature_result = SignatureResult(
            signature="base64-encoded-signature",
            algorithm="sha256-hmac",
            key_id="test-key",
            timestamp="2025-01-01T00:00:00Z",
            metadata={"test": "value"},
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):
            signature_result.signature = "new-signature"


class TestContractTests:
    """Test contract compliance."""

    def test_same_inputs_same_outputs(self):
        """Test that same inputs produce same outputs (determinism)."""
        master_key = b"contract-test-key"
        signer = EvidenceSigner()
        deterministic_signer = signer.create_deterministic_signer(
            master_key, "2025-01-01T00:00:00Z"
        )

        data = {"test": "value", "number": 42}
        key_id = "contract-key"

        # Sign multiple times
        sig1 = deterministic_signer.sign(data, key_id)
        sig2 = deterministic_signer.sign(data, key_id)
        sig3 = deterministic_signer.sign(data, key_id)

        # All should be identical
        assert sig1.signature == sig2.signature == sig3.signature
        assert sig1.algorithm == sig2.algorithm == sig3.algorithm
        assert sig1.key_id == sig2.key_id == sig3.key_id
        assert sig1.timestamp == sig2.timestamp == sig3.timestamp

    def test_different_inputs_different_outputs(self):
        """Test that different inputs produce different outputs."""
        master_key = b"contract-test-key"
        signer = EvidenceSigner()
        deterministic_signer = signer.create_deterministic_signer(
            master_key, "2025-01-01T00:00:00Z"
        )

        data1 = {"test": "value1"}
        data2 = {"test": "value2"}
        key_id = "contract-key"

        sig1 = deterministic_signer.sign(data1, key_id)
        sig2 = deterministic_signer.sign(data2, key_id)

        # Should be different
        assert sig1.signature != sig2.signature

    def test_verification_contract(self):
        """Test verification contract."""
        master_key = b"contract-test-key"
        signer = EvidenceSigner()
        deterministic_signer = signer.create_deterministic_signer(
            master_key, "2025-01-01T00:00:00Z"
        )

        data = "test data"
        key_id = "contract-key"

        signature_result = deterministic_signer.sign(data, key_id)

        # Should verify successfully
        assert deterministic_signer.verify(data, signature_result) is True

        # Should fail with tampered data
        tampered_data = "tampered data"
        assert deterministic_signer.verify(tampered_data, signature_result) is False
