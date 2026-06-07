"""Record draft normalization and deterministic identity."""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from .io import canonical_json, record_hash


DRAFT_REQUIRED = {
    "key",
    "type",
    "title",
    "summary",
    "confidence",
    "verification_status",
    "payload",
}
DRAFT_OPTIONAL = {
    "status",
    "scope",
    "tags",
    "evidence",
    "relations",
    "extensions",
}
DRAFT_ALLOWED = DRAFT_REQUIRED | DRAFT_OPTIONAL


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:64] or "record"


def record_id(key: str) -> str:
    suffix = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"rec_{_slug(key)}_{suffix}"


def _evidence_identity(evidence: dict[str, Any]) -> str:
    semantic = copy.deepcopy(evidence)
    semantic.pop("observed_at", None)
    return canonical_json(semantic)


def _normalize_evidence(
    evidence: Any,
    *,
    now: str,
    existing_record: dict[str, Any] | None,
) -> Any:
    normalized = copy.deepcopy(evidence)
    if not isinstance(normalized, list):
        return normalized

    previous: dict[str, list[str]] = {}
    if existing_record is not None:
        for item in existing_record.get("evidence", []):
            if isinstance(item, dict) and isinstance(item.get("observed_at"), str):
                previous.setdefault(_evidence_identity(item), []).append(
                    item["observed_at"]
                )

    for item in normalized:
        if not isinstance(item, dict) or "observed_at" in item:
            continue
        matches = previous.get(_evidence_identity(item), [])
        item["observed_at"] = matches.pop(0) if matches else now
    return normalized


def build_record(
    draft: dict[str, Any],
    *,
    run_id: str,
    project_scope: list[str],
    now: str,
    existing_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = sorted(DRAFT_REQUIRED - draft.keys())
    if missing:
        raise ValueError(f"record draft missing required field(s): {', '.join(missing)}")

    unknown = sorted(draft.keys() - DRAFT_ALLOWED)
    if unknown:
        raise ValueError(f"record draft has unknown field(s): {', '.join(unknown)}")

    key = draft["key"]
    if not isinstance(key, str) or re.fullmatch(
        r"[a-z0-9][a-z0-9_-]{0,79}",
        key,
    ) is None:
        raise ValueError(
            "record draft key must match ^[a-z0-9][a-z0-9_-]{0,79}$"
        )

    evidence = _normalize_evidence(
        draft.get("evidence", []),
        now=now,
        existing_record=existing_record,
    )

    record: dict[str, Any] = {
        "id": existing_record["id"] if existing_record else record_id(key),
        "key": key,
        "type": copy.deepcopy(draft["type"]),
        "status": copy.deepcopy(draft.get("status", "active")),
        "title": copy.deepcopy(draft["title"]),
        "summary": copy.deepcopy(draft["summary"]),
        "scope": copy.deepcopy(draft.get("scope", project_scope)),
        "tags": copy.deepcopy(draft.get("tags", [])),
        "confidence": copy.deepcopy(draft["confidence"]),
        "verification_status": copy.deepcopy(draft["verification_status"]),
        "evidence": evidence,
        "relations": copy.deepcopy(draft.get("relations", [])),
        "payload": copy.deepcopy(draft["payload"]),
        "created_at": existing_record["created_at"] if existing_record else now,
        "updated_at": now,
        "generated_by": run_id,
        "content_hash": "",
    }
    if "extensions" in draft:
        record["extensions"] = copy.deepcopy(draft["extensions"])
    record["content_hash"] = record_hash(record)
    return record


def record_semantics(
    record: dict[str, Any],
    *,
    include_key: bool = True,
    include_observed_at: bool = False,
) -> dict[str, Any]:
    semantic = copy.deepcopy(record)
    for field in (
        "id",
        "created_at",
        "updated_at",
        "generated_by",
        "content_hash",
    ):
        semantic.pop(field, None)
    if not include_key:
        semantic.pop("key", None)
    evidence = semantic.get("evidence")
    if not include_observed_at and isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                item.pop("observed_at", None)
    return semantic
