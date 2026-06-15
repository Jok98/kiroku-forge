# KirokuForge File Contract

This contract defines the default `kiroku/` Markdown hub. It is intentionally
small: the text is the memory, not hidden metadata.

## Contents

- Layout
- General Writing Contract
- Reading Policy
- Operating Modes
- Compression Policy
- Operational State And History
- Final Checklist
- File Ownership
- Entry Patterns
- Track Layer

## Layout

The base hub uses the standard top-level files. Multi-repository projects or
parallel workstreams may add a lightweight track layer:

```text
kiroku/
  START_HERE.md
  TRACKS.md            # optional index for multiple active workstreams
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

Use top-level files for global or cross-repo truth. Use `tracks/<slug>/` for a
specific feature, migration, incident, spike, or discussion whose detail would
pollute unrelated work. Read [track-contract.md](track-contract.md) before
creating, restructuring, migrating, closing, or broadly updating tracks. Use
the bundled `assets/templates/kiroku/TRACKS.md` and
`assets/templates/kiroku/tracks/_template/` files when creating the optional
track layer.

## General Writing Contract

- Use stable headings and compact prose.
- Prefer bullets for scannable facts and short paragraphs for rationale.
- Keep entries project-specific and actionable.
- Make status visible in text, for example `Status: active`.
- Use file paths, commands, dates, and module names only when they help future
  work.
- Avoid frontmatter unless the user explicitly wants machine parsing.
- Avoid duplicate explanations across files. Put the detail in one owner file
  and link or name it elsewhere.
- For a new hub, use the dominant language of the project or the user's
  request; for an existing hub, preserve its language and terminology unless
  the user asks to translate it.
- Keep `kiroku/*.md` file names stable. Translate headings and placeholder prose
  only as direct equivalents in the hub language.
- Use lowercase hyphenated track slugs, for example `tax-migration` or
  `goal-proposal-cleanup`.

## Reading Policy

Agents should not read the whole hub by default.

- Start with `START_HERE.md`.
- Open `TRACKS.md` only when several tracks may match the request or the user
  did not name the target track.
- After selecting a track, open `tracks/<slug>/START_HERE.md` before any other
  file in that track.
- Open `STATE.md` for current project status.
- Open `WORK.md` for TODO, ongoing, blocked, done, or planning context.
- Open `DECISIONS.md` and `CONSTRAINTS.md` before changing direction or scope.
- Open `ARCHITECTURE.md` before implementation work.
- Open `IDEAS.md` for proposals, rejected ideas, or forbidden directions.
- Open `RISKS.md` for fragile areas, tradeoffs, or known failure modes.
- Open `LOG.md` only when update history matters.

Do not read sibling tracks by default. Read every file only for explicit
full-memory review, migration, cleanup, or major restructuring.

## Operating Modes

- `read`: answer from existing memory without editing.
- `update`: save durable project state, choices, constraints, work, or risks.
- `handoff`: keep `START_HERE.md` goal-focused and point to detail files.
- `cleanup`: compress stale, duplicated, or misplaced memory.
- `init`: create the default hub from templates.

Use one primary mode per request. If unsure, use `read` for questions and
`update` for explicit memory-maintenance requests.

## Compression Policy

Every update should make the hub at least as clear as it was before.

- Remove stale text when newer state replaces it.
- Merge duplicate notes instead of adding parallel versions.
- Prefer one precise sentence over a recap paragraph.
- Keep history only when it explains an active decision, constraint, risk, or
  rejected idea.
- Keep detail in the owning file and point to it from other files.
- Do not preserve transient session progress, command chatter, or generic
  summaries.

Before adding content, check whether it is still true, useful for future work,
already stated elsewhere, and filed under the right owner.

## Operational State And History

`START_HERE.md`, `STATE.md`, and `WORK.md` are operational files. They should
answer what is true now and what should happen next.

- Put chronological history in `LOG.md`.
- Put rationale and meaningful past alternatives in `DECISIONS.md`.
- Put obsolete or rejected directions in `IDEAS.md` only when they prevent
  repeated discussion.
- Put historical context in constraints or risks only when it still affects
  future work.
- Rewrite operational text into current-tense rules instead of preserving a
  change narrative.

## Final Checklist

Before finishing a memory write, verify:

- `START_HERE.md` stays within its line budget.
- TODO items have `Completion:` conditions.
- Active decisions have rationale.
- `LOG.md` has no more than one concise entry for the update.
- New content is not duplicated across owner files.
- Track-specific content stays in the track unless intentionally promoted.
- `TRACKS.md` remains an index, not a copied summary of all track details.
- Operational files stay present-tense.
- No hidden canonical store or generated machine layer was added without an
  explicit user request.

The optional checker `scripts/check_hub.py` validates the default contract
mechanically: required files, template placeholders, `START_HERE.md` length,
TODO `Completion:` conditions, active decision rationales, and track routing
when `TRACKS.md` or `tracks/` exist. Treat checker errors as blocking; inspect
warnings before deciding whether the hub is good enough for the current update.

The optional initializer `scripts/init_hub.py` copies the bundled templates
into a project `kiroku/` hub. It refuses to overwrite standard hub files unless
`--overwrite` is passed. Use `--with-tracks` to add `TRACKS.md`, and
`--track <slug>` to add a track from `tracks/_template/` while preserving
existing standard hub files.

## File Ownership

`START_HERE.md`

- First file for a new agent.
- Target 25-40 lines; hard cap 60 lines unless the user asks for a fuller
  handoff.
- Use only these sections, or their direct equivalents in the hub language:
  `Mission`, `Current State`, `Next Action`, `Hard Constraints`, and
  `Read Only If Needed`.
- Contains only what a new agent needs before opening another file.
- Link to details instead of copying them.

`TRACKS.md`

- Optional index for hubs with multiple active, paused, or recently closed
  workstreams.
- Contains routing facts only: status, one-line purpose, repositories/modules,
  keywords, path to the track handoff, and related tracks when useful.
- Does not duplicate track progress, decisions, or risk detail.
- Keeps closed tracks visible only while their outcome affects future routing.
- Detailed lifecycle and entry rules live in [track-contract.md](track-contract.md).

`STATE.md`

- Current project status, what works, what is incomplete, recent verified
  facts, and open questions that shape next work.
- Use this for the present tense state of the project.
- In a track, limit state to that workstream.

`ARCHITECTURE.md`

- Main flows, module boundaries, design patterns, integration points, and
  important implementation details.
- Use this for knowledge that guides future code changes.

`DECISIONS.md`

- Adopted choices and their rationale.
- Include consequences and alternatives when they explain future constraints.
- Keep replaced decisions if their history prevents repeating old reasoning.
- Promote track decisions to the top-level file only when they affect the
  project, multiple repositories, multiple tracks, or shared architecture.

`WORK.md`

- Ongoing, TODO, blocked, done, and cancelled work.
- Every TODO should have a completion condition.
- Every DONE item should state the outcome.
- Top-level work should be global or cross-track; track work belongs under
  `tracks/<slug>/WORK.md`.

`CONSTRAINTS.md`

- Active constraints, out-of-scope boundaries, forbidden changes, and things
  that must not be broken.
- A constraint should say what it prevents and why.

`IDEAS.md`

- Open, deferred, rejected, and forbidden ideas.
- Rejected ideas should include the rejection reason.
- Forbidden ideas should explain the failure mode or project rule they violate.

`RISKS.md`

- Open risks, mitigations, accepted risks, and closed risks that still matter.
- Keep risks practical: condition, impact, mitigation or signal to watch.

`LOG.md`

- Short history of meaningful memory updates.
- Do not log every command or every small edit.
- Track logs describe only that track; top-level logs describe global memory
  changes or track lifecycle changes.

`tracks/<slug>/`

- Optional workstream folder with its own compact handoff and owner files.
- Use when work can progress independently from other active work.
- Keep local implementation detail here unless it becomes global project memory.
- Close or pause stale tracks instead of leaving them active indefinitely.
- Use [track-contract.md](track-contract.md) for routing, lifecycle, promotion,
  closure, and track-specific entry patterns.

## Entry Patterns

Decision:

```md
### Decision: Short name

Status: active
Area: module-or-topic

Decision:
State the adopted choice.

Rationale:
Explain why this choice was made.

Consequences:
- Consequence that affects future work.
- Tradeoff or limitation if relevant.
```

Task:

```md
### Task: Short name

Status: todo
Completion:
State the condition that makes the task done.

Notes:
- Context needed to continue.
```

Constraint:

```md
### Constraint: Short name

Status: active

Rule:
State the constraint.

Why:
Explain what breaks or becomes risky if ignored.
```

Rejected idea:

```md
### Rejected: Short name

Reason:
Explain why the idea was rejected.

Keep in mind:
State when, if ever, this should be reconsidered.
```

## Track Layer

For track index entries, track handoff skeletons, lifecycle status values,
promotion rules, closure rules, and track-specific reading order, use
[track-contract.md](track-contract.md).
