---
name: kiroku-forge
description: Initialize and maintain a lightweight Markdown project-memory hub in `kiroku/`; create or resume task workspaces with roadmap and work status; catch up on one task; onboard a new agent or session to the whole project; and preserve durable architecture, decisions, constraints, risks, progress, and handoffs. Use when project context must persist across sessions, a non-trivial task needs continuation memory, an existing task must be resumed, or a project-wide context refresh is needed. Prefer concise human-readable Markdown as primary memory, minimal metadata, and no canonical JSON unless the user explicitly asks for it.
---

# KirokuForge

KirokuForge maintains a curated Markdown memory hub for a project. The output
is meant to be read directly by developers and agents.

## Product Boundary

Preserve durable project knowledge:

- current state and next useful action;
- multi-repo project context and separate workstream focus when needed;
- main flows, architecture, implementation patterns, and design rationale;
- adopted decisions, active constraints, and forbidden directions;
- TODO, ongoing, blocked, done, and cancelled work;
- risks, open questions, rejected ideas, and important history.

Do not preserve generic conversation summaries, raw transcripts, incidental
tool output, or details that will not help future work.

## Core Rules

- Treat Markdown files under `kiroku/` as the primary memory.
- Keep metadata minimal. Prefer clear headings and explanatory text.
- Make entries self-explanatory: write what is true, why it matters, and what
  it changes.
- Update existing entries instead of appending duplicates.
- Remove or rewrite stale text when newer information supersedes it.
- Separate facts, decisions, proposals, constraints, risks, and tasks.
- Do not convert an idea into a decision unless the user or project evidence
  clearly adopts it.
- Do not create `memory.json`, schemas, receipts, hashes, or generated indexes
  unless the user explicitly asks for a machine-readable layer.
- For a new hub, use the dominant language of the project or the user's
  request; for an existing hub, preserve its language and terminology unless
  the user asks to translate it.

## Hub Files

Create or maintain this folder:

```text
kiroku/
  START_HERE.md
  TRACKS.md            # optional, when multiple workstreams exist
  STATE.md
  ARCHITECTURE.md
  DECISIONS.md
  WORK.md
  CONSTRAINTS.md
  IDEAS.md
  RISKS.md
  LOG.md
  tracks/              # optional, one folder per active workstream
    <track-slug>/
      START_HERE.md
      STATE.md
      ROADMAP.md
      WORK.md
      DECISIONS.md
      RISKS.md
      LOG.md
```

Read [references/file-contract.md](references/file-contract.md) before creating
a new hub, restructuring an existing hub, or making a broad memory update.
Read [references/track-contract.md](references/track-contract.md) before
creating, restructuring, migrating, closing, or broadly updating tracks.
Use the templates in [assets/templates/kiroku](assets/templates/kiroku) when
initializing a project hub.
Use [assets/templates/kiroku/TRACKS.md](assets/templates/kiroku/TRACKS.md) and
[assets/templates/kiroku/tracks/_template](assets/templates/kiroku/tracks/_template)
when adding the optional track layer; `_template` is a source template, not an
active track.
Use `python scripts/init_hub.py <project-root-or-kiroku-dir>` from this skill
when a deterministic template copy is useful. The script refuses to overwrite
standard hub files unless `--overwrite` is passed.
Use `python scripts/init_hub.py <project-root-or-kiroku-dir> --with-tracks`
to add `TRACKS.md` when the optional track layer is needed.
Use `python scripts/init_hub.py <project-root-or-kiroku-dir> --track <slug>`
to scaffold a track from `tracks/_template`; existing standard hub files are
preserved in this additive mode. Existing files inside the named track are also
preserved unless `--overwrite` is explicit, so the helper can add newly required
contract files safely. Complete the scaffold according to the track contract
before treating the task workspace as ready.
Template text is scaffolding: when initializing a non-English hub, translate
headings and placeholder prose into the chosen hub language while preserving
file names and section meanings.

## Operating Modes

Choose one primary mode before reading beyond `START_HERE.md`:

- `init`: inspect a project, create a missing `kiroku/` hub, replace template
  placeholders with verified durable context, and validate the result.
