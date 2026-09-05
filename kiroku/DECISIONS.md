# Decisions

## Active Decisions

### Decision: Curated Markdown with minimal metadata

Status: active

Decision:
Keep human-readable Markdown as primary project memory, with stable files,
headings, and small textual fields instead of a canonical machine layer.

Rationale:
Developers and agents need durable reasoning they can read and edit directly;
heavy schemas and bookkeeping undermine that purpose.

Consequences:
- No canonical JSON, database, schema registry, receipts, or generated index by default.
- Store each fact in its owner file and keep operational state concise.

### Decision: Separate evidence gathering from scaffolding and checking

Status: active

Decision:
The agent verifies and curates project knowledge; helpers perform deterministic
scaffolding and structural validation only.

Rationale:
File presence and valid Markdown cannot establish factual accuracy or whether
a milestone's outcome was actually achieved.

Consequences:
- Initialization requires replacing placeholders and passing a strict check.
- The checker covers the documented entry patterns and bundled scaffold prose.
- Translated placeholders and semantic consistency require agent review.

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

### Decision: Keep future views and documentation derived

Status: active

Decision:
A future semantic HTML viewer should derive entry types, IDs, relationships, and
filters from Markdown. Documentation output and any query cache must not become
canonical memory. Do not introduce a database in the current product direction.

Rationale:
Parallel editable stores create synchronization problems and make the underlying
memory less useful when read without the viewer.

Consequences:
- Start any viewer as read-only; future editing must write back to Markdown.
- Keep generated identifiers deterministic, adding explicit markers only if justified.
- Define documentation authorization and output boundaries before adding that mode.

## Replaced Or Obsolete Decisions

- The v3 compiler pipeline, canonical `memory.json`, schemas, hashes, and generated
  projections were intentionally removed. Their past implementation does not
  define the current architecture; meaningful history remains in `LOG.md`.
