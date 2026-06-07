#!/usr/bin/env python3
"""KirokuForge command-line interface."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from kiroku_core.bootstrap import build_bootstrap
from kiroku_core.io import (
    load_json,
    record_hash,
    sha256_bytes,
    sha256_file,
    write_json_if_changed,
    write_text_if_changed,
)
from kiroku_core.query import (
    QUERY_FORMATS,
    QUERY_SORT_DIRECTIONS,
    QUERY_SORT_FIELDS,
    RecordQuery,
    format_records,
    query_records,
)
from kiroku_core.rendering import render_views
from kiroku_core.records import build_record, record_semantics
from kiroku_core.validation import ValidationResult, validate_memory
from kiroku_core.viewer import InvalidMemoryError, create_viewer_server


SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_DIR / "schemas" / "memory-v2.schema.json"
SOURCE_KINDS = (
    "conversation",
    "user_input",
    "repository_file",
    "document",
    "command_output",
    "url",
    "test_result",
    "agent_observation",
)
RUN_OPERATIONS = ("create", "update", "review", "import")
ACTOR_TYPES = ("agent", "user", "tool")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00",
        "Z",
    )


def _now_after(timestamp: str) -> str:
    current = datetime.now(timezone.utc)
    previous = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if current <= previous:
        current = previous + timedelta(microseconds=1)
    return current.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:80] or "project"


def _memory_path(directory: Path) -> Path:
    return directory / "memory.json"


def _load(directory: Path) -> dict[str, Any]:
    return load_json(_memory_path(directory))


def _source_id(kind: str, uri: str, revision: str | None) -> str:
    identity = f"{kind}\0{uri}\0{revision or ''}".encode("utf-8")
    suffix = hashlib.sha256(identity).hexdigest()[:12]
    return f"src_{_slug(Path(uri).name or kind)[:48]}_{suffix}"


def _run_id(operation: str, started_at: str) -> str:
    timestamp = re.sub(r"[^0-9a-z]+", "", started_at.lower())
    return f"run_{operation}_{timestamp}_{uuid.uuid4().hex[:8]}"


def _metadata(values: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"invalid metadata {value!r}; expected KEY=JSON")
        key, raw = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid metadata {value!r}; key is empty")
        if key in metadata:
            raise ValueError(f"duplicate metadata key {key!r}")
        try:
            metadata[key] = json.loads(raw)
        except json.JSONDecodeError:
            metadata[key] = raw
    return metadata


def _source_content(
    args: argparse.Namespace,
) -> tuple[str, str | None, dict[str, Any]]:
    metadata = _metadata(args.metadata)

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise ValueError(f"source file not found: {path}")
        uri = args.uri or Path(args.file).as_posix()
        metadata.setdefault("size_bytes", path.stat().st_size)
        return uri, sha256_file(path), metadata

    if args.text is not None:
        if not args.uri:
            raise ValueError("--uri is required with --text")
        content = args.text.encode("utf-8")
        metadata.setdefault("size_bytes", len(content))
        metadata.setdefault("encoding", "utf-8")
        return args.uri, sha256_bytes(content), metadata

    if args.stdin:
        if not args.uri:
            raise ValueError("--uri is required with --stdin")
        content = sys.stdin.buffer.read()
        metadata.setdefault("size_bytes", len(content))
        return args.uri, sha256_bytes(content), metadata

    if not args.uri:
        raise ValueError("--uri is required when no content input is provided")
    return args.uri, None, metadata


def _source_status_candidates(
    args: argparse.Namespace,
) -> list[tuple[str, str, Path]]:
    candidates: list[tuple[str, str, Path]] = []

    if args.file:
        for raw_path in args.file:
            candidates.append(
                (
                    Path(raw_path).as_posix(),
                    raw_path,
                    Path(raw_path),
                )
            )
    else:
        for mapping in args.map:
            if "=" not in mapping:
                raise ValueError(
                    f"invalid source mapping {mapping!r}; expected URI=PATH"
                )
            uri, raw_path = mapping.split("=", 1)
            uri = uri.strip()
            raw_path = raw_path.strip()
            if not uri or not raw_path:
                raise ValueError(
                    f"invalid source mapping {mapping!r}; expected URI=PATH"
                )
            candidates.append((uri, raw_path, Path(raw_path)))

    seen_uris: set[str] = set()
    duplicate_uris: set[str] = set()
    for uri, _, _ in candidates:
        if uri in seen_uris:
            duplicate_uris.add(uri)
        seen_uris.add(uri)
    if duplicate_uris:
        raise ValueError(
            f"duplicate source URI candidate(s): "
            f"{', '.join(sorted(duplicate_uris))}"
        )

    resolved: list[tuple[str, str, Path]] = []
    for uri, raw_path, path in candidates:
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise ValueError(f"source file not found: {path}")
        resolved.append((uri, raw_path, path))
    return resolved


def command_source_status(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    result = validate_memory(memory, SCHEMA_PATH)
    if not result.ok:
        _print_result(result)
        return 2

    candidates = _source_status_candidates(args)
    latest_by_uri: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, source in enumerate(memory["sources"]):
        current = latest_by_uri.get(source["uri"])
        source_key = (
            datetime.fromisoformat(source["captured_at"].replace("Z", "+00:00")),
            index,
        )
        if current is None:
            latest_by_uri[source["uri"]] = (index, source)
            continue
        current_index, current_source = current
        current_key = (
            datetime.fromisoformat(
                current_source["captured_at"].replace("Z", "+00:00")
            ),
            current_index,
        )
        if source_key > current_key:
            latest_by_uri[source["uri"]] = (index, source)

    statuses: list[dict[str, Any]] = []
    counts = {"unchanged": 0, "changed": 0, "new": 0}
    for uri, raw_path, path in candidates:
        current_hash = sha256_file(path)
        stored_entry = latest_by_uri.get(uri)
        stored = stored_entry[1] if stored_entry is not None else None
        if stored is None:
            status = "new"
        elif stored.get("content_hash") == current_hash:
            status = "unchanged"
        else:
            status = "changed"
        counts[status] += 1
        statuses.append(
            {
                "uri": uri,
                "path": raw_path,
                "status": status,
                "current_hash": current_hash,
                "source_id": stored["id"] if stored else None,
                "stored_hash": stored.get("content_hash") if stored else None,
                "revision": stored.get("revision") if stored else None,
            }
        )

    statuses.sort(key=lambda item: item["uri"])
    actionable = [
        item for item in statuses if item["status"] in {"changed", "new"}
    ]
    visible = actionable if args.changed_only else statuses
    output = {
        "summary": {
            **counts,
            "total": len(statuses),
            "actionable": len(actionable),
            "returned": len(visible),
        },
        "sources": visible,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def _record_draft(args: argparse.Namespace) -> dict[str, Any]:
    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.is_file():
            raise ValueError(f"record draft file not found: {path}")
        return load_json(path)

    try:
        draft = json.loads(sys.stdin.buffer.read())
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid record draft JSON from stdin: {exc}") from exc
    if not isinstance(draft, dict):
        raise ValueError("record draft from stdin must be a JSON object")
    return draft


def _print_result(result: ValidationResult) -> None:
    for error in result.errors:
        print(f"[ERROR] {error}")
    for warning in result.warnings:
        print(f"[WARN]  {warning}")
    if result.ok:
        print(
            f"Validation OK"
            + (f" with {len(result.warnings)} warning(s)" if result.warnings else "")
        )
    else:
        print(
            f"Validation FAILED: {len(result.errors)} error(s), "
            f"{len(result.warnings)} warning(s)"
        )


def command_init(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    path = _memory_path(directory)
    if path.exists() and not args.force:
        print(f"[ERROR] {path} already exists; use --force to replace it")
        return 2

    now = _now()
    slug = _slug(args.name)
    suffix = uuid.uuid4().hex[:8]
    memory = {
        "schema_version": "2.0.0",
        "memory_id": f"mem_{slug}_{suffix}",
        "project": {
            "id": f"project_{slug}",
            "name": args.name,
            "description": args.description or args.goal,
            "domain": args.domain,
            "status": "active",
            "goal": args.goal,
            "scope": args.scope or [slug],
            "created_at": now,
            "updated_at": now,
        },
        "sources": [],
        "runs": [
            {
                "id": f"run_initialize_{suffix}",
                "operation": "create",
                "status": "completed",
                "actor": {
                    "type": "tool",
                    "name": "kiroku-forge",
                    "version": "2.0.0",
                },
                "inputs": [],
                "started_at": now,
                "completed_at": now,
                "summary": "Initialized canonical Kiroku memory.",
                "warnings": [],
            }
        ],
        "records": [],
    }
    write_json_if_changed(path, memory)
    print(f"[OK] Created {path}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    try:
        memory = _load(directory)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 2
    result = validate_memory(memory, SCHEMA_PATH)
    _print_result(result)
    return 0 if result.ok else 2


def command_start_run(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    baseline = validate_memory(memory, SCHEMA_PATH)
    if not baseline.ok:
        print("[ERROR] canonical memory is invalid; run was not started")
        _print_result(baseline)
        return 2

    running = next(
        (run for run in memory["runs"] if run["status"] == "running"),
        None,
    )
    if running:
        print(
            f"[ERROR] run {running['id']} is already running; "
            "finish it before starting another"
        )
        return 2

    inputs = list(dict.fromkeys(args.input))
    source_ids = {source["id"] for source in memory["sources"]}
    missing = sorted(set(inputs) - source_ids)
    if missing:
        print(f"[ERROR] unknown input source(s): {', '.join(missing)}")
        return 2

    started_at = _now()
    run_id = _run_id(args.operation, started_at)
    candidate = copy.deepcopy(memory)
    candidate["runs"].append(
        {
            "id": run_id,
            "operation": args.operation,
            "status": "running",
            "actor": {
                "type": args.actor_type,
                "name": args.actor_name,
                "version": args.actor_version,
            },
            "inputs": inputs,
            "started_at": started_at,
            "completed_at": None,
            "summary": None,
            "warnings": [],
        }
    )
    result = validate_memory(candidate, SCHEMA_PATH)
    if not result.ok:
        print("[ERROR] run would make canonical memory invalid; no changes written")
        _print_result(result)
        return 2

    write_json_if_changed(_memory_path(directory), candidate)
    print(f"[OK] Started run {run_id}")
    print(f"     Operation: {args.operation}")
    print(f"     Inputs: {len(inputs)}")
    return 0


def command_finish_run(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    baseline = validate_memory(memory, SCHEMA_PATH)
    if not baseline.ok:
        print("[ERROR] canonical memory is invalid; run was not finished")
        _print_result(baseline)
        return 2

    run = next((item for item in memory["runs"] if item["id"] == args.run_id), None)
    if run is None:
        print(f"[ERROR] unknown run: {args.run_id}")
        return 2

    warnings = list(dict.fromkeys(args.warning))
    if run["status"] == "completed":
        if run["summary"] == args.summary and run["warnings"] == warnings:
            print(f"[SAME] Run already completed: {args.run_id}")
            return 0
        print(
            f"[ERROR] run {args.run_id} is already completed; "
            "completed runs are immutable"
        )
        return 2

    candidate = copy.deepcopy(memory)
    target = next(item for item in candidate["runs"] if item["id"] == args.run_id)
    target["status"] = "completed"
    target["completed_at"] = _now()
    target["summary"] = args.summary
    target["warnings"] = warnings

    result = validate_memory(candidate, SCHEMA_PATH)
    if not result.ok:
        print("[ERROR] completion would make canonical memory invalid; no changes written")
        _print_result(result)
        return 2

    write_json_if_changed(_memory_path(directory), candidate)
    print(f"[OK] Finished run {args.run_id}")
    print(f"     Warnings: {len(warnings)}")
    return 0


def command_add_source(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    baseline = validate_memory(memory, SCHEMA_PATH)
    if not baseline.ok:
        print("[ERROR] canonical memory is invalid; source was not added")
        _print_result(baseline)
        return 2

    uri, content_hash, metadata = _source_content(args)
    revision = args.revision or None
    identity = (args.kind, uri, revision)

    for source in memory["sources"]:
        current_identity = (
            source["kind"],
            source["uri"],
            source.get("revision"),
        )
        if current_identity != identity:
            continue
        if source.get("content_hash") == content_hash:
            print(f"[SAME] Source already registered: {source['id']}")
            return 0
        print(
            "[ERROR] source identity already exists with different content: "
            f"{source['id']}; provide a distinct --revision or --uri"
        )
        return 2

    source_id = _source_id(args.kind, uri, revision)
    if any(source["id"] == source_id for source in memory["sources"]):
        print(f"[ERROR] generated source ID collision: {source_id}")
        return 2

    candidate = copy.deepcopy(memory)
    candidate["sources"].append(
        {
            "id": source_id,
            "kind": args.kind,
            "title": args.title,
            "uri": uri,
            "revision": revision,
            "integrity": "verified" if content_hash else "unavailable",
            "content_hash": content_hash,
            "captured_at": _now(),
            "metadata": metadata,
        }
    )
    result = validate_memory(candidate, SCHEMA_PATH)
    if not result.ok:
        print("[ERROR] source would make canonical memory invalid; no changes written")
        _print_result(result)
        return 2

    write_json_if_changed(_memory_path(directory), candidate)
    print(f"[OK] Added source {source_id}")
    print(f"     URI: {uri}")
    print(f"     Integrity: {'verified' if content_hash else 'unavailable'}")
    return 0


def command_add_record(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    baseline = validate_memory(memory, SCHEMA_PATH)
    if not baseline.ok:
        print("[ERROR] canonical memory is invalid; record was not added")
        _print_result(baseline)
        return 2

    run = next((item for item in memory["runs"] if item["id"] == args.run_id), None)
    if run is None:
        print(f"[ERROR] unknown run: {args.run_id}")
        return 2
    if run["status"] != "running":
        print(f"[ERROR] run {args.run_id} is not running")
        return 2

    draft = _record_draft(args)
    record = build_record(
        draft,
        run_id=args.run_id,
        project_scope=memory["project"]["scope"],
        now=_now(),
    )

    existing = next(
        (item for item in memory["records"] if item["key"] == record["key"]),
        None,
    )
    if existing:
        if record_semantics(existing) == record_semantics(record):
            print(f"[SAME] Record already registered: {existing['id']}")
            return 0
        print(
            f"[ERROR] record key {record['key']!r} already exists with "
            f"different content: {existing['id']}; use update-record"
        )
        return 2

    duplicate = next(
        (
            item
            for item in memory["records"]
            if record_semantics(item, include_key=False)
            == record_semantics(record, include_key=False)
        ),
        None,
    )
    if duplicate:
        print(f"[SAME] Equivalent record already registered: {duplicate['id']}")
        return 0

    if any(item["id"] == record["id"] for item in memory["records"]):
        print(f"[ERROR] generated record ID collision: {record['id']}")
        return 2

    candidate = copy.deepcopy(memory)
    candidate["records"].append(record)
    result = validate_memory(candidate, SCHEMA_PATH)
    if not result.ok:
        print("[ERROR] record would make canonical memory invalid; no changes written")
        _print_result(result)
        return 2

    write_json_if_changed(_memory_path(directory), candidate)
    print(f"[OK] Added record {record['id']}")
    print(f"     Key: {record['key']}")
    print(f"     Type: {record['type']}")
    for warning in result.warnings:
        print(f"[WARN]  {warning}")
    return 0


def command_update_record(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    baseline = validate_memory(memory, SCHEMA_PATH)
    if not baseline.ok:
        print("[ERROR] canonical memory is invalid; record was not updated")
        _print_result(baseline)
        return 2

    run = next((item for item in memory["runs"] if item["id"] == args.run_id), None)
    if run is None:
        print(f"[ERROR] unknown run: {args.run_id}")
        return 2
    if run["status"] != "running":
        print(f"[ERROR] run {args.run_id} is not running")
        return 2

    existing = next(
        (item for item in memory["records"] if item["key"] == args.key),
        None,
    )
    if existing is None:
        print(f"[ERROR] unknown record key: {args.key}")
        return 2
    if existing["content_hash"] != args.expect_hash:
        print(
            f"[ERROR] record {args.key!r} changed since it was read; "
            f"expected {args.expect_hash}, current {existing['content_hash']}"
        )
        return 2

    draft = _record_draft(args)
    if draft.get("key") != args.key:
        print(
            f"[ERROR] record draft key must match --key {args.key!r}; "
            f"got {draft.get('key')!r}"
        )
        return 2
    if draft.get("type") != existing["type"]:
        print(
            f"[ERROR] record type is immutable for {args.key!r}; "
            f"expected {existing['type']!r}, got {draft.get('type')!r}"
        )
        return 2
    if existing["status"] == "superseded":
        print(f"[ERROR] superseded record {args.key!r} is immutable")
        return 2
    if draft.get("status") == "superseded":
        print("[ERROR] use supersede-record to mark a record as superseded")
        return 2

    updated = build_record(
        draft,
        run_id=args.run_id,
        project_scope=memory["project"]["scope"],
        now=_now_after(existing["updated_at"]),
        existing_record=existing,
    )
    if record_semantics(
        existing,
        include_observed_at=True,
    ) == record_semantics(
        updated,
        include_observed_at=True,
    ):
        print(f"[SAME] Record is unchanged: {existing['id']}")
        return 0

    duplicate = next(
        (
            item
            for item in memory["records"]
            if item["id"] != existing["id"]
            and record_semantics(item, include_key=False)
            == record_semantics(updated, include_key=False)
        ),
        None,
    )
    if duplicate:
        print(
            f"[ERROR] update would duplicate existing record {duplicate['id']}; "
            "no changes written"
        )
        return 2

    candidate = copy.deepcopy(memory)
    index = next(
        index
        for index, item in enumerate(candidate["records"])
        if item["id"] == existing["id"]
    )
    candidate["records"][index] = updated
    result = validate_memory(candidate, SCHEMA_PATH)
    if not result.ok:
        print("[ERROR] update would make canonical memory invalid; no changes written")
        _print_result(result)
        return 2

    write_json_if_changed(_memory_path(directory), candidate)
    print(f"[OK] Updated record {updated['id']}")
    print(f"     Previous hash: {existing['content_hash']}")
    print(f"     Current hash:  {updated['content_hash']}")
    for warning in result.warnings:
        print(f"[WARN]  {warning}")
    return 0


def command_supersede_record(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    baseline = validate_memory(memory, SCHEMA_PATH)
    if not baseline.ok:
        print("[ERROR] canonical memory is invalid; record was not superseded")
        _print_result(baseline)
        return 2

    run = next((item for item in memory["runs"] if item["id"] == args.run_id), None)
    if run is None:
        print(f"[ERROR] unknown run: {args.run_id}")
        return 2
    if run["status"] != "running":
        print(f"[ERROR] run {args.run_id} is not running")
        return 2

    existing = next(
        (item for item in memory["records"] if item["key"] == args.key),
        None,
    )
    if existing is None:
        print(f"[ERROR] unknown record key: {args.key}")
        return 2
    if existing["status"] == "superseded":
        replacement = next(
            (
                item
                for item in memory["records"]
                if any(
                    relation["type"] == "supersedes"
                    and relation["target_id"] == existing["id"]
                    for relation in item["relations"]
                )
            ),
            None,
        )
        suffix = f" by {replacement['key']!r}" if replacement else ""
        print(f"[ERROR] record {args.key!r} is already superseded{suffix}")
        return 2
    if existing["content_hash"] != args.expect_hash:
        print(
            f"[ERROR] record {args.key!r} changed since it was read; "
            f"expected {args.expect_hash}, current {existing['content_hash']}"
        )
        return 2

    draft = _record_draft(args)
    replacement_key = draft.get("key")
    if replacement_key == args.key:
        print("[ERROR] replacement record must use a different key")
        return 2
    if any(item["key"] == replacement_key for item in memory["records"]):
        print(f"[ERROR] replacement record key already exists: {replacement_key!r}")
        return 2
    if draft.get("status", "active") in {"superseded", "obsolete", "cancelled"}:
        print("[ERROR] replacement record must have a live lifecycle status")
        return 2
    if any(
        relation.get("type") == "supersedes"
        for relation in draft.get("relations", [])
        if isinstance(relation, dict)
    ):
        print("[ERROR] supersedes relation is managed by supersede-record")
        return 2

    changed_at = _now_after(existing["updated_at"])
    replacement = build_record(
        draft,
        run_id=args.run_id,
        project_scope=memory["project"]["scope"],
        now=changed_at,
    )
    replacement["relations"].append(
        {
            "type": "supersedes",
            "target_id": existing["id"],
        }
    )
    replacement["content_hash"] = record_hash(replacement)

    duplicate = next(
        (
            item
            for item in memory["records"]
            if record_semantics(item, include_key=False)
            == record_semantics(replacement, include_key=False)
        ),
        None,
    )
    if duplicate:
        print(
            f"[ERROR] replacement would duplicate existing record {duplicate['id']}; "
            "no changes written"
        )
        return 2
    if any(item["id"] == replacement["id"] for item in memory["records"]):
        print(f"[ERROR] generated record ID collision: {replacement['id']}")
        return 2

    predecessor = copy.deepcopy(existing)
    predecessor["status"] = "superseded"
    predecessor["updated_at"] = changed_at
    predecessor["generated_by"] = args.run_id
    predecessor["content_hash"] = record_hash(predecessor)

    candidate = copy.deepcopy(memory)
    predecessor_index = next(
        index
        for index, item in enumerate(candidate["records"])
        if item["id"] == existing["id"]
    )
    candidate["records"][predecessor_index] = predecessor
    candidate["records"].append(replacement)

    result = validate_memory(candidate, SCHEMA_PATH)
    if not result.ok:
        print(
            "[ERROR] supersession would make canonical memory invalid; "
            "no changes written"
        )
        _print_result(result)
        return 2

    write_json_if_changed(_memory_path(directory), candidate)
    print(f"[OK] Superseded record {existing['id']}")
    print(f"     Replacement: {replacement['id']}")
    print(f"     Previous hash: {existing['content_hash']}")
    print(f"     Historical hash: {predecessor['content_hash']}")
    for warning in result.warnings:
        print(f"[WARN]  {warning}")
    return 0


def _render(directory: Path, memory: dict[str, Any]) -> int:
    changed = 0
    view_dir = directory / "views"
    for filename, content in render_views(memory).items():
        if write_text_if_changed(view_dir / filename, content):
            changed += 1
    print(f"[OK] Rendered views ({changed} changed)")
    return changed


def command_render(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    result = validate_memory(memory, SCHEMA_PATH)
    if not result.ok:
        _print_result(result)
        return 2
    _render(directory, memory)
    return 0


def _bootstrap(
    directory: Path,
    memory: dict[str, Any],
    *,
    scope: str | None,
    max_records: int,
) -> bool:
    bootstrap = build_bootstrap(
        memory,
        scope=scope,
        max_records=max_records,
    )
    changed = write_json_if_changed(directory / "agent-bootstrap.json", bootstrap)
    print(f"[OK] Agent bootstrap ({'changed' if changed else 'unchanged'})")
    return changed


def command_bootstrap(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    result = validate_memory(memory, SCHEMA_PATH)
    if not result.ok:
        _print_result(result)
        return 2
    _bootstrap(
        directory,
        memory,
        scope=args.scope,
        max_records=args.max_records,
    )
    return 0


def command_query(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    result = validate_memory(memory, SCHEMA_PATH)
    if not result.ok:
        _print_result(result)
        return 2

    query = RecordQuery(
        key=args.key,
        record_type=args.type,
        status=args.status,
        scope=args.scope,
        tag=args.tag,
        confidence=args.confidence,
        verification_status=args.verification_status,
        relation_target=args.relation_target,
        relation_type=args.relation_type,
        search=args.search,
        sort=args.sort,
        sort_direction=args.sort_dir,
    )
    records = query_records(memory, query)

    if args.count:
        print(len(records))
        return 0

    output = format_records(records, args.format)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def command_serve(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    try:
        server = create_viewer_server(
            directory,
            SCHEMA_PATH,
            SKILL_DIR / "assets" / "viewer",
            port=args.port,
        )
    except InvalidMemoryError as exc:
        print("[ERROR] canonical memory is invalid; viewer was not started")
        for detail in exc.details:
            print(f"[ERROR] {detail}")
        return 2

    host, port = server.server_address
    print(f"[OK] Kiroku viewer serving {directory / 'memory.json'}")
    print(f"     http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] Kiroku viewer stopped")
    finally:
        server.server_close()
    return 0


def command_build(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
    running = next(
        (run for run in memory["runs"] if run["status"] == "running"),
        None,
    )
    if running:
        print(
            f"[ERROR] cannot build while run {running['id']} is running; "
            "finish the run first"
        )
        return 2

    for record in memory.get("records", []):
        record["content_hash"] = record_hash(record)

    result = validate_memory(memory, SCHEMA_PATH)
    _print_result(result)
    if not result.ok:
        return 2

    changed = write_json_if_changed(_memory_path(directory), memory)
    print(f"[OK] Canonical memory ({'changed' if changed else 'unchanged'})")
    if not args.no_render:
        _render(directory, memory)
    _bootstrap(
        directory,
        memory,
        scope=args.scope,
        max_records=args.max_records,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage KirokuForge memory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Initialize canonical memory")
    init.add_argument("--dir", default="./kiroku")
    init.add_argument("--name", required=True)
    init.add_argument("--domain", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--description")
    init.add_argument("--scope", action="append")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    validate = subparsers.add_parser("validate", help="Validate canonical memory")
    validate.add_argument("--dir", default="./kiroku")
    validate.set_defaults(func=command_validate)

    add_source = subparsers.add_parser(
        "add-source",
        help="Register a provenance source",
    )
    add_source.add_argument("--dir", default="./kiroku")
    add_source.add_argument("--kind", choices=SOURCE_KINDS, required=True)
    add_source.add_argument("--title", required=True)
    add_source.add_argument("--uri")
    add_source.add_argument("--revision")
    content = add_source.add_mutually_exclusive_group()
    content.add_argument("--file")
    content.add_argument("--text")
    content.add_argument("--stdin", action="store_true")
    add_source.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=JSON",
    )
    add_source.set_defaults(func=command_add_source)

    source_status = subparsers.add_parser(
        "source-status",
        help="Compare local source files with their latest stored hashes",
    )
    source_status.add_argument("--dir", default="./kiroku")
    source_input = source_status.add_mutually_exclusive_group(required=True)
    source_input.add_argument(
        "--file",
        action="append",
        help="Local file whose path is also its source URI; repeat as needed",
    )
    source_input.add_argument(
        "--map",
        action="append",
        metavar="URI=PATH",
        help="Map a stored source URI to a local file; repeat as needed",
    )
    source_status.add_argument(
        "--changed-only",
        action="store_true",
        help="Return only changed and new source candidates",
    )
    source_status.set_defaults(func=command_source_status)

    start_run = subparsers.add_parser(
        "start-run",
        help="Start an extraction or update run",
    )
    start_run.add_argument("--dir", default="./kiroku")
    start_run.add_argument("--operation", choices=RUN_OPERATIONS, required=True)
    start_run.add_argument("--input", action="append", default=[])
    start_run.add_argument("--actor-type", choices=ACTOR_TYPES, default="agent")
    start_run.add_argument("--actor-name", default="kiroku-forge-agent")
    start_run.add_argument("--actor-version")
    start_run.set_defaults(func=command_start_run)

    finish_run = subparsers.add_parser(
        "finish-run",
        help="Complete a running extraction or update run",
    )
    finish_run.add_argument("--dir", default="./kiroku")
    finish_run.add_argument("--run-id", required=True)
    finish_run.add_argument("--summary", required=True)
    finish_run.add_argument("--warning", action="append", default=[])
    finish_run.set_defaults(func=command_finish_run)

    add_record = subparsers.add_parser(
        "add-record",
        help="Add a validated record to a running run",
    )
    add_record.add_argument("--dir", default="./kiroku")
    add_record.add_argument("--run-id", required=True)
    draft_input = add_record.add_mutually_exclusive_group(required=True)
    draft_input.add_argument("--file")
    draft_input.add_argument("--stdin", action="store_true")
    add_record.set_defaults(func=command_add_record)

    update_record = subparsers.add_parser(
        "update-record",
        help="Replace the semantic content of an existing record",
    )
    update_record.add_argument("--dir", default="./kiroku")
    update_record.add_argument("--run-id", required=True)
    update_record.add_argument("--key", required=True)
    update_record.add_argument("--expect-hash", required=True)
    update_input = update_record.add_mutually_exclusive_group(required=True)
    update_input.add_argument("--file")
    update_input.add_argument("--stdin", action="store_true")
    update_record.set_defaults(func=command_update_record)

    supersede_record = subparsers.add_parser(
        "supersede-record",
        help="Atomically replace a record while preserving history",
    )
    supersede_record.add_argument("--dir", default="./kiroku")
    supersede_record.add_argument("--run-id", required=True)
    supersede_record.add_argument("--key", required=True)
    supersede_record.add_argument("--expect-hash", required=True)
    replacement_input = supersede_record.add_mutually_exclusive_group(required=True)
    replacement_input.add_argument("--file")
    replacement_input.add_argument("--stdin", action="store_true")
    supersede_record.set_defaults(func=command_supersede_record)

    render = subparsers.add_parser("render", help="Generate Markdown views")
    render.add_argument("--dir", default="./kiroku")
    render.set_defaults(func=command_render)

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="Generate compact agent context",
    )
    bootstrap.add_argument("--dir", default="./kiroku")
    bootstrap.add_argument("--scope")
    bootstrap.add_argument("--max-records", type=int, default=40)
    bootstrap.set_defaults(func=command_bootstrap)

    query = subparsers.add_parser(
        "query",
        help="Filter and retrieve records from canonical memory",
    )
    query.add_argument("--dir", default="./kiroku")
    query.add_argument("--key")
    query.add_argument("--type")
    query.add_argument("--status")
    query.add_argument("--scope")
    query.add_argument("--tag")
    query.add_argument("--confidence")
    query.add_argument("--verification-status")
    query.add_argument("--relation-target")
    query.add_argument("--relation-type")
    query.add_argument("--search")
    query.add_argument("--format", choices=QUERY_FORMATS, default="compact")
    query.add_argument("--sort", choices=QUERY_SORT_FIELDS, default="title")
    query.add_argument(
        "--sort-dir",
        choices=QUERY_SORT_DIRECTIONS,
        default="asc",
    )
    query.add_argument("--count", action="store_true")
    query.set_defaults(func=command_query)

    serve = subparsers.add_parser(
        "serve",
        help="Serve validated memory through a local read-only API",
    )
    serve.add_argument("--dir", default="./kiroku")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=command_serve)

    build = subparsers.add_parser(
        "build",
        help="Hash, validate, render, and generate bootstrap",
    )
    build.add_argument("--dir", default="./kiroku")
    build.add_argument("--scope")
    build.add_argument("--max-records", type=int, default=40)
    build.add_argument("--no-render", action="store_true")
    build.set_defaults(func=command_build)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
