"""Record draft normalization and deterministic identity."""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from .io import record_hash


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


def build_record(
    draft: dict[str, Any],
    *,
    run_id: str,
    project_scope: list[str],
    now: str,
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

    evidence = copy.deepcopy(draft.get("evidence", []))
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                item.setdefault("observed_at", now)

    record: dict[str, Any] = {
        "id": record_id(key),
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
        "created_at": now,
        "updated_at": now,
        "generated_by": run_id,
        "content_hash": "",
    }
    if "extensions" in draft:
        record["extensions"] = copy.deepcopy(draft["extensions"])
    record["content_hash"] = record_hash(record)
    return record


def record_semantics(record: dict[str, Any], *, include_key: bool = True) -> dict[str, Any]:
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
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                item.pop("observed_at", None)
    return semantic
