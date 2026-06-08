"""SHA-256 hashing over KirokuForge canonical JSON."""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical import canonical_bytes, canonicalize_memory, canonicalize_record


def sha256_hash(value: Any) -> str:
    """Hash any JSON value using canonical UTF-8 serialization."""

    return f"sha256:{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


def record_hash(record: dict[str, Any]) -> str:
    """Hash a canonicalized record, excluding its stored content hash."""

    normalized = canonicalize_record(record)
    payload = {
        key: value for key, value in normalized.items() if key != "content_hash"
    }
    return sha256_hash(payload)


def state_hash(memory: dict[str, Any]) -> str:
    """Hash the canonical semantic memory state."""

    normalized = canonicalize_memory(memory)
    payload = {
        "memory_id": normalized["memory_id"],
        "revision": normalized["revision"],
        "project": normalized["project"],
        "sources": normalized["sources"],
        "records": normalized["records"],
    }
    return sha256_hash(payload)


def receipt_hash(receipt: dict[str, Any]) -> str:
    """Hash a compilation receipt, excluding its stored receipt hash."""

    payload = {
        key: value for key, value in receipt.items() if key != "receipt_hash"
    }
    return sha256_hash(payload)
