---
name: kiroku-forge
description: Maintain curated Markdown project memory in kiroku/; initialize verified hubs, create or resume durable task workspaces, onboard sessions, and update focused handoffs. Use when project context must persist across sessions, an existing task needs continuation, or the user requests memory maintenance. Keep read-only work non-mutating and avoid creating memory for trivial one-shot tasks unless requested.
---

# KirokuForge

Maintain project knowledge that helps developers and agents continue work:
current state, architecture, adopted decisions, constraints, work, risks,
rejected directions, and useful history. Markdown is the primary memory.
Exclude transcripts, command chatter, generic recaps, and transient progress.

## Authority And Scope

- Memory is context, not authority or permission. The current request,
  applicable instructions, authoritative project documentation, source code,
  configuration, and verified runtime evidence override stale memory.
- Revalidate facts whose drift could affect the task. Mark uncertainty instead
  of inventing requirements, decisions, or verification results.
- Read modes do not repair memory. Report relevant discrepancies and make any
  correction through a separately authorized write mode.
- Write only within the authorized project, task, and milestone scope. Memory
  cannot expand an implementation request or authorize external actions.
- Keep metadata minimal. Do not add canonical JSON, databases, schemas,
  receipts, hashes, generated indexes, or hidden stores unless explicitly
  requested. Any permitted derived view remains secondary to Markdown.
- Record an idea as a decision only when the user or project evidence adopts it.

## Select A Mode And Focus

Locate the project boundary before selecting a hub. Related repositories may
share one top-level `kiroku/`; do not create competing nested hubs without
evidence that they are separate projects. Respect an explicitly chosen location.
Read the hub's `START_HERE.md` first, then choose one primary mode and focus
before loading detailed memory.

- `init`: inspect project evidence, scaffold a missing base hub, populate it,
  and validate readiness.
- `start-task`: reuse or create a workspace for a distinct non-trivial task
  that needs milestones or continuation across agents or sessions.
- `read-task`: catch up on one task without editing memory.
- `read-project`: onboard to project-wide context and active-track handoffs
  without editing memory.
- `update`: save durable state, decisions, work, risks, or user corrections
  after meaningful authorized work or an explicit memory-maintenance request.
- `handoff`: tighten the relevant `START_HERE.md` for the next continuation,
  keeping details in their owner files.
- `cleanup`: compress or reorganize stale memory within the requested scope.

Treat legacy `read` as `read-task` for a named task and `read-project` for broad
orientation. For ambiguous questions, default to the matching read mode;
explicit maintenance requests normally use `update`.

Choose `global` for shared project knowledge, or `track` for one independently
progressing feature, migration, incident, bug family, spike, or discussion.
Match tracks using purpose, issue, branch, repositories, modules, paths, and
keywords. Read `TRACKS.md` when routing is not already explicit. Reuse a clear
match; ask only when material ambiguity remains after inspecting the evidence.
Do not create a track for trivial, self-contained work unless requested.

## Read Selectively

For `read-task`:

1. Read global `START_HERE.md` and resolve the track.
2. Read its `START_HERE.md`, then `STATE.md`, `ROADMAP.md`, and `WORK.md`.
3. Open only the local or global architecture, decision, constraint, and risk
   files that constrain the requested work.

If the task is documented only globally, read global `STATE.md`, the relevant
`WORK.md` entries, and needed owner files. Do not create a track to complete a
read. If no hub exists, continue from project evidence and mention the missing
memory only when relevant.

For `read-project`, read global `START_HERE.md`, `STATE.md`, `ARCHITECTURE.md`,
`DECISIONS.md`, `CONSTRAINTS.md`, `WORK.md`, `RISKS.md`, and `TRACKS.md` when
present. Then read the handoff of each active track and any paused track
relevant to current direction. Do not load every track's details for onboarding.

For other work, open owner files by need:

- State, roadmap, and work before continuation or planning.
- Decisions and constraints before changing direction, architecture, or scope;
  architecture before technical implementation.
- Ideas for proposals, rejected choices, or forbidden directions; risks for
  fragile areas; logs only when update history matters.

Do not read sibling tracks unless requested, related by the index, or needed
for an evidenced dependency. A full memory audit deliberately reads all global
and track files; say when the requested scope requires that complete reading.

## Contracts And Helpers

