# Roadmap

## Milestones

### M-01: Portable indexed memory and focused retrieval

Status: completed

Objective:
Deliver a complete first version of a Markdown-derived SQLite graph and search
index that can travel with a project repository.

Scope:
- One self-contained snapshot per hub, rebuilt from Markdown.
- Read-only status, search, source retrieval, graph navigation, and task context.
- Skill integration, Git snapshot guidance, and this project's indexed memory.

Expected artifacts:
- `scripts/memory_store.py` and `scripts/memory.py`.
- `references/memory-index.md` and aligned existing instructions.
- `kiroku/memory.sqlite`, Git attributes, and curated project memory.

Dependencies:
- The approved Markdown-authoritative, per-hub SQLite design.
- Existing structural parser and hub path conventions.

Validation:
- Existing strict hub and skill validators, Python syntax checks, and diff review.
- Real CLI reads and snapshot builds, including a relocated project copy.
- Focused checks for stale/missing indexes, budget limits, and preserved source bytes.
- Independent script review and a realistic retrieval exercise.

Completion criteria:
- The snapshot has only relative source paths and needs no server or WAL sidecars.
- Rebuilds preserve Markdown and are byte-stable when source content is unchanged.
- Read commands reject missing/stale/invalid indexes without writing.
- Search and explicit graph traversal return original text with source provenance.
- Context preserves mandatory sources or reports an insufficient budget explicitly.
- The project's final snapshot matches its documented memory and passes validation.

Risks:
- A fresh graph index can still contain semantically stale Markdown claims.
- A binary Git conflict requires rebuilding the index from the resolved sources.
- Full-text availability depends on the Python runtime's SQLite build.

### M-02: Typed Markdown decisions and constraints

Status: completed

Objective:
Extract validated decision and constraint records from explicit Markdown markers
while preserving Markdown authority and direct editing.

Scope:
- Versioned entry markers, stable hub-wide IDs, typed fields, and explicit links.
- Derived SQLite records, filtered listing, source retrieval, and structural checks.
- Opt-in compatibility for existing prose and a pilot in this repository's memory.

Expected artifacts:
- A shared structured-entry parser and its focused contract.
- Updated index, CLI, checker, and decision/constraint templates.
- Curated tagged project decisions and constraints with a rebuilt snapshot.

Dependencies:
- M-01.
- User approval for structured Markdown as the canonical input to SQLite.

Validation:
- Existing strict hub and skill validators, Python syntax, and diff review.
- Real extraction, filtered retrieval, stable-ID navigation, and exact source reads.
- Local failure checks for malformed entries, duplicate IDs, and invalid references.
- Snapshot preservation on rejected input, unchanged rebuilds, and independent review.

Completion criteria:
- Structured decisions and constraints have validated fields and stable identifiers.
- Typed retrieval distinguishes active/adopted content from proposed or retired content.
- Invalid structured sources cannot publish a partial index as ready.
- Legacy prose remains readable; all indexed source documents reconstruct exactly.
- The skill's own memory exercises the format and its snapshot is current.

Risks:
- Structural validation does not establish factual truth or permission.
- Existing lexical language limits and context-output overhead remain separate work.
- Guided Markdown writing and additional record families are deferred beyond this pilot.

### M-03: Guided Markdown entry writes

Status: completed

Objective:
Create and update structured decisions and constraints through validated commands
that preserve Markdown authority and refresh the derived index.

Scope:
- JSON input from a file or stdin, generated IDs for new records, and patch updates.
- Explicit owner-file and section selection, source-preserving edits, and dry-run diffs.
- Atomic publication of one Markdown file followed by an explicit index rebuild.
- Clear recovery reporting when Markdown is saved but the index cannot be rebuilt.

Expected artifacts:
- Pure edit planning and a file-publication helper integrated into the memory CLI.
- Guided-write contract and updated skill instructions.
- Verified use on this project's memory and temporary project copies.

Dependencies:
- M-02.
- User approval to implement the guided writer after the structured-entry checkpoint.

