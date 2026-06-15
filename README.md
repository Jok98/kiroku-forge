# KirokuForge

KirokuForge is an agent skill for maintaining a Markdown-first project memory
hub. It keeps durable project context readable by both developers and future
agent sessions: current state, architecture, decisions, constraints, detailed
workstreams, TODOs, risks, rejected ideas, forbidden directions, and handoffs.

The goal is not to archive conversations. The goal is to preserve the minimum
useful project knowledge needed to continue work without rediscovering the same
context every session.

## What It Creates

By default, KirokuForge maintains a `kiroku/` folder inside a project:

```text
kiroku/
  START_HERE.md
  TRACKS.md
  STATE.md
  ARCHITECTURE.md
  DECISIONS.md
  WORK.md
  CONSTRAINTS.md
  IDEAS.md
  RISKS.md
  LOG.md
  tracks/
    <track-slug>/
      START_HERE.md
      STATE.md
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

KirokuForge uses Markdown as the primary memory. There is no canonical
`memory.json`, generated index, receipt store, hash chain, or hidden machine
layer unless the user explicitly asks for one.

The skill follows a selective reading model:

- read `START_HERE.md` first;
- read `TRACKS.md` only when a request may belong to a specific workstream;
- read a track `START_HERE.md` before opening that track's detailed files;
- read only the owner files needed for the task.

This keeps agent context small while preserving enough detail for future work.

## Core Files

- `START_HERE.md`: strict handoff for the next agent.
- `TRACKS.md`: compact routing index for active, paused, or recently closed
  workstreams.
- `STATE.md`: current project facts and recently verified status.
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

Use tracks when multiple pieces of work share the same project but should not
all be loaded together. A track is useful when the work:

- can progress independently;
- has durable context likely to be resumed later;
- touches a specific feature, migration, bug family, incident, or spike;
- would pollute top-level memory if all details were stored globally.

Information should be promoted from a track to the top-level hub only when it
affects the whole project, multiple repositories, shared architecture, shared
constraints, or forbidden directions.

## Operating Modes

The skill supports these modes:

- `read`: answer from the hub without editing it.
- `update`: save durable project state, decisions, constraints, tasks, or risks.
- `handoff`: tighten `START_HERE.md` for the next agent or a specific goal.
- `cleanup`: compress stale, duplicated, or misplaced memory.
- `init`: create a missing `kiroku/` hub from templates.

If the mode is ambiguous, KirokuForge treats questions as `read` and explicit
memory maintenance requests as `update`.

## Commands

Initialize a hub:

```bash
python scripts/init_hub.py <project-root-or-kiroku-dir>
```

Initialize a hub with track support:

```bash
python scripts/init_hub.py <project-root-or-kiroku-dir> --with-tracks
```

Add a workstream track:

```bash
python scripts/init_hub.py <project-root-or-kiroku-dir> --track <track-slug>
```

Validate a hub:

```bash
python scripts/check_hub.py <project-root-or-kiroku-dir>
```

The checker catches missing files, stale template placeholders, TODOs without
completion conditions, active decisions without rationale, `START_HERE.md`
length drift, and track routing issues.

## Example Prompts

```text
$kiroku-forge initialize memory for this project
```

```text
$kiroku-forge update the memory after this refactor
```

```text
$kiroku-forge create a track for the tax migration workstream
```

```text
$kiroku-forge what should the next agent read before continuing Product migration?
```

```text
$kiroku-forge clean up stale memory and keep only durable project facts
```

## Design Principles

- Keep Markdown human-readable and authoritative.
- Keep metadata minimal.
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
  scripts/
    init_hub.py
    check_hub.py
  assets/templates/kiroku/
```

`SKILL.md` contains the agent-facing operating instructions. The reference files
define the file and track contracts. The scripts provide deterministic
initialization and validation. The templates are copied into projects when a
new memory hub or track is created.
