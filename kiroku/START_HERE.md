# Start Here

## Mission

- Maintain KirokuForge as a lightweight Markdown project-memory skill.
- Let developers and agents resume either the whole project or one task.

## Current State

- Current source of truth: `SKILL.md`, `references/*-contract.md`,
  `scripts/init_hub.py`, `scripts/check_hub.py`, templates, and this hub.
- Modes are explicit: `init`, `start-task`, `read-task`, `read-project`,
  `update`, `handoff`, and `cleanup`.
- Active tasks use tracks with separate state, roadmap, work, decisions, risks,
  and handoff context.
- Global Codex rules now activate KirokuForge selectively from project context.
- The `autonomous-memory-routing` restructuring track is completed and closed.

## Next Action

- Select the next durable backlog item before creating another task track.

## Hard Constraints

- Markdown files are the primary memory.
- Metadata must stay minimal and readable in plain text.
- Do not recreate `memory.json`, schemas, receipts, hashes, generated indexes,
  or the old pipeline unless the user explicitly changes direction.
- Do not make a database or generated HTML the source of truth.
- Do not let track detail pollute global project files.
- `init` is agent-led; the helper only scaffolds and must preserve existing files.
- Keep autonomous use selective and preserve analysis-only read behavior.

## Read Only If Needed

- `TRACKS.md` to route work to the active initiative.
- `STATE.md` and `WORK.md` for global status and backlog.
- `ARCHITECTURE.md`, `DECISIONS.md`, and `CONSTRAINTS.md` before direction changes.
- `IDEAS.md` and `RISKS.md` for deferred approaches or fragile parts.
