#!/usr/bin/env python3
"""Build or query a portable, Markdown-derived Kiroku memory snapshot."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import deque
from contextlib import closing
from pathlib import Path

from check_hub import resolve_hub
from memory_store import MemoryIndexError, build_index, index_status, open_index
from memory_writer import load_payload, write_entry


CONTEXT_MIN_CHARS = 256
CONTEXT_MAX_CHARS = 1000000


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, json.dumps({"state": "error", "error": message}, ensure_ascii=False) + "\n")


def bounded_integer(minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("expected an integer") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"expected {minimum}..{maximum}")
        return number
    return parse


def parse_args() -> argparse.Namespace:
    parser = JsonArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    descriptions = {
        "checkpoint": "Publish one snapshot after completing the checkpoint's Markdown edits.",
        "build": "Compatibility alias for checkpoint; publish the prepared Markdown snapshot.",
        "status": "Explicitly audit snapshot integrity and correspondence with current Markdown.",
        "search": "Search indexed Markdown with literal words and OR matching.",
        "entries": "List structured Markdown records by type, status, and track.",
        "show": "Read a document or section by its returned node ID.",
        "related": "Navigate explicit graph edges in either direction.",
        "context": "Assemble a focused track context with visible budget omissions.",
        "add": "Save a structured Markdown entry; publish the index at checkpoint completion.",
        "update": "Save a patch by stable ID; publish the index at checkpoint completion.",
    }
    for name, description in descriptions.items():
        command = commands.add_parser(name, help=description, description=description)
        command.add_argument("path", help="Project root or kiroku hub directory.")
        command.add_argument("--hub-dir", action="store_true", help="Select a custom hub directory exactly.")
        if name in {"add", "update"}:
            command.add_argument("--data", required=True, help="JSON payload file, or - for stdin.")
            command.add_argument("--dry-run", action="store_true", help="Validate and display a diff without writing.")
            command.add_argument("--section", required=name == "add", help="Exact existing level-two heading; update can relocate within the same file.")
            if name == "add":
                command.add_argument("--file", required=True, dest="source_file", help="Existing hub-relative Markdown owner file.")
            else:
                command.add_argument("entry_id", help="Stable memory ID or entry:<ID>.")
        elif name == "search":
            command.add_argument("query")
            command.add_argument("--track", help="Include only this track and shared global memory.")
            command.add_argument("--limit", type=bounded_integer(1, 100), default=8)
        elif name == "entries":
            command.add_argument("--type", choices=("decision", "constraint"), dest="entry_type")
            command.add_argument("--status", choices=("proposed", "active", "superseded", "retired"))
            command.add_argument("--track", help="Include this track and shared global memory.")
            command.add_argument("--limit", type=bounded_integer(1, 100), default=20)
            command.add_argument("--offset", type=bounded_integer(0, 1000000000), default=0)
        elif name in {"show", "related"}:
            command.add_argument("node_id", help="Exact ID returned by search or related.")
            if name == "related":
                command.add_argument("--depth", type=bounded_integer(1, 3), default=1)
                command.add_argument("--limit", type=bounded_integer(1, 100), default=20)
        elif name == "context":
            command.add_argument("--track", required=True)
            command.add_argument("--query", default="", help="Optional question for additional relevant sections.")
            command.add_argument("--max-chars", type=bounded_integer(CONTEXT_MIN_CHARS, CONTEXT_MAX_CHARS), default=16000,
                                 help="Maximum complete compact JSON characters, including metadata and final LF; not tokens.")
    return parser.parse_args()


def require_track(connection: sqlite3.Connection, slug: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise MemoryIndexError("Invalid track slug.")
    handoff = f"tracks/{slug}/START_HERE.md"
    if connection.execute("SELECT 1 FROM nodes WHERE kind = 'document' AND path = ?", (handoff,)).fetchone() is None:
        raise MemoryIndexError(f"Track not present in the indexed Markdown: {slug}")


def node(connection: sqlite3.Connection, node_id: str) -> dict:
    row = connection.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if row is None:
        raise MemoryIndexError(f"Unknown node ID: {node_id}. Search again after a heading or path rename.")
    return dict(row)


def document_sections(connection: sqlite3.Connection, path: str) -> list[dict]:
    return [dict(row) for row in connection.execute(
        "SELECT * FROM nodes WHERE path = ? AND kind IN ('section', 'entry') ORDER BY start_line, id", (path,)
    )]


def show(connection: sqlite3.Connection, node_id: str) -> dict:
    result = node(connection, node_id)
    if result["kind"] == "document":
        result["body"] = "".join(part["body"] for part in document_sections(connection, result["path"]))
    elif result["kind"] == "entry":
        result.update(dict(connection.execute(
            "SELECT memory_id, type FROM entries WHERE node_id = ?", (node_id,)
        ).fetchone()))
        result["fields"] = dict(connection.execute(
            "SELECT name, body FROM entry_fields WHERE entry_id = ? ORDER BY name", (node_id,)
        ))
    return result


def entries(connection: sqlite3.Connection, entry_type: str | None, status: str | None,
            track: str | None, limit: int, offset: int) -> dict:
    conditions: list[str] = []
    parameters: list = []
    for column, value in (("e.type", entry_type), ("n.status", status)):
        if value is not None:
            conditions.append(column + " = ?")
            parameters.append(value)
    if track is not None:
        require_track(connection, track)
        conditions.append("n.scope IN ('global', ?)")
        parameters.append(f"tracks/{track}")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    rows = list(connection.execute(
        "SELECT n.id, e.memory_id, e.type, n.status, n.scope, n.title, n.path, n.start_line "
        "FROM entries e JOIN nodes n ON n.id = e.node_id" + where +
        " ORDER BY e.memory_id LIMIT ? OFFSET ?", parameters + [limit + 1, offset],
    ))
    truncated = len(rows) > limit
    return {"results": [dict(row) for row in rows[:limit]], "truncated": truncated,
            "next_offset": offset + limit if truncated else None}


def search(connection: sqlite3.Connection, query: str, track: str | None, limit: int) -> list[dict]:
    words = list(dict.fromkeys(re.findall(r"\w+", query, flags=re.UNICODE)))
    if not words:
        raise MemoryIndexError("Search requires at least one word or identifier.")
    if len(words) > 64:
        raise MemoryIndexError("Search supports at most 64 distinct words; use a focused question.")
    expression = " OR ".join('"' + word + '"' for word in words)
    parameters: list = [expression]
    scope_clause = ""
    if track is not None:
        require_track(connection, track)
        scope_clause = " AND n.scope IN ('global', ?)"
        parameters.append(f"tracks/{track}")
    parameters.append(limit)
    rows = connection.execute(
        "SELECT n.id, n.kind, e.type, e.memory_id, n.path, n.title, n.start_line, n.end_line, n.scope, n.status, "
        "snippet(nodes_fts, 2, '', '', ' … ', 48) AS excerpt, "
        "bm25(nodes_fts, 0.0, 3.0, 1.0) AS score "
        "FROM nodes_fts JOIN nodes n ON n.id = nodes_fts.id "
        "LEFT JOIN entries e ON e.node_id = n.id "
        "WHERE nodes_fts MATCH ? AND n.kind IN ('section', 'entry')" + scope_clause +
        " ORDER BY score, n.id LIMIT ?", parameters,
    )
    return [dict(row) for row in rows]


def incident_edges(connection: sqlite3.Connection, node_id: str, semantic_only: bool = False) -> list[dict]:
    condition = " AND relation != 'contains'" if semantic_only else ""
    return [dict(row) for row in connection.execute(
        "SELECT * FROM edges WHERE (source = ? OR target = ?)" + condition +
        " ORDER BY relation, source, target, source_path, source_line", (node_id, node_id)
    )]


def related(connection: sqlite3.Connection, node_id: str, depth: int, limit: int) -> dict:
    origin = node(connection, node_id)
    queue = deque([(node_id, 0)])
    seen = {node_id}
    results: list[dict] = []
    edges: list[dict] = []
    edge_keys: set[tuple] = set()
    truncated = False
    while queue:
        current, distance = queue.popleft()
        if distance >= depth:
            continue
        for edge in incident_edges(connection, current):
            target = edge["target"] if edge["source"] == current else edge["source"]
            if target not in seen:
                if len(results) >= limit:
                    truncated = True
                    continue
                item = node(connection, target)
                item["excerpt"] = item.pop("body")[:320]
                item["distance"] = distance + 1
                results.append(item)
                seen.add(target)
                queue.append((target, distance + 1))
            key = tuple(edge.values())
            if key not in edge_keys:
                edges.append(edge)
                edge_keys.add(key)
    return {"origin": origin["id"], "depth": depth, "nodes": results, "edges": edges, "truncated": truncated}


def serialize_context(result: dict) -> str:
    """The exact context wire representation, including its single final LF."""
    return json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"


def _measure_context(result: dict, minimum: bool = False) -> int:
    result["used_chars"] = 0
    if minimum:
        result["max_chars"] = result["required_chars"] = 0
    while True:
        size = len(serialize_context(result))
        if result["used_chars"] == size:
            return size
        result["used_chars"] = size
        if minimum:
            # Compute the least sufficient budget, including the digit widths
            # of the budget itself and both self-describing size fields.
            result["max_chars"] = result["required_chars"] = size


def _check_context_budget(max_chars: int) -> None:
    if type(max_chars) is not int or not CONTEXT_MIN_CHARS <= max_chars <= CONTEXT_MAX_CHARS:
        raise MemoryIndexError(f"Context budget must be {CONTEXT_MIN_CHARS}..{CONTEXT_MAX_CHARS} characters")


def context_error(message: str, max_chars: int) -> dict:
    """Keep operational diagnostics within every valid context budget too."""
    _check_context_budget(max_chars)
    result = {"format_version": 2, "state": "error", "max_chars": max_chars,
              "budget_unit": "serialized_json_characters", "error": message,
              "error_truncated": False}
    if _measure_context(result) <= max_chars:
        return result
    result["error_truncated"] = True
    low, high = 0, len(message)
    while low < high:
        middle = (low + high + 1) // 2
        result["error"] = message[:middle] + "…"
        if _measure_context(result) <= max_chars:
            low = middle
        else:
            high = middle - 1
    result["error"] = message[:low] + "…"
    _measure_context(result)
    return result


def context(connection: sqlite3.Connection, track: str, query: str, max_chars: int) -> dict:
    _check_context_budget(max_chars)
    require_track(connection, track)
    required_paths = ["START_HERE.md", "CONSTRAINTS.md"] + [
        f"tracks/{track}/{name}.md" for name in ("START_HERE", "STATE", "ROADMAP", "WORK")
    ]
    required_set = set(required_paths)
    items: list[dict] = []
    seeds: list[str] = []
    for path in required_paths:
        document = connection.execute("SELECT id FROM nodes WHERE path = ? AND kind = 'document'", (path,)).fetchone()
        if document is None:
            raise MemoryIndexError(f"Required context source is missing: {path}. Read and validate the Markdown hub.")
        parts = document_sections(connection, path)
        items.append({"id": path, "body": "".join(part["body"] for part in parts), "reason": "required"})
        # The output groups complete documents, but graph edges still originate
        # from their individual sections and typed entries.
        seeds.extend(part["id"] for part in parts)

    candidates: dict[str, dict] = {}

    def candidate(part: dict, reason: str, edge: dict | None = None) -> None:
        if part["path"] in required_set or part["id"] in candidates:
            return
        item = {key: part[key] for key in ("id", "path", "start_line", "end_line", "body")}
        item["reason"] = reason
        if edge is not None:
            item["via"] = {key: edge[key] for key in ("source", "relation", "source_path", "source_line")}
        candidates[part["id"]] = item

    search_limited = False
    if query:
        hits = search(connection, query, track, 65)
        search_limited = len(hits) > 64
        for hit in hits[:64]:
            candidate(node(connection, hit["id"]), "search")
    # Freeze seeds before graph expansion: preserve exactly one outgoing hop.
    seeds.extend(candidates)
    seeds.extend(required_paths)
    for seed in dict.fromkeys(seeds):
        for edge in incident_edges(connection, seed, semantic_only=True):
            if edge["source"] != seed:
                continue
            target = node(connection, edge["target"])
            parts = document_sections(connection, target["path"]) if target["kind"] == "document" else [target]
            for part in parts:
                candidate(part, "related", edge)

    result = {
        "format_version": 2, "state": "ready", "track": track,
        "budget_unit": "serialized_json_characters", "max_chars": max_chars,
        "required_chars": 0, "items": items,
        "omitted_count": len(candidates), "search_limited": search_limited,
    }
    required_chars = _measure_context(result, minimum=True)
    result["max_chars"] = max_chars
    if _measure_context(result) > max_chars:
        failure = {"format_version": 2, "state": "budget_exceeded", "max_chars": max_chars,
                   "budget_unit": "serialized_json_characters", "required_chars": required_chars,
                   "items": [], "error": "Increase --max-chars or read the required Markdown directly."}
        _measure_context(failure)
        return failure

    for item in candidates.values():
        result["items"].append(item)
        result["omitted_count"] -= 1
        if _measure_context(result) > max_chars:
            result["items"].pop()
            result["omitted_count"] += 1
            _measure_context(result)
    return result


def emit_context(result: dict) -> None:
    payload = serialize_context(result)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(payload.encode("utf-8"))
    else:
        sys.stdout.write(payload)


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    try:
        hub = resolve_hub(Path(args.path), hub_dir=args.hub_dir)
        if args.command in {"add", "update"}:
            payload_text = sys.stdin.read() if args.data == "-" else Path(args.data).read_text(encoding="utf-8")
            result = write_entry(hub, args.command, load_payload(payload_text),
                                 source_file=getattr(args, "source_file", None),
                                 section=args.section, entry_id=getattr(args, "entry_id", None),
                                 dry_run=args.dry_run)
            emit(result)
            return 0 if result["state"] in {"saved", "dry_run"} else 1
        if args.command in {"checkpoint", "build"}:
            emit(build_index(hub))
            return 0
        if args.command == "status":
            result = index_status(hub)
            emit(result)
            return 0 if result["state"] == "ready" else 1
        with closing(open_index(hub)) as connection:
            if args.command == "search":
                emit({"query": args.query, "results": search(connection, args.query, args.track, args.limit)})
            elif args.command == "entries":
                emit(entries(connection, args.entry_type, args.status, args.track, args.limit, args.offset))
            elif args.command == "show":
                emit(show(connection, args.node_id))
            elif args.command == "related":
                emit(related(connection, args.node_id, args.depth, args.limit))
            else:
                result = context(connection, args.track, args.query, args.max_chars)
                emit_context(result)
                return 0 if result["state"] == "ready" else 1
        return 0
    except (MemoryIndexError, OSError, RuntimeError, sqlite3.Error, UnicodeError) as exc:
        if args.command == "context":
            emit_context(context_error(str(exc), args.max_chars))
        else:
            emit({"state": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
