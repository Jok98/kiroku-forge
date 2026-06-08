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


def compile_memory_schema(
    memory_schema_path: Path = MEMORY_SCHEMA_PATH,
    common_schema_path: Path = COMMON_SCHEMA_PATH,
) -> SchemaValidator:
    """Compile the memory schema using only explicitly supplied local schemas."""

    memory_schema = _load_schema(memory_schema_path)
    common_schema = _load_schema(common_schema_path)
    schemas = {
        memory_schema["$id"]: memory_schema,
        common_schema["$id"]: common_schema,
    }
    if len(schemas) != 2:
        raise SchemaContractError("memory and common schemas must have unique $id")

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
            memory_schema,
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
            f"cannot compile memory schema: {exc}"
        ) from exc


@lru_cache(maxsize=1)
def _default_validator() -> SchemaValidator:
    return compile_memory_schema()


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

    for component in components:
        if isinstance(current, dict):
            entity_id = current.get("id")
            if isinstance(entity_id, str):
                nearest_entity = entity_id
            elif path == "$" and isinstance(current.get("memory_id"), str):
                nearest_entity = current["memory_id"]

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
        entity_id = current.get("id")
        if isinstance(entity_id, str):
            nearest_entity = entity_id
        elif path == "$" and isinstance(current.get("memory_id"), str):
            nearest_entity = current["memory_id"]

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
