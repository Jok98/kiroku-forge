"""Parse and validate opt-in typed entries in canonical Kiroku Markdown."""

from __future__ import annotations

import json
import re


ENTRY_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,95}\Z")
ENTRY_TYPES = {"decision", "constraint"}
ENTRY_STATUSES = {"proposed", "active", "superseded", "retired"}
LINK_RELATIONS = {"depends_on", "supersedes", "constrained_by", "related"}
REQUIRED_FIELDS = {"decision": {"Decision", "Rationale"}, "constraint": {"Rule", "Why"}}
ALLOWED_FIELDS = {
    "decision": REQUIRED_FIELDS["decision"] | {"Status", "Area", "Consequences"},
    "constraint": REQUIRED_FIELDS["constraint"] | {"Status", "Area"},
}
OPEN_RE = re.compile(r"^[ \t]*<!--[ \t]*kiroku:entry[ \t]+(\{.*\})[ \t]*-->[ \t]*$")
CLOSE_RE = re.compile(r"^[ \t]*<!--[ \t]*kiroku:end[ \t]*-->[ \t]*$")
MARKER_RE = re.compile(r"<!--[ \t]*kiroku:")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*))?$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 _-]*):")


class StructuredMemoryError(ValueError):
    """A malformed typed entry or invalid cross-entry reference."""


def _fail(path: str, line: int, message: str) -> None:
    raise StructuredMemoryError(f"{path}:{line}: {message}")


def _line_kinds(lines: list[str]) -> list[str]:
    kinds: list[str] = []
    fence_char = ""
    fence_length = 0
    in_comment = False
    for raw in lines:
        line = raw.rstrip("\r\n")
        match = FENCE_RE.match(line)
        if fence_char:
            if (match and match[1][0] == fence_char
                    and len(match[1]) >= fence_length and not match[2].strip()):
                fence_char = ""
                kinds.append("fence")
            else:
                kinds.append("code")
        elif not in_comment and match and not (match[1][0] == "`" and "`" in match[2]):
            fence_char = match[1][0]
            fence_length = len(match[1])
            kinds.append("fence")
        else:
            _, in_comment = _visible_line(line, in_comment)
            kinds.append("text")
    return kinds


def _visible_line(line: str, in_comment: bool) -> tuple[str, bool]:
    """Mask HTML comments while preserving the columns of visible text."""
    visible = []
    offset = 0
    while offset < len(line):
        if in_comment:
            end = line.find("-->", offset)
            boundary = len(line) if end < 0 else end + 3
            visible.append(" " * (boundary - offset))
            offset = boundary
            in_comment = end < 0
        else:
            start = line.find("<!--", offset)
            if start < 0:
                visible.append(line[offset:])
                break
            visible.append(line[offset:start])
            offset = start
            in_comment = True
    return "".join(visible), in_comment


def visible_lines(lines: list[str]) -> list[tuple[str, bool]]:
    """Expose graph-readable lines with comments masked and fences marked."""
    result: list[tuple[str, bool]] = []
    in_comment = False
    for raw, kind in zip(lines, _line_kinds(lines)):
        line = raw.rstrip("\r\n")
        if kind == "fence":
            result.append(("", True))
        elif kind == "code":
            result.append((line, True))
        else:
            visible, in_comment = _visible_line(line, in_comment)
            result.append((visible, False))
    return result


def _has_content(value: str) -> bool:
    lines = value.splitlines(keepends=True)
    in_comment = False
    for raw, kind in zip(lines, _line_kinds(lines)):
        if kind == "fence":
            continue
        if kind == "code":
            if raw.strip():
                return True
            continue
        visible, in_comment = _visible_line(raw.rstrip("\r\n"), in_comment)
        text = visible.strip()
        if (text and not HEADING_RE.match(visible)
                and not re.fullmatch(r"(?:[-*+]|[0-9]+[.)])(?:[ \t]+\[[ xX]\])?", text)
                and not re.fullmatch(r"(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,}", text)):
            return True
    return False


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant {value!r}")


