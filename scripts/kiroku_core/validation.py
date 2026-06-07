"""Structural and semantic memory validation."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
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


def _git(
    repository_root: Path,
    *args: str,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repository_root), *args],
        capture_output=True,
        check=False,
    )


def validate_repository_sources(
    memory: dict[str, Any],
    repository_root: Path,
) -> ValidationResult:
    result = ValidationResult()
    repository_root = repository_root.resolve()

    try:
        top_level = _git(repository_root, "rev-parse", "--show-toplevel")
    except OSError as exc:
        result.errors.append(f"cannot execute git: {exc}")
        return result

    if top_level.returncode != 0:
        detail = top_level.stderr.decode("utf-8", errors="replace").strip()
        result.errors.append(
            f"repository verification requires a Git worktree at "
            f"{repository_root}: {detail or 'not a Git repository'}"
        )
        return result

    git_root = Path(
        top_level.stdout.decode("utf-8", errors="strict").strip()
    ).resolve()

    for source in memory["sources"]:
        if source["kind"] != "repository_file":
            continue

        source_id = source["id"]
        revision = source.get("revision")
        if not revision:
            result.errors.append(
                f"{source_id}: repository source requires revision for Git verification"
            )
            continue

        content_hash = source.get("content_hash")
        if source["integrity"] != "verified" or not content_hash:
            result.errors.append(
                f"{source_id}: repository source requires verified content_hash "
                "for Git verification"
            )
            continue

        uri = source["uri"]
        path = PurePosixPath(uri)
        if path.is_absolute() or ".." in path.parts:
            result.errors.append(
                f"{source_id}: repository source URI must be repository-relative: {uri}"
            )
            continue

        commit = _git(git_root, "cat-file", "-e", f"{revision}^{{commit}}")
        if commit.returncode != 0:
            result.errors.append(
                f"{source_id}: Git revision does not resolve to a commit: {revision}"
            )
            continue

        blob = _git(git_root, "cat-file", "blob", f"{revision}:{uri}")
        if blob.returncode != 0:
            result.errors.append(
                f"{source_id}: repository file not found at "
                f"{revision}:{uri}"
            )
            continue

        actual_hash = "sha256:" + hashlib.sha256(blob.stdout).hexdigest()
        if actual_hash != content_hash:
            result.errors.append(
                f"{source_id}: repository content_hash mismatch at "
                f"{revision}:{uri}; expected {content_hash}, got {actual_hash}"
            )

    return result


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
    runs_by_id = {run["id"]: run for run in runs}
    record_ids = {record["id"] for record in records}
    records_by_id = {record["id"]: record for record in records}

    for duplicate in sorted(_duplicates([record["key"] for record in records])):
        result.errors.append(f"duplicate record key: {duplicate}")

    superseded_by: dict[str, list[str]] = {}
    supersedes_edges: dict[str, list[str]] = {}
    for record in records:
        for relation in record["relations"]:
            if relation["type"] != "supersedes":
                continue
            target_id = relation["target_id"]
            superseded_by.setdefault(target_id, []).append(record["id"])
            supersedes_edges.setdefault(record["id"], []).append(target_id)

    for target_id, replacement_ids in superseded_by.items():
        target = records_by_id.get(target_id)
        if target is not None and target["status"] != "superseded":
            result.errors.append(
                f"{target_id}: supersedes relation requires superseded status"
            )
        if len(replacement_ids) > 1:
            result.errors.append(
                f"{target_id}: record has multiple direct replacements: "
                f"{', '.join(sorted(replacement_ids))}"
            )

    for replacement_id, target_ids in supersedes_edges.items():
        if len(target_ids) > 1:
            result.errors.append(
                f"{replacement_id}: record supersedes multiple direct predecessors: "
                f"{', '.join(sorted(target_ids))}"
            )

    visited: set[str] = set()
    visiting: set[str] = set()

    def visit_supersession(record_id: str) -> None:
        if record_id in visiting:
            result.errors.append(f"supersession cycle detected at {record_id}")
            return
        if record_id in visited:
            return
        visiting.add(record_id)
        for target_id in supersedes_edges.get(record_id, []):
            if target_id in record_ids:
                visit_supersession(target_id)
        visiting.remove(record_id)
        visited.add(record_id)

    for record_id in sorted(record_ids):
        visit_supersession(record_id)

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
            generated_by = runs_by_id.get(record["generated_by"])
            if (
                generated_by is not None
                and evidence["source_id"] not in generated_by["inputs"]
            ):
                result.errors.append(
                    f"{record_id}: evidence source {evidence['source_id']} "
                    f"is not an input of run {record['generated_by']}"
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
            replacements = superseded_by.get(record_id, [])
            if not replacements:
                result.errors.append(
                    f"{record_id}: superseded record requires one direct replacement"
                )

        if check_hashes and record["content_hash"] != record_hash(record):
            result.errors.append(f"{record_id}: content_hash mismatch")

    return result