Validation:
- Existing hub and skill validators, Python syntax, and diff review.
- Real create/update/dry-run operations and byte preservation of unrelated content.
- Invalid input, injection, source boundaries, no-op, and publication-failure checks.
- Independent implementation review and a realistic writer exercise in a project copy.

Completion criteria:
- Commands validate the complete proposed typed memory before modifying a source.
- New records get stable IDs; updates preserve unspecified fields and unrelated text.
- Dry-runs make no writes and expose a concrete diff.
- A successful write leaves a current index; partial completion is reported accurately.
- The project's final source memory and derived snapshot pass the existing validators.

Risks:
- Markdown and SQLite are separate files; a saved source can outlive a failed rebuild.
- Structural validation cannot determine whether a proposed fact is true or adopted.
- Context serialization, multilingual retrieval, and additional record types stay separate.

### M-04: Bound the complete context response

Status: completed

Objective:
Keep the complete serialized context response within the requested character
budget without cutting mandatory source content or hiding omissions.

Scope:
- Compact versioned context output, including metadata, JSON escapes, and final newline.
- Complete mandatory documents once, deduplicated optional records, and omission counts.
- Bounded insufficient-budget and operational diagnostics for valid context budgets.
- Updated output contract and focused standard-library regression tests.

Expected artifacts:
- Updated context assembly and serialization in the memory CLI.
- Aligned context documentation and regression tests.
- Verified use against this project's memory and a refreshed derived snapshot.

Dependencies:
- M-01 through M-03 remain complete; no storage or writer redesign is required.
- User approval to implement the complete-response context budget.

Validation:
- Measure actual CLI stdout length, escaping, mandatory coverage, and omissions.
- Exercise exact-fit and insufficient budgets, long metadata, errors, and graph deduplication.
- Run the regression tests, existing hub/skill validators, and independent review.
- Verify that context reads preserve source and database bytes and modification times.

Completion criteria:
- Valid context invocations emit at most max_chars serialized Unicode characters.
- Success includes every required source intact; insufficient budgets report no partial context.
- used_chars equals the emitted JSON response length, including the final newline.
- Omission reporting and selected relationship metadata obey the same budget.
- The measured overflow on this hub is corrected without changing search ranking or the DB schema.

Risks:
- Context output shape and max_chars semantics change; clients must use the v2 contract.
- Characters do not equal model tokens or UTF-8 bytes, nor include tool-wrapper overhead.
- Lexical ranking and cross-language retrieval limitations remain outside this milestone.

### M-05: Read published snapshots and batch checkpoint writes

Status: completed

Objective:
Use SQLite alone for ordinary memory reads and publish one snapshot after all
durable Markdown edits at a task/milestone or explicit handoff boundary.

Scope:
- Lightweight database-only query opening, with explicit source/integrity audits.
- Source-only guided edits and one checkpoint command, retaining build as an alias.
- Aligned skill workflows, recovery semantics, regression tests, and project memory.

Expected artifacts:
- Updated store, writer, CLI, and maintained contracts.
- Checkpoint regression suite and adapted context source-drift expectations.
- This hub's completed task state and a single final snapshot publication.

Dependencies:
- M-01 through M-04.
- User approval of database-only ordinary reads and checkpoint-boundary writes.

Validation:
- Guard all read paths against Markdown access and full integrity scans.
- Verify source-only edits, one publication, no-ops, drift audits, and failed checkpoints.
- Run context/checkpoint suites, Python syntax, hub/skill validators, and review.
- Exercise an independent maintenance checkpoint in an isolated project copy.

Completion criteria:
- Queries return the published snapshot with no source reads, hashes, or integrity scan.
- Guided edits preserve database bytes and mtime until explicit checkpoint publication.
- A successful checkpoint exposes every completed source edit; failures preserve the old DB.
- Instructions distinguish published memory, pending Markdown, and explicit drift audits.
- Existing context budgets and source provenance remain valid.

Risks:
- Unobserved manual edits or checkout changes are not detected by ordinary queries.
- A checkpoint is atomic for SQLite publication, not for the whole Markdown edit set.
- Existing lexical retrieval and character-versus-token limitations remain.
