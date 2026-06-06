"""Compact agent-oriented memory projection."""

from __future__ import annotations

from typing import Any

from .io import memory_hash


TYPE_PRIORITY = {
    "decision": 0,
    "constraint": 1,
    "preference": 2,
    "task": 3,
    "risk": 4,
    "question": 5,
    "assumption": 6,
    "fact": 7,
    "implementation_detail": 8,
    "roadmap_item": 9,
    "conflict": 10,
    "idea": 11,
    "rejected_idea": 12,
    "event": 13,
}

STATUS_PRIORITY = {
    "active": 0,
    "proposed": 1,
    "resolved": 2,
    "completed": 3,
    "superseded": 4,
    "obsolete": 5,
    "cancelled": 6,
}


def build_bootstrap(
    memory: dict[str, Any],
    *,
    scope: str | None = None,
    max_records: int = 40,
) -> dict[str, Any]:
    records = memory["records"]
    if scope:
        records = [record for record in records if scope in record["scope"]]

    records = sorted(
        records,
        key=lambda record: (
            STATUS_PRIORITY.get(record["status"], 99),
            TYPE_PRIORITY.get(record["type"], 99),
            record["title"].lower(),
        ),
    )[:max_records]

    source_ids = {
        evidence["source_id"]
        for record in records
        for evidence in record["evidence"]
    }
    sources = [
        {
            "id": source["id"],
            "kind": source["kind"],
            "title": source["title"],
            "uri": source["uri"],
            "revision": source.get("revision"),
        }
        for source in memory["sources"]
        if source["id"] in source_ids
    ]

    compact_records = []
    for record in records:
        compact_records.append(
            {
                "id": record["id"],
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
        )

    return {
        "schema_version": memory["schema_version"],
        "generated_from": memory_hash(memory),
        "scope_filter": scope,
        "project": {
            "id": memory["project"]["id"],
            "name": memory["project"]["name"],
            "domain": memory["project"]["domain"],
            "status": memory["project"]["status"],
            "goal": memory["project"]["goal"],
            "scope": memory["project"]["scope"],
        },
        "records": compact_records,
        "sources": sources,
    }
