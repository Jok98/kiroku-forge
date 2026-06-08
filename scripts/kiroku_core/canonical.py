"""Canonical JSON serialization and memory ordering."""

from __future__ import annotations

import copy
import json
import math
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented as canonical JSON."""


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError(f"{path}: non-finite numbers are not JSON")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"{path}: object keys must be strings")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise CanonicalizationError(
        f"{path}: unsupported JSON value type {type(value).__name__}"
    )


def canonical_dumps(value: Any) -> str:
    """Serialize a JSON value with deterministic keys and no extra whitespace."""

    _validate_json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_bytes(value: Any) -> bytes:
    """Serialize a JSON value as canonical UTF-8 bytes."""

    return canonical_dumps(value).encode("utf-8")


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalizationError(f"{path}: expected object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise CanonicalizationError(f"{path}: expected array")
    return value


def _field(value: dict[str, Any], name: str, path: str) -> Any:
    if name not in value:
        raise CanonicalizationError(f"{path}: missing field {name!r}")
    return value[name]


def _sort_strings(value: dict[str, Any], name: str, path: str) -> None:
    items = _list(_field(value, name, path), f"{path}.{name}")
    if not all(isinstance(item, str) for item in items):
        raise CanonicalizationError(f"{path}.{name}: expected string array")
    items.sort()


def _sort_record(record: dict[str, Any], path: str) -> None:
    _sort_strings(record, "scope", path)
    _sort_strings(record, "tags", path)

    evidence = _list(_field(record, "evidence", path), f"{path}.evidence")
    evidence.sort(
        key=lambda item: _evidence_key(
            _mapping(item, f"{path}.evidence[]"),
            f"{path}.evidence[]",
        )
    )

    relations = _list(_field(record, "relations", path), f"{path}.relations")
    relations.sort(
        key=lambda item: _relation_key(
            _mapping(item, f"{path}.relations[]"),
            f"{path}.relations[]",
        )
    )


def _sort_records(records: list[Any]) -> None:
    for index, value in enumerate(records):
        path = f"$.records[{index}]"
        _sort_record(_mapping(value, path), path)
    records.sort(
        key=lambda item: _string_field(
            _mapping(item, "$.records[]"),
            "id",
            "$.records[]",
        )
    )


def _string_field(value: dict[str, Any], name: str, path: str) -> str:
    result = _field(value, name, path)
    if not isinstance(result, str):
        raise CanonicalizationError(f"{path}.{name}: expected string")
    return result


def _integer_field(value: dict[str, Any], name: str, path: str) -> int:
    result = _field(value, name, path)
    if isinstance(result, bool) or not isinstance(result, int):
        raise CanonicalizationError(f"{path}.{name}: expected integer")
    return result


def _evidence_key(value: dict[str, Any], path: str) -> tuple[str, str, str, bytes]:
    locator = _mapping(_field(value, "locator", path), f"{path}.locator")
    return (
        _string_field(value, "source_id", path),
        _string_field(value, "relation", path),
        _string_field(value, "method", path),
        canonical_bytes(locator),
    )


def _relation_key(value: dict[str, Any], path: str) -> tuple[str, str]:
    return (
        _string_field(value, "type", path),
        _string_field(value, "target_id", path),
    )


def canonicalize_memory(memory: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied memory value with every canonical set ordered."""

    _validate_json_value(memory)
    result = copy.deepcopy(_mapping(memory, "$"))

    project = _mapping(_field(result, "project", "$"), "$.project")
    boundaries = _mapping(
        _field(project, "boundaries", "$.project"),
        "$.project.boundaries",
    )
    _sort_strings(boundaries, "included", "$.project.boundaries")
    _sort_strings(boundaries, "excluded", "$.project.boundaries")

    sources = _list(_field(result, "sources", "$"), "$.sources")
    sources.sort(
        key=lambda item: _string_field(
            _mapping(item, "$.sources[]"),
            "id",
            "$.sources[]",
        )
    )

    records = _list(_field(result, "records", "$"), "$.records")
    _sort_records(records)

    compilations = _list(_field(result, "compilations", "$"), "$.compilations")
    compilations.sort(
        key=lambda item: _integer_field(
            _mapping(item, "$.compilations[]"),
            "result_revision",
            "$.compilations[]",
        )
    )

    return result


def canonicalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-copied canonical record."""

    _validate_json_value(record)
    result = copy.deepcopy(_mapping(record, "$"))
    _sort_record(result, "$")
    return result


def is_canonical_memory(memory: dict[str, Any]) -> bool:
    """Return whether every set-like memory array is canonically ordered."""

    return memory == canonicalize_memory(memory)
