# Work

## Ongoing

- None.

## TODO

### Task: Design semantic HTML viewer contract

Status: todo
Completion:
Define the minimum Markdown entry patterns, generated ID rules, HTML attributes,
output location, and read-only behavior for a local Kiroku viewer.

Notes:
- Keep Markdown canonical and directly readable.
- Include useful quality diagnostics before introducing additional metadata.

### Task: Define documentation mode boundaries

Status: todo
Completion:
Specify authorization, output ownership, and source-verification requirements for
project documentation generated with Kiroku context.

Notes:
- Project documentation belongs outside the memory hub.
- Avoid duplicating maintained project files or adding a new canonical store.

## Blocked

- None.

## Done

- Project/task reading modes, evidence-led initialization, optional tracks,
  roadmaps, and bounded activation rules support durable continuation.
- Helper reliability, operational contract alignment, and instruction consolidation
  are complete; `validation-contract-alignment` retains the verified outcomes.
- Shared product decisions preserve Markdown and keep future views derived.
- `local-sqlite-memory` delivered per-hub SQLite snapshots, focused retrieval,
  explicit graphs, source freshness, and repository portability.
- Its structured-entry pilot added validated decisions/constraints, stable IDs,
  typed retrieval, and explicit record relationships without replacing Markdown.
- Guided add/update commands save typed Markdown entries with source-preserving
  patches and dry-run diffs; the complete checkpoint is published once afterward.
- Context v2 bounds the complete response and retains required source content,
  with explicit omission counts and a focused regression suite.
- Ordinary memory reads use only the published database, with full source and
  integrity audits reserved for explicit status checks and checkpoint publication.

## Cancelled

- Rebuilding the removed v3 compiler and canonical JSON pipeline.
