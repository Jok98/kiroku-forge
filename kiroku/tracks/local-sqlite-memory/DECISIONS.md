# Decisions

## Active Decisions

### Decision: Build an index instead of a second editable memory

Status: active
Decision:
Store indexed original sections and explicit graph edges in `memory.sqlite`.
Derive the entire snapshot from the hub's Markdown and keep source references relative.
Rationale:
The approved workflow preserves Git-reviewable narrative memory and makes the
retrieval layer portable and recoverable without a server.
Consequences:
- Index writes publish the complete checkpoint after authorized Markdown curation.
- Ordinary reads use only the published snapshot; status explicitly audits source drift.
- Unchanged sources reuse the existing snapshot without rewriting it.

### Decision: Deliver bounded lexical and graph retrieval first

Status: active
Decision:
Use SQLite FTS5 and evidenced graph links, with source-preserving output and an
explicit character budget for focused task context.
Rationale:
This implements the requested navigation using the existing Python standard-library
runtime and avoids introducing extraction models before their value is measured.
Consequences:
- Similarity alone never creates a dependency or adopts a decision.
- Embeddings, a graphical viewer, and a shared memory service remain separate work.

<!-- kiroku:entry {"version":1,"id":"DEC-guided-source-publication","type":"decision","status":"active","links":[{"relation":"constrained_by","target":"CON-001"}]} -->
### Save canonical entries before one checkpoint publication

Status: active

Decision:
Guided writes validate typed memory and atomically save one Markdown owner without opening SQLite. Finish the complete checkpoint edit set, validate it, then publish the derived snapshot once.

Rationale:
Markdown remains authoritative while readers use a stable published checkpoint. Separating source saves from publication avoids repeated rebuilds and preserves saved decisions after a failed checkpoint.

Consequences:
- Report saved with index_updated false; checkpoint publishes the completed edit set.
- Preserve unspecified fields, comments outside rewritten spans, and unrelated files.
- No-op edits do not confirm that pending Markdown has been published.
- Preview without writes; retain its ID when applying a new entry.
- Recover failed publication by retrying checkpoint, not repeating saved additions.

<!-- kiroku:end -->
