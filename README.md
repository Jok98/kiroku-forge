# KirokuForge

KirokuForge is an agent skill for maintaining a Markdown project memory hub
with a local SQLite index for search, relationship navigation, and focused
context. It keeps durable project context readable by both developers and
future agent sessions: current state, architecture, decisions, constraints,
workstreams, TODOs, risks, rejected ideas, and handoffs.

The goal is not to archive conversations. The goal is to preserve the minimum
useful project knowledge needed to continue work without rediscovering the same
context every session.

## What It Creates

By default, KirokuForge maintains a `kiroku/` folder inside a project:

```text
kiroku/
  START_HERE.md
  TRACKS.md            # optional, when task routing is needed
  STATE.md
  ARCHITECTURE.md
  DECISIONS.md
  WORK.md
  CONSTRAINTS.md
  IDEAS.md
  RISKS.md
  LOG.md
  memory.sqlite        # derived after Markdown curation and validation
  tracks/              # optional, one workspace per durable task
    <track-slug>/
      START_HERE.md
      STATE.md
      ROADMAP.md
      WORK.md
      DECISIONS.md
      RISKS.md
      LOG.md
```

Top-level files hold global project truth. Track folders hold focused memory
for a specific feature, migration, incident, spike, or long-running discussion.
This makes one shared memory hub practical even for projects made of several
related repositories.

## How It Works

Markdown is the authoritative memory. Each hub can carry one `memory.sqlite`
derived from its Markdown, using SQLite FTS5 for text search and explicit links
for graph navigation. The database can travel with the project and be rebuilt
from source. It requires no Redis service, embeddings, or external Python package.

One agent reads the last published database throughout a task. At a task/milestone
boundary or an explicit handoff, it curates all Markdown changes, validates them,
and publishes one checkpoint. Queries use only SQLite, without scanning Markdown
or running a full integrity audit. `status` performs that audit explicitly after
external source changes or suspected damage. Legacy bootstrap and recovery can
read Markdown directly; ordinary reads do not silently switch to that path.

The skill follows a selective reading model through database document IDs:

- read `START_HERE.md` first;
- read `TRACKS.md` only when a request may belong to a specific workstream;
- read a track `START_HERE.md` before opening that track's detailed files;
- read only the owner files needed for the task.

`read-task` resumes one task from its state, roadmap, and work files.
`read-project` gives a new agent or session the global project context plus the
handoffs of active tracks without loading every task detail.

This selects focused memory without loading every task's details.
The `context` command can assemble a track's required files plus selected search
and relationship results within a budget covering its entire compact JSON output,
including metadata and the final newline. It reports selection reasons
and omissions, and fails if the required files cannot fit. Neither graph links
nor a current index prove that memory still agrees with the project's code.

## Core Files

- `START_HERE.md`: strict handoff for the next agent.
- `TRACKS.md`: compact routing index for active, paused, or recently closed
  workstreams.
- `STATE.md`: current project facts and recently verified status.
- Track `ROADMAP.md`: milestone objectives, dependencies, validation, and
  completion criteria.
- `ARCHITECTURE.md`: flows, boundaries, patterns, and integration points.
- `DECISIONS.md`: adopted decisions with rationale and consequences.
- `WORK.md`: ongoing work, TODOs, blocked items, done items, and cancelled work.
- `CONSTRAINTS.md`: active constraints, out-of-scope boundaries, and forbidden
  changes.
- `IDEAS.md`: open, deferred, rejected, and forbidden ideas.
- `RISKS.md`: open risks, accepted risks, mitigations, and closed risks that
  still matter.
- `LOG.md`: concise history of meaningful memory updates.

## Workstreams

Use task tracks when pieces of work share the same project but should not all
be loaded together. A track is useful when the work:

- can progress independently;
- has durable context likely to be resumed later;
- touches a specific feature, migration, bug family, incident, or spike;
- would pollute top-level memory if all details were stored globally.

Information should be promoted from a track to the top-level hub only when it
affects the whole project, multiple repositories, shared architecture, shared
constraints, or forbidden directions.

## Operating Modes

The skill supports these modes:

- `init`: inspect a project, scaffold its hub, replace placeholders with
  verified context, and validate strict readiness.
- `start-task`: reuse or create a task workspace with state, roadmap, work, and
  routing metadata.
- `read-task`: catch up on one task without editing memory.
- `read-project`: onboard to global project truth and active-track handoffs.
- `update`: save durable project state, decisions, constraints, tasks, or risks.
- `handoff`: tighten `START_HERE.md` for the next agent or a specific goal.
- `cleanup`: compress stale, duplicated, or misplaced memory.

Generic `read` remains shorthand resolved to `read-task` or `read-project` from
the request scope.

## Commands

The helpers use Python 3.9+ and the standard library. The memory index also
requires SQLite FTS5, available in usual Python SQLite builds; an unavailable
extension produces an explicit error requiring runtime recovery.

Scaffold a hub before the agent fills verified project context:

```bash
python scripts/init_hub.py <project-root-or-kiroku-dir>
```

Scaffold a hub with track support:

```bash
python scripts/init_hub.py <project-root-or-kiroku-dir> --with-tracks
```

Add a task track or safely complete missing files in an existing track:

```bash
python scripts/init_hub.py <project-root-or-kiroku-dir> --track <track-slug>
```

Validate a hub:

```bash
python scripts/check_hub.py <project-root-or-kiroku-dir>
```

