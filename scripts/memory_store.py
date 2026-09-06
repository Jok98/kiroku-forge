"""Build and read a disposable SQLite snapshot of a Markdown memory hub."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import sqlite3
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from check_hub import CONTRACT_LABELS, HEADING_RE, iter_hub_markdown, label_value
from structured_memory import StructuredMemoryError, parse_entries, validate_entries, visible_lines


DB_NAME = "memory.sqlite"
SCHEMA_VERSION = 2
PARSER_VERSION = "2"
APPLICATION_ID = 0x4B49524F

SCHEMA_SQL = """
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE sources (path TEXT PRIMARY KEY, sha256 TEXT NOT NULL);
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('document', 'section', 'entry')),
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL,
    parent_id TEXT REFERENCES nodes(id)
);
CREATE TABLE entries (
    node_id TEXT PRIMARY KEY REFERENCES nodes(id),
    memory_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('decision', 'constraint'))
);
CREATE TABLE entry_fields (
    entry_id TEXT NOT NULL REFERENCES entries(node_id),
    name TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY(entry_id, name)
);
CREATE INDEX entries_type ON entries(type);
CREATE TABLE edges (
    source TEXT NOT NULL REFERENCES nodes(id),
    target TEXT NOT NULL REFERENCES nodes(id),
    relation TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_line INTEGER NOT NULL,
    UNIQUE(source, target, relation, source_path, source_line)
);
CREATE INDEX nodes_path ON nodes(path, start_line);
CREATE INDEX nodes_scope ON nodes(scope);
CREATE INDEX nodes_parent ON nodes(parent_id);
CREATE INDEX edges_source ON edges(source);
CREATE INDEX edges_target ON edges(target);
CREATE VIRTUAL TABLE nodes_fts USING fts5(id UNINDEXED, title, body, tokenize='unicode61');
"""

NODE_COLUMNS = (
    "id", "kind", "path", "title", "body", "start_line", "end_line",
    "scope", "status", "parent_id",
)
LINK_RE = re.compile(
    r"(?<![!\\])\[[^\]\n]*\]\(\s*(?:<(?P<angle>[^>\n]+)>|(?P<plain>[^\s()]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
CODE_RE = re.compile(r"(`+)(.+?)\1")
MILESTONE_RE = re.compile(r"\bM-[0-9]{2,}\b")
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class MemoryIndexError(RuntimeError):
    """An index cannot be built or used safely."""


@dataclass(frozen=True)
class Source:
    path: str
    text: str
    sha256: str


def _hub_path(hub: Path) -> Path:
    try:
        resolved = hub.resolve()
        if not resolved.is_dir():
            raise MemoryIndexError("The selected memory hub is not a directory")
        return resolved
    except (OSError, RuntimeError) as exc:
        if isinstance(exc, MemoryIndexError):
            raise
        raise MemoryIndexError(f"Cannot resolve the memory hub: {exc}") from exc


def _read_sources(hub: Path) -> list[Source]:
    sources: list[Source] = []

    try:
        for path in iter_hub_markdown(hub):
            relative = path.relative_to(hub).as_posix()
            data = path.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise MemoryIndexError(f"Markdown source is not UTF-8: {relative}") from exc
            sources.append(Source(relative, text, hashlib.sha256(data).hexdigest()))
    except (OSError, ValueError) as exc:
        raise MemoryIndexError(f"Cannot read Markdown sources: {exc}") from exc

    return sorted(sources, key=lambda source: source.path)


def _digest(sources: list[Source]) -> str:
    payload = [SCHEMA_VERSION, PARSER_VERSION, [(s.path, s.sha256) for s in sources]]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _title(heading: str) -> str:
    return re.sub(r"[ \t]+#+[ \t]*$", "", heading).strip()


def _anchor(title: str) -> str:
    text = unicodedata.normalize("NFKC", title).casefold()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s+", "-", text).strip("-") or "section"


def _single_target(value: str) -> str:
    link = LINK_RE.fullmatch(value)
    if link is not None:
        return link.group("angle") or link.group("plain")
    code = CODE_RE.fullmatch(value)
    return code.group(2) if code is not None else value


def _structured_entries(sources: list[Source]) -> list[dict]:
    try:
        entries = [entry for source in sources for entry in parse_entries(source.path, source.text)]
        validate_entries(entries)
        return entries
    except StructuredMemoryError as exc:
        raise MemoryIndexError(str(exc)) from exc


def _graph(sources: list[Source], entries: list[dict]) -> tuple[list[dict], list[tuple], list[dict]]:
    nodes: list[dict] = []
    edges: set[tuple] = set()
    documents: dict[str, tuple[list[tuple[str, bool]], list[str]]] = {}
    milestone_nodes: dict[tuple[str, str], list[str]] = {}
    aliases: dict[str, str] = {}
    by_path: dict[str, list[dict]] = {}
    for entry in entries:
        by_path.setdefault(entry["path"], []).append(entry)

    for source in sources:
        raw = source.text.splitlines(keepends=True)
        lines = source.text.splitlines()
        parsed = visible_lines(raw)
        headings = []
        for index, (line, is_code) in enumerate(parsed):
            match = None if is_code else HEADING_RE.match(line)
            if match is not None:
                headings.append((index, len(match.group(1)), _title(match.group(2))))
        parts = source.path.split("/")
        scope = "/".join(parts[:2]) if len(parts) >= 3 and parts[0] == "tracks" else "global"
        nodes.append(dict(
            id=source.path, kind="document", path=source.path,
            title=headings[0][2] if headings else Path(source.path).stem,
            body="", start_line=1 if raw else 0, end_line=len(raw),
            scope=scope, status="", parent_id=None,
        ))
        tagged = by_path.get(source.path, [])
        entry_lines = {
            line: entry for entry in tagged
            for line in range(entry["start_line"] - 1, entry["end_line"])
        }
        used: set[str] = set()
        boundaries: dict[int, tuple[int, str, str, dict | None]] = {}
        for start, level, title in headings:
            base = _anchor(title)
            anchor = base
            suffix = 1
            while anchor in used:
                anchor = f"{base}-{suffix}"
                suffix += 1
            used.add(anchor)
            heading_id = f"{source.path}#{anchor}"
            entry = entry_lines.get(start)
            if entry is None:
                boundaries[start] = (level, title, heading_id, None)
            else:
                aliases[heading_id] = "entry:" + entry["id"]
        for entry in tagged:
            boundaries[entry["start_line"] - 1] = (3, entry["title"], "entry:" + entry["id"], entry)
            end = entry["end_line"]
            if end < len(raw) and end not in boundaries and end not in entry_lines:
                boundaries[end] = (0, "Continuation", f"gap:{source.path}:{end + 1}", None)
        if raw and 0 not in boundaries:
            boundaries[0] = (0, "Preamble", f"gap:{source.path}:1", None)
        ordered = sorted(boundaries.items())
        owners = [source.path] * len(lines)
        parents: list[tuple[int, str]] = []
        for position, (start, (level, title, node_id, entry)) in enumerate(ordered):
            end = ordered[position + 1][0] if position + 1 < len(ordered) else len(raw)
            while level and parents and parents[-1][0] >= level:
                parents.pop()
            parent_id = parents[-1][1] if parents and level else source.path
            if level:
                parents.append((level, node_id))
            node = dict(
                id=node_id, kind="entry" if entry is not None else "section", path=source.path, title=title,
                body="".join(raw[start:end]), start_line=start + 1, end_line=end,
                scope=scope, status=entry["status"] if entry is not None else (label_value(lines[start:end], "Status:") or "").lower(),
                parent_id=parent_id,
            )
            nodes.append(node)
            owners[start:end] = [node_id] * (end - start)
            edges.add((parent_id, node_id, "contains", source.path, start + 1))
            milestone = re.match(r"^(M-[0-9]{2,}):", title)
            if milestone is not None and Path(source.path).name == "ROADMAP.md":
                milestone_nodes.setdefault((source.path, milestone.group(1)), []).append(node_id)
        documents[source.path] = parsed, owners

    node_ids = {node["id"] for node in nodes}
    source_paths = {source.path for source in sources}
    unresolved: dict[tuple, dict] = {}

    def missing(path: str, line: int, target: str, relation: str, reason: str) -> None:
        key = path, line, target, relation
        unresolved[key] = dict(source_path=path, source_line=line, target=target, relation=relation, reason=reason)

    def reference(path: str, line: int, owner: str, target: str, preference: str) -> None:
        try:
            url = urlsplit(target)
        except ValueError:
            return
        if url.scheme or url.netloc:
            return
        target_path, fragment = unquote(url.path), unquote(url.fragment)
        if target_path and not target_path.endswith(".md"):
            return
        if not target_path and not fragment:
            return
        if target_path.startswith("/") or url.query:
            missing(path, line, target, "references", "not a supported hub-local Markdown target")
            return
        if not target_path:
            candidates = [path]
        else:
            local = posixpath.normpath(posixpath.join(posixpath.dirname(path), target_path))
            hub_relative = posixpath.normpath(target_path)
            candidates = [local]
            if preference == "hub":
                candidates = [hub_relative, local]
            elif preference == "inline":
                candidates.append(hub_relative)
            if preference != "document" and target_path.startswith("kiroku/"):
                candidates.append(posixpath.normpath(target_path[len("kiroku/"):]))
        destination = next((candidate for candidate in candidates if candidate in source_paths), None)
        if destination is None:
            missing(path, line, target, "references", "Markdown document is not indexed")
            return
        target_id = destination + ("#" + fragment if fragment else "")
        target_id = aliases.get(target_id, target_id)
        if target_id not in node_ids:
            missing(path, line, target, "references", "heading anchor is not indexed")
            return
        edges.add((owner, target_id, "references", path, line))

    for path, (parsed, owners) in documents.items():
        field: str | None = None
        for index, (line, is_code) in enumerate(parsed):
            if is_code:
                continue
            stripped = line.strip()
            if HEADING_RE.match(line):
                field = None
            label = next((label for label in CONTRACT_LABELS if stripped.startswith(label)), None)
            if label is not None:
                field = label
                value = stripped[len(label):].strip()
            else:
                value = stripped
            owner = owners[index]
            line_number = index + 1
            code_spans = list(CODE_RE.finditer(line))
            links = [match for match in LINK_RE.finditer(line) if not any(
                code.start() <= match.start() < code.end() for code in code_spans
            )]
            for link in links:
                reference(path, line_number, owner, link.group("angle") or link.group("plain"), "hub" if field == "Read:" else "document")
            for code in code_spans:
                if ".md" in code.group(2) and not any(link.start() <= code.start() < link.end() for link in links):
                    reference(path, line_number, owner, code.group(2), "hub" if field == "Read:" else "inline")
            if field == "Read:" and value and not links and not code_spans:
                reference(path, line_number, owner, _single_target(value.removeprefix("- ")), "hub")
            if field == "Related:" and value:
                for item in value.removeprefix("- ").split(","):
                    slug = item.strip().strip("`")
                    if not SLUG_RE.fullmatch(slug) or slug in {"none", "null"}:
                        continue
                    target_id = f"tracks/{slug}/START_HERE.md"
                    if target_id in node_ids:
                        edges.add((owner, target_id, "related", path, line_number))
                    else:
                        missing(path, line_number, target_id, "related", "related track handoff is not indexed")
            if field == "Dependencies:" and Path(path).name == "ROADMAP.md":
                for milestone_id in MILESTONE_RE.findall(value):
                    matches = milestone_nodes.get((path, milestone_id), [])
                    if len(matches) == 1:
                        edges.add((owner, matches[0], "depends_on", path, line_number))
                    else:
                        missing(path, line_number, milestone_id, "depends_on", "milestone is missing or ambiguous")
            if field == "Read:" and value:
                field = None
    for entry in entries:
        for link in entry["links"]:
            edges.add(("entry:" + entry["id"], "entry:" + link["target"],
                       link["relation"], entry["path"], entry["start_line"]))
    return nodes, sorted(edges), [unresolved[key] for key in sorted(unresolved)]


def _target_header(hub: Path) -> bytes | None:
    target = hub / DB_NAME
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = hub / (DB_NAME + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            raise MemoryIndexError(f"SQLite sidecar present: {sidecar.name}; close external writers before using the snapshot")
    if target.is_symlink():
        raise MemoryIndexError(f"Refusing a symlink database target: {DB_NAME}")
    if not target.exists():
        return None
    if not target.is_file():
        raise MemoryIndexError(f"Database target is not a regular file: {DB_NAME}")
    try:
        with target.open("rb") as stream:
            header = stream.read(100)
    except OSError as exc:
        raise MemoryIndexError(f"Cannot inspect {DB_NAME}: {exc}") from exc
    if len(header) < 100 or header[:16] != b"SQLite format 3\x00":
        raise MemoryIndexError("Existing database is corrupt or cannot be identified as Kiroku; it will not be replaced")
    if int.from_bytes(header[68:72], "big") != APPLICATION_ID:
        raise MemoryIndexError("Existing database is not a Kiroku index; it will not be replaced")
    if header[18:20] != b"\x01\x01":
        raise MemoryIndexError("The index is not a DELETE-journal snapshot; close external writers before rebuilding")
    return header


def _connect_readonly(hub: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        (hub / DB_NAME).as_uri() + "?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def _counts(connection: sqlite3.Connection | None, source_count: int | None) -> dict:
    counts: dict = {"sources": source_count, "nodes": None, "edges": None, "entries": None}
    if connection is not None:
        for table in ("sources", "nodes", "edges", "entries"):
            try:
                counts[table] = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            except sqlite3.Error:
                pass
    return counts


def _snapshot_metadata(connection: sqlite3.Connection) -> dict[str, str]:
    """Check the query interface without scanning snapshot content or sources."""
    if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        raise MemoryIndexError("Index schema is incompatible; publish a new checkpoint")
    for table, columns in (
        ("nodes", ",".join(NODE_COLUMNS)),
        ("edges", "source,target,relation,source_path,source_line"),
        ("sources", "path,sha256"),
        ("nodes_fts", "id,title,body"),
        ("entries", "node_id,memory_id,type"),
        ("entry_fields", "entry_id,name,body"),
    ):
        connection.execute(f"SELECT {columns} FROM {table} LIMIT 0")
    metadata = dict(connection.execute(
        "SELECT key,value FROM metadata "
        "WHERE key IN ('schema_version', 'parser_version', 'source_digest')"
    ))
    if metadata.get("schema_version") != str(SCHEMA_VERSION):
        raise MemoryIndexError("Index schema metadata is incompatible; publish a new checkpoint")
    digest = metadata.get("source_digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise MemoryIndexError("Index source-digest metadata is invalid; publish a new checkpoint")
    return metadata


def _assess(hub: Path, sources: list[Source]) -> tuple[dict, sqlite3.Connection | None]:
    connection = None
    try:
        if _target_header(hub) is None:
            return dict(state="missing", reason="No published index exists; run checkpoint", counts=_counts(None, len(sources))), None
        connection = _connect_readonly(hub)
        counts = _counts(connection, len(sources))
        metadata = _snapshot_metadata(connection)
        result = connection.execute("PRAGMA integrity_check").fetchall()
        if len(result) != 1 or result[0][0] != "ok":
            raise MemoryIndexError("SQLite integrity check failed; publish a new checkpoint of the identified Kiroku snapshot")
        stored_sources = dict(connection.execute("SELECT path,sha256 FROM sources"))
        fresh = (
            metadata.get("parser_version") == PARSER_VERSION
            and metadata.get("source_digest") == _digest(sources)
            and stored_sources == {source.path: source.sha256 for source in sources}
        )
        unresolved_row = connection.execute("SELECT value FROM metadata WHERE key='unresolved'").fetchone()
        unresolved = json.loads(unresolved_row[0] if unresolved_row is not None else "[]")
        if not isinstance(unresolved, list):
            raise MemoryIndexError("Unresolved-reference metadata is invalid; publish a new checkpoint")
        report = dict(state="ready" if fresh else "stale", counts=counts, unresolved=unresolved)
        if not fresh:
            report["reason"] = "Markdown sources or parser version changed; run checkpoint to publish their current state"
        return report, connection
    except (MemoryIndexError, sqlite3.Error, ValueError) as exc:
        counts = _counts(connection, len(sources))
        if connection is not None:
            connection.close()
        return dict(state="invalid", reason=str(exc), counts=counts), None


def index_status(hub: Path) -> dict:
    """Explicitly check snapshot integrity and source freshness without writes."""
    try:
        resolved = _hub_path(hub)
        sources = _read_sources(resolved)
        report, connection = _assess(resolved, sources)
        if connection is not None:
            connection.close()
        return report
    except MemoryIndexError as exc:
        return dict(state="invalid", reason=str(exc), counts=_counts(None, None))


def open_index(hub: Path) -> sqlite3.Connection:
    """Open the last compatible checkpoint without reading Markdown sources.

    This checks the DB interface, not its content integrity or freshness against
    Markdown. Call index_status explicitly when those checks are needed. Callers
    own and must close the returned read-only connection.
    """
    resolved = _hub_path(hub)
    connection = None
    try:
        if _target_header(resolved) is None:
            raise MemoryIndexError("No published index exists; run checkpoint")
        connection = _connect_readonly(resolved)
        metadata = _snapshot_metadata(connection)
        if metadata.get("parser_version") != PARSER_VERSION:
            raise MemoryIndexError("Index parser version is incompatible; publish a new checkpoint")
        return connection
    except (MemoryIndexError, sqlite3.Error, ValueError) as exc:
        if connection is not None:
            connection.close()
        if isinstance(exc, MemoryIndexError):
            raise
        raise MemoryIndexError(
            f"Cannot open the published snapshot: {exc}; run status to inspect it before checkpoint"
        ) from exc


def build_index(hub: Path) -> dict:
    """Atomically replace a derived snapshot, preserving an identical existing one."""
    resolved = _hub_path(hub)
    _target_header(resolved)
    sources = _read_sources(resolved)
    digest = _digest(sources)
    current, connection = _assess(resolved, sources)
    if connection is not None:
        connection.close()
    if current["state"] == "ready":
        return dict(current, changed=False)
    entries = _structured_entries(sources)
    nodes, edges, unresolved = _graph(sources, entries)
    metadata = {
        "schema_version": str(SCHEMA_VERSION), "parser_version": PARSER_VERSION,
        "source_digest": digest,
        "unresolved": json.dumps(unresolved, ensure_ascii=False, separators=(",", ":")),
    }
    temporary: Path | None = None
    writable: sqlite3.Connection | None = None
    durability_warning: str | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{DB_NAME}.", suffix=".tmp", dir=resolved)
        os.close(descriptor)
        temporary = Path(name)
        writable = sqlite3.connect(temporary)
        writable.execute("PRAGMA journal_mode=DELETE")
        writable.execute("PRAGMA synchronous=FULL")
        writable.execute("PRAGMA foreign_keys=ON")
        writable.execute(f"PRAGMA application_id={APPLICATION_ID}")
        writable.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        writable.executescript(SCHEMA_SQL)
        writable.executemany("INSERT INTO metadata VALUES (?, ?)", sorted(metadata.items()))
        writable.executemany("INSERT INTO sources VALUES (?, ?)", [(s.path, s.sha256) for s in sources])
        writable.executemany(
            "INSERT INTO nodes VALUES (" + ",".join("?" for _ in NODE_COLUMNS) + ")",
            [tuple(node[column] for column in NODE_COLUMNS) for node in nodes],
        )
        writable.executemany("INSERT INTO edges VALUES (?, ?, ?, ?, ?)", edges)
        writable.executemany("INSERT INTO entries VALUES (?, ?, ?)", [
            ("entry:" + entry["id"], entry["id"], entry["type"]) for entry in entries
        ])
        writable.executemany("INSERT INTO entry_fields VALUES (?, ?, ?)", [
            ("entry:" + entry["id"], name, value)
            for entry in entries for name, value in sorted(entry["fields"].items())
        ])
        writable.executemany("INSERT INTO nodes_fts(id,title,body) VALUES (?, ?, ?)", [
            (node["id"], node["title"], node["body"]) for node in nodes if node["body"].strip()
        ])
        writable.execute("INSERT INTO nodes_fts(nodes_fts) VALUES ('integrity-check')")
        writable.commit()
        if writable.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise MemoryIndexError("The rebuilt SQLite snapshot failed its integrity check")
        writable.close()
        writable = None
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        if _digest(_read_sources(resolved)) != digest:
            raise MemoryIndexError("Markdown changed during build; the previous snapshot was preserved")
        _target_header(resolved)
        os.replace(temporary, resolved / DB_NAME)
        temporary = None
        if os.name == "posix":
            directory_descriptor = None
            try:
                directory_descriptor = os.open(resolved, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                os.fsync(directory_descriptor)
            except OSError as exc:
                durability_warning = (
                    "The snapshot is usable, but syncing its directory failed; "
                    "persistence after a power loss is not confirmed: "
                    f"{exc}"
                )
            finally:
                if directory_descriptor is not None:
                    try:
                        os.close(directory_descriptor)
                    except OSError as exc:
                        durability_warning = f"The snapshot is usable, but closing its directory descriptor failed: {exc}"
    except (OSError, sqlite3.Error) as exc:
        raise MemoryIndexError(f"Cannot build the derived SQLite snapshot: {exc}") from exc
    finally:
        if writable is not None:
            writable.close()
        if temporary is not None:
            for suffix in ("", "-journal", "-wal", "-shm"):
                Path(str(temporary) + suffix).unlink(missing_ok=True)
    report = dict(state="ready", changed=True, counts=dict(sources=len(sources), nodes=len(nodes), edges=len(edges), entries=len(entries)), unresolved=unresolved)
    if durability_warning is not None:
        report["durability_warning"] = durability_warning
    return report
