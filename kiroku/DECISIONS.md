# Decisions

## Active Decisions

<!-- kiroku:entry {"version":1,"id":"DEC-001","type":"decision","status":"active"} -->
### Decision: Curated Markdown with minimal metadata

Status: active

Decision:
Keep human-readable Markdown as primary project memory, with stable files,
headings, small textual fields, and explicit typed markers where reliable
extraction is needed. SQLite remains a derived representation.

Rationale:
Developers and agents need durable reasoning they can read and edit directly;
metadata must support reliable extraction without replacing readable reasoning.

Consequences:
- No canonical JSON, database, schema registry, or receipt store. The approved
  SQLite index is derived from these Markdown files and remains disposable.
- Store each fact in its owner file and keep operational state concise.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-002","type":"decision","status":"active"} -->
### Decision: Separate evidence gathering from scaffolding and checking

Status: active

Decision:
The agent verifies and curates project knowledge; helpers perform deterministic
scaffolding, structural validation, indexing, and source-preserving retrieval.

Rationale:
File presence and valid Markdown cannot establish factual accuracy or whether
a milestone's outcome was actually achieved.

Consequences:
- Initialization requires replacing placeholders and passing a strict check.
- The checker covers the documented entry patterns and bundled scaffold prose.
- Translated placeholders and semantic consistency require agent review.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-003","type":"decision","status":"active"} -->
### Decision: Match project language while preserving technical tokens

Status: active

Decision:
Use the project's or request's language for new prose; preserve the language of
existing memory. Keep file names, slugs, milestone IDs, field labels, and status
values invariant while allowing translated descriptive headings and contents.

Rationale:
Readable local-language memory and dependable lightweight parsing need an
explicit boundary between prose and structural identifiers.

Consequences:
- Select a translated index section by its observed heading text.
- An agent completes and curates generated English scaffold prose before readiness.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-004","type":"decision","status":"active"} -->
### Decision: Separate global context from durable task workspaces

Status: active

Decision:
Use one hub for related repositories, with optional tracks for independently
resumable work. Keep milestone outcomes in roadmap files and granular work in
work files. Separate task continuation from project onboarding.

Rationale:
Focused task reads need detailed local state; project onboarding needs shared
context and routing without loading every task's implementation detail.

Consequences:
- Promote only conclusions that affect shared direction, architecture, or constraints.
- Preserve stable milestone IDs and allow at most one in-progress milestone per roadmap.
- A task read can fall back to global entries without creating a workspace.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-005","type":"decision","status":"active"} -->
### Decision: Bound automatic activation and update scope

Status: active

Decision:
Use applicable AGENTS rules for selective activation, preserve read-only modes,
and perform memory writes only within authorized project and milestone scope.

Rationale:
Automatic memory use should aid continuation without creating trivial tracks,
changing unrelated files, or treating old memory as current authority.

Consequences:
- Current instructions and verified project evidence override stale memory.
- Local compression touches only affected owner files and direct references.
- Historical installation notes do not prove current host configuration.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-006","type":"decision","status":"active"} -->
### Decision: Make helper destinations and exceptions explicit

Status: active

Decision:
Select custom hubs with `--hub-dir`, translated index headings with
`--track-section`, and user-requested long handoffs with individual
`--allow-long-handoff` paths. Preserve existing files in additive scaffolding.

Rationale:
A generic filename cannot reliably identify a hub, translated empty sections
cannot be guessed, and an exception for one file must not weaken checks elsewhere.

Consequences:
- Validate destination types and index plans before copying.
- Legacy custom hubs relying on filename detection require the explicit flag.
- Advisory handoff targets do not become blocking warnings.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-007","type":"decision","status":"active"} -->
### Decision: Keep future views and documentation derived

Status: active

Decision:
A future semantic HTML viewer should derive entry types, IDs, relationships, and
filters from Markdown. Documentation output and query indexes must not become
canonical memory. The user approved a portable SQLite index for focused retrieval.

Rationale:
Parallel editable stores create synchronization problems and make the underlying
memory less useful when read without the viewer.

Consequences:
- Start any viewer as read-only; future editing must write back to Markdown.
- Use stable source IDs for structured entries; derive identifiers for other sections.
- Define documentation authorization and output boundaries before adding that mode.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-008","type":"decision","status":"active","links":[{"relation":"constrained_by","target":"CON-001"}]} -->
### Decision: Version one derived SQLite snapshot per hub

Status: active

Decision:
Build `memory.sqlite` from each hub's Markdown using Python and SQLite FTS5.
Store original sections, explicit relationships, and relative source references.
The snapshot may be committed with the matching Markdown in an authorized Git action.

Rationale:
The user wants project-local graph navigation and fast retrieval with an index
that travels with the repository. A single agent writes each project's memory,
so no shared server or coordination service is needed.

Consequences:
- Builds replace complete self-contained snapshots; reads never rebuild memory.
- Freshness describes correspondence with Markdown, not truth about the code.
- Rebuild binary conflicts from the resolved Markdown rather than merging SQL rows.
- Keep embeddings and automatic relation inference outside the first implementation.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-009","type":"decision","status":"active","links":[{"relation":"constrained_by","target":"CON-001"}]} -->
### Decision: Extract typed records from structured Markdown

Status: active

Decision:
Use explicit versioned entry delimiters, stable IDs, typed fields, and declared
relations in canonical Markdown. Begin with decisions and constraints; extract
validated records into the same per-hub SQLite snapshot.

Rationale:
The user wants editable Markdown that a deterministic program can interpret
without guessing entry boundaries or losing the reasoning behind each memory.

Consequences:
- Keep field labels invariant and narrative values in the existing hub language.
- Reject invalid tagged records and references before replacing the snapshot.
- Preserve legacy prose and migrate entries only within the authorized scope.
- Guided add/update commands manage canonical Markdown; additional record families remain separate.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"DEC-010","type":"decision","status":"active","links":[{"relation":"constrained_by","target":"CON-001"}]} -->
### Read published checkpoints and batch durable memory writes

Status: active

Decision:
Use the last published SQLite snapshot as the sole ordinary memory reading interface. Save canonical Markdown at task/milestone completion or an explicit handoff/maintenance boundary, validate all changes, and publish one checkpoint.

Rationale:
One agent writes each project memory. Re-reading every source and rebuilding after each entry adds repeated work without improving the intended stable-checkpoint workflow.

Consequences:
- Ordinary queries do not scan Markdown or audit full database integrity.
- Guided edits return saved and leave SQLite untouched until checkpoint.
- Use status explicitly after known external source changes or suspected damage.
- A failed checkpoint preserves the prior database and pending canonical edits.
- Bootstrap and recovery can read source Markdown; normal queries do not fall back to it.

<!-- kiroku:end -->

## Replaced Or Obsolete Decisions

- The v3 compiler pipeline, canonical `memory.json`, schemas, hashes, and generated
  projections were intentionally removed. Their past implementation does not
  define the current architecture; meaningful history remains in `LOG.md`.
- The earlier deferral of every database/index was superseded by explicit approval
  of per-hub, derived SQLite snapshots; Markdown authority remains unchanged.