- `start-task`: select an existing matching track or create a task workspace
  with handoff, state, roadmap, work status, and routing metadata.
- `read-task`: catch up on one task without editing memory. Read the selected
  track and only the global context that constrains it.
- `read-project`: onboard a new agent or session to the whole project without
  editing memory. Read global truth and the handoffs of active tracks.
- `update`: edit the hub after project work, decisions, or user corrections.
  Use when the user asks to save, remember, update memory, or invokes
  `$kiroku-forge` after meaningful work.
- `handoff`: tighten `START_HERE.md` for the next agent or a specific goal.
  Keep detail in owner files and link to them.
- `cleanup`: compress, reorganize, or remove stale memory. Read the full hub
  only when cleanup scope requires it.

Treat the legacy name `read` as routing shorthand: use `read-task` when the
request identifies one task and `read-project` when it asks for project-wide
orientation. If the mode is otherwise ambiguous, default to the matching read
mode for questions and `update` for explicit memory-maintenance requests.

## Initialization Workflow

`init` is complete only when the generated hub contains project evidence, not
template prose:

1. Locate the project boundary and inspect the repositories, project docs,
   current state, architecture, constraints, validation paths, and known work
   needed to create a useful base memory.
2. Read `references/file-contract.md`, choose the hub language, and scaffold
   `kiroku/` from the bundled templates.
3. Replace every placeholder with verified durable context. Mark uncertainty
   as unknown; do not invent missing facts or decisions.
4. Populate `START_HERE.md` as the project-wide entrypoint and routing guide.
5. Add `TRACKS.md` only when known tasks or workstreams need independent
   continuation; do not create speculative empty tracks.
6. Run the checker with strict warnings. Do not report initialization complete
   while placeholders, missing completion conditions, or structural warnings
   remain.

## Task Workspace Workflow

Use `start-task` for a non-trivial task that needs a roadmap, milestone
tracking, or continuation across agents or sessions:

1. Read top-level `START_HERE.md` and `TRACKS.md` when present.
2. Match by purpose, issue, branch, repositories, modules, paths, and keywords.
   Reuse one clearly matching track instead of creating a duplicate.
3. If no track matches, create a lowercase hyphenated slug and populate the
   track `START_HERE.md`, `STATE.md`, `ROADMAP.md`, and `WORK.md`; add local
   decisions, risks, and a log only when useful.
4. Add or update the compact routing entry in `TRACKS.md`.
5. Record outcome-oriented milestones in `ROADMAP.md`; keep granular ongoing,
   TODO, blocked, done, and cancelled items in `WORK.md`.
6. Keep the current milestone and next action aligned across `ROADMAP.md`,
   `STATE.md`, `WORK.md`, and the track handoff without copying detailed text.

Do not create a task workspace for a trivial, self-contained operation unless
the user explicitly asks to preserve it.

## Selective Reading

Do not load every file in `kiroku/` by default. Read only what the request
needs:

- Always read `START_HERE.md` first when a hub exists.
- Read `TRACKS.md` when the request may belong to one of several active
  workstreams and the user did not name the exact track.
- Read `tracks/<slug>/START_HERE.md` after selecting a track, before opening
  other files in that track.
- Read `STATE.md` when current status or verified present-tense facts matter.
- Read a track's `ROADMAP.md` when continuing, planning, or assessing milestone
  progress.
- Read `WORK.md` when continuing, planning, or updating tasks.
- Read `DECISIONS.md` and `CONSTRAINTS.md` before changing direction,
  architecture, scope, or product rules.
- Read `ARCHITECTURE.md` before technical implementation changes.
- Read `IDEAS.md` when evaluating proposals, rejected directions, or forbidden
  approaches.
- Read `RISKS.md` when the work touches fragile areas, tradeoffs, or known
  failure modes.
- Read `LOG.md` only when recent memory-update history is relevant.

For `read-task`, read top-level `START_HERE.md`, resolve the track, read its
`START_HERE.md`, `STATE.md`, `ROADMAP.md`, and `WORK.md`, then open only the
local or global decision, constraint, architecture, and risk files needed for
the requested work.

