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
