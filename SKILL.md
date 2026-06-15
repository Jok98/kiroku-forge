---
name: kiroku-forge
description: Maintain a lightweight Markdown project-memory hub in `kiroku/` for durable project state, multi-repo context, workstream tracks, architecture, design patterns, decisions, constraints, TODO/DONE/ongoing work, risks, rejected ideas, forbidden directions, and continuation handoffs. Use when project context must persist across agent sessions or be readable by developers. Prefer concise human-readable Markdown as primary memory, minimal metadata, and no canonical JSON unless the user explicitly asks for it.
---

# KirokuForge

KirokuForge maintains a curated Markdown memory hub for a project. The output
is meant to be read directly by developers and future agents.

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
to create a track from `tracks/_template`; existing standard hub files are
preserved in this additive mode.
Template text is scaffolding: when initializing a non-English hub, translate
headings and placeholder prose into the chosen hub language while preserving
file names and section meanings.

## Operating Modes

Choose one primary mode before reading beyond `START_HERE.md`:

- `read`: answer from the hub without editing it. Use when the user asks what
  is true, what happened, or what to do next.
- `update`: edit the hub after project work, decisions, or user corrections.
  Use when the user asks to save, remember, update memory, or invokes
  `$kiroku-forge` after meaningful work.
- `handoff`: tighten `START_HERE.md` for the next agent or a specific goal.
  Keep detail in owner files and link to them.
- `cleanup`: compress, reorganize, or remove stale memory. Read the full hub
  only when cleanup scope requires it.
- `init`: create a missing `kiroku/` hub from templates, then fill only the
  durable project context available.

If the mode is ambiguous, default to `read` for questions and `update` for
explicit memory-maintenance requests.

## Selective Reading

Do not load every file in `kiroku/` by default. Read only what the request
needs:

- Always read `START_HERE.md` first when a hub exists.
- Read `TRACKS.md` when the request may belong to one of several active
  workstreams and the user did not name the exact track.
- Read `tracks/<slug>/START_HERE.md` after selecting a track, before opening
  other files in that track.
- Read `STATE.md` when current status or verified present-tense facts matter.
- Read `WORK.md` when continuing, planning, or updating tasks.
- Read `DECISIONS.md` and `CONSTRAINTS.md` before changing direction,
  architecture, scope, or product rules.
- Read `ARCHITECTURE.md` before technical implementation changes.
- Read `IDEAS.md` when evaluating proposals, rejected directions, or forbidden
  approaches.
- Read `RISKS.md` when the work touches fragile areas, tradeoffs, or known
  failure modes.
- Read `LOG.md` only when recent memory-update history is relevant.

If the user asks for a full memory review, read all files deliberately and say
that the request requires the full hub.

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
keywords clearly match it. Create a new track only when the work is durable,
distinct from existing tracks, and likely to be resumed later.

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

Before finishing `update`, `handoff`, `cleanup`, or `init`, verify:

- `START_HERE.md` is 25-40 lines when practical and never over 60 lines unless
  the user asked for a fuller handoff.
- Every TODO has a `Completion:` condition.
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
  conditions, missing decision rationales, `START_HERE.md` length drift, and
  track routing issues when `TRACKS.md` or `tracks/` exist.

## Operating Workflow

1. Locate the project memory hub. Use `kiroku/` at the project root unless the
   user points to another location.
2. Choose the operating mode.
3. Choose the focus: `global` or a specific `track`.
4. If the hub exists, follow the selective reading policy before opening more
   files.
5. If the hub does not exist and the user asked to create or update memory,
   initialize it from the templates.
6. If the focus is ambiguous and multiple tracks exist, read `TRACKS.md` and
   ask the user only when routing cannot be inferred safely.
7. Inspect the current project evidence needed for the update: code, docs,
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

When updating tracks:

- update `TRACKS.md` only for routing facts, not detailed progress;
- keep track `START_HERE.md` focused on that workstream's next continuation;
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
