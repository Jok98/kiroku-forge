# Constraints

## Active Constraints

### Constraint: Markdown first

Status: active

Rule:
Project memory must live primarily in readable Markdown files.

Why:
The memory has to be useful to developers and agents without requiring a parser
or generated projection.

### Constraint: Minimal metadata

Status: active

Rule:
Do not add frontmatter, IDs, hashes, receipts, or structured indexes by
default.

Why:
The user explicitly wants speaking project information, not a format that
fills context with bookkeeping.

### Constraint: No canonical JSON by default

Status: active

Rule:
Do not create `memory.json` or equivalent canonical JSON unless explicitly
asked.

Why:
The prior JSON-centered design was judged too limiting for human-editable
Markdown memory.

## Out Of Scope

- Rebuilding the old v3 pipeline.
- Maintaining compatibility with the removed v3 schemas or fixtures.
- Creating a full CLI before the Markdown format is proven useful.

## Forbidden Changes

- Do not reintroduce the v3 compiler architecture under a new name.
- Do not make generated views read-only projections of a hidden canonical
  store.
- Do not save generic conversation summaries as durable memory.
