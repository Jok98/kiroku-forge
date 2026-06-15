# KirokuForge Track Contract

This contract defines the optional track layer for projects where one shared
hub covers several repositories or several parallel workstreams.

## Contents

- Purpose
- When To Use A Track
- Layout
- Focus Routing
- TRACKS.md Contract
- Track File Ownership
- Lifecycle
- Promotion Rules
- Reading Rules
- Update Rules
- Compression And Closure
- Entry Patterns

## Purpose

A track isolates one durable stream of work inside the same project hub.

Use tracks to keep one shared memory for cross-repository truth while avoiding
irrelevant context when an agent is working on only one problem.

Top-level files remain the source for global project truth. Track files hold
local state, work, decisions, risks, and handoff context for one workstream.

## When To Use A Track

Create or use a track when the work:

- can progress independently from other active work;
- has enough durable context that it will likely be resumed later;
- touches a specific feature, migration, bug family, incident, spike, or
  discussion;
- would pollute top-level memory if every detail were stored globally.

Do not create a track for a short-lived task, generic conversation recap,
single command result, or detail that belongs directly in a global decision,
constraint, or architecture note.

## Layout

```text
kiroku/
  TRACKS.md
  tracks/
    <track-slug>/
      START_HERE.md
      STATE.md
      WORK.md
      DECISIONS.md
      RISKS.md
      LOG.md
```

Use lowercase hyphenated slugs. Prefer domain names that users and agents will
recognize, for example `tax-migration`, `goal-proposal-cleanup`, or
`auth-refresh`.

Track folders may omit files that are not useful yet, but every active track
should have `START_HERE.md`, `STATE.md`, and `WORK.md`.

Bundled templates live under `assets/templates/kiroku/`:

- `TRACKS.md` initializes the top-level track index.
- `tracks/_template/` initializes a new track folder.

Copy `_template` to a concrete lowercase hyphenated slug and replace all
placeholder prose. Do not leave `_template` listed as an active track.
Prefer `python scripts/init_hub.py <project-root-or-kiroku-dir> --track <slug>`
when creating track files from this skill.

## Focus Routing

Before opening detailed memory, choose one focus:

- `global`: use top-level files for project-wide state, shared architecture,
  cross-repo decisions, shared constraints, global risks, and work that affects
  several tracks.
- `track`: use `tracks/<slug>/` for workstream-specific state, tasks,
  decisions, risks, and handoff.

Select a track when the user names it, `TRACKS.md` maps the request to it, or
the prompt, branch, changed paths, issue, repository names, modules, or
keywords clearly match it.

Ask the user only when several active tracks could match and routing cannot be
inferred safely.

## TRACKS.md Contract

`TRACKS.md` is a compact routing index. It should not become a summary of every
track.

Keep each entry short and readable:

- status: `active`, `paused`, `closed`, or `candidate`;
- one-line purpose;
- repositories, modules, or areas when useful;
- keywords that help future agents route requests;
- path to the track handoff;
- related tracks only when the relationship affects routing.

Closed tracks should remain listed only while their outcome, replaced decision,
or warning helps future routing. Otherwise remove or archive the entry during
cleanup.

## Track File Ownership

`tracks/<slug>/START_HERE.md`

- First file for the track.
- Target 20-35 lines; tolerate up to 50 only for delicate work.
- Use the same section meanings as the global handoff: `Mission`,
  `Current State`, `Next Action`, `Hard Constraints`, and `Read Only If Needed`.
- Include only what an agent needs before opening another track file.

`tracks/<slug>/STATE.md`

- Current state for this track only.
- Verified facts, current scope, known incomplete work, and questions that
  affect this track.

`tracks/<slug>/WORK.md`

- Ongoing, TODO, blocked, done, and cancelled work for this track.
- Every TODO has a `Completion:` condition.
- Done items state outcome, not just activity.

`tracks/<slug>/DECISIONS.md`

- Decisions local to this track.
- Active decisions need rationale.
- Promote decisions to top-level `DECISIONS.md` only when they affect the wider
  project.

`tracks/<slug>/RISKS.md`

- Risks local to this track.
- Include condition, impact, mitigation, or signal to watch.

`tracks/<slug>/LOG.md`

- Concise history of meaningful track memory updates.
- Do not log command chatter or every small edit.

## Lifecycle

Use these statuses in `TRACKS.md`:

- `candidate`: possible track, not enough durable context yet.
- `active`: current workstream likely to be resumed.
- `paused`: valid workstream, intentionally not current.
- `closed`: workstream completed, cancelled, or absorbed elsewhere.

Close or pause stale tracks during cleanup. Do not leave old tracks active just
because their files still exist.

## Promotion Rules

Promote information from a track to top-level files when it:

- affects multiple repositories or multiple tracks;
- changes shared architecture, product direction, or implementation patterns;
- creates a constraint or forbidden direction for the wider project;
- closes a risk that future agents must know before choosing direction;
- changes the global project state or next cross-track work.

Do not promote local task progress, implementation minutiae, exploratory notes,
or decisions that only matter inside the track.

When promoting, summarize globally and keep detailed context in the track.

## Reading Rules

For track work:

1. Read top-level `START_HERE.md`.
2. Read `TRACKS.md` only if the target track is not explicit.
3. Read `tracks/<slug>/START_HERE.md`.
4. Read only the track files needed for the request.
5. Read top-level `DECISIONS.md`, `CONSTRAINTS.md`, or `ARCHITECTURE.md` only
   when the track touches shared direction, constraints, or design.

Do not read sibling tracks unless the user asks, `TRACKS.md` marks them as
related, or evidence shows a direct dependency.

## Update Rules

When updating a track:

- update `TRACKS.md` only for routing facts and lifecycle changes;
- put current status in the track `STATE.md`;
- put next actions and TODOs in the track `WORK.md`;
- put local adopted choices in the track `DECISIONS.md`;
- put fragile areas in the track `RISKS.md`;
- add at most one concise entry to the track `LOG.md`;
- promote only wider conclusions to the top-level hub.

If the user asks to update memory after broad project work, update both the
track and top-level files only when both changed materially.

## Compression And Closure

Before finishing a track update:

- remove duplicated text between global files and track files;
- replace stale progress with current state;
- move history out of `START_HERE.md`, `STATE.md`, and `WORK.md` unless it
  explains current action;
- close completed TODOs with outcomes;
- pause or close tracks that are no longer active;
- ensure `TRACKS.md` points to the right handoff and does not copy detail.
- run `python scripts/check_hub.py <project-root-or-kiroku-dir>` when practical.

When closing a track, preserve only:

- final outcome;
- remaining follow-up if any;
- decisions or constraints that still matter;
- risks that remain open or intentionally accepted;
- links or paths needed to understand the closure.

## Entry Patterns

Track index entry:

```md
### track-slug

Status: active
Purpose: One-line description of the workstream.
Repos: repo-a, repo-b
Areas: module-or-domain names when useful
Keywords: short terms that help route future requests
Read: tracks/track-slug/START_HERE.md
Related: other-track-slug only when useful
```

Track handoff skeleton:

```md
# Start Here

## Mission

- State the workstream goal.

## Current State

- State what is true now for this track.

## Next Action

- Name the next concrete step.

## Hard Constraints

- List only constraints that affect this track.

## Read Only If Needed

- Point to track detail files and required global files.
```
