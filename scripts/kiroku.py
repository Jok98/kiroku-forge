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
from datetime import datetime, timezone
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
from kiroku_core.rendering import render_views
from kiroku_core.validation import ValidationResult, validate_memory


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


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


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


def command_build(args: argparse.Namespace) -> int:
    directory = Path(args.dir).resolve()
    memory = _load(directory)
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
