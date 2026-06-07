"""Structural and semantic memory validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import record_hash
from .schema import load_schema, validate_schema


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_memory(
    memory: dict[str, Any],
    schema_path: Path,
    *,
    check_hashes: bool = True,
) -> ValidationResult:
    result = ValidationResult()
    schema = load_schema(schema_path)
    result.errors.extend(validate_schema(memory, schema))
    if result.errors:
        return result

    sources = memory["sources"]
    runs = memory["runs"]
    records = memory["records"]

    all_ids = [
        memory["memory_id"],
        memory["project"]["id"],
        *[source["id"] for source in sources],
        *[run["id"] for run in runs],
        *[record["id"] for record in records],
    ]
    for duplicate in sorted(_duplicates(all_ids)):
        result.errors.append(f"duplicate ID: {duplicate}")

    source_ids = {source["id"] for source in sources}
    run_ids = {run["id"] for run in runs}
    record_ids = {record["id"] for record in records}

    project = memory["project"]
    if _timestamp(project["updated_at"]) < _timestamp(project["created_at"]):
        result.errors.append("project.updated_at precedes project.created_at")

    for source in sources:
        if source["integrity"] == "verified" and not source.get("content_hash"):
            result.errors.append(
                f"{source['id']}: verified source requires content_hash"
            )
        if source["integrity"] == "unavailable" and source.get("content_hash"):
            result.warnings.append(
                f"{source['id']}: unavailable integrity has a content_hash"
            )

    running_runs = [run for run in runs if run["status"] == "running"]
    if len(running_runs) > 1:
        result.errors.append("multiple running runs are not allowed")

    for run in runs:
        missing = sorted(set(run["inputs"]) - source_ids)
        for source_id in missing:
            result.errors.append(f"{run['id']}: unknown input source {source_id}")
        if run["status"] == "running":
            if run["completed_at"] is not None:
                result.errors.append(
                    f"{run['id']}: running run cannot have completed_at"
                )
            if run["summary"] is not None:
                result.errors.append(f"{run['id']}: running run cannot have summary")
        else:
            if run["completed_at"] is None:
                result.errors.append(
                    f"{run['id']}: completed run requires completed_at"
                )
            if run["summary"] is None:
                result.errors.append(f"{run['id']}: completed run requires summary")
            if (
                run["completed_at"] is not None
                and _timestamp(run["completed_at"]) < _timestamp(run["started_at"])
            ):
                result.errors.append(
                    f"{run['id']}: completed_at precedes started_at"
                )

    for record in records:
        record_id = record["id"]
        if record["generated_by"] not in run_ids:
            result.errors.append(
                f"{record_id}: unknown generated_by run {record['generated_by']}"
            )
        if _timestamp(record["updated_at"]) < _timestamp(record["created_at"]):
            result.errors.append(f"{record_id}: updated_at precedes created_at")

        for evidence in record["evidence"]:
            if evidence["source_id"] not in source_ids:
                result.errors.append(
                    f"{record_id}: unknown evidence source {evidence['source_id']}"
                )
            locator = evidence["locator"]
            if (
                locator["kind"] == "lines"
                and "start_line" in locator
                and "end_line" in locator
                and locator["end_line"] < locator["start_line"]
            ):
                result.errors.append(
                    f"{record_id}: evidence end_line precedes start_line"
                )

        for relation in record["relations"]:
            target_id = relation["target_id"]
            if target_id not in record_ids:
                result.errors.append(
                    f"{record_id}: unknown relation target {target_id}"
                )
            if target_id == record_id:
                result.errors.append(f"{record_id}: relation cannot target itself")

        blocked_by = record["payload"].get("blocked_by", [])
        for target_id in blocked_by:
            if target_id not in record_ids:
                result.errors.append(
                    f"{record_id}: unknown blocked_by record {target_id}"
                )

        if record["type"] == "conflict":
            for claim in record["payload"]["claims"]:
                target_id = claim.get("record_id")
                if target_id and target_id not in record_ids:
                    result.errors.append(
                        f"{record_id}: unknown conflict claim record {target_id}"
                    )

        evidence = record["evidence"]
        direct_support = any(
            item["relation"] == "supports"
            and item["method"] in {
                "user_statement",
                "direct_observation",
                "test_result",
            }
            for item in evidence
        )
        refuting = any(item["relation"] == "refutes" for item in evidence)
        verification = record["verification_status"]

        if verification == "verified" and not direct_support:
            result.errors.append(
                f"{record_id}: verified record requires direct supporting evidence"
            )
        if verification == "partially_verified" and not evidence:
            result.errors.append(
                f"{record_id}: partially verified record requires evidence"
            )
        if verification == "contradicted" and not refuting:
            result.errors.append(
                f"{record_id}: contradicted record requires refuting evidence"
            )
        if record["confidence"] == "confirmed" and verification != "verified":
            result.errors.append(
                f"{record_id}: confirmed confidence requires verified status"
            )
        if (
            record["type"] == "task"
            and record["status"] == "completed"
            and not direct_support
        ):
            result.errors.append(
                f"{record_id}: completed task requires direct completion evidence"
            )
        if (
            record["type"] == "conflict"
            and record["status"] == "resolved"
            and not record["payload"].get("resolution")
        ):
            result.errors.append(
                f"{record_id}: resolved conflict requires payload.resolution"
            )
        if verification == "unverified" and direct_support:
            result.warnings.append(
                f"{record_id}: direct evidence exists but record is unverified"
            )

        if record["status"] == "superseded":
            incoming = any(
                relation["type"] == "supersedes"
                and relation["target_id"] == record_id
                for other in records
                for relation in other["relations"]
            )
            if not incoming:
                result.warnings.append(
                    f"{record_id}: superseded record has no incoming supersedes relation"
                )

        if check_hashes and record["content_hash"] != record_hash(record):
            result.errors.append(f"{record_id}: content_hash mismatch")

    return result
