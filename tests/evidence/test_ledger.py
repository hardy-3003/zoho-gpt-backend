"""
Unit tests for evidence ledger.

Tests append-only guarantees, hash chaining, tamper detection,
and Merkle tree integrity.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from evidence.ledger import EvidenceLedger, LedgerRecord, Bundle
from evidence.blob_store import BlobStore


class TestEvidenceLedger:
    """Test evidence ledger functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def ledger(self, temp_dir):
        """Create ledger instance."""
        return EvidenceLedger(temp_dir / "ledger")

    def test_write_and_read(self, ledger):
        """Test basic write and read operations."""
        key = "test_key"
        data = "test data for ledger"

        record = ledger.write(key, data)

        assert isinstance(record, LedgerRecord)
        assert record.key == key
        assert record.data_hash.startswith("sha256:")
        assert record.previous_hash is None  # First record

        # Read data back
        read_data = ledger.read(key)
        assert read_data.decode("utf-8") == data

    def test_write_bytes(self, ledger):
        """Test writing bytes data."""
        key = "bytes_key"
        data = b"test bytes data"

        record = ledger.write(key, data)
        assert record.key == key

        read_data = ledger.read(key)
        assert read_data == data

    def test_write_dict(self, ledger):
        """Test writing dictionary data."""
        key = "dict_key"
        data = {"test": "value", "number": 42}

        record = ledger.write(key, data)
        assert record.key == key

        read_data = ledger.read_as_json(key)
        assert read_data == data

    def test_write_with_metadata(self, ledger):
        """Test writing with metadata."""
        key = "metadata_key"
        data = "test data"
        metadata = {"source": "test", "version": "1.0"}

        record = ledger.write(key, data, metadata=metadata)
        assert record.metadata == metadata

    def test_hash_chaining(self, ledger):
        """Test that records are hash-chained."""
        # Write multiple records
        record1 = ledger.write("key1", "data1")
        record2 = ledger.write("key2", "data2")
        record3 = ledger.write("key3", "data3")

        # Check hash chaining
        assert record1.previous_hash is None
        assert record2.previous_hash == record1.data_hash
        assert record3.previous_hash == record2.data_hash

    def test_read_record(self, ledger):
        """Test reading ledger record."""
        key = "record_key"
        data = "test data"

        written_record = ledger.write(key, data)
        read_record = ledger.read_record(key)

        assert read_record is not None
        assert read_record.record_id == written_record.record_id
        assert read_record.key == written_record.key
        assert read_record.data_hash == written_record.data_hash

    def test_read_by_id(self, ledger):
        """Test reading record by ID."""
        key = "id_key"
        data = "test data"

        written_record = ledger.write(key, data)
        read_record = ledger.read_by_id(written_record.record_id)

        assert read_record is not None
        assert read_record.record_id == written_record.record_id
        assert read_record.key == written_record.key

    def test_read_nonexistent(self, ledger):
        """Test reading nonexistent record."""
        assert ledger.read("nonexistent_key") is None
        assert ledger.read_record("nonexistent_key") is None
        assert ledger.read_by_id("nonexistent_id") is None

    def test_list_keys(self, ledger):
        """Test listing all keys."""
        ledger.write("key1", "data1")
        ledger.write("key2", "data2")
        ledger.write("key3", "data3")

        keys = ledger.list_keys()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys
        assert keys == sorted(keys)  # Should be sorted

    def test_list_records(self, ledger):
        """Test listing all records."""
        record1 = ledger.write("key1", "data1")
        record2 = ledger.write("key2", "data2")
        record3 = ledger.write("key3", "data3")

        records = ledger.list_records()
        assert len(records) == 3
        assert records[0].record_id == record1.record_id
        assert records[1].record_id == record2.record_id
        assert records[2].record_id == record3.record_id

    def test_list_records_with_limit(self, ledger):
        """Test listing records with limit."""
        ledger.write("key1", "data1")
        ledger.write("key2", "data2")
        ledger.write("key3", "data3")

        records = ledger.list_records(limit=2)
        assert len(records) == 2

    def test_verify_integrity(self, ledger):
        """Test integrity verification."""
        key = "integrity_key"
        data = "test data for integrity"

        record = ledger.write(key, data)
        assert ledger.verify_integrity(key) is True

    def test_verify_integrity_nonexistent(self, ledger):
        """Test integrity verification for nonexistent record."""
        assert ledger.verify_integrity("nonexistent_key") is False

    def test_verify_integrity_tampered(self, ledger):
        """Test integrity verification detects tampering."""
        key = "tamper_key"
        data = "original data"

        record = ledger.write(key, data)

        # Tamper with the blob data directly
        blob_path = ledger.blob_store._get_blob_path(record.data_hash)
        with open(blob_path, "wb") as f:
            f.write(b"tampered data")

        # Integrity check should fail
        assert ledger.verify_integrity(key) is False

    def test_get_stats(self, ledger):
        """Test getting ledger statistics."""
        ledger.write("key1", "data1")
        ledger.write("key2", "data2")

        stats = ledger.get_stats()
        assert stats["total_records"] == 2
        assert stats["unique_keys"] == 2
        assert "latest_hash" in stats
        assert "current_bundle_size" in stats
        assert "blob_store_stats" in stats

    def test_finalize_bundle(self, ledger):
        """Test manual bundle finalization."""
        # Write some records
        ledger.write("key1", "data1")
        ledger.write("key2", "data2")

        # Finalize bundle
        bundle_id = ledger.finalize_bundle()
        assert bundle_id is not None

        # Check that new bundle is created
        stats = ledger.get_stats()
        assert stats["current_bundle_size"] == 0

    def test_finalize_empty_bundle(self, ledger):
        """Test finalizing empty bundle."""
        bundle_id = ledger.finalize_bundle()
        assert bundle_id is None

    def test_bundle_size_limit(self, ledger):
        """Test automatic bundle finalization at size limit."""
        # Set small bundle size limit
        ledger.bundle_size_limit = 2

        # Write records
        record1 = ledger.write("key1", "data1")
        record2 = ledger.write("key2", "data2")
        record3 = ledger.write("key3", "data3")

        # Bundle should be automatically finalized after 2 records
        stats = ledger.get_stats()
        assert stats["current_bundle_size"] == 1  # Only record3 in current bundle

    def test_invalid_key(self, ledger):
        """Test writing with invalid key."""
        with pytest.raises(ValueError, match="Key cannot be empty"):
            ledger.write("", "data")

        with pytest.raises(ValueError, match="Key cannot be empty"):
            ledger.write("   ", "data")  # Whitespace only

    def test_persistence(self, temp_dir):
        """Test that ledger persists data across instances."""
        ledger_path = temp_dir / "ledger"

        # Write data with first instance
        ledger1 = EvidenceLedger(ledger_path)
        record1 = ledger1.write("persistent_key", "persistent_data")

        # Create new instance
        ledger2 = EvidenceLedger(ledger_path)

        # Should be able to read data
        read_data = ledger2.read("persistent_key")
        assert read_data.decode("utf-8") == "persistent_data"

        # Should maintain hash chain
        record2 = ledger2.write("new_key", "new_data")
        assert record2.previous_hash == record1.data_hash

    def test_merkle_root_consistency(self, ledger):
        """Test that Merkle roots are consistent within bundle."""
        # Set bundle size limit to ensure records stay in same bundle
        ledger.bundle_size_limit = 10

        # Write multiple records in same bundle
        record1 = ledger.write("key1", "data1")
        record2 = ledger.write("key2", "data2")
        record3 = ledger.write("key3", "data3")

        # Force finalize the bundle to ensure all records have the same merkle root
        ledger.finalize_bundle()

        # Read the records back to get their final merkle roots
        final_record1 = ledger.read_record("key1")
        final_record2 = ledger.read_record("key2")
        final_record3 = ledger.read_record("key3")

        # All records should have same Merkle root (bundle-level)
        assert final_record1.merkle_root == final_record2.merkle_root
        assert final_record2.merkle_root == final_record3.merkle_root
        assert final_record1.merkle_root.startswith("sha256:")

        # The Merkle root should be computed from all record hashes in the bundle
        # For a single record, it should be the record's data hash
        # For multiple records, it should be the Merkle root of all record hashes

    def test_bundle_id_consistency(self, ledger):
        """Test that bundle IDs are consistent within bundle."""
        record1 = ledger.write("key1", "data1")
        record2 = ledger.write("key2", "data2")
        record3 = ledger.write("key3", "data3")

        # All records should have same bundle ID
        assert record1.bundle_id == record2.bundle_id
        assert record2.bundle_id == record3.bundle_id

    def test_timestamp_format(self, ledger):
        """Test that timestamps are in ISO 8601 format."""
        record = ledger.write("timestamp_key", "data")

        # Check timestamp format
        from datetime import datetime

        try:
            datetime.fromisoformat(record.timestamp.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Timestamp is not in valid ISO 8601 format")


class TestBundle:
    """Test Bundle functionality."""

    def test_bundle_creation(self):
        """Test bundle creation."""
        bundle = Bundle("test_bundle")
        assert bundle.bundle_id == "test_bundle"
        assert len(bundle.records) == 0
        assert bundle.merkle_root is None

    def test_add_record(self):
        """Test adding record to bundle."""
        bundle = Bundle("test_bundle")

        # Create mock record
        record = LedgerRecord(
            record_id="record_1",
            timestamp="2025-01-01T00:00:00Z",
            key="test_key",
            data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            previous_hash=None,
            merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            bundle_id="test_bundle",
            metadata={},
        )

        bundle.add_record(record)
        assert len(bundle.records) == 1
        assert bundle.records[0] == record
        assert bundle.merkle_root is not None

    def test_merkle_root_single_record(self):
        """Test Merkle root for single record."""
        bundle = Bundle("test_bundle")

        record = LedgerRecord(
            record_id="record_1",
            timestamp="2025-01-01T00:00:00Z",
            key="test_key",
            data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            previous_hash=None,
            merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            bundle_id="test_bundle",
            metadata={},
        )

        bundle.add_record(record)
        assert bundle.merkle_root == record.data_hash

    def test_merkle_root_multiple_records(self):
        """Test Merkle root for multiple records."""
        bundle = Bundle("test_bundle")

        # Add multiple records
        for i in range(3):
            record = LedgerRecord(
                record_id=f"record_{i}",
                timestamp="2025-01-01T00:00:00Z",
                key=f"key_{i}",
                data_hash=f"sha256:{'0' * 63}{i}",
                previous_hash=None,
                merkle_root=f"sha256:{'0' * 63}{i}",
                bundle_id="test_bundle",
                metadata={},
            )
            bundle.add_record(record)

        # Should have computed Merkle root
        assert bundle.merkle_root is not None
        assert bundle.merkle_root.startswith("sha256:")

    def test_merkle_root_odd_records(self):
        """Test Merkle root computation with odd number of records."""
        bundle = Bundle("test_bundle")

        # Add 5 records (odd number)
        for i in range(5):
            record = LedgerRecord(
                record_id=f"record_{i}",
                timestamp="2025-01-01T00:00:00Z",
                key=f"key_{i}",
                data_hash=f"sha256:{'0' * 63}{i}",
                previous_hash=None,
                merkle_root=f"sha256:{'0' * 63}{i}",
                bundle_id="test_bundle",
                metadata={},
            )
            bundle.add_record(record)

        # Should compute Merkle root correctly
        assert bundle.merkle_root is not None
        assert bundle.merkle_root.startswith("sha256:")


class TestLedgerRecord:
    """Test LedgerRecord validation."""

    def test_valid_record(self):
        """Test creating valid ledger record."""
        record = LedgerRecord(
            record_id="test_record",
            timestamp="2025-01-01T00:00:00Z",
            key="test_key",
            data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            previous_hash=None,
            merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            bundle_id="test_bundle",
            metadata={"test": "value"},
        )

        assert record.record_id == "test_record"
        assert record.key == "test_key"
        assert record.data_hash.startswith("sha256:")
        assert record.merkle_root.startswith("sha256:")
        assert record.bundle_id == "test_bundle"
        assert record.metadata == {"test": "value"}

    def test_empty_record_id(self):
        """Test empty record ID."""
        with pytest.raises(ValueError, match="Record ID cannot be empty"):
            LedgerRecord(
                record_id="",
                timestamp="2025-01-01T00:00:00Z",
                key="test_key",
                data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                previous_hash=None,
                merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                bundle_id="test_bundle",
                metadata={},
            )

    def test_empty_key(self):
        """Test empty key."""
        with pytest.raises(ValueError, match="Key cannot be empty"):
            LedgerRecord(
                record_id="test_record",
                timestamp="2025-01-01T00:00:00Z",
                key="",
                data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                previous_hash=None,
                merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                bundle_id="test_bundle",
                metadata={},
            )

    def test_invalid_data_hash(self):
        """Test invalid data hash format."""
        with pytest.raises(ValueError, match="Data hash must start with 'sha256:'"):
            LedgerRecord(
                record_id="test_record",
                timestamp="2025-01-01T00:00:00Z",
                key="test_key",
                data_hash="invalid-hash",
                previous_hash=None,
                merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                bundle_id="test_bundle",
                metadata={},
            )

    def test_invalid_merkle_root(self):
        """Test invalid Merkle root format."""
        with pytest.raises(ValueError, match="Merkle root must start with 'sha256:'"):
            LedgerRecord(
                record_id="test_record",
                timestamp="2025-01-01T00:00:00Z",
                key="test_key",
                data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                previous_hash=None,
                merkle_root="invalid-root",
                bundle_id="test_bundle",
                metadata={},
            )

    def test_empty_bundle_id(self):
        """Test empty bundle ID."""
        with pytest.raises(ValueError, match="Bundle ID cannot be empty"):
            LedgerRecord(
                record_id="test_record",
                timestamp="2025-01-01T00:00:00Z",
                key="test_key",
                data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                previous_hash=None,
                merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                bundle_id="",
                metadata={},
            )

    def test_immutable(self):
        """Test that LedgerRecord is immutable."""
        record = LedgerRecord(
            record_id="test_record",
            timestamp="2025-01-01T00:00:00Z",
            key="test_key",
            data_hash="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            previous_hash=None,
            merkle_root="sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            bundle_id="test_bundle",
            metadata={"test": "value"},
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):
            record.key = "new_key"
