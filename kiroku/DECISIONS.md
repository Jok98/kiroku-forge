# Decisions

## Active Decisions

### Decision: Markdown is the primary memory

Status: active
Area: product direction

Decision:
KirokuForge stores project memory primarily in human-readable Markdown files
under `kiroku/`.

Rationale:
The user wants memory that is directly useful to developers and agents, with
project reasoning and decisions written in a speaking form rather than hidden
inside structured metadata.

Consequences:
- No canonical `memory.json` in the current design.
- No required frontmatter, schema registry, hash chain, or generated index.
- Structure comes from stable files, headings, and compact prose.

### Decision: Keep metadata minimal

Status: active
Area: file format

Decision:
Use plain text status lines and clear sections instead of heavy metadata.

Rationale:
Generated memory will grow over time. Heavy metadata would consume context and
make the files less pleasant for humans to edit.

Consequences:
- Entries should explain themselves in prose.
- A line such as `Status: active` is acceptable when it helps scanning.
- Machine parsing is secondary and should not drive the format.

### Decision: Match the hub language to the project

Status: active
Area: file format

Decision:
For a new hub, write in the dominant language of the project or the user's
request. For an existing hub, preserve its current language and terminology
unless the user explicitly asks for translation.

Rationale:
The memory is meant to be read by the project's developers and future agents.
Matching the project's working language reduces friction, while preserving an
existing hub's language avoids noisy churn.

Consequences:
- `kiroku/*.md` file names remain stable.
- Template headings and placeholder prose may be translated during init as
  direct equivalents in the selected hub language.

### Decision: Add a lightweight hub checker

Status: active
Area: validation

Decision:
Provide `scripts/check_hub.py` as an optional local checker for the default
Markdown hub contract.

Rationale:
The skill benefits from deterministic checks for easy-to-miss structural
problems, but the current direction rejects a heavy runtime, schemas, or a
canonical machine-readable memory layer.

Consequences:
- The checker validates required files, stale template placeholders,
  `START_HERE.md` length, TODO completion conditions, and active decision
  rationales.
- Checker errors should block completion of init, cleanup, or broad updates;
  warnings should be inspected rather than treated as automatic failures.
- The checker does not make Markdown secondary to generated metadata.

### Decision: Add a cautious init helper

Status: active
Area: initialization

Decision:
Provide `scripts/init_hub.py` to copy bundled Markdown templates into a target
project's `kiroku/` hub.

Rationale:
Initialization is repetitive and easy to do inconsistently by hand. A small
copy helper improves consistency without making the helper the source of truth
or reintroducing the old runtime architecture.

Consequences:
- The script creates the nine standard hub files from
  `assets/templates/kiroku/`.
- Existing standard hub files are not overwritten unless `--overwrite` is
  passed.
- The script can run the lightweight checker with `--check`, but template
  placeholders still need to be filled or translated by the agent.

### Decision: Generated views are derived

Status: active
Area: generated outputs

Decision:
Any local HTML UI, project documentation output, tags, generated IDs, or query
aid must be derived from the Markdown hub rather than becoming a parallel
source of truth.

Rationale:
The user wants a clearer, more interactive view for humans, but agents should
still be able to read and maintain the plain Markdown files directly.

Consequences:
- The first HTML viewer should be read-only.
- Generated IDs should be deterministic from file, heading, and entry text,
  with optional explicit markers only when stability is needed.
- Generated artifacts should be ignored or safely regenerable unless the user
  explicitly asks to publish them.

### Decision: Do not introduce a database now

Status: active
Area: generated outputs

Decision:
Do not add a database as canonical KirokuForge storage or as a required layer
for the current local UI direction.

Rationale:
A database would add schema design, migrations, sync concerns, harder Git
review, and drift risk while giving agents less useful narrative context than
well-structured Markdown.

Consequences:
- The current direction is structured Markdown plus semantic HTML generation.
- If a SQLite or similar cache is ever justified, it must be disposable and
  regenerated from Markdown.
- Agents should continue to read Markdown first instead of querying a database.

### Decision: Use semantic Markdown for local UI generation

Status: active
Area: file format

Decision:
Future HTML generation should parse stable Markdown entry patterns rather than
perform only a vanilla Markdown-to-HTML conversion.

Rationale:
A plain conversion produces readable pages, but a useful local UI needs entry
types, statuses, tags, relationships, filters, and diagnostics that come from
consistent Markdown structure.

Consequences:
- Existing entry patterns such as decisions, tasks, constraints, risks, and
  rejected ideas should become the renderer contract.
- HTML can include `id`, `data-type`, `data-status`, `data-area`, and
  `data-tags` derived from Markdown.
- The Markdown must remain pleasant to read without the renderer.

### Decision: Remove the v3 implementation

Status: active
Area: repository structure

Decision:
Delete the v3 compiler-style implementation and recreate the skill from a
small Markdown-first base.

Rationale:
The old design had a strong formal pipeline, schemas, ChangeSets, hashes, and
canonical JSON. That was too heavy for the desired manual, readable project
memory hub.

Consequences:
- `schemas/`, `scripts/kiroku_core/`, `tests/`, `references/contracts-v3.md`,
  and `todo_kiroku.txt` were removed.
- Old v3 validation state is historical only.
- New maturity will come from practical use and forward-testing.

## Replaced Or Obsolete Decisions

- The previous decision to use `memory.json` as canonical memory is obsolete
  for this skill direction.
- The previous pipeline model `CAPTURE -> CLASSIFY -> RECONCILE -> COMPILE ->
  VALIDATE -> HANDOFF` is obsolete as user-facing product shape.
