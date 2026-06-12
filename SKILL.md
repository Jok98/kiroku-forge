---
name: kiroku-forge
description: Maintain a lightweight Markdown project-memory hub in `kiroku/` for durable project state, architecture, design patterns, decisions, constraints, TODO/DONE/ongoing work, risks, rejected ideas, forbidden directions, and continuation handoffs. Use when project context must persist across agent sessions or be readable by developers. Prefer concise human-readable Markdown as primary memory, minimal metadata, and no canonical JSON unless the user explicitly asks for it.
---

# KirokuForge

KirokuForge maintains a curated Markdown memory hub for a project. The output
is meant to be read directly by developers and future agents.

## Product Boundary

Preserve durable project knowledge:

- current state and next useful action;
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
- Preserve the language and terminology already used by the project memory.

## Hub Files

Create or maintain this folder:

```text
kiroku/
  START_HERE.md
  STATE.md
  ARCHITECTURE.md
  DECISIONS.md
  WORK.md
  CONSTRAINTS.md
  IDEAS.md
  RISKS.md
  LOG.md
```

Read [references/file-contract.md](references/file-contract.md) before creating
a new hub, restructuring an existing hub, or making a broad memory update.
Use the templates in [assets/templates/kiroku](assets/templates/kiroku) when
initializing a project hub.

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
- Operational files describe the present; history is in `LOG.md` or justified
  by an active decision, constraint, risk, or rejected idea.
- No `memory.json`, schema, receipt, hash chain, generated index, or hidden
  canonical store was added unless the user explicitly requested it.

## Operating Workflow

1. Locate the project memory hub. Use `kiroku/` at the project root unless the
   user points to another location.
2. Choose the operating mode.
3. If the hub exists, follow the selective reading policy before opening more
   files.
4. If the hub does not exist and the user asked to create or update memory,
   initialize it from the templates.
5. Inspect the current project evidence needed for the update: code, docs,
   user statements, command results, or existing memory.
6. Decide whether each item is durable memory. Exclude transient progress,
   verbose logs, speculative noise, and implementation minutiae that are not
   reusable.
7. Apply the compression rule to avoid duplicating or bloating the hub.
8. Edit the owning Markdown files directly. Keep the text compact but complete.
9. Add one concise entry to `LOG.md` for meaningful memory updates.
10. Run the final checklist.
11. Finish with a short summary of changed memory files and any uncertainty.

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
- use only these sections: `Mission`, `Current State`, `Next Action`,
  `Hard Constraints`, and `Read Only If Needed`;
- write bullets, not narrative paragraphs;
- include only what a new agent needs before opening another file;
- point to detail files instead of copying their content.

If the user asks for a goal-specific handoff, update `START_HERE.md` and point
to the relevant detailed files instead of duplicating all content.

## Quality Bar

A good KirokuForge update lets a new agent continue the project without asking
for basic context, while still being concise enough that a developer can read
the hub without fighting generated clutter.
