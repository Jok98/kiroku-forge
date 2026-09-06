"""Plan focused edits to canonical Markdown without filesystem or DB writes."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import PurePosixPath

from memory_store import MemoryIndexError, Source
from structured_memory import (
    ALLOWED_FIELDS,
    ENTRY_STATUSES,
    ENTRY_TYPES,
    FIELD_RE,
    HEADING_RE,
    OPEN_RE,
    REQUIRED_FIELDS,
    StructuredMemoryError,
    parse_entries,
    validate_entries,
    visible_lines,
)


def _error(message: str) -> None:
    raise MemoryIndexError(message)


def _object(value: object, name: str) -> dict:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        _error(f"{name} must be an object with string keys")
    return value


def _keys(payload: dict, allowed: set[str], required: set[str] | None = None) -> None:
    unknown = payload.keys() - allowed
    missing = (required or set()) - payload.keys()
    if unknown:
        _error(f"Unsupported payload fields: {', '.join(sorted(unknown))}")
    if missing:
        _error(f"Missing payload fields: {', '.join(sorted(missing))}")


def _title(value: object) -> str:
    if (not isinstance(value, str) or not value.strip()
            or any(char in value for char in "\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029")):
        _error("title must be non-empty text on one line")
    return value.strip()


def _status(value: object) -> str:
    if not isinstance(value, str) or value not in ENTRY_STATUSES:
        _error("status must be proposed, active, superseded, or retired")
    return value


def _newline(text: str) -> str:
    match = re.search(r"\r\n|\n|\r", text)
    return match[0] if match else "\n"


def _value(value: object, newline: str, field: str) -> str:
    if not isinstance(value, str):
        _error(f"Field {field!r} must be a string")
    return re.sub(r"\r\n|\r|\n", lambda _: newline, value).strip()


def _metadata(entry: dict, previous: dict | None = None) -> str:
    data = dict(previous) if previous is not None else {"version": 1}
    for key in ("id", "type", "status"):
        data[key] = entry[key]
    if entry["links"] or "links" in data:
        data["links"] = entry["links"]
    try:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise MemoryIndexError(f"Entry metadata is not JSON-compatible: {exc}") from exc


def _field_text(name: str, value: str, newline: str, tail: str) -> str:
    if name in {"Status", "Area"} and not re.search(r"\r|\n", value):
        return f"{name}: {value}{tail}"
    return f"{name}:{newline}{value}{tail}"


def _render(entry: dict, newline: str) -> str:
    lines = [f"<!-- kiroku:entry {_metadata(entry)} -->", f"### {entry['title']}", ""]
    prefix = newline.join(lines) + newline
    fields = "".join(_field_text(name, value, newline, newline + newline)
                     for name, value in entry["fields"].items())
    return prefix + fields + "<!-- kiroku:end -->" + newline


def _offsets(lines: list[str]) -> list[int]:
    positions = [0]
    for line in lines:
        positions.append(positions[-1] + len(line))
    return positions


def _entry_bounds(text: str, entry: dict) -> tuple[int, int]:
    positions = _offsets(text.splitlines(keepends=True))
    return positions[entry["start_line"] - 1], positions[entry["end_line"]]


def _sections(path: str, text: str) -> list[dict]:
    lines = text.splitlines(keepends=True)
    positions = _offsets(lines)
    occupied = set()
    for entry in parse_entries(path, text):
        occupied.update(range(entry["start_line"] - 1, entry["end_line"]))
    headings = []
    for index, (visible, is_code) in enumerate(visible_lines(lines)):
        if is_code or index in occupied:
            continue
        match = HEADING_RE.match(visible)
        if match and len(match[1]) <= 2:
            title = re.sub(r"[ \t]+#+[ \t]*$", "", match[2] or "").strip()
            headings.append((index, len(match[1]), title))
    sections = []
    for position, (index, level, title) in enumerate(headings):
        if level != 2:
            continue
        end = positions[headings[position + 1][0]] if position + 1 < len(headings) else len(text)
        sections.append({"title": title, "start": positions[index],
                         "body_start": positions[index + 1], "end": end})
    return sections


def _section(path: str, text: str, requested: object) -> dict:
    if not isinstance(requested, str) or not requested.strip():
        _error("An existing exact H2 section title is required")
    matches = [item for item in _sections(path, text) if item["title"] == requested]
    if len(matches) != 1:
        _error(f"{path}: expected exactly one H2 section {requested!r}; found {len(matches)}")
    return matches[0]


def _insert(path: str, text: str, section: str, body: str, newline: str) -> str:
    target = _section(path, text, section)
    insertion = target["end"]
    # Only this exact empty-section placeholder may be removed by an add/move.
    if text[target["body_start"]:target["end"]].strip() == "- None.":
        insertion = target["body_start"]
    prefix = text[:insertion]
    suffix = text[target["end"]:]
    if prefix and not prefix.endswith(("\n", "\r")):
        prefix += newline
    if not prefix.splitlines() or prefix.splitlines()[-1].strip():
        prefix += newline
    if not body.endswith(("\n", "\r")):
        body += newline
    return prefix + body + (newline if suffix else "") + suffix


def _layout(body: str) -> tuple[list[str], list[int], int, dict[str, tuple[int, int]]]:
    lines = body.splitlines(keepends=True)
    positions = _offsets(lines)
    title_line = None
    starts = []
    for index, (visible, is_code) in enumerate(visible_lines(lines)):
        if is_code or index in {0, len(lines) - 1}:
            continue
        heading = HEADING_RE.match(visible)
        if heading and len(heading[1]) == 3:
            title_line = index
        field = FIELD_RE.match(visible)
        if field:
            starts.append((field[1], index))
    if title_line is None:
        _error("Validated entry is missing its title span")
    spans = {}
    for index, (name, start) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else len(lines) - 1
        spans[name] = (positions[start], positions[end])
    return lines, positions, title_line, spans


def _title_change(raw: str, title: str) -> str:
    visible = visible_lines([raw])[0][0]
    match = HEADING_RE.match(visible)
    content = match[2]
    trimmed = re.sub(r"[ \t]+#+[ \t]*$", "", content).rstrip()
    start = match.start(2) + len(trimmed) - len(trimmed.lstrip())
    end = match.start(2) + len(trimmed)
    if "<!--" in raw[start:end] or "-->" in raw[start:end]:
        _error("The title contains embedded comments; edit that title directly in Markdown to preserve them")
    return raw[:start] + title + raw[end:]


def _rewrite(previous: dict, expected: dict, newline: str) -> str:
    body = previous["body"]
    lines, positions, title_line, fields = _layout(body)
    replacements = []
    if expected["status"] != previous["status"] or expected["links"] != previous["links"]:
        opening = OPEN_RE.fullmatch(lines[0].rstrip("\r\n"))
        metadata = json.loads(opening[1])
        replacements.append((opening.start(1), opening.end(1), _metadata(expected, metadata)))
    if expected["title"] != previous["title"]:
        replacements.append((positions[title_line], positions[title_line + 1],
                             _title_change(lines[title_line], expected["title"])))
    for name, (start, end) in fields.items():
        if name not in expected["fields"]:
            replacements.append((start, end, ""))
        elif expected["fields"][name] != previous["fields"][name]:
            tail = re.search(r"\s*\Z", body[start:end])[0]
            replacements.append((start, end, _field_text(name, expected["fields"][name], newline, tail or newline)))
    additions = [(name, value) for name, value in expected["fields"].items() if name not in fields]
    if additions:
        content = "".join(_field_text(name, value, newline, newline + newline) for name, value in additions)
        replacements.append((positions[-2], positions[-2], content))
    for start, end, replacement in sorted(replacements, reverse=True):
        body = body[:start] + replacement + body[end:]
    return body


def _expected_add(payload: dict, ids: set[str], newline: str) -> dict:
    _keys(payload, {"id", "type", "status", "title", "fields", "links"},
          {"type", "status", "title", "fields"})
    kind = payload["type"]
    if not isinstance(kind, str) or kind not in ENTRY_TYPES:
        _error("type must be decision or constraint")
    status = _status(payload["status"])
    identifier = payload.get("id")
    if "id" not in payload:
        prefix = "DEC-" if kind == "decision" else "CON-"
        identifier = prefix + uuid.uuid4().hex
        while identifier in ids:
            identifier = prefix + uuid.uuid4().hex
    if isinstance(identifier, str) and identifier in ids:
        _error(f"Entry ID already exists in the hub: {identifier}")
    supplied = _object(payload["fields"], "fields")
    _keys(supplied, ALLOWED_FIELDS[kind], REQUIRED_FIELDS[kind])
    values = {name: _value(value, newline, name) for name, value in supplied.items()}
    if "Status" in values and values["Status"] != status:
        _error("fields.Status must agree with the payload status")
    return {"id": identifier, "type": kind, "status": status,
            "title": _title(payload["title"]), "fields": {"Status": status, **values},
            "links": payload.get("links", [])}


def _expected_update(previous: dict, payload: dict, newline: str) -> dict:
    _keys(payload, {"title", "status", "fields", "links"})
    expected = {key: previous[key] for key in ("id", "type", "status", "title", "links")}
    expected["fields"] = dict(previous["fields"])
    if "title" in payload:
        expected["title"] = _title(payload["title"])
    if "status" in payload:
        expected["status"] = _status(payload["status"])
    if "links" in payload:
        expected["links"] = payload["links"]
    supplied = _object(payload.get("fields", {}), "fields")
    _keys(supplied, ALLOWED_FIELDS[previous["type"]])
    for name, value in supplied.items():
        if value is None:
            if name in REQUIRED_FIELDS[previous["type"]]:
                _error(f"Cannot remove required field {name!r}")
            expected["fields"].pop(name, None)
        else:
            expected["fields"][name] = _value(value, newline, name)
    if "Status" in supplied and supplied["Status"] is not None:
        if expected["fields"]["Status"] != expected["status"]:
            _error("fields.Status must agree with the entry metadata status")
    elif "Status" in expected["fields"] and "status" in payload:
        expected["fields"]["Status"] = expected["status"]
    return expected


def _entries(sources: list[Source], replacement: tuple[str, str] | None = None) -> list[dict]:
    result = []
    for source in sources:
        text = replacement[1] if replacement and source.path == replacement[0] else source.text
        result.extend(parse_entries(source.path, text))
    return result


def _roundtrip(sources: list[Source], previous: list[dict], path: str, after: str,
               expected: dict, operation: str) -> None:
    proposed = _entries(sources, (path, after))
    validate_entries(proposed)
    by_id = {entry["id"]: entry for entry in proposed}
    expected_ids = {entry["id"] for entry in previous} | {expected["id"]}
    if set(by_id) != expected_ids:
        _error("Payload changed the set of entries unexpectedly; field and marker injection is not allowed")
    result = by_id[expected["id"]]
    if any(result[key] != value for key, value in expected.items()):
        _error("Payload did not round-trip as exactly the requested fields, title, status, and links")
    for entry in previous:
        if entry["id"] != expected["id"] and entry["body"] != by_id[entry["id"]]["body"]:
            _error(f"The planned {operation} unexpectedly changed another entry: {entry['id']}")


def plan_edit(sources: list[Source], operation: str, payload: dict, *,
              source_file: str | None = None, section: str | None = None,
              entry_id: str | None = None) -> dict:
    """Return one source's before/after text after validating the proposed hub.

    ADD requires an explicit source file and exact H2 title. UPDATE keeps the
    source file and only moves when a different observed H2 is requested.
    Rewritten field values use the source's newline and strip outer whitespace.
    Other entry spans and surrounding narrative are preserved; only an exact
    '- None.' empty-section body may be removed when inserting.
    """
    try:
        payload = _object(payload, "payload")
        if not isinstance(operation, str) or operation not in {"add", "update"}:
            _error("operation must be add or update")
        by_path = {source.path: source for source in sources}
        if len(by_path) != len(sources):
            _error("The source snapshot contains duplicate paths")
        if source_file is not None:
            if (not isinstance(source_file, str) or not source_file
                    or "\\" in source_file or PurePosixPath(source_file).is_absolute()
                    or ".." in PurePosixPath(source_file).parts
                    or str(PurePosixPath(source_file)) != source_file):
                _error("source_file must be an exact hub-relative source path")
            if source_file not in by_path:
                _error(f"Source file is not present in the memory snapshot: {source_file}")
        entries = _entries(sources)
        ids = [entry["id"] for entry in entries]
        if len(ids) != len(set(ids)):
            _error("The hub contains duplicate stable entry IDs; resolve them before planning an edit")
        if operation == "add":
            if source_file is None or entry_id is not None:
                _error("add requires source_file; specify an optional new ID in the payload, not entry_id")
            before = by_path[source_file].text
            newline = _newline(before)
            expected = _expected_add(payload, set(ids), newline)
            after = _insert(source_file, before, section, _render(expected, newline), newline)
        else:
            if not isinstance(entry_id, str) or not entry_id:
                _error("update requires an existing stable entry ID or entry:<ID>")
            identifier = entry_id[6:] if entry_id.startswith("entry:") else entry_id
            matches = [entry for entry in entries if entry["id"] == identifier]
            if len(matches) != 1:
                _error(f"Expected one existing entry for ID {identifier!r}; found {len(matches)}")
            previous = matches[0]
            if source_file is not None and source_file != previous["path"]:
                _error("update cannot move an entry to another source file")
            source_file = previous["path"]
            before = by_path[source_file].text
            newline = _newline(previous["body"])
            expected = _expected_update(previous, payload, newline)
            body = _rewrite(previous, expected, newline)
            start, end = _entry_bounds(before, previous)
            after = before[:start] + body + before[end:]
            if section is not None:
                target = _section(source_file, before, section)
                if not target["body_start"] <= start < target["end"]:
                    without_entry = before[:start] + before[end:]
                    after = _insert(source_file, without_entry, section, body, newline)
        _roundtrip(sources, entries, source_file, after, expected, operation)
        return {"source_file": source_file, "before": before, "after": after,
                "id": expected["id"], "operation": operation, "changed": after != before}
    except StructuredMemoryError as exc:
        raise MemoryIndexError(str(exc)) from exc
