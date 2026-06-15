# Start Here

## Mission

- Rebuild KirokuForge as a lightweight Markdown project-memory skill.
- Keep project memory readable to developers and future agents.

## Current State

- Current source of truth: `SKILL.md`, `references/*-contract.md`,
  `scripts/init_hub.py`, `scripts/check_hub.py`, templates, and this hub.
- Skill validation and the hub checker pass; guardrails cover selective reading,
  strict handoff, compression, operating modes, and final checklist.
- Focus routing is documented: top-level files hold global/cross-repo truth,
  while optional tracks isolate parallel workstreams.

## Next Action

- Forward-test with a fresh agent on a project containing two active tracks.
- Decide whether to lower the global `START_HERE.md` hard cap from 60 to 50.

## Hard Constraints

- Markdown files are the primary memory.
- Metadata must stay minimal and readable in plain text.
- Do not recreate `memory.json`, schemas, receipts, hashes, generated indexes,
  or the old pipeline unless the user explicitly changes direction.
- Do not make a database or generated HTML the source of truth.
- Do not let track detail pollute global project files.
- Initialization and validation are lightweight helper scripts, not the
  removed v3 runtime pipeline.

## Read Only If Needed

- `STATE.md` and `WORK.md` for current status and follow-up tasks.
- `ARCHITECTURE.md`, `DECISIONS.md`, and `CONSTRAINTS.md` before direction changes.
- `IDEAS.md` and `RISKS.md` for deferred approaches or fragile parts.
