# KirokuForge Track Contract

This contract owns the track index, lifecycle, roadmaps, promotion, and closure.
[SKILL.md](../SKILL.md) owns activation, focus selection, reading order, and the
write workflow. The [file contract](file-contract.md) owns file responsibilities,
required files, language, entry syntax, handoffs, and helper commands.

A track isolates an independently resumable feature, migration, incident,
spike, bug family, or discussion inside the shared project hub. Global files
retain shared context; detailed local work belongs to its track.

## Track Index

`TRACKS.md` is a compact routing index, not a copied summary of work, decisions,
or risks. Keep each entry's purpose to one line, add useful repository/module
names and keywords, and link related tracks only when that relationship affects
routing. Change entries only for routing facts or lifecycle changes.

Each entry uses a unique lowercase hyphenated slug as its level-three heading
and has an explicit `Status:`. Every track folder has a matching entry and
retains the [required workspace files](file-contract.md#layout), regardless of
lifecycle status. `_template` is a source scaffold, not an indexed track.

Only a `candidate` entry may omit its folder and `Read:` until a workspace is
created. If a candidate already has a folder, the normal file and routing
requirements apply. Other statuses require an existing workspace.

For an existing workspace, `Read:` must resolve to its actual local
`tracks/<slug>/START_HERE.md` file. A similar name or a URL containing that text
is insufficient. Accepted forms include:

```md
Read: tracks/tax-migration/START_HERE.md
Read: `tracks/tax-migration/START_HERE.md`
Read: [Task handoff](tracks/tax-migration/START_HERE.md)
```

Lifecycle section headings may use the hub language; field labels and status
values remain invariant. See [helper commands](file-contract.md#helper-commands)
for insertion into a translated index without creating duplicate sections.

Example entry:

```md
### tax-migration

Status: active
Purpose: Migrate tax calculation while preserving existing invoice behavior.
Repos: billing-service
Areas: tax calculation, invoicing
Keywords: tax, migration, invoice
Read: tracks/tax-migration/START_HERE.md
Related: invoice-rounding
```

Omit optional context fields when they add no routing value. The example is a
shape to adapt, not authorization to create the named workstream.

The [derived memory graph](memory-index.md) follows explicit `Read:` targets,
`Related:` slugs, and local Markdown links. Shared keywords do not create a
relationship. Keep routing references accurate in Markdown; rebuilding the
database does not decide which tracks are related.

## Lifecycle

Use these exact values in the index:

| Status | Meaning |
| --- | --- |
| `candidate` | Possible workstream without enough durable context yet. |
| `active` | Current workstream likely to be resumed. |
| `paused` | Valid workstream intentionally not current. |
| `closed` | Completed, cancelled, or absorbed workstream. |

Pause or close a stale track when the authorized update or cleanup includes
its lifecycle. Existing files alone do not make a track active. Keep a closed
entry only while its outcome, replaced decision, or warning helps routing.
When later removing or archiving it during cleanup, keep the index and folder
set coherent; leaving an unindexed folder violates the contract.

## Roadmap Contract

Every existing track has `ROADMAP.md` with at least one milestone. Use ordered,
outcome-oriented milestones that can be verified independently. Give each a
stable unique ID such as `M-01`, preserving it while the milestone is relevant.
Every level-three heading in this file must follow `### M-01: Short outcome`;
put non-milestone notes under another heading level or in the owning file.

Each milestone has a non-empty `Status:` and every field shown below. Valid
statuses are `pending`, `in_progress`, `completed`, and `blocked`. At most one
milestone is `in_progress` in a track. Use `None` or `None known` when an absence
of dependencies or risks is supported, rather than leaving required fields empty.

```md
### M-01: Short outcome

Status: pending

Objective:
State the outcome this milestone must achieve.

Scope:
- State what is included.

Expected artifacts:
- Name the files, modules, or deliverables.

Dependencies:
- State prerequisites or `None`.

Validation:
- State the command, review, or evidence required.

Completion criteria:
- State the evidence that proves completion.

Risks:
- State material risks or `None known`.
```

Change milestone status only from implementation or validation evidence. Mark
completion only when the criteria are satisfied by current evidence. After each
completed milestone, compare results with the roadmap, reassess remaining work,
and record any material addition, removal, reordering, or scope change.

Keep the current milestone and next action aligned with track `STATE.md`,
`WORK.md`, and `START_HERE.md` without copying milestone definitions. The
roadmap owns the current milestone plan; granular tasks remain in `WORK.md`
and chronological reassessment history belongs in `LOG.md`.

Explicit `M-xx` references in a milestone's `Dependencies:` field can be followed
in the memory graph within that roadmap. They record the stated dependency,
not evidence that its prerequisites or completion criteria have been satisfied.

## Promotion And Closure

Promote a local conclusion to the global owner only when it:

- affects multiple repositories or tracks;
- changes shared architecture, product direction, or implementation patterns;
- creates a shared constraint or forbidden direction;
- closes a risk future agents must understand before choosing direction; or
- changes global state or the next cross-track action.

Summarize the wider implication globally and keep detailed context in the
track. Local progress, implementation minutiae, exploratory notes, and choices
that matter only to the track do not qualify. Update both levels only when
both changed materially.

When closing a track, preserve its final outcome, final milestone outcomes or
remaining roadmap, follow-up, still-relevant decisions and constraints, open
or accepted risks, and the paths needed to understand closure. Resolve or
transfer remaining work explicitly instead of hiding it behind a closed
status. Retained track folders still follow the required-file contract.
