"""
Evidence OS - Deterministic, content-addressed evidence storage and verification.

This package provides the foundational primitives for evidence-first architecture:
- Ledger: Append-only, hash-chained record storage
- Blob Store: Content-addressed artifact storage
- Signer: Deterministic signing and verification

All components are designed for determinism, replayability, and audit compliance.
"""

from .ledger import EvidenceLedger, LedgerRecord
from .blob_store import BlobStore, BlobReference
from .signer import EvidenceSigner, SignatureResult

__all__ = [
    "EvidenceLedger",
    "LedgerRecord",
    "BlobStore",
    "BlobReference",
    "EvidenceSigner",
    "SignatureResult",
]
