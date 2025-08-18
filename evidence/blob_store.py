"""
Content-addressed blob storage for evidence artifacts.

Provides deterministic, content-addressed storage for blobs (PDFs, JSON, CSV, images)
with SHA256 hashing and pure Python local backend.
"""

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class BlobReference:
    """Immutable reference to a stored blob."""
    hash: str  # SHA256 hash
    size: int  # Size in bytes
    content_type: str  # MIME type or format identifier
    metadata: Dict[str, Any]  # Additional metadata
    
    def __post_init__(self):
        """Validate blob reference."""
        if not self.hash.startswith('sha256:'):
            raise ValueError("Hash must start with 'sha256:'")
        if len(self.hash) != 71:  # sha256: + 64 hex chars
            raise ValueError("Invalid SHA256 hash length")
        if self.size < 0:
            raise ValueError("Size must be non-negative")


class BlobStore:
    """
    Content-addressed blob storage with deterministic SHA256 hashing.
    
    Provides pure Python local backend with clear interfaces for later swap.
    All operations are deterministic and idempotent.
    """
    
    def __init__(self, storage_path: Union[str, Path] = "data/evidence/blobs"):
        """
        Initialize blob store.
        
        Args:
            storage_path: Directory for blob storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for hash-based organization
        self.blobs_dir = self.storage_path / "blobs"
        self.metadata_dir = self.storage_path / "metadata"
        self.blobs_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
    
    def write(self, data: Union[bytes, str, Dict[str, Any]], 
              content_type: str = "application/octet-stream",
              metadata: Optional[Dict[str, Any]] = None) -> BlobReference:
        """
        Write data to blob store and return content-addressed reference.
        
        Args:
            data: Data to store (bytes, string, or JSON-serializable dict)
            content_type: MIME type or format identifier
            metadata: Additional metadata to store
            
        Returns:
            BlobReference with SHA256 hash and metadata
            
        Raises:
            ValueError: If data is invalid
        """
        # Convert data to bytes
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        elif isinstance(data, dict):
            data_bytes = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        elif isinstance(data, bytes):
            data_bytes = data
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Compute deterministic SHA256 hash
        hash_obj = hashlib.sha256(data_bytes)
        hash_hex = hash_obj.hexdigest()
        content_hash = f"sha256:{hash_hex}"
        
        # Create blob reference
        blob_ref = BlobReference(
            hash=content_hash,
            size=len(data_bytes),
            content_type=content_type,
            metadata=metadata or {}
        )
        
        # Check if already exists (idempotent)
        if self._exists(content_hash):
            return blob_ref
        
        # Store blob data
        blob_path = self._get_blob_path(content_hash)
        with open(blob_path, 'wb') as f:
            f.write(data_bytes)
        
        # Store metadata
        metadata_path = self._get_metadata_path(content_hash)
        with open(metadata_path, 'w') as f:
            json.dump(asdict(blob_ref), f, indent=2)
        
        return blob_ref
    
    def read(self, content_hash: str) -> bytes:
        """
        Read blob data by content hash.
        
        Args:
            content_hash: SHA256 hash of the blob
            
        Returns:
            Blob data as bytes
            
        Raises:
            FileNotFoundError: If blob doesn't exist
            ValueError: If hash format is invalid
        """
        if not content_hash.startswith('sha256:'):
            raise ValueError("Hash must start with 'sha256:'")
        
        blob_path = self._get_blob_path(content_hash)
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {content_hash}")
        
        with open(blob_path, 'rb') as f:
            return f.read()
    
    def read_as_text(self, content_hash: str, encoding: str = 'utf-8') -> str:
        """
        Read blob data as text.
        
        Args:
            content_hash: SHA256 hash of the blob
            encoding: Text encoding
            
        Returns:
            Blob data as string
        """
        data = self.read(content_hash)
        return data.decode(encoding)
    
    def read_as_json(self, content_hash: str) -> Dict[str, Any]:
        """
        Read blob data as JSON.
        
        Args:
            content_hash: SHA256 hash of the blob
            
        Returns:
            Parsed JSON data
        """
        data = self.read_as_text(content_hash)
        return json.loads(data)
    
    def get_reference(self, content_hash: str) -> BlobReference:
        """
        Get blob reference without reading data.
        
        Args:
            content_hash: SHA256 hash of the blob
            
        Returns:
            BlobReference with metadata
            
        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        metadata_path = self._get_metadata_path(content_hash)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Blob metadata not found: {content_hash}")
        
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
        
        return BlobReference(**metadata_dict)
    
    def exists(self, content_hash: str) -> bool:
        """
        Check if blob exists.
        
        Args:
            content_hash: SHA256 hash of the blob
            
        Returns:
            True if blob exists
        """
        return self._exists(content_hash)
    
    def delete(self, content_hash: str) -> bool:
        """
        Delete blob and metadata.
        
        Args:
            content_hash: SHA256 hash of the blob
            
        Returns:
            True if blob was deleted, False if it didn't exist
        """
        blob_path = self._get_blob_path(content_hash)
        metadata_path = self._get_metadata_path(content_hash)
        
        deleted = False
        if blob_path.exists():
            blob_path.unlink()
            deleted = True
        
        if metadata_path.exists():
            metadata_path.unlink()
        
        return deleted
    
    def list_hashes(self) -> list[str]:
        """
        List all stored blob hashes.
        
        Returns:
            List of content hashes
        """
        hashes = []
        for metadata_file in self.metadata_dir.glob("*.json"):
            hash_part = metadata_file.stem
            hashes.append(f"sha256:{hash_part}")
        return sorted(hashes)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        hashes = self.list_hashes()
        total_size = 0
        
        for content_hash in hashes:
            try:
                ref = self.get_reference(content_hash)
                total_size += ref.size
            except FileNotFoundError:
                continue
        
        return {
            "blob_count": len(hashes),
            "total_size_bytes": total_size,
            "storage_path": str(self.storage_path)
        }
    
    def _exists(self, content_hash: str) -> bool:
        """Check if blob exists internally."""
        blob_path = self._get_blob_path(content_hash)
        return blob_path.exists()
    
    def _get_blob_path(self, content_hash: str) -> Path:
        """Get blob file path."""
        hash_part = content_hash[7:]  # Remove 'sha256:' prefix
        return self.blobs_dir / f"{hash_part}.blob"
    
    def _get_metadata_path(self, content_hash: str) -> Path:
        """Get metadata file path."""
        hash_part = content_hash[7:]  # Remove 'sha256:' prefix
        return self.metadata_dir / f"{hash_part}.json"