For `read-project`, read top-level `START_HERE.md`, `STATE.md`,
`ARCHITECTURE.md`, `DECISIONS.md`, `CONSTRAINTS.md`, `WORK.md`, `RISKS.md`, and
`TRACKS.md` when present. Then read `START_HERE.md` for every active track and
for paused tracks relevant to current project direction. Do not load every
track detail merely to produce project-wide orientation.

If the user asks for a full memory audit, read all global and track files
deliberately and say that the request requires the complete hub.

## Focus Routing And Tracks

Use one project hub for related repositories, but separate unrelated active
work into tracks when a shared top-level hub would add irrelevant context.

Before reading or writing beyond the top-level `START_HERE.md`, choose a focus:

- `global`: use top-level files for project-wide state, cross-repo architecture,
  shared decisions, constraints, risks, and work that affects multiple tracks.
- `track`: use `tracks/<slug>/` for a specific feature, migration, incident,
  bug family, spike, or discussion that can progress independently.

Choose an existing track when the user names it, when `TRACKS.md` maps the
request to it, or when the prompt, branch, changed paths, issue, repo names, or
keywords clearly match it. Create a new track through `start-task` when the
work is distinct, non-trivial, and needs roadmap or continuation state.

Do not read sibling tracks by default. Open another track only when the user
asks, `TRACKS.md` says the tracks are related, or evidence shows a direct
dependency.

Keep `TRACKS.md` as a compact human-readable index:

- active, paused, and recently closed tracks;
- one-line purpose and current status;
- involved repositories or modules when useful;
- keywords that help future agents route requests;
- path to the track `START_HERE.md`;
- links to related tracks only when they matter.

Promote information from a track to the top-level hub only when it affects the
whole project, multiple repositories, multiple tracks, architecture, shared
constraints, or forbidden directions. Keep local implementation detail inside
the track.

For detailed track lifecycle, promotion, closure, and entry patterns, read
[references/track-contract.md](references/track-contract.md).

## Compression Rule

Before and after every memory update, compress the hub:

- remove or rewrite stale text that no longer represents the project state;
- merge duplicate entries instead of adding another version;
- replace verbose recap with the smallest clear statement;
- keep detail only in the file that owns it;
- move history out of current-state sections unless it explains a live
  decision, constraint, or risk;
- delete transient session notes, command chatter, and implementation noise
  that future work will not reuse.

Ask these questions before writing a new bullet or paragraph:

- Is this still true and useful for future work?
- Is it already stated elsewhere?
- Can it be one sentence instead of a paragraph?
- Does it belong as state, decision, constraint, task, risk, idea, or log?

## Operational State And History

Keep operational files focused on the present:

- `START_HERE.md`, `STATE.md`, and `WORK.md` should describe what is true now
  and what to do next.
- A track's operational files should describe only that track; global
  operational files should not absorb track-specific noise.
- Move chronological history to `LOG.md`.
- Keep history in `DECISIONS.md` only when it explains an active decision.
- Keep history in `CONSTRAINTS.md`, `RISKS.md`, or `IDEAS.md` only when it
  affects future choices.
- Prefer "this is the current rule" over "we previously changed from X to Y"
  in operational files.

## Final Checklist

Before finishing `init`, `start-task`, `update`, `handoff`, or `cleanup`, verify:

- `START_HERE.md` is 25-40 lines when practical and never over 60 lines unless
  the user asked for a fuller handoff.
- Every TODO has a `Completion:` condition.
- Every active task track has a `ROADMAP.md` whose milestones define objective,
  dependencies, validation, completion criteria, and current status.
- Every active decision has a rationale.
- `LOG.md` has at most one concise entry for the memory update.
- New content is not duplicated across owner files.
- Track-specific content stays in its track unless it was intentionally
  promoted to the global hub.
- `TRACKS.md` is concise and points to track detail instead of copying it.
- Operational files describe the present; history is in `LOG.md` or justified
  by an active decision, constraint, risk, or rejected idea.
