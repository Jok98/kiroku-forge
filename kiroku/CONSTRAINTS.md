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

### Constraint: Generated outputs are noncanonical

Status: active

Rule:
Generated HTML, generated project docs, query caches, tags, and generated IDs
must not become the canonical memory store.

Why:
KirokuForge has to remain useful when opened as plain Markdown by a developer
or agent, and generated projections create drift if treated as authoritative.

### Constraint: Track detail stays local

Status: active

Rule:
Do not copy track-specific progress, local decisions, or implementation detail
into top-level hub files unless it affects the wider project.

Why:
The track layer exists to keep unrelated parallel work out of an agent's
context while preserving one shared project memory for cross-repo truth.

### Constraint: Initialization requires verified content

Status: active

Rule:
Do not report `init` complete while template placeholders, structural errors,
or strict checker warnings remain.

Why:
A copied template is scaffolding, not durable project memory, and would give a
future session false confidence that project context is available.

### Constraint: Autonomous writes respect the task mode

Status: active

Rule:
Context-driven Kiroku use may read existing memory during analysis-only work,
but it must not initialize a hub or create a task workspace without write
authority.

Why:
Memory automation must not override the user's analysis-only or repository
instruction boundaries.

### Constraint: No database dependency

Status: active

Rule:
Do not require a database for KirokuForge memory or for the first local UI.

Why:
The current use case is local, read-mostly, and human-scale; a database adds
schema and synchronization complexity before there is a clear repeated need.

## Out Of Scope

- Rebuilding the old v3 pipeline.
- Maintaining compatibility with the removed v3 schemas or fixtures.
- Creating a full CLI before the Markdown format is proven useful.
- Creating an editable local web app before a read-only semantic viewer has
  proven useful.

## Forbidden Changes

- Do not reintroduce the v3 compiler architecture under a new name.
- Do not make generated views read-only projections of a hidden canonical
  store.
- Do not save generic conversation summaries as durable memory.
- Do not replace Markdown with a canonical database and generated Markdown
  projection.
