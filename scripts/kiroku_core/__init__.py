"""Deterministic core primitives for KirokuForge."""

from .canonical import (
    CanonicalizationError,
    canonical_bytes,
    canonical_dumps,
    canonicalize_record,
    canonicalize_memory,
    is_canonical_memory,
)
from .change_set import (
    validate_change_set,
)
from .hashing import receipt_hash, record_hash, sha256_hash, state_hash
from .findings import Finding, ValidationResult, finding_sort_key
from .integrity import validate_memory_integrity
from .schema import (
    SCHEMA_VIOLATION,
    SchemaContractError,
    compile_change_set_schema,
    compile_memory_schema,
    compile_pipeline_definition,
    validate_change_set_schema,
    validate_memory_schema,
)

__all__ = [
    "CanonicalizationError",
    "Finding",
    "SCHEMA_VIOLATION",
    "SchemaContractError",
    "ValidationResult",
    "canonical_bytes",
    "canonical_dumps",
    "canonicalize_record",
    "canonicalize_memory",
    "compile_memory_schema",
    "compile_change_set_schema",
    "compile_pipeline_definition",
    "finding_sort_key",
    "is_canonical_memory",
    "receipt_hash",
    "record_hash",
    "sha256_hash",
    "state_hash",
    "validate_memory_schema",
    "validate_memory_integrity",
    "validate_change_set",
    "validate_change_set_schema",
]
