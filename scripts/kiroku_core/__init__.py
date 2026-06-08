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
from .capture import (
    CaptureResult,
    CaptureSourceInput,
    capture_bundle_hash,
    capture_sources,
    source_content_hash,
)
from .compiler import (
    CompileLockError,
    CompilePersistenceError,
    CompileResult,
    compile_change_set,
    compile_memory_file,
)
from .hashing import receipt_hash, record_hash, sha256_hash, state_hash
from .findings import Finding, ValidationResult, finding_sort_key
from .integrity import validate_memory_integrity
from .schema import (
    SCHEMA_VIOLATION,
    SchemaContractError,
    compile_capture_bundle_schema,
    compile_change_set_schema,
    compile_memory_schema,
    compile_pipeline_definition,
    validate_capture_bundle_schema,
    validate_change_set_schema,
    validate_memory_schema,
)

__all__ = [
    "CanonicalizationError",
    "CaptureResult",
    "CaptureSourceInput",
    "CompileResult",
    "CompileLockError",
    "CompilePersistenceError",
    "Finding",
    "SCHEMA_VIOLATION",
    "SchemaContractError",
    "ValidationResult",
    "canonical_bytes",
    "canonical_dumps",
    "capture_bundle_hash",
    "capture_sources",
    "canonicalize_record",
    "canonicalize_memory",
    "compile_change_set",
    "compile_memory_file",
    "compile_memory_schema",
    "compile_change_set_schema",
    "compile_capture_bundle_schema",
    "compile_pipeline_definition",
    "finding_sort_key",
    "is_canonical_memory",
    "receipt_hash",
    "record_hash",
    "sha256_hash",
    "source_content_hash",
    "state_hash",
    "validate_memory_schema",
    "validate_memory_integrity",
    "validate_capture_bundle_schema",
    "validate_change_set",
    "validate_change_set_schema",
]
