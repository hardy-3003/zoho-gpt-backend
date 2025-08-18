"""
Deterministic signing and verification for evidence records.

Provides SHA256 + HMAC wrapper with pluggable signers for legal defensibility.
All operations are deterministic and produce consistent outputs for same inputs.
"""

import hashlib
import hmac
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union


@dataclass(frozen=True)
class SignatureResult:
    """Immutable signature result with verification metadata."""

    signature: str  # Base64-encoded signature
    algorithm: str  # Signature algorithm (e.g., "sha256-hmac")
    key_id: str  # Key identifier
    timestamp: str  # ISO 8601 timestamp
    metadata: Dict[str, Any]  # Additional signature metadata

    def __post_init__(self):
        """Validate signature result."""
        if not self.signature:
            raise ValueError("Signature cannot be empty")
        if not self.algorithm:
            raise ValueError("Algorithm cannot be empty")
        if not self.key_id:
            raise ValueError("Key ID cannot be empty")
        if not self.timestamp:
            raise ValueError("Timestamp cannot be empty")


class Signer(ABC):
    """Abstract base class for pluggable signers."""

    @abstractmethod
    def sign(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        key_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SignatureResult:
        """
        Sign data deterministically.

        Args:
            data: Data to sign
            key_id: Key identifier
            metadata: Additional metadata

        Returns:
            SignatureResult with signature and metadata
        """
        pass

    @abstractmethod
    def verify(
        self, data: Union[bytes, str, Dict[str, Any]], signature_result: SignatureResult
    ) -> bool:
        """
        Verify signature.

        Args:
            data: Original data
            signature_result: Signature result to verify

        Returns:
            True if signature is valid
        """
        pass

    @abstractmethod
    def get_algorithm(self) -> str:
        """Get signature algorithm identifier."""
        pass


class HMACSigner(Signer):
    """
    HMAC-based signer using SHA256 for deterministic signatures.

    Provides pure Python implementation with configurable keys.
    """

    def __init__(self, keys: Dict[str, bytes]):
        """
        Initialize HMAC signer.

        Args:
            keys: Dictionary mapping key_id to secret key bytes
        """
        self.keys = keys

    def sign(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        key_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SignatureResult:
        """
        Sign data using HMAC-SHA256.

        Args:
            data: Data to sign
            key_id: Key identifier
            metadata: Additional metadata

        Returns:
            SignatureResult with HMAC signature

        Raises:
            KeyError: If key_id not found
            ValueError: If data is invalid
        """
        if key_id not in self.keys:
            raise KeyError(f"Key ID not found: {key_id}")

        # Convert data to bytes deterministically
        data_bytes = self._normalize_data(data)

        # Get secret key
        secret_key = self.keys[key_id]

        # Create HMAC signature
        hmac_obj = hmac.new(secret_key, data_bytes, hashlib.sha256)
        signature_bytes = hmac_obj.digest()

        # Encode signature as base64
        import base64

        signature = base64.b64encode(signature_bytes).decode("ascii")

        # Create timestamp
        timestamp = self._get_timestamp()

        return SignatureResult(
            signature=signature,
            algorithm=self.get_algorithm(),
            key_id=key_id,
            timestamp=timestamp,
            metadata=metadata or {},
        )

    def verify(
        self, data: Union[bytes, str, Dict[str, Any]], signature_result: SignatureResult
    ) -> bool:
        """
        Verify HMAC signature.

        Args:
            data: Original data
            signature_result: Signature result to verify

        Returns:
            True if signature is valid
        """
        try:
            # Verify algorithm matches
            if signature_result.algorithm != self.get_algorithm():
                return False

            # Verify key exists
            if signature_result.key_id not in self.keys:
                return False

            # Normalize data
            data_bytes = self._normalize_data(data)

            # Get secret key
            secret_key = self.keys[signature_result.key_id]

            # Decode signature
            import base64

            expected_signature_bytes = base64.b64decode(signature_result.signature)

            # Compute HMAC
            hmac_obj = hmac.new(secret_key, data_bytes, hashlib.sha256)
            computed_signature_bytes = hmac_obj.digest()

            # Compare signatures (constant-time)
            return hmac.compare_digest(
                expected_signature_bytes, computed_signature_bytes
            )

        except Exception:
            return False

    def get_algorithm(self) -> str:
        """Get HMAC-SHA256 algorithm identifier."""
        return "sha256-hmac"

    def _normalize_data(self, data: Union[bytes, str, Dict[str, Any]]) -> bytes:
        """Normalize data to bytes deterministically."""
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data.encode("utf-8")
        elif isinstance(data, dict):
            # Sort keys for deterministic JSON
            json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
            return json_str.encode("utf-8")
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


class DeterministicSigner(Signer):
    """
    Deterministic signer that produces consistent signatures for same inputs.

    Uses a fixed timestamp and deterministic key derivation for testing and replay.
    """

    def __init__(self, master_key: bytes, timestamp: Optional[str] = None):
        """
        Initialize deterministic signer.

        Args:
            master_key: Master key for key derivation
            timestamp: Fixed timestamp for deterministic signatures
        """
        self.master_key = master_key
        self.timestamp = timestamp or "2025-01-01T00:00:00Z"

    def sign(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        key_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SignatureResult:
        """
        Sign data deterministically.

        Args:
            data: Data to sign
            key_id: Key identifier
            metadata: Additional metadata

        Returns:
            SignatureResult with deterministic signature
        """
        # Derive key deterministically
        derived_key = self._derive_key(key_id)

        # Normalize data
        data_bytes = self._normalize_data(data)

        # Create deterministic signature
        hmac_obj = hmac.new(derived_key, data_bytes, hashlib.sha256)
        signature_bytes = hmac_obj.digest()

        # Encode signature
        import base64

        signature = base64.b64encode(signature_bytes).decode("ascii")

        return SignatureResult(
            signature=signature,
            algorithm=self.get_algorithm(),
            key_id=key_id,
            timestamp=self.timestamp,
            metadata=metadata or {},
        )

    def verify(
        self, data: Union[bytes, str, Dict[str, Any]], signature_result: SignatureResult
    ) -> bool:
        """
        Verify deterministic signature.

        Args:
            data: Original data
            signature_result: Signature result to verify

        Returns:
            True if signature is valid
        """
        try:
            if signature_result.algorithm != self.get_algorithm():
                return False

            # Derive key
            derived_key = self._derive_key(signature_result.key_id)

            # Normalize data
            data_bytes = self._normalize_data(data)

            # Decode signature
            import base64

            expected_signature_bytes = base64.b64decode(signature_result.signature)

            # Compute signature
            hmac_obj = hmac.new(derived_key, data_bytes, hashlib.sha256)
            computed_signature_bytes = hmac_obj.digest()

            # Compare signatures
            return hmac.compare_digest(
                expected_signature_bytes, computed_signature_bytes
            )

        except Exception:
            return False

    def get_algorithm(self) -> str:
        """Get deterministic algorithm identifier."""
        return "sha256-hmac-deterministic"

    def _derive_key(self, key_id: str) -> bytes:
        """Derive key deterministically from master key and key_id."""
        hmac_obj = hmac.new(self.master_key, key_id.encode("utf-8"), hashlib.sha256)
        return hmac_obj.digest()

    def _normalize_data(self, data: Union[bytes, str, Dict[str, Any]]) -> bytes:
        """Normalize data to bytes deterministically."""
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data.encode("utf-8")
        elif isinstance(data, dict):
            json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
            return json_str.encode("utf-8")
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")


class EvidenceSigner:
    """
    Evidence signer with pluggable backends and deterministic guarantees.

    Provides unified interface for signing evidence records with multiple
    signer implementations and verification capabilities.
    """

    def __init__(self, signer: Optional[Signer] = None):
        """
        Initialize evidence signer.

        Args:
            signer: Signer implementation (creates default HMAC signer if None)
        """
        if signer is None:
            # Create default signer with test key
            default_key = b"default-evidence-signer-key-2025"
            self.signer = HMACSigner({"default": default_key})
        else:
            self.signer = signer

    def sign(
        self,
        data: Union[bytes, str, Dict[str, Any]],
        key_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SignatureResult:
        """
        Sign data using configured signer.

        Args:
            data: Data to sign
            key_id: Key identifier
            metadata: Additional metadata

        Returns:
            SignatureResult with signature and metadata
        """
        return self.signer.sign(data, key_id, metadata)

    def verify(
        self, data: Union[bytes, str, Dict[str, Any]], signature_result: SignatureResult
    ) -> bool:
        """
        Verify signature using configured signer.

        Args:
            data: Original data
            signature_result: Signature result to verify

        Returns:
            True if signature is valid
        """
        return self.signer.verify(data, signature_result)

    def get_algorithm(self) -> str:
        """Get current signer algorithm."""
        return self.signer.get_algorithm()

    def create_deterministic_signer(
        self, master_key: bytes, timestamp: Optional[str] = None
    ) -> "EvidenceSigner":
        """
        Create deterministic signer for testing and replay.

        Args:
            master_key: Master key for key derivation
            timestamp: Fixed timestamp for deterministic signatures

        Returns:
            New EvidenceSigner with deterministic signer
        """
        deterministic_signer = DeterministicSigner(master_key, timestamp)
        return EvidenceSigner(deterministic_signer)

    def create_hmac_signer(self, keys: Dict[str, bytes]) -> "EvidenceSigner":
        """
        Create HMAC signer with custom keys.

        Args:
            keys: Dictionary mapping key_id to secret key bytes

        Returns:
            New EvidenceSigner with HMAC signer
        """
        hmac_signer = HMACSigner(keys)
        return EvidenceSigner(hmac_signer)
