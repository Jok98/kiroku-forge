"""Offline JSON Schema validation for canonical memory."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urldefrag, urljoin

import fastjsonschema

from .canonical import canonical_dumps
from .findings import Finding, ValidationResult


ROOT = Path(__file__).resolve().parents[2]
COMMON_SCHEMA_PATH = ROOT / "schemas" / "common-v1.schema.json"
MEMORY_SCHEMA_PATH = ROOT / "schemas" / "memory-v3.schema.json"
PIPELINE_SCHEMA_PATH = ROOT / "schemas" / "pipeline-v1.schema.json"
CAPTURE_BUNDLE_SCHEMA_PATH = ROOT / "schemas" / "capture-bundle-v1.schema.json"
CHANGE_SET_SCHEMA_PATH = ROOT / "schemas" / "change-set-v1.schema.json"
SCHEMA_VIOLATION = "SCHEMA_VIOLATION"

SchemaValidator = Callable[[Any], Any]


class SchemaContractError(RuntimeError):
    """Raised when local schema files cannot be compiled safely."""


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaContractError(
            f"cannot load schema {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SchemaContractError(f"schema {path} must contain an object")
    if not isinstance(value.get("$id"), str):
        raise SchemaContractError(f"schema {path} must declare a string $id")
    return value


def _iter_references(value: Any) -> list[str]:
    references: list[str] = []
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            references.append(reference)
        for nested in value.values():
            references.extend(_iter_references(nested))
    elif isinstance(value, list):
        for nested in value:
            references.extend(_iter_references(nested))
    return references


def _verify_local_references(
    schema: dict[str, Any],
    allowed_documents: set[str],
) -> None:
    schema_id = schema["$id"]
    for reference in _iter_references(schema):
        document_uri, _ = urldefrag(urljoin(schema_id, reference))
        if document_uri not in allowed_documents:
            raise SchemaContractError(
                f"schema {schema_id} references non-local document "
                f"{document_uri}"
            )


def _compile_local_schema(
    root_schema_path: Path,
    dependency_paths: tuple[Path, ...],
) -> SchemaValidator:
    root_schema = _load_schema(root_schema_path)
    dependencies = [_load_schema(path) for path in dependency_paths]
    schemas = {
        schema["$id"]: schema
        for schema in [root_schema, *dependencies]
    }
    if len(schemas) != len(dependencies) + 1:
        raise SchemaContractError("local schemas must have unique $id values")

    allowed_documents = set(schemas)
    for schema in schemas.values():
        _verify_local_references(schema, allowed_documents)

    def resolve_local(uri: str) -> dict[str, Any]:
        document_uri, _ = urldefrag(uri)
        try:
            return schemas[document_uri]
        except KeyError as exc:
            raise SchemaContractError(
                f"schema resolution is restricted to local documents: {uri}"
            ) from exc

    try:
        return fastjsonschema.compile(
            root_schema,
            handlers={
                "http": resolve_local,
                "https": resolve_local,
            },
            use_default=False,
            detailed_exceptions=True,
        )
    except SchemaContractError:
        raise
    except Exception as exc:
        raise SchemaContractError(
            f"cannot compile schema {root_schema_path}: {exc}"
        ) from exc


def compile_memory_schema(
    memory_schema_path: Path = MEMORY_SCHEMA_PATH,
    common_schema_path: Path = COMMON_SCHEMA_PATH,
) -> SchemaValidator:
    """Compile the memory schema using only explicitly supplied local schemas."""

    return _compile_local_schema(
        memory_schema_path,
        (common_schema_path,),
    )


def compile_change_set_schema(
    change_set_schema_path: Path = CHANGE_SET_SCHEMA_PATH,
    pipeline_schema_path: Path = PIPELINE_SCHEMA_PATH,
    memory_schema_path: Path = MEMORY_SCHEMA_PATH,
    common_schema_path: Path = COMMON_SCHEMA_PATH,
) -> SchemaValidator:
    """Compile the ChangeSet schema and its local dependency graph."""

    return _compile_local_schema(
        change_set_schema_path,
        (
            pipeline_schema_path,
            memory_schema_path,
            common_schema_path,
        ),
    )


def compile_capture_bundle_schema(
    capture_bundle_schema_path: Path = CAPTURE_BUNDLE_SCHEMA_PATH,
    pipeline_schema_path: Path = PIPELINE_SCHEMA_PATH,
    memory_schema_path: Path = MEMORY_SCHEMA_PATH,
    common_schema_path: Path = COMMON_SCHEMA_PATH,
) -> SchemaValidator:
    """Compile the CaptureBundle schema and its local dependency graph."""

    return _compile_local_schema(
        capture_bundle_schema_path,
        (
            pipeline_schema_path,
            memory_schema_path,
            common_schema_path,
        ),
    )


def compile_pipeline_definition(
    definition: str,
    pipeline_schema_path: Path = PIPELINE_SCHEMA_PATH,
    memory_schema_path: Path = MEMORY_SCHEMA_PATH,
    common_schema_path: Path = COMMON_SCHEMA_PATH,
) -> SchemaValidator:
    """Compile one shared pipeline definition with local dependencies."""

    pipeline_schema = _load_schema(pipeline_schema_path)
    wrapper = {
        "$schema": pipeline_schema["$schema"],
        "$id": (
            "https://kiroku-forge.local/runtime/"
            f"{definition}.schema.json"
        ),
        "$ref": f"{pipeline_schema['$id']}#/$defs/{definition}",
    }
    schemas = {
        wrapper["$id"]: wrapper,
        pipeline_schema["$id"]: pipeline_schema,
    }
    for path in (memory_schema_path, common_schema_path):
        schema = _load_schema(path)
        schemas[schema["$id"]] = schema

    allowed_documents = set(schemas)
    for schema in schemas.values():
        _verify_local_references(schema, allowed_documents)

    def resolve_local(uri: str) -> dict[str, Any]:
        document_uri, _ = urldefrag(uri)
        try:
            return schemas[document_uri]
        except KeyError as exc:
            raise SchemaContractError(
                f"schema resolution is restricted to local documents: {uri}"
            ) from exc

    try:
        return fastjsonschema.compile(
            wrapper,
            handlers={"http": resolve_local, "https": resolve_local},
            use_default=False,
            detailed_exceptions=True,
        )
    except SchemaContractError:
        raise
    except Exception as exc:
        raise SchemaContractError(
            f"cannot compile pipeline definition {definition!r}: {exc}"
        ) from exc


@lru_cache(maxsize=1)
def _default_validator() -> SchemaValidator:
    return compile_memory_schema()


@lru_cache(maxsize=1)
def _default_change_set_validator() -> SchemaValidator:
    return compile_change_set_schema()


@lru_cache(maxsize=1)
def _default_capture_bundle_validator() -> SchemaValidator:
    return compile_capture_bundle_schema()


def _path_and_entities(
    instance: Any,
    raw_path: list[Any],
) -> tuple[str, tuple[str, ...]]:
    components = list(raw_path)
    if components and components[0] == "data":
        components.pop(0)

    current = instance
    path = "$"
    nearest_entity: str | None = None
    entity_fields = (
        "id",
        "operation_id",
        "candidate_id",
        "captured_source_id",
        "change_set_id",
        "memory_id",
        "capture_bundle_id",
        "candidate_bundle_id",
        "audit_report_id",
        "context_pack_id",
    )

    for component in components:
        if isinstance(current, dict):
            for field in entity_fields:
                entity_id = current.get(field)
                if isinstance(entity_id, str):
                    nearest_entity = entity_id
                    break

            key = str(component)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                path += f".{key}"
            else:
                path += f"[{json.dumps(key, ensure_ascii=False)}]"
            current = current.get(key)
            continue

        if isinstance(current, list):
            try:
                index = int(component)
            except (TypeError, ValueError):
                path += f"[{json.dumps(str(component), ensure_ascii=False)}]"
                current = None
                continue
            path += f"[{index}]"
            current = current[index] if 0 <= index < len(current) else None
            continue

        path += f"[{json.dumps(str(component), ensure_ascii=False)}]"
        current = None

    if isinstance(current, dict):
        for field in entity_fields:
            entity_id = current.get(field)
            if isinstance(entity_id, str):
                nearest_entity = entity_id
                break

    entity_ids = (nearest_entity,) if nearest_entity is not None else ()
    return path, entity_ids


def _schema_message(
    exc: fastjsonschema.JsonSchemaException,
    path: str,
) -> str:
    rule = exc.rule or "unknown"
    definition = exc.rule_definition

    if rule == "required" and isinstance(exc.value, dict):
        required = definition if isinstance(definition, list) else []
        missing = sorted(
            item
            for item in required
            if isinstance(item, str) and item not in exc.value
        )
        return f"{path}: missing required properties {canonical_dumps(missing)}"

    if rule == "additionalProperties" and isinstance(exc.value, dict):
        properties = exc.definition.get("properties", {})
        allowed = set(properties) if isinstance(properties, dict) else set()
        unexpected = sorted(set(exc.value) - allowed)
        return f"{path}: unexpected properties {canonical_dumps(unexpected)}"

    if rule == "enum":
        return (
            f"{path}: value must match one of "
            f"{canonical_dumps(definition)}"
        )

    if rule == "const":
        return f"{path}: value must equal {canonical_dumps(definition)}"

    if rule == "type":
        return f"{path}: value must have type {canonical_dumps(definition)}"

    return f"{path}: schema rule {rule!r} failed"


def validate_memory_schema(
    memory: Any,
    *,
    validator: SchemaValidator | None = None,
) -> ValidationResult:
    """Validate memory shape without mutation or remote schema resolution."""

    active_validator = validator or _default_validator()
    try:
        active_validator(memory)
    except fastjsonschema.JsonSchemaException as exc:
        path, entity_ids = _path_and_entities(memory, exc.path)
        return ValidationResult(
            (
                Finding(
                    code=SCHEMA_VIOLATION,
                    severity="error",
                    path=path,
                    message=_schema_message(exc, path),
                    entity_ids=entity_ids,
                ),
            )
        )
    return ValidationResult()


def validate_change_set_schema(
    change_set: Any,
    *,
    validator: SchemaValidator | None = None,
) -> ValidationResult:
    """Validate ChangeSet shape without mutation or remote resolution."""

    active_validator = validator or _default_change_set_validator()
    try:
        active_validator(change_set)
    except fastjsonschema.JsonSchemaException as exc:
        path, entity_ids = _path_and_entities(change_set, exc.path)
        return ValidationResult(
            (
                Finding(
                    code=SCHEMA_VIOLATION,
                    severity="error",
                    path=path,
                    message=_schema_message(exc, path),
                    entity_ids=entity_ids,
                ),
            )
        )
    return ValidationResult()


def validate_capture_bundle_schema(
    capture_bundle: Any,
    *,
    validator: SchemaValidator | None = None,
) -> ValidationResult:
    """Validate CaptureBundle shape without mutation or remote resolution."""

    active_validator = validator or _default_capture_bundle_validator()
    try:
        active_validator(capture_bundle)
    except fastjsonschema.JsonSchemaException as exc:
        path, entity_ids = _path_and_entities(capture_bundle, exc.path)
        return ValidationResult(
            (
                Finding(
                    code=SCHEMA_VIOLATION,
                    severity="error",
                    path=path,
                    message=_schema_message(exc, path),
                    entity_ids=entity_ids,
                ),
            )
        )
    return ValidationResult()
