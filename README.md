# KirokuForge

**Durable, provenance-backed project memory for agents and humans.**

KirokuForge transforms conversations, planning sessions, project files,
notes, and technical investigations into structured, versioned, and verifiable
project knowledge. It is designed so that a future agent can answer both *"what
is true?"* and *"why do we believe it?"* without re-reading the full
conversation history.

---

## Table of Contents

1. [Concepts](#concepts)
2. [Canonical Artifact](#canonical-artifact)
3. [Data Model](#data-model)
4. [Command Reference](#command-reference)
5. [Typical Workflow](#typical-workflow)
6. [Record Types](#record-types)
7. [Provenance & Evidence](#provenance--evidence)
8. [Validation Rules](#validation-rules)
9. [Projections](#projections)
10. [Architecture](#architecture)
11. [Usage Examples](#usage-examples)

---

## Concepts

### One Source Of Truth

`kiroku/memory.json` is the only editable artifact. Every other file in
`kiroku/` is a **generated projection** and must never be edited as a source.
Projections include:

- `agent-bootstrap.json` — compact agent context (filtered by scope)
- `views/*.md` — human-readable Markdown views
- `views/INDEX.md` — table of contents with statistics

### Provenance-Backed Claims

Every durable claim carries structured evidence linking it back to its original
source — a conversation, a file, a command output, a test result. Evidence
records the **method** of observation (direct, inferred, user-stated, test
result) so future readers can distinguish certainty from speculation.

### Controlled Mutation Pipeline

All writes to `memory.json` flow through an explicit run lifecycle. No
concurrent mutations are allowed. Every record carries a content hash for
optimistic concurrency control, and historical claims are preserved through
linear supersession chains (no branches, no cycles, no deletions).

---

## Canonical Artifact

```
kiroku/
├── memory.json              ← canonical (only editable file)
├── agent-bootstrap.json     ← generated, compact agent context
└── views/
    ├── INDEX.md             ← table of contents + statistics
    ├── overview.md          ← facts, constraints, implementation details
    ├── decisions.md         ← decisions and assumptions
    ├── actions.md           ← tasks and roadmap items
    ├── risks-and-questions.md ← risks, questions, conflicts
    ├── preferences.md       ← durable user/project preferences
    ├── history.md           ← ideas, rejected ideas, events
    └── sources.md           ← evidence source index
```

---

## Data Model

### memory.json Structure

```json
{
  "schema_version": "2.0.0",
  "memory_id": "mem_project_xxxxxxxx",
  "project": { … },
  "sources": [ … ],
  "runs": [ … ],
  "records": [ … ]
}
```

### Project

| Field         | Description                                  |
|---------------|----------------------------------------------|
| `id`          | Stable project identifier                    |
| `name`        | Human-facing name                            |
| `domain`      | Business or technical domain                 |
| `status`      | `active`, `paused`, `completed`, `archived`  |
| `goal`        | Durable project target                       |
| `scope`       | List of system/module/product scopes         |

### Sources

A source identifies an input artifact — it does not contain extracted
conclusions. Sources are immutable once registered.

| Kind               | Typical URI                                  |
|--------------------|----------------------------------------------|
| `conversation`       | `conversation://project/session-id`        |
| `user_input`         | `conversation://project/message-42`        |
| `repository_file`    | `src/main/java/example/SecurityConfig.java` |
| `document`           | `docs/architecture.md`                     |
| `command_output`     | `command://analysis/project`               |
| `url`                | `https://example.com/rfc/1234`             |
| `test_result`        | `command://pytest/project`                 |
| `agent_observation`  | `observation://project/2026-06-07`         |

Each source has:
- **Identity**: `kind + uri + revision` (unique tuple)
- **Integrity**: `verified` (content hash available) or `unavailable`
- **Content hash**: SHA-256 when content was captured

### Runs

A run represents one **create**, **update**, **review**, or **import**
operation. It groups the sources that were analysed and the records that were
created or changed. Only one run may be active (status `running`) at a time.

```
add-source(s) → start-run → add/update/supersede-record(s) → finish-run → build
```

A run cannot be completed until all its record operations succeed. `build`
refuses to generate projections while any run is `running`.

### Records

Every record shares a common envelope:

| Field                 | Purpose                                      |
|-----------------------|----------------------------------------------|
| `id`                  | Deterministic, derived from `key`            |
| `key`                 | Stable logical identity (lowercase, `[a-z0-9][a-z0-9_-]{0,79}`) |
| `type`                | One of 14 record types                       |
| `status`              | Lifecycle state                              |
| `title`               | Human-readable short name                    |
| `summary`             | One-sentence description                     |
| `scope`               | Project scopes this record applies to        |
| `tags`                | Free-form categorization                     |
| `confidence`          | `confirmed`, `high`, `medium`, `low`, `unknown` |
| `verification_status` | `verified`, `partially_verified`, `unverified`, `contradicted` |
| `evidence`            | Structured source references                 |
| `relations`           | Links to other records                       |
| `payload`             | Type-specific content                        |
| `content_hash`        | SHA-256 of canonical JSON (excluding hash)   |

---

## Command Reference

All commands operate on a `--dir ./kiroku` directory (default).

### Init

```bash
python scripts/kiroku.py init \
  --dir ./kiroku \
  --name "Project Name" \
  --domain "project-domain" \
  --goal "Project goal" \
  [--description "Optional description"] \
  [--scope scope1 --scope scope2] \
  [--force]
```

Creates a new `memory.json`. Use `--force` to overwrite an existing one.

### Add Source

```bash
python scripts/kiroku.py add-source \
  --dir ./kiroku \
  --kind repository_file \
  --title "Security configuration" \
  [--file path/to/file | --text "content" | --stdin] \
  [--uri "stable/identifier"] \
  [--revision "<source-revision>"] \
  [--metadata KEY=VALUE ...]
```

Content input methods (mutually exclusive):
- `--file` — hash file content (URI defaults to file path)
- `--text` — inline text (requires `--uri`)
- `--stdin` — pipe content (requires `--uri`)
- Neither — registers with `unavailable` integrity (requires `--uri`)

Re-registering the same identity+content is idempotent. Same identity with
different content is rejected (use a new `--revision` or `--uri`).

### Start Run

```bash
python scripts/kiroku.py start-run \
  --dir ./kiroku \
  --operation update \
  --input src_example \
  [--actor-type agent|user|tool] \
  [--actor-name codex] \
  [--actor-version gpt-5]
```

Returns a run ID. All `--input` source IDs must already be registered.

### Add Record

```bash
python scripts/kiroku.py add-record \
  --dir ./kiroku \
  --run-id run_update_xxxx \
  --file ./record-draft.json
```

Or via stdin:

```bash
cat record-draft.json | python scripts/kiroku.py add-record \
  --dir ./kiroku --run-id run_update_xxxx --stdin
```

Required draft fields: `key`, `type`, `title`, `summary`, `confidence`,
`verification_status`, `payload`. Optional: `status` (default `active`),
`scope` (default project scope), `tags`, `evidence`, `relations`, `extensions`.

Duplicate keys are rejected. Equivalent content under a different key is
deduplicated (returns `[SAME]`).

### Update Record

```bash
python scripts/kiroku.py update-record \
  --dir ./kiroku \
  --run-id run_update_xxxx \
  --key existing_key \
  --expect-hash sha256:... \
  --file ./record-draft.json
```

Complete semantic replacement with optimistic concurrency control. Preserves
`id`, `key`, `type`, `created_at`, and unchanged evidence timestamps. The
`--expect-hash` must match the record's current `content_hash` — stale hashes
reject the update atomically.

### Supersede Record

```bash
python scripts/kiroku.py supersede-record \
  --dir ./kiroku \
  --run-id run_update_xxxx \
  --key existing_key \
  --expect-hash sha256:... \
  --file ./replacement-draft.json
```

Atomically:
1. Marks the predecessor `superseded`
2. Creates the replacement with a new key and live status
3. Adds a `supersedes` relation from replacement to predecessor

Constraints:
- Replacement must use a **new, unused** key
- Replacement must have a live status (not `superseded`/`obsolete`/`cancelled`)
- Each superseded record has exactly **one** direct replacement
- Chains must be **linear** (no branches, no cycles)
- Do not manually include `supersedes` in the draft

### Finish Run

```bash
python scripts/kiroku.py finish-run \
  --dir ./kiroku \
  --run-id run_update_xxxx \
  --summary "Extracted current architecture decisions." \
  [--warning "One assumption remains unverified."]
```

Completed runs are immutable. Idempotent for the same summary and warnings.

### Query

```bash
python scripts/kiroku.py query \
  --dir ./kiroku \
  [--key exact_key] \
  [--type decision] \
  [--status active] \
  [--scope my-scope] \
  [--tag architecture] \
  [--relation-target rec_xxxx] \
  [--relation-type depends_on] \
  [--format compact|full|ids] \
  [--sort title|type|status|created_at|updated_at] \
  [--sort-dir asc|desc] \
  [--count]
```

Filters compose conjunctively. `--relation-target` and `--relation-type`
compose within the **same relation** (not across different relations on the
same record). Enum values (`--type`, `--status`, `--relation-type`) are
validated and unknown values are rejected with a clear error.

Output formats:
- `compact` (default): id, key, type, status, title, summary, scope,
  confidence, verification_status, payload, evidence_source_ids, relations
- `full`: complete record objects
- `ids`: list of record IDs only
- `--count`: prints integer count, ignores format

### Validate

```bash
python scripts/kiroku.py validate --dir ./kiroku
```

Checks structural JSON Schema compliance and semantic rules. Returns exit code
2 on errors.

### Render

```bash
python scripts/kiroku.py render --dir ./kiroku
```

Generates Markdown views from `memory.json`. Files are written only when
content changes (avoids unnecessary filesystem noise).

### Bootstrap

```bash
python scripts/kiroku.py bootstrap \
  --dir ./kiroku \
  [--scope my-scope] \
  [--max-records 40]
```

Generates `agent-bootstrap.json` — a compact, agent-optimized projection.
Filtered by scope, capped at `max-records`, sorted by status priority then
type priority then title.

### Build

```bash
python scripts/kiroku.py build \
  --dir ./kiroku \
  [--scope my-scope] \
  [--max-records 40] \
  [--no-render]
```

Complete pipeline: recalculates hashes, validates, writes canonical memory,
generates Markdown views (unless `--no-render`), and generates the agent
bootstrap. Requires all runs to be completed.

---

## Typical Workflow

### Creating New Memory

```bash
# 1. Initialize
python scripts/kiroku.py init --dir ./kiroku \
  --name "My Project" --domain "web" --goal "Build a reliable API"

# 2. Register sources
python scripts/kiroku.py add-source --dir ./kiroku \
  --kind conversation --title "Architecture discussion" \
  --uri "conversation://myproject/session-1" \
  --revision "2026-06-07" --text "…discussion transcript…"

python scripts/kiroku.py add-source --dir ./kiroku \
  --kind repository_file --title "Current architecture" \
  --file src/architecture.md --revision "architecture-v1"

# 3. Start a run
python scripts/kiroku.py start-run --dir ./kiroku \
  --operation create --input src_conversation --input src_architecture \
  --actor-name codex

# 4. Add records (repeat for each claim)
python scripts/kiroku.py add-record --dir ./kiroku \
  --run-id run_create_xxxx --file ./decision-draft.json

# 5. Finish the run
python scripts/kiroku.py finish-run --dir ./kiroku \
  --run-id run_create_xxxx \
  --summary "Initial memory extraction from architecture discussion."

# 6. Build projections
python scripts/kiroku.py build --dir ./kiroku
```

### Updating Existing Memory

```bash
# 1. Register new sources
python scripts/kiroku.py add-source ...

# 2. Start a run
python scripts/kiroku.py start-run --dir ./kiroku \
  --operation update --input src_new_file --actor-name codex

# 3. Read the hash of the record to update
RECORD_HASH=$(python -c "
import json
m = json.load(open('kiroku/memory.json'))
for r in m['records']:
    if r['key'] == 'my_decision': print(r['content_hash'])
")

# 4. Update or supersede
python scripts/kiroku.py update-record --dir ./kiroku \
  --run-id run_update_xxxx --key my_decision \
  --expect-hash "$RECORD_HASH" --file ./updated-draft.json

# 5. Finish and build
python scripts/kiroku.py finish-run --dir ./kiroku \
  --run-id run_update_xxxx --summary "Updated decision with new findings."
python scripts/kiroku.py build --dir ./kiroku
```

---

## Record Types

| Type                     | Payload                                                  | Use Case                                    |
|--------------------------|----------------------------------------------------------|---------------------------------------------|
| `fact`                   | `statement`                                              | Verifiable technical fact                   |
| `decision`               | `decision`, `context`, `implications`                    | Architectural or design decision            |
| `assumption`             | `basis`, `risk`, `validation_needed`                     | Unverified premise                          |
| `idea`                   | `description`, `expected_value`                          | Proposed enhancement                        |
| `rejected_idea`          | `idea`, `reason`, `reconsider_when`                      | Idea with documented rejection reason       |
| `task`                   | `action`, `owner`, `priority`, `blocked_by`, `acceptance_criteria` | Actionable work item          |
| `question`               | `question`, `category`, `why_matters`, `known_options`, `required_input` | Open design question            |
| `risk`                   | `description`, `category`, `impact`, `likelihood`, `mitigations` | Technical or project risk           |
| `preference`             | `preference`, `applies_to`, `reason`                     | Durable user or project preference          |
| `constraint`             | `constraint`, `consequences`                             | Non-negotiable system constraint            |
| `implementation_detail`  | `detail`, `components`                                   | How something is/was implemented            |
| `roadmap_item`           | `outcome`, `horizon` (`now`/`next`/`later`/`maybe`), `priority` | Planned future work              |
| `conflict`               | `claims`, `resolution`, `recommended_action`             | Documented disagreement                     |
| `event`                  | `description`, `occurred_at`                             | Time-bound occurrence                       |

### Lifecycle States

`proposed` → `active` → `resolved` | `completed` | `superseded` | `obsolete` | `cancelled`

### Confidence & Verification

| Confidence   | Requires                             |
|--------------|--------------------------------------|
| `confirmed`  | `verification_status: verified`      |
| `high`       | At least partial evidence            |
| `medium`     | Some inference or weak evidence      |
| `low`        | Speculation, early brainstorming     |
| `unknown`    | No evidence available                |

---

## Provenance & Evidence

Evidence explains **why** a record exists — not just what it claims.

### Evidence Object

```json
{
  "source_id": "src_architecture_doc",
  "relation": "supports",
  "method": "direct_observation",
  "target": "/payload/decision",
  "locator": {
    "kind": "lines",
    "start_line": 42,
    "end_line": 56
  },
  "observed_at": "2026-06-07T10:00:00Z",
  "note": "The file explicitly mandates service-layer data access."
}
```

### Relations

| Relation      | Meaning                                       |
|---------------|-----------------------------------------------|
| `supports`    | Evidence confirms the claim                   |
| `refutes`     | Evidence contradicts the claim                |
| `context`     | Evidence provides background, not proof       |
| `supersedes`  | Managed automatically by `supersede-record`   |

### Observation Methods

| Method                | Makes record verified? | Typical Use                        |
|-----------------------|----------------------|-------------------------------------|
| `user_statement`      | Yes                  | User explicitly stated a decision   |
| `direct_observation`  | Yes                  | Code/documentation directly shows it |
| `test_result`         | Yes                  | Automated test confirms it          |
| `inference`           | No                   | Agent deduces from context          |

### Locator Kinds

| Kind           | Fields                         | Use When                             |
|----------------|--------------------------------|--------------------------------------|
| `lines`        | `start_line`, `end_line`       | Source code or text file             |
| `message`      | `message_id`                   | Conversation message                 |
| `section`      | `section`                      | Document section heading             |
| `selector`     | `selector`                     | CSS/XPath/JSONPath                   |
| `command`      | `command`                      | Shell command that produced output   |
| `url_fragment` | `fragment`                     | URL with anchor                      |
| `whole_source` | *none*                         | Entire source is relevant            |

---

## Validation Rules

`build` and `validate` enforce:

### Structural (JSON Schema)
- All required fields present
- Correct types for all fields
- Enums match allowed values
- No unknown properties outside `extensions`
- Only one matching schema branch per record type

### Semantic
- No duplicate IDs across all entities
- No duplicate record keys
- Evidence sources exist and are inputs of the generating run
- Verified records have direct supporting evidence (not inference)
- `confidence: confirmed` requires `verified`
- Completed tasks require direct completion evidence
- Completed runs have `completed_at` and `summary`
- Running runs cannot have `completed_at` or `summary`
- Superseded records have exactly one direct replacement
- Supersession chains are linear (no branches, no cycles)
- Content hashes match computed values
- Locator line ranges have `end_line >= start_line`
- Relation targets exist and are not self-referential
- Completed runs have `completed_at >= started_at`

---

## Projections

### Views (Markdown)

Each view groups records by type:

| View                      | Record Types                              |
|---------------------------|-------------------------------------------|
| `overview.md`             | `fact`, `constraint`, `implementation_detail` |
| `decisions.md`            | `decision`, `assumption`                  |
| `actions.md`              | `task`, `roadmap_item`                    |
| `risks-and-questions.md`  | `risk`, `question`, `conflict`            |
| `preferences.md`          | `preference`                              |
| `history.md`              | `idea`, `rejected_idea`, `event`          |
| `sources.md`              | *all sources*                             |

Each record appears in exactly one primary view. Views include the record
header, payload rendered as key-value pairs, and evidence references.

### Agent Bootstrap

`agent-bootstrap.json` is a compact projection optimized for agent context
windows. It includes only:

- Project identity and goal
- Records (sorted by status priority → type priority → title)
- Sources referenced by selected records
- Filtered by scope (optional)
- Capped at `max_records` (default 40)

---

## Architecture

```
scripts/
├── kiroku.py                  ← CLI entry point (~1100 lines)
└── kiroku_core/
    ├── __init__.py
    ├── io.py                  ← JSON loading, hashing, atomic write
    ├── schema.py              ← Custom JSON Schema validator (no deps)
    ├── records.py             ← Draft normalization, ID generation, semantics comparison
    ├── validation.py          ← Structural + semantic validation
    ├── rendering.py           ← Markdown view generation
    └── bootstrap.py           ← Agent bootstrap generation

schemas/
└── memory-v2.schema.json      ← Normative machine contract (~1040 lines)

references/
├── data-model.md              ← Detailed data model reference
├── record-draft.md            ← Draft contract for add/update/supersede
└── provenance.md              ← Evidence and verification rules
```

### Design Principles

- **Zero dependencies beyond stdlib**: the entire toolchain runs on Python 3.9+
  with no pip packages
- **Atomic writes**: files are written via tempfile + `os.replace()`, never
  truncated in place
- **Optimistic concurrency**: record updates require hash confirmation
- **Deterministic identity**: record IDs are SHA-256-derived from keys
- **Canonical JSON**: all hashing uses `sort_keys=True, separators=(",",":")`
- **Single active run**: serialized mutation simplifies reasoning about state
- **Linear history**: supersession chains are acyclic linked lists, not DAGs

---

## Usage Examples

### Query for open tasks

```bash
python scripts/kiroku.py query --dir ./kiroku \
  --type task --status active --sort created_at
```

### Find all records depending on a specific decision

```bash
python scripts/kiroku.py query --dir ./kiroku \
  --relation-type depends_on --relation-target rec_use_postgres
```

### List all roadmap items, latest first

```bash
python scripts/kiroku.py query --dir ./kiroku \
  --type roadmap_item --sort created_at --sort-dir desc
```

### Count verified decisions in scope

```bash
python scripts/kiroku.py query --dir ./kiroku \
  --type decision --status active --scope my-module --count
```

### Get just the IDs of all active constraints

```bash
python scripts/kiroku.py query --dir ./kiroku \
  --type constraint --status active --format ids
```

---

## Quality Bar (for Agents)

1. Do not invent facts, decisions, dates, owners, or evidence.
2. Keep temporary command results as `event` records or source evidence, not
   stable facts.
3. Use concise titles and payloads.
4. Use project terminology exactly where compatibility matters.
5. Prefer explicit uncertainty over false precision.
6. Ensure another agent can answer both *"what is true?"* and *"why do we
   believe it?"* without rereading the full conversation.
7. Distinguish observation from inference in evidence methods.
8. Never convert brainstorming into a decision.
9. Never delete unresolved work during an update — supersede instead.
