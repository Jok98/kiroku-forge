# Structured Memory Pilot

This contract defines optional typed decision and constraint entries in the
canonical Markdown. Existing unmarked content remains narrative memory; it is
not converted or assigned a type automatically. The [file contract](file-contract.md)
continues to own file placement and language, and [memory-index.md](memory-index.md)
owns the derived database.
The [guided writer](guided-writes.md) can create and patch these entries from
validated operation inputs at a checkpoint while keeping their owner Markdown
editable. The complete checkpoint is published once after its edits are finished.

## Entry Format

An entry begins and ends with complete, single-line HTML comments outside
fenced code. Between them, use one `###` title followed by the existing
technical field labels. The title and values may use the hub's language;
metadata keys, types, statuses, relations, and field labels remain invariant.

```markdown
<!-- kiroku:entry {"version":1,"id":"decision-local-index","type":"decision","status":"active","links":[{"relation":"constrained_by","target":"constraint-markdown-owner"}]} -->
### Decision: Keep the index derived

Decision:
Rebuild the local index from the canonical Markdown.

Rationale:
Developers can edit and review the authoritative memory directly.

Consequences:
- Database rows are not edited independently.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"constraint-markdown-owner","type":"constraint","status":"active"} -->
### Constraint: Preserve the source memory

Rule:
Keep Markdown as the authoritative project memory.

Why:
Independent editable copies can disagree about the current project state.
<!-- kiroku:end -->
```

The examples illustrate syntax, not adoption of a decision in another project.
The markers provide stable identity and relationships while the existing labels
remain readable and compatible with the Markdown checker. `#### Decision`
and similar heading aliases do not replace fields in this pilot.

## Metadata And Identity

The opening JSON object contains exactly `version`, `id`, `type`, `status`,
and optional `links`. `version` must be the integer `1`.

- `id` matches `[A-Za-z][A-Za-z0-9_-]{0,95}` and is unique throughout the hub.
  Assign it once; retain it when changing the title or moving the entry.
  The scaffold placeholder `REPLACE_WITH_UNIQUE_ID` is rejected.
- `type` is `decision` or `constraint`.
- `status` is `proposed`, `active`, `superseded`, or `retired`.
- `links`, when present, is an array of objects containing exactly `relation`
  and `target`. Targets are stable entry IDs, not paths or heading anchors.

`proposed` records a choice or rule still under consideration. `active` records
an adopted choice or applicable rule. `superseded` preserves an entry replaced
by another; `retired` preserves one no longer applicable. The parser validates
these values; it does not infer adoption, update another entry's status, or
prove that the status agrees with current project evidence.

Scope and file provenance come from the Markdown location, not metadata fields.
Unknown metadata keys, duplicate JSON keys, and invalid values are errors.

## Body Fields

| Type | Required fields | Optional fields |
| --- | --- | --- |
| `decision` | `Decision:`, `Rationale:` | `Status:`, `Area:`, `Consequences:` |
| `constraint` | `Rule:`, `Why:` | `Status:`, `Area:` |

Use field labels at column zero, exactly as shown. Their order is not fixed.
An optional `Status:` value must exactly match the metadata status. Optional
fields may be omitted; when present, they must contain meaningful content.
Do not invent an area, consequence, rationale, or evidence to fill a template.

Values may be inline, multiline prose, bullets, or non-empty fenced code.
Blank text, HTML comments, empty list markers, and heading-only content do not
satisfy a field. Outside fenced code, another heading is not allowed inside
the entry; use the field labels rather than nested headings. Text before the
first field is rejected, except for blank lines and comments.

Lines of the form `Label: value` at column zero are reserved for fields.
Unsupported or repeated labels are errors. Put prose or code with that form
in a bullet or fence when it is part of a value, so it cannot be mistaken for a
field. Fenced examples do not create fields, markers, or operational entries;
backtick and tilde fences are recognized.

## Relationships

| Relation | Meaning and target rule |
| --- | --- |
| `depends_on` | The source declares a dependency on the target entry. |
| `supersedes` | The source replaces the target; both entries must have the same type. |
| `constrained_by` | The source is subject to a target of type `constraint`. |
| `related` | The source records a relevant connection without asserting dependency or replacement. |

Targets must exist among the hub's parsed entries. Forward references and
references to another file are resolved after all sources have been parsed.
Self-links are rejected. References do not establish factual truth, authorize
work, or infer missing relationships. Link validation does not detect semantic
contradictions or decide which entries should be adopted or retired.

## Parser Contract And Errors

`scripts/structured_memory.py` uses only the Python 3.9+ standard library:

- `parse_entries(path, text)` returns entries containing `id`, `type`, `status`,
  `title`, `path`, `start_line`, `end_line`, `body`, `fields`, and `links`.
- `body` is the exact original span, including both delimiters and its original
  line endings. Line numbers are one-based and include both delimiter lines.
- `fields` uses labels without their trailing colon as keys. Values preserve
  internal text and line endings while stripping surrounding whitespace.
- `validate_entries(entries)` checks hub-wide unique IDs and link targets after
  parsing all sources. It accepts the entries returned by the parser.

Malformed, nested, unmatched, or unclosed markers are errors. JSON must stay
on the opening marker's line. A missing title, missing required field, empty
declared field, or conflicting status is also an error. Each
`StructuredMemoryError` includes `path:line` for the offending source.

Parsing and validation do not write files, rebuild a database, rewrite legacy
memory, or establish semantic accuracy. Unmarked Markdown remains outside
this typed contract; explicitly convert only entries whose meaning and state
are known.
