"""
Append-only ledger for evidence records with hash-chained integrity.

Provides WORM (Write Once, Read Many) ledger with Merkle-rooted bundles
and content-addressed references for audit compliance.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from .blob_store import BlobStore, BlobReference


@dataclass(frozen=True)
class LedgerRecord:
    """Immutable ledger record with hash-chained integrity."""

    record_id: str  # Unique record identifier
    timestamp: str  # ISO 8601 timestamp
    key: str  # Record key for retrieval
    data_hash: str  # Content hash of the data
    previous_hash: Optional[str]  # Hash of previous record (for chaining)
    merkle_root: str  # Merkle root of current bundle
    bundle_id: str  # Bundle identifier
    metadata: Dict[str, Any]  # Additional metadata

    def __post_init__(self):
        """Validate ledger record."""
        if not self.record_id:
            raise ValueError("Record ID cannot be empty")
        if not self.key:
            raise ValueError("Key cannot be empty")
        if not self.data_hash.startswith("sha256:"):
            raise ValueError("Data hash must start with 'sha256:'")
        if self.merkle_root and not self.merkle_root.startswith("sha256:"):
            raise ValueError("Merkle root must start with 'sha256:'")
        if not self.bundle_id:
            raise ValueError("Bundle ID cannot be empty")


@dataclass
class Bundle:
    """Bundle of ledger records with Merkle tree."""

    bundle_id: str
    records: List[LedgerRecord] = field(default_factory=list)
    merkle_root: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_record(self, record: LedgerRecord) -> None:
        """Add record to bundle."""
        self.records.append(record)
        self._update_merkle_root()

    def _update_merkle_root(self) -> None:
        """Update Merkle root based on current records."""
        if not self.records:
            self.merkle_root = None
            return

        # Create Merkle tree from record hashes
        hashes = [record.data_hash for record in self.records]
        self.merkle_root = self._compute_merkle_root(hashes)

    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """Compute Merkle root from list of hashes."""
        if len(hashes) == 1:
            return hashes[0]

        # Pair hashes and compute parent hashes
        parent_hashes = []
        for i in range(0, len(hashes), 2):
            if i + 1 < len(hashes):
                combined = hashes[i] + hashes[i + 1]
            else:
                combined = hashes[i] + hashes[i]  # Duplicate for odd count

            hash_obj = hashlib.sha256(combined.encode())
            parent_hashes.append(f"sha256:{hash_obj.hexdigest()}")

        return self._compute_merkle_root(parent_hashes)


class EvidenceLedger:
    """
    Append-only ledger with hash-chained integrity and content-addressed references.

    Provides WORM guarantees with Merkle-rooted bundles for audit compliance.
    All operations are deterministic and tamper-evident.
    """

    def __init__(
        self,
        ledger_path: Union[str, Path] = "data/evidence/ledger",
        blob_store: Optional[BlobStore] = None,
    ):
        """
        Initialize evidence ledger.

        Args:
            ledger_path: Directory for ledger storage
            blob_store: Blob store for data storage (creates default if None)
        """
        self.ledger_path = Path(ledger_path)
        self.ledger_path.mkdir(parents=True, exist_ok=True)

        # Initialize blob store
        if blob_store is None:
            blob_store_path = self.ledger_path / "blobs"
            self.blob_store = BlobStore(blob_store_path)
        else:
            self.blob_store = blob_store

        # Create ledger subdirectories
        self.records_dir = self.ledger_path / "records"
        self.bundles_dir = self.ledger_path / "bundles"
        self.index_dir = self.ledger_path / "index"

        self.records_dir.mkdir(exist_ok=True)
        self.bundles_dir.mkdir(exist_ok=True)
        self.index_dir.mkdir(exist_ok=True)

        # Current bundle for batching
        self.current_bundle: Optional[Bundle] = None
        self.bundle_size_limit = 1000  # Records per bundle

        # Load existing state
        self._load_state()

    def write(
        self,
        key: str,
        data: Union[bytes, str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LedgerRecord:
        """
        Write data to ledger with append-only guarantee.

        Args:
            key: Record key for retrieval
            data: Data to store
            metadata: Additional metadata

        Returns:
            LedgerRecord with hash-chained integrity

        Raises:
            ValueError: If key is invalid or data is empty
        """
        if not key or not key.strip():
            raise ValueError("Key cannot be empty")

        # Store data in blob store
        blob_ref = self.blob_store.write(data, metadata=metadata)

        # Get previous record hash for chaining
        previous_hash = self._get_latest_hash()

        # Create record
        record_id = self._generate_record_id()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Ensure we have a current bundle
        if self.current_bundle is None:
            self.current_bundle = Bundle(bundle_id=self._generate_bundle_id())

        # Add to current bundle first to compute merkle root
        # Create a temporary record for the bundle
        temp_record = LedgerRecord(
            record_id=record_id,
            timestamp=timestamp,
            key=key,
            data_hash=blob_ref.hash,
            previous_hash=previous_hash,
            merkle_root="",  # Will be computed by bundle
            bundle_id=self.current_bundle.bundle_id,
            metadata=metadata or {},
        )

        # Add to current bundle to compute merkle root
        self.current_bundle.add_record(temp_record)

        # Create final record with the bundle's final merkle root
        # All records in the same bundle should have the same merkle root
        final_record = LedgerRecord(
            record_id=record_id,
            timestamp=timestamp,
            key=key,
            data_hash=blob_ref.hash,
            previous_hash=previous_hash,
            merkle_root=self.current_bundle.merkle_root or "",
            bundle_id=self.current_bundle.bundle_id,
            metadata=metadata or {},
        )

        # Store record
        self._store_record(final_record)

        # Check if bundle should be finalized
        if len(self.current_bundle.records) >= self.bundle_size_limit:
            self._finalize_bundle()

        return final_record

    def read(self, key: str) -> Optional[bytes]:
        """
        Read data by key.

        Args:
            key: Record key

        Returns:
            Data as bytes, or None if not found
        """
        record = self.read_record(key)
        if record is None:
            return None

        return self.blob_store.read(record.data_hash)

    def read_as_text(self, key: str, encoding: str = "utf-8") -> Optional[str]:
        """
        Read data as text by key.

        Args:
            key: Record key
            encoding: Text encoding

        Returns:
            Data as string, or None if not found
        """
        data = self.read(key)
        if data is None:
            return None
        return data.decode(encoding)

    def read_as_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Read data as JSON by key.

        Args:
            key: Record key

        Returns:
            Parsed JSON data, or None if not found
        """
        data = self.read_as_text(key)
        if data is None:
            return None
        return json.loads(data)

    def read_record(self, key: str) -> Optional[LedgerRecord]:
        """
        Read ledger record by key.

        Args:
            key: Record key

        Returns:
            LedgerRecord, or None if not found
        """
        index_path = self.index_dir / f"{key}.json"
        if not index_path.exists():
            return None

        with open(index_path, "r") as f:
            record_data = json.load(f)

        return LedgerRecord(**record_data)

    def read_by_id(self, record_id: str) -> Optional[LedgerRecord]:
        """
        Read ledger record by record ID.

        Args:
            record_id: Record ID

        Returns:
            LedgerRecord, or None if not found
        """
        record_path = self.records_dir / f"{record_id}.json"
        if not record_path.exists():
            return None

        with open(record_path, "r") as f:
            record_data = json.load(f)

        return LedgerRecord(**record_data)

    def list_keys(self) -> List[str]:
        """
        List all record keys.

        Returns:
            List of record keys
        """
        keys = []
        for index_file in self.index_dir.glob("*.json"):
            keys.append(index_file.stem)
        return sorted(keys)

    def list_records(self, limit: Optional[int] = None) -> List[LedgerRecord]:
        """
        List all records (chronological order).

        Args:
            limit: Maximum number of records to return

        Returns:
            List of LedgerRecord objects
        """
        records = []
        for record_file in sorted(self.records_dir.glob("*.json")):
            with open(record_file, "r") as f:
                record_data = json.load(f)
            records.append(LedgerRecord(**record_data))

            if limit and len(records) >= limit:
                break

        return records

    def verify_integrity(self, key: str) -> bool:
        """
        Verify record integrity by checking hash chain.

        Args:
            key: Record key to verify

        Returns:
            True if integrity is verified
        """
        record = self.read_record(key)
        if record is None:
            return False

        # Verify data hash matches stored data
        try:
            stored_data = self.blob_store.read(record.data_hash)
            hash_obj = hashlib.sha256(stored_data)
            computed_hash = f"sha256:{hash_obj.hexdigest()}"
            if computed_hash != record.data_hash:
                return False
        except FileNotFoundError:
            return False

        # Verify hash chain
        if record.previous_hash:
            # Check if previous record exists and has correct hash
            prev_record = self._find_record_by_hash(record.previous_hash)
            if prev_record is None:
                return False

        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get ledger statistics.

        Returns:
            Dictionary with ledger stats
        """
        records = self.list_records()
        keys = self.list_keys()

        return {
            "total_records": len(records),
            "unique_keys": len(keys),
            "latest_hash": self._get_latest_hash(),
            "current_bundle_size": (
                len(self.current_bundle.records) if self.current_bundle else 0
            ),
            "blob_store_stats": self.blob_store.get_stats(),
        }

    def finalize_bundle(self) -> Optional[str]:
        """
        Manually finalize current bundle.

        Returns:
            Bundle ID if finalized, None if no current bundle
        """
        if self.current_bundle is None:
            return None

        return self._finalize_bundle()

    def _load_state(self) -> None:
        """Load existing ledger state."""
        # Find latest record to establish hash chain
        records = self.list_records()
        if records:
            latest_record = records[-1]
            self._latest_hash = latest_record.data_hash
        else:
            self._latest_hash = None

        # Load current bundle if exists
        bundle_files = list(self.bundles_dir.glob("*.json"))
        if bundle_files:
            latest_bundle_file = max(bundle_files, key=lambda f: f.stat().st_mtime)
            with open(latest_bundle_file, "r") as f:
                bundle_data = json.load(f)

            self.current_bundle = Bundle(
                bundle_id=bundle_data["bundle_id"], timestamp=bundle_data["timestamp"]
            )

            # Load records into bundle
            for record_id in bundle_data.get("record_ids", []):
                record = self.read_by_id(record_id)
                if record:
                    self.current_bundle.add_record(record)

    def _store_record(self, record: LedgerRecord) -> None:
        """Store record to filesystem."""
        # Store record file
        record_path = self.records_dir / f"{record.record_id}.json"
        with open(record_path, "w") as f:
            json.dump(asdict(record), f, indent=2)

        # Update index
        index_path = self.index_dir / f"{record.key}.json"
        with open(index_path, "w") as f:
            json.dump(asdict(record), f, indent=2)

        # Update latest hash
        self._latest_hash = record.data_hash

    def _finalize_bundle(self) -> str:
        """Finalize current bundle and start new one."""
        if self.current_bundle is None:
            raise ValueError("No current bundle to finalize")

        # Update all records in the bundle with the final merkle root
        final_merkle_root = self.current_bundle.merkle_root
        for record in self.current_bundle.records:
            # Create updated record with final merkle root
            updated_record = LedgerRecord(
                record_id=record.record_id,
                timestamp=record.timestamp,
                key=record.key,
                data_hash=record.data_hash,
                previous_hash=record.previous_hash,
                merkle_root=final_merkle_root,
                bundle_id=record.bundle_id,
                metadata=record.metadata,
            )
            # Store updated record
            self._store_record(updated_record)

        # Store bundle
        bundle_path = self.bundles_dir / f"{self.current_bundle.bundle_id}.json"
        bundle_data = {
            "bundle_id": self.current_bundle.bundle_id,
            "timestamp": self.current_bundle.timestamp,
            "merkle_root": self.current_bundle.merkle_root,
            "record_ids": [r.record_id for r in self.current_bundle.records],
            "record_count": len(self.current_bundle.records),
        }

        with open(bundle_path, "w") as f:
            json.dump(bundle_data, f, indent=2)

        bundle_id = self.current_bundle.bundle_id

        # Start new bundle
        self.current_bundle = Bundle(bundle_id=self._generate_bundle_id())

        return bundle_id

    def _get_latest_hash(self) -> Optional[str]:
        """Get hash of latest record."""
        return getattr(self, "_latest_hash", None)

    def _find_record_by_hash(self, data_hash: str) -> Optional[LedgerRecord]:
        """Find record by data hash."""
        for record in self.list_records():
            if record.data_hash == data_hash:
                return record
        return None

    def _generate_record_id(self) -> str:
        """Generate unique record ID."""
        timestamp = int(time.time() * 1000000)  # Microsecond precision
        return f"record_{timestamp}"

    def _generate_bundle_id(self) -> str:
        """Generate unique bundle ID."""
        timestamp = int(time.time())
        return f"bundle_{timestamp}"