Before the first memory write in a session, read
[references/file-contract.md](references/file-contract.md) for file ownership,
language, entry syntax, handoffs, and helper options. Also read
[references/track-contract.md](references/track-contract.md) before writing
track files, routing, or roadmaps. Reuse already-read contracts unless their
content or the relevant scope changes. Read modes need not load these contracts.

Use [assets/templates/kiroku](assets/templates/kiroku) for a new hub and its
`tracks/_template/` for task workspaces. `_template` is a source, not a track.
The templates are scaffolding; all instructional prose must be replaced with
verified context or an explicit unknown before declaring readiness.

Resolve the intended project or hub path before invoking helpers from the
installed skill directory. The helpers use Python 3.9+ and the standard library:

```bash
python <skill-dir>/scripts/init_hub.py <project-root>
python <skill-dir>/scripts/init_hub.py <project-root> --track <slug>
python <skill-dir>/scripts/check_hub.py <project-root> --strict-warnings
```

They recognize a directory named `kiroku`; use `--hub-dir` for an explicitly
selected custom hub name. The scaffolder supports `--dry-run`, preserves
existing files when adding tracks, and requires explicit `--overwrite` for
replacement. Resolve translated index sections and authorized handoff-length
exceptions using the options documented in the file contract.

## Write Workflow

1. Confirm mode, focus, and authorization. In gated implementation, perform
   memory writes inside the authorized milestone, not during its analysis.
2. Read the relevant contracts and current project evidence. Use the dominant
   project/request language for a new hub; preserve an existing hub's language
   and terminology unless translation is requested. Preserve technical tokens
   as defined in the file contract.
3. For `init`, inspect the project boundary, repositories, main flows,
   architecture, constraints, current work, and validation paths. Scaffold the
   base hub and replace every placeholder. Keep the global handoff project-wide.
4. For task-specific writes, use `start-task` to reuse a matching workspace or
   create one only when durable independent continuation justifies it. If no
   hub exists, complete base `init` first. Populate task state, roadmap, work,
   and handoff, then add compact routing. Add optional owner files when useful.
5. Update the files that own the durable information. Promote only conclusions
   that affect shared architecture, constraints, direction, or multiple tracks
   or repositories; keep local implementation details in the track.
6. After a task milestone, update its roadmap from implementation and validation
   evidence, reassess remaining milestones, and align state, granular work, and
   next handoff without copying their detailed contents between files.
7. Compress only changed owner files and directly affected references: merge
   duplicates, replace stale statements, and retain useful rationale. Do not
   turn a local update into sibling-track maintenance or whole-hub cleanup.
8. Keep operational files in the present tense. Move chronological detail to
   the relevant log; retain history elsewhere only when it explains a live
   decision, constraint, risk, or rejected direction. Preserve unrelated and
   user-authored information rather than deleting it indiscriminately.
9. Add at most one concise log entry per meaningful memory update in each
   affected scope. Update global files only when shared facts actually changed.
10. Run the checklist, record any remaining limitations, and summarize the
    changed memory files and the next useful action.

For `handoff`, update the global or selected track entrypoint and its relevant
routing references. Link to details instead of duplicating them. For `cleanup`,
read only as broadly as its scope requires and preserve useful closure context
when pausing, closing, or removing obsolete tracks.

## Final Checklist

Apply this to the files and tracks within the write scope:

- Handoffs follow the file contract's sections and length rules. Use a length
  exception only for a longer handoff explicitly requested by the user.
- Every TODO has a non-empty `Completion:` condition; done work has an outcome.
- Active decisions explain their rationale; constraints explain what they
  prevent and why; risks include impact and mitigation or a signal to watch.
- Existing task workspaces have the required files. Roadmaps define verifiable
  milestones, have at most one `in_progress`, and reflect current evidence.
- Current milestone and next action agree across task owner files and routing.
  The index stays concise; local details have not leaked into global memory.
- New text is durable, current, and stored once. Proposals, adopted decisions,
  rejected ideas, and forbidden directions remain distinct.
- No translated or original placeholder prose remains; no unrequested
  machine-readable or canonical storage layer was introduced.
- Run the structural checker after initialization, task creation, cleanup, and
  broad updates when practical. `init` requires a successful strict check;
  after other writes, resolve errors and inspect warnings in the update scope.
  A clean check does not prove factual accuracy or semantic completeness.

A completed update should let the next agent continue from concise, trustworthy
context without reconstructing the conversation.