- No `memory.json`, schema, receipt, hash chain, generated index, or hidden
  canonical store was added unless the user explicitly requested it.
- When practical after `init`, `cleanup`, or broad updates, run
  `python scripts/check_hub.py <project-root-or-kiroku-dir>` from this skill
  to catch missing files, stale placeholders, missing TODO completion
  conditions, missing decision rationales, `START_HERE.md` length drift,
  roadmap structure or status errors, and track routing issues when
  `TRACKS.md` or `tracks/` exist.

## Operating Workflow

1. Locate the project memory hub. Use `kiroku/` at the project root unless the
   user points to another location.
2. Choose one operating mode and the focus: `global` or a specific `track`.
3. If the hub is missing, use `init` before any write mode that requires
   durable memory; do not treat scaffolded placeholders as initialized memory.
4. For task work, use `start-task` to reuse or create the workspace before
   updating it.
5. For reads, follow the `read-task` or `read-project` order and do not edit.
6. If the focus is ambiguous and multiple tracks exist, read `TRACKS.md` and
   ask the user only when routing cannot be inferred safely.
7. Inspect the current project evidence needed for a write: code, docs,
   user statements, command results, or existing memory.
8. Decide whether each item is durable memory. Exclude transient progress,
   verbose logs, speculative noise, and implementation minutiae that are not
   reusable.
9. Apply the compression rule to avoid duplicating or bloating the hub.
10. Edit the owning Markdown files directly. Keep the text compact but complete.
11. Add one concise entry to the relevant `LOG.md` for meaningful memory
    updates.
12. Run the final checklist and the hub checker when its scope matches the
    update.
13. Finish with a short summary of changed memory files and any uncertainty.

## Update Guidance

When updating decisions:

- record the adopted choice, rationale, consequences, and alternatives only
  when useful;
- move replaced decisions to an obsolete/replaced section instead of deleting
  their history when the history matters.

When updating work:

- keep `Ongoing` focused on work currently in flight;
- give TODO items a completion condition;
- give DONE items an outcome, not just a title;
- keep cancelled or blocked work visible only when it affects future choices.

When updating a task roadmap:

- keep milestones outcome-oriented and independently verifiable;
- record status as `pending`, `in_progress`, `completed`, or `blocked`;
- keep at most one milestone `in_progress`;
- update milestone status only from implementation or validation evidence;
- reassess future milestones after each completed milestone.

When updating tracks:

- update `TRACKS.md` only for routing facts, not detailed progress;
- keep track `START_HERE.md` focused on that workstream's next continuation;
- keep `STATE.md`, `ROADMAP.md`, and `WORK.md` aligned by ownership rather than
  duplicating the same progress narrative;
- promote only cross-track or cross-repo conclusions to top-level files;
- close or pause stale tracks instead of keeping them active indefinitely.

When updating constraints and forbidden directions:

- state what the constraint prevents;
- explain why violating it would be harmful;
- keep forbidden ideas separate from merely rejected or deferred ideas.

When updating architecture:

- document flows, boundaries, dependencies, and patterns that guide future
  implementation;
- avoid turning `ARCHITECTURE.md` into an exhaustive codebase map.

## Handoff Behavior

`START_HERE.md` is the standing handoff for the next agent. Keep it strict:

- target 25-40 lines;
- hard cap 60 lines unless the user explicitly asks for a fuller handoff;
- use only these sections, or their direct equivalents in the hub language:
  `Mission`, `Current State`, `Next Action`, `Hard Constraints`, and
  `Read Only If Needed`;
- write bullets, not narrative paragraphs;
- include only what a new agent needs before opening another file;
- point to detail files instead of copying their content.

If the user asks for a goal-specific handoff, update `START_HERE.md` and point
to the relevant detailed files instead of duplicating all content.

For track-specific handoffs, update `tracks/<slug>/START_HERE.md` and ensure
the top-level `TRACKS.md` points to it. Do not copy sibling-track detail into
the handoff.

## Quality Bar

A good KirokuForge update lets a new agent continue the project without asking
for basic context, while still being concise enough that a developer can read
the hub without fighting generated clutter.
