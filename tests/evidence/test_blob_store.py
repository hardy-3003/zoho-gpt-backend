"""
Unit tests for evidence blob store.

Tests content-addressed storage, deterministic hashing, idempotency,
and tamper detection capabilities.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from evidence.blob_store import BlobStore, BlobReference


class TestBlobStore:
    """Test blob store functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def blob_store(self, temp_dir):
        """Create blob store instance."""
        return BlobStore(temp_dir / "blobs")

    def test_write_bytes(self, blob_store):
        """Test writing bytes data."""
        data = b"test data for blob store"
        blob_ref = blob_store.write(data, content_type="application/octet-stream")

        assert isinstance(blob_ref, BlobReference)
        assert blob_ref.size == len(data)
        assert blob_ref.content_type == "application/octet-stream"
        assert blob_ref.hash.startswith("sha256:")
        assert len(blob_ref.hash) == 71  # sha256: + 64 hex chars

    def test_write_string(self, blob_store):
        """Test writing string data."""
        data = "test string data"
        blob_ref = blob_store.write(data, content_type="text/plain")

        assert blob_ref.size == len(data.encode("utf-8"))
        assert blob_ref.content_type == "text/plain"

    def test_write_dict(self, blob_store):
        """Test writing dictionary data."""
        data = {"key": "value", "number": 42, "nested": {"test": True}}
        blob_ref = blob_store.write(data, content_type="application/json")

        assert blob_ref.content_type == "application/json"
        # Verify deterministic JSON serialization
        expected_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
        assert blob_ref.size == len(expected_json.encode("utf-8"))

    def test_write_with_metadata(self, blob_store):
        """Test writing with metadata."""
        data = "test data"
        metadata = {"source": "test", "version": "1.0", "tags": ["test", "evidence"]}
        blob_ref = blob_store.write(data, metadata=metadata)

        assert blob_ref.metadata == metadata

    def test_read_bytes(self, blob_store):
        """Test reading bytes data."""
        original_data = b"test bytes data"
        blob_ref = blob_store.write(original_data)

        read_data = blob_store.read(blob_ref.hash)
        assert read_data == original_data

    def test_read_as_text(self, blob_store):
        """Test reading as text."""
        original_data = "test text data"
        blob_ref = blob_store.write(original_data)

        read_data = blob_store.read_as_text(blob_ref.hash)
        assert read_data == original_data

    def test_read_as_json(self, blob_store):
        """Test reading as JSON."""
        original_data = {"test": "value", "number": 123}
        blob_ref = blob_store.write(original_data)

        read_data = blob_store.read_as_json(blob_ref.hash)
        assert read_data == original_data

    def test_read_nonexistent(self, blob_store):
        """Test reading nonexistent blob."""
        with pytest.raises(FileNotFoundError):
            blob_store.read(
                "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            )

    def test_read_invalid_hash(self, blob_store):
        """Test reading with invalid hash format."""
        with pytest.raises(ValueError, match="Hash must start with 'sha256:'"):
            blob_store.read("invalid-hash")

    def test_idempotency(self, blob_store):
        """Test that writing same data returns same reference."""
        data = "test data for idempotency"

        ref1 = blob_store.write(data)
        ref2 = blob_store.write(data)

        assert ref1.hash == ref2.hash
        assert ref1.size == ref2.size
        assert ref1.content_type == ref2.content_type

    def test_deterministic_hashing(self, blob_store):
        """Test that same data produces same hash."""
        data = {"key": "value", "nested": {"test": True}}

        ref1 = blob_store.write(data)
        ref2 = blob_store.write(data)

        assert ref1.hash == ref2.hash

    def test_different_data_different_hash(self, blob_store):
        """Test that different data produces different hashes."""
        data1 = "test data 1"
        data2 = "test data 2"

        ref1 = blob_store.write(data1)
        ref2 = blob_store.write(data2)

        assert ref1.hash != ref2.hash

    def test_get_reference(self, blob_store):
        """Test getting blob reference without reading data."""
        data = "test data for reference"
        blob_ref = blob_store.write(data)

        retrieved_ref = blob_store.get_reference(blob_ref.hash)
        assert retrieved_ref.hash == blob_ref.hash
        assert retrieved_ref.size == blob_ref.size
        assert retrieved_ref.content_type == blob_ref.content_type
        assert retrieved_ref.metadata == blob_ref.metadata

    def test_exists(self, blob_store):
        """Test checking if blob exists."""
        data = "test data for exists"
        blob_ref = blob_store.write(data)

        assert blob_store.exists(blob_ref.hash) is True
        assert (
            blob_store.exists(
                "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
            )
            is False
        )

    def test_delete(self, blob_store):
        """Test deleting blob."""
        data = "test data for deletion"
        blob_ref = blob_store.write(data)

        assert blob_store.exists(blob_ref.hash) is True

        # Delete the blob
        deleted = blob_store.delete(blob_ref.hash)
        assert deleted is True

        assert blob_store.exists(blob_ref.hash) is False

        # Try to delete again
        deleted_again = blob_store.delete(blob_ref.hash)
        assert deleted_again is False

    def test_list_hashes(self, blob_store):
        """Test listing all blob hashes."""
        data1 = "test data 1"
        data2 = "test data 2"
        data3 = "test data 3"

        ref1 = blob_store.write(data1)
        ref2 = blob_store.write(data2)
        ref3 = blob_store.write(data3)

        hashes = blob_store.list_hashes()
        assert len(hashes) == 3
        assert ref1.hash in hashes
        assert ref2.hash in hashes
        assert ref3.hash in hashes
        assert hashes == sorted(hashes)  # Should be sorted

    def test_get_stats(self, blob_store):
        """Test getting storage statistics."""
        data1 = "test data 1"
        data2 = "test data 2"

        ref1 = blob_store.write(data1)
        ref2 = blob_store.write(data2)

        stats = blob_store.get_stats()
        assert stats["blob_count"] == 2
        assert stats["total_size_bytes"] == ref1.size + ref2.size
        assert "storage_path" in stats

    def test_unsupported_data_type(self, blob_store):
        """Test writing unsupported data type."""
        with pytest.raises(ValueError, match="Unsupported data type"):
            blob_store.write(123)  # int is not supported

    def test_empty_data(self, blob_store):
        """Test writing empty data."""
        empty_bytes = b""
        empty_string = ""
        empty_dict = {}

        # All should work
        ref1 = blob_store.write(empty_bytes)
        ref2 = blob_store.write(empty_string)
        ref3 = blob_store.write(empty_dict)

        assert ref1.size == 0
        assert ref2.size == 0
        assert ref3.size > 0  # Empty dict becomes "{}"

    def test_large_data(self, blob_store):
        """Test writing large data."""
        large_data = "x" * 10000
        blob_ref = blob_store.write(large_data)

        assert blob_ref.size == 10000
        read_data = blob_store.read_as_text(blob_ref.hash)
        assert read_data == large_data

    def test_special_characters(self, blob_store):
        """Test writing data with special characters."""
        special_data = "test with unicode: 🚀 émojis and special chars: !@#$%^&*()"
        blob_ref = blob_store.write(special_data)

        read_data = blob_store.read_as_text(blob_ref.hash)
        assert read_data == special_data

    def test_json_determinism(self, blob_store):
        """Test that JSON serialization is deterministic."""
        data1 = {"a": 1, "b": 2, "c": 3}
        data2 = {"c": 3, "b": 2, "a": 1}  # Same data, different key order

        ref1 = blob_store.write(data1)
        ref2 = blob_store.write(data2)

        # Should produce same hash due to sorted keys
        assert ref1.hash == ref2.hash


class TestBlobReference:
    """Test BlobReference validation."""

    def test_valid_reference(self):
        """Test creating valid blob reference."""
        ref = BlobReference(
            hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            size=100,
            content_type="text/plain",
            metadata={"test": "value"},
        )

        assert (
            ref.hash
            == "sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        assert ref.size == 100
        assert ref.content_type == "text/plain"
        assert ref.metadata == {"test": "value"}

    def test_invalid_hash_format(self):
        """Test invalid hash format."""
        with pytest.raises(ValueError, match="Hash must start with 'sha256:'"):
            BlobReference(
                hash="invalid-hash", size=100, content_type="text/plain", metadata={}
            )

    def test_invalid_hash_length(self):
        """Test invalid hash length."""
        with pytest.raises(ValueError, match="Invalid SHA256 hash length"):
            BlobReference(
                hash="sha256:short", size=100, content_type="text/plain", metadata={}
            )

    def test_negative_size(self):
        """Test negative size."""
        with pytest.raises(ValueError, match="Size must be non-negative"):
            BlobReference(
                hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                size=-1,
                content_type="text/plain",
                metadata={},
            )

    def test_immutable(self):
        """Test that BlobReference is immutable."""
        ref = BlobReference(
            hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            size=100,
            content_type="text/plain",
            metadata={"test": "value"},
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):
            ref.hash = "new-hash"