def _metadata(payload: str, path: str, line: int) -> dict:
    try:
        data = json.loads(payload, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        _fail(path, line, f"invalid entry metadata: {exc}")
    if not isinstance(data, dict):
        _fail(path, line, "entry metadata must be a JSON object")
    required = {"version", "id", "type", "status"}
    missing = required - data.keys()
    unknown = data.keys() - (required | {"links"})
    if missing:
        _fail(path, line, f"missing metadata fields: {', '.join(sorted(missing))}")
    if unknown:
        _fail(path, line, f"unknown metadata fields: {', '.join(sorted(unknown))}")
    if type(data["version"]) is not int or data["version"] != 1:
        _fail(path, line, "version must be the integer 1")
    if not isinstance(data["id"], str) or not ENTRY_ID_RE.fullmatch(data["id"]):
        _fail(path, line, "id must match [A-Za-z][A-Za-z0-9_-]{0,95}")
    if data["id"] == "REPLACE_WITH_UNIQUE_ID":
        _fail(path, line, "replace the template ID with a stable hub-unique entry ID")
    if not isinstance(data["type"], str) or data["type"] not in ENTRY_TYPES:
        _fail(path, line, "type must be decision or constraint")
    if not isinstance(data["status"], str) or data["status"] not in ENTRY_STATUSES:
        _fail(path, line, "status must be proposed, active, superseded, or retired")
    links = data.get("links", [])
    if not isinstance(links, list):
        _fail(path, line, "links must be an array")
    for link in links:
        if not isinstance(link, dict) or set(link) != {"relation", "target"}:
            _fail(path, line, "each link must contain exactly relation and target")
        if not isinstance(link["relation"], str) or link["relation"] not in LINK_RELATIONS:
            _fail(path, line, f"invalid link relation {link['relation']!r}")
        if not isinstance(link["target"], str) or not ENTRY_ID_RE.fullmatch(link["target"]):
            _fail(path, line, "link target must be a stable entry ID")
        if link["target"] == data["id"]:
            _fail(path, line, "an entry cannot link to itself")
    data["links"] = links
    return data


def _entry(path: str, lines: list[str], kinds: list[str], start: int, end: int, metadata: dict) -> dict:
    title = None
    field = None
    values: dict[str, list[str]] = {}
    field_lines: dict[str, int] = {}
    in_comment = False
    for index in range(start + 1, end):
        raw = lines[index]
        kind = kinds[index]
        if kind != "text":
            if field is None:
                _fail(path, index + 1, "fenced content must belong to a field after the ### title")
            values[field].append(raw)
            continue
        visible, in_comment = _visible_line(raw.rstrip("\r\n"), in_comment)
        if not visible.strip():
            if field is not None:
                values[field].append(raw)
            continue
        heading = HEADING_RE.match(visible)
        if title is None:
            if not heading or len(heading[1]) != 3:
                _fail(path, index + 1, "the entry must begin with one ### title")
            title = re.sub(r"[ \t]+#+[ \t]*$", "", heading[2] or "").strip()
            if not _has_content(title):
                _fail(path, index + 1, "the ### title must contain text")
            continue
        if heading:
            _fail(path, index + 1, "additional headings are not fields; use the existing technical labels")
        match = FIELD_RE.match(visible)
        if match:
            field = match[1]
            if field not in ALLOWED_FIELDS[metadata["type"]]:
                _fail(path, index + 1, f"unsupported field {field!r} for {metadata['type']}")
            if field in values:
                _fail(path, index + 1, f"duplicate field {field!r}")
            values[field] = [raw[match.end():].lstrip(" \t")]
            field_lines[field] = index + 1
        elif field is None:
            _fail(path, index + 1, "text after the title must begin with a technical field label")
        else:
            values[field].append(raw)
    if title is None:
        _fail(path, start + 1, "entry is missing its ### title")
    fields = {name: "".join(parts).strip() for name, parts in values.items()}
    for name in sorted(REQUIRED_FIELDS[metadata["type"]] - fields.keys()):
        _fail(path, start + 1, f"entry is missing required field {name!r}")
    for name, value in fields.items():
        if not _has_content(value):
            _fail(path, field_lines[name], f"field {name!r} must contain text or non-empty fenced code")
    if "Status" in fields and fields["Status"] != metadata["status"]:
        _fail(path, field_lines["Status"], "Status field must match the metadata status exactly")
    return {
        "id": metadata["id"], "type": metadata["type"], "status": metadata["status"],
        "title": title, "path": path, "start_line": start + 1, "end_line": end + 1,
        "body": "".join(lines[start:end + 1]), "fields": fields, "links": metadata["links"],
    }


def parse_entries(path: str, text: str) -> list[dict]:
    """Parse opt-in entries; body and inclusive spans retain both delimiters."""
    lines = text.splitlines(keepends=True)
    kinds = _line_kinds(lines)
    entries = []
    start = None
    metadata = None
    seen = set()
    for index, (raw, kind) in enumerate(zip(lines, kinds)):
        if kind != "text":
            continue
        line = raw.rstrip("\r\n")
        if not MARKER_RE.search(line):
            continue
        opening = OPEN_RE.fullmatch(line)
        closing = CLOSE_RE.fullmatch(line)
        if not opening and not closing:
            _fail(path, index + 1, "malformed marker; use a complete kiroku:entry or kiroku:end comment on its own line")
        if opening:
            if start is not None:
                _fail(path, index + 1, f"nested entry; entry at line {start + 1} is still open")
            start = index
            metadata = _metadata(opening[1], path, index + 1)
        else:
            if start is None:
                _fail(path, index + 1, "kiroku:end has no matching entry")
            entry = _entry(path, lines, kinds, start, index, metadata)
            if entry["id"] in seen:
                _fail(path, start + 1, f"duplicate entry ID {entry['id']!r}")
            seen.add(entry["id"])
            entries.append(entry)
            start = None
            metadata = None
    if start is not None:
        _fail(path, start + 1, "unclosed entry; expected a kiroku:end marker outside fenced code")
    return entries


def validate_entries(entries: list[dict]) -> None:
    """Check hub-wide IDs and references after parsing all selected sources."""
    by_id = {}
    for entry in entries:
        existing = by_id.get(entry["id"])
        if existing is not None:
            _fail(entry["path"], entry["start_line"],
                  f"duplicate entry ID {entry['id']!r}; first declared at {existing['path']}:{existing['start_line']}")
        by_id[entry["id"]] = entry
    for entry in entries:
        for link in entry["links"]:
            path, line = entry["path"], entry["start_line"]
            if link["target"] == entry["id"]:
                _fail(path, line, "an entry cannot link to itself")
            target = by_id.get(link["target"])
            if target is None:
                _fail(path, line, f"link target {link['target']!r} does not exist in the hub")
            if link["relation"] == "constrained_by" and target["type"] != "constraint":
                _fail(path, line, "constrained_by must target a constraint entry")
            if link["relation"] == "supersedes" and target["type"] != entry["type"]:
                _fail(path, line, "supersedes must target an entry of the same type")
