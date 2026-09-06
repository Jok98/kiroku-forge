# Start Here

## Mission

- Deliver one portable, versionable SQLite index for each Markdown memory hub.
- Improve focused retrieval through text search and explicit graph relationships.

## Current State

- The user approved a local database per project, stored with project files.
- M-01 is complete: index, query helper, contracts, and project snapshot are delivered.
- M-02 is complete: tagged decisions/constraints, stable IDs, fields, and typed retrieval.
- M-03 is complete: guided entry writes and explicit index recovery.
- M-04 is complete: verified complete-response context budgeting in format v2.
- M-05 is complete: database-only ordinary reads and batched checkpoint publication.
- Markdown remains authoritative; the database is derived and rebuildable.

## Next Action

- No milestone is pending. Use `STATE.md` for verification and `RISKS.md` for limitations.

## Hard Constraints

- Assume one agent writes this project's memory; no coordination service is needed.
- Reads must not create or repair the index or change Markdown.
- Read the published snapshot through SQLite; save durable memory at checkpoint boundaries.
- Audit known external source changes explicitly with status before relying on their snapshot.
- Do not promote inferred relationships or historical claims to verified facts.
- Keep snapshots independent of machine paths and SQLite runtime sidecars.
- Keep the runtime in Python's standard library; no external service is needed.

## Read Only If Needed

- `STATE.md`, `ROADMAP.md`, and `WORK.md` for implementation and validation state.
- `DECISIONS.md` and `RISKS.md` for scope and evidence boundaries.