The helpers recognize a directory named `kiroku` as the hub. For an explicitly
selected custom hub directory, add `--hub-dir`; an unrelated `START_HERE.md`
does not change where the helpers operate. Existing custom hubs that previously
relied on that filename heuristic now need the flag.

For an index with translated lifecycle headings, add a track with
`--track-section "Attivi"` (using the exact existing heading text). The helper
rejects an absent or ambiguous destination section before writing files.

Handoff targets are advisory: 25-40 lines globally and 20-35 per track. The
checker enforces caps of 60 and 50 respectively. If the user explicitly asks
for a longer handoff, use `--allow-long-handoff START_HERE.md` or the relevant
`tracks/<slug>/START_HERE.md` path; the exception covers only that file's length.

The checker catches missing files, stale template placeholders, TODOs without
completion conditions, active decisions without rationale, `START_HERE.md`
length drift, track routing issues, invalid roadmap fields or statuses, and
multiple milestones marked `in_progress`.
It recognizes the bundled English placeholders; translated scaffold text,
factual accuracy, and semantic consistency still require agent review. Keep
technical field labels and status values unchanged when translating a hub.

After all checkpoint Markdown edits and validation, publish the database once:

```bash
python scripts/memory.py checkpoint <project-root>
```

`build` remains an alias for `checkpoint`. Search and navigate the published
snapshot without reading source files or changing anything:

```bash
python scripts/memory.py search <project-root> "handoff validation" --limit 5
python scripts/memory.py entries <project-root> --type decision --status active
python scripts/memory.py show <project-root> <node-id>
python scripts/memory.py related <project-root> <node-id> --depth 2 --limit 10
python scripts/memory.py context <project-root> --track <track-slug> --max-chars 20000
```

All `memory.py` commands return JSON and accept `--hub-dir` for custom hubs.
`context` uses format version 2: `--max-chars` counts the complete serialized
response (default 16000, minimum 256), `used_chars` reports its exact size, and
`omitted_count` summarizes excluded candidates. Required files are returned once
and intact, or a bounded `budget_exceeded` response reports the minimum needed.

Decisions and constraints can be stored as structured Markdown entries with
stable IDs, explicit types, validated fields, and declared relationships. New
templates include the markers; replace their placeholder IDs during curation.
`entries` lists typed records and `show` retrieves each complete entry and its
fields. Existing untagged Markdown remains readable. See the
[structured memory contract](references/structured-memory.md) for the format;
the database is still rebuilt from Markdown and is never edited independently.

For guided writes, `memory.py add` creates a tagged entry in an explicitly
selected owner file and section; `memory.py update` patches one by stable ID.
Both accept JSON from a file or stdin and support `--dry-run` diffs. They validate
the proposed records and return `saved` without touching SQLite. Complete all
edits, then use `checkpoint` once to make them visible to readers. See
[guided writes](references/guided-writes.md) for payloads and recovery if publication
fails. Pending Markdown and the previous published snapshot remain separate.

`status` explicitly audits source correspondence and database integrity, reporting
`ready`, `missing`, `stale`, or `invalid`. It is not required before each query or
immediately after a successful checkpoint. Run it after known manual memory edits,
checkout/merge, a restored tree, or suspected corruption before relying on that
snapshot for the changed tree. Queries themselves do not detect external edits.
An unchanged checkpoint does not rewrite the database. When committing is authorized, version it
with its source Markdown; resolve a binary conflict by rebuilding after resolving
the Markdown. See the [memory index contract](references/memory-index.md) for
query options, provenance, source exclusions, and context limits.

## Example Prompts

```text
$kiroku-forge initialize memory for this project
```

```text
$kiroku-forge start a task workspace for the tax migration
```

```text
$kiroku-forge catch me up on the tax migration task without editing memory
```

```text
$kiroku-forge onboard this new session to the whole project
```

```text
$kiroku-forge update the task memory after this milestone
```

```text
$kiroku-forge clean up stale memory and keep only durable project facts
```

## Design Principles

- Keep Markdown human-readable and authoritative.
- Keep the SQLite index derived and rebuildable; edit the source Markdown.
- Prefer concise, self-explanatory entries over generated summaries.
- Update or rewrite existing entries instead of appending duplicates.
- Keep operational state current; move meaningful history to `LOG.md`.
- Keep workstream-specific detail inside the owning track.
- Give every TODO a completion condition.
- Give every active decision a rationale.
- Do not preserve raw transcripts, generic recaps, command chatter, or
  implementation noise that future work will not reuse.

## Skill Layout

```text
kiroku-forge/
  SKILL.md
  agents/openai.yaml
  references/
    file-contract.md
    track-contract.md
    memory-index.md
    structured-memory.md
    guided-writes.md
  scripts/
    init_hub.py
    check_hub.py
    memory.py
    memory_store.py
    structured_memory.py
    memory_edit.py
    memory_writer.py
  tests/
    test_context.py
    test_checkpoint.py
  assets/templates/kiroku/
```

`SKILL.md` contains the agent-facing operating instructions. The reference files
define file, track, and index contracts. The scripts provide scaffolding,
structural validation, indexing, and context retrieval. The agent-led `init`
workflow turns the scaffold into verified project memory before building its
index; templates alone are never a completed hub.

Run the context-budget and checkpoint regression suites with the standard library:

```bash
python -B -m unittest discover -s tests -v
```
