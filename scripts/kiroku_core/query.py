"""Shared record query and indexing primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


VALID_RECORD_TYPES = (
    "fact",
    "decision",
    "assumption",
    "idea",
    "rejected_idea",
    "task",
    "question",
    "risk",
    "preference",
    "constraint",
    "implementation_detail",
    "roadmap_item",
    "conflict",
    "event",
)

VALID_RECORD_STATUSES = (
    "proposed",
    "active",
    "resolved",
    "superseded",
    "obsolete",
    "completed",
    "cancelled",
)

VALID_CONFIDENCE_LEVELS = (
    "confirmed",
    "high",
    "medium",
    "low",
    "unknown",
)

VALID_VERIFICATION_STATUSES = (
    "verified",
    "partially_verified",
    "unverified",
    "contradicted",
)

VALID_RELATION_TYPES = (
    "depends_on",
    "blocks",
    "supersedes",
    "contradicts",
    "implements",
    "mitigates",
    "answers",
    "derived_from",
    "related_to",
)

QUERY_SORT_FIELDS = (
    "title",
    "type",
    "status",
    "created_at",
    "updated_at",
)

QUERY_SORT_DIRECTIONS = ("asc", "desc")
QUERY_FORMATS = ("compact", "full", "ids")


@dataclass(frozen=True)
class RecordQuery:
    """Transport-independent record query."""

    key: str | None = None
    record_type: str | None = None
    status: str | None = None
    scope: str | None = None
    tag: str | None = None
    confidence: str | None = None
    verification_status: str | None = None
    relation_target: str | None = None
    relation_type: str | None = None
    search: str | None = None
    sort: str = "title"
    sort_direction: str = "asc"


@dataclass
class MemoryIndex:
    """Lookup tables derived from a validated canonical memory."""

    records_by_id: dict[str, dict[str, Any]]
    records_by_key: dict[str, dict[str, Any]]
    sources_by_id: dict[str, dict[str, Any]]
    runs_by_id: dict[str, dict[str, Any]]
    incoming_relations: dict[str, list[dict[str, Any]]]
    record_ids_by_source: dict[str, list[str]]
    record_ids_by_run: dict[str, list[str]]


def validate_record_query(query: RecordQuery) -> None:
    checks = (
        (query.record_type, VALID_RECORD_TYPES, "record type"),
        (query.status, VALID_RECORD_STATUSES, "record status"),
        (query.confidence, VALID_CONFIDENCE_LEVELS, "confidence"),
        (
            query.verification_status,
            VALID_VERIFICATION_STATUSES,
            "verification status",
        ),
        (query.relation_type, VALID_RELATION_TYPES, "relation type"),
        (query.sort, QUERY_SORT_FIELDS, "sort field"),
        (query.sort_direction, QUERY_SORT_DIRECTIONS, "sort direction"),
    )
    for value, allowed, label in checks:
        if value is not None and value not in allowed:
            raise ValueError(f"unknown {label}: {value}")


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "key": record["key"],
        "type": record["type"],
        "status": record["status"],
        "title": record["title"],
        "summary": record["summary"],
        "scope": record["scope"],
        "confidence": record["confidence"],
        "verification_status": record["verification_status"],
        "payload": record["payload"],
        "evidence_source_ids": sorted(
            {item["source_id"] for item in record["evidence"]}
        ),
        "relations": record["relations"],
    }


def format_records(
    records: list[dict[str, Any]],
    output_format: str,
) -> list[Any]:
    if output_format not in QUERY_FORMATS:
        raise ValueError(f"unknown output format: {output_format}")
    if output_format == "compact":
        return [compact_record(record) for record in records]
    if output_format == "full":
        return records
    return [record["id"] for record in records]


def query_records(
    memory: dict[str, Any],
    query: RecordQuery,
) -> list[dict[str, Any]]:
    validate_record_query(query)
    records = list(memory["records"])

    if query.key is not None:
        records = [record for record in records if record["key"] == query.key]
    if query.record_type is not None:
        records = [
            record for record in records if record["type"] == query.record_type
        ]
    if query.status is not None:
        records = [
            record for record in records if record["status"] == query.status
        ]
    if query.scope is not None:
        records = [
            record for record in records if query.scope in record["scope"]
        ]
    if query.tag is not None:
        records = [record for record in records if query.tag in record["tags"]]
    if query.confidence is not None:
        records = [
            record
            for record in records
            if record["confidence"] == query.confidence
        ]
    if query.verification_status is not None:
        records = [
            record
            for record in records
            if record["verification_status"] == query.verification_status
        ]

    if query.relation_target is not None or query.relation_type is not None:
        records = [
            record
            for record in records
            if any(
                (
                    query.relation_target is None
                    or relation["target_id"] == query.relation_target
                )
                and (
                    query.relation_type is None
                    or relation["type"] == query.relation_type
                )
                for relation in record["relations"]
            )
        ]

    if query.search is not None:
        term = query.search.strip().casefold()
        if term:
            records = [
                record for record in records if term in _search_text(record)
            ]

    return sorted(
        records,
        key=_sort_key(query.sort),
        reverse=(query.sort_direction == "desc"),
    )


def build_memory_index(memory: dict[str, Any]) -> MemoryIndex:
    records_by_id = {record["id"]: record for record in memory["records"]}
    records_by_key = {record["key"]: record for record in memory["records"]}
    sources_by_id = {source["id"]: source for source in memory["sources"]}
    runs_by_id = {run["id"]: run for run in memory["runs"]}
    incoming_relations = {record_id: [] for record_id in records_by_id}
    record_ids_by_source = {source_id: [] for source_id in sources_by_id}
    record_ids_by_run = {run_id: [] for run_id in runs_by_id}

    for record in memory["records"]:
        for relation in record["relations"]:
            incoming_relations.setdefault(relation["target_id"], []).append(
                {
                    "source_id": record["id"],
                    "type": relation["type"],
                    **(
                        {"note": relation["note"]}
                        if "note" in relation
                        else {}
                    ),
                }
            )
        for source_id in sorted(
            {evidence["source_id"] for evidence in record["evidence"]}
        ):
            record_ids_by_source.setdefault(source_id, []).append(record["id"])
        record_ids_by_run.setdefault(record["generated_by"], []).append(
            record["id"]
        )

    return MemoryIndex(
        records_by_id=records_by_id,
        records_by_key=records_by_key,
        sources_by_id=sources_by_id,
        runs_by_id=runs_by_id,
        incoming_relations=incoming_relations,
        record_ids_by_source=record_ids_by_source,
        record_ids_by_run=record_ids_by_run,
    )


def _search_text(record: dict[str, Any]) -> str:
    values = [
        record["key"],
        record["title"],
        record["summary"],
        *record["scope"],
        *record["tags"],
        json.dumps(record["payload"], ensure_ascii=False, sort_keys=True),
    ]
    return "\n".join(values).casefold()


def _sort_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sort_key(field: str):
    if field == "title":
        return lambda record: record["title"].casefold()
    if field == "type":
        return lambda record: record["type"]
    if field == "status":
        return lambda record: record["status"]
    if field == "created_at":
        return lambda record: _sort_timestamp(record["created_at"])
    return lambda record: _sort_timestamp(record["updated_at"])
