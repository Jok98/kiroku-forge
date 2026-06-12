# Start Here

## Mission

- Rebuild KirokuForge as a lightweight Markdown project-memory skill.
- Keep project memory readable to developers and future agents.

## Current State

- Current source of truth: `SKILL.md`, `references/file-contract.md`,
  templates, and this `kiroku/` hub.
- Skill validation passes with `quick_validate.py`.
- The hub enforces selective reading, strict `START_HERE.md`, compression on
  update, operating modes, and operational/history separation.

## Next Action

- Forward-test with a fresh agent that reads only this file first.

## Hard Constraints

- Markdown files are the primary memory.
- Metadata must stay minimal and readable in plain text.
- Do not recreate `memory.json`, schemas, receipts, hashes, generated indexes,
  or the old pipeline unless the user explicitly changes direction.
- Current validation is skill-level validation, not Python runtime validation.

## Read Only If Needed

- `STATE.md` for current status.
- `WORK.md` for follow-up tasks.
- `ARCHITECTURE.md` before changing the operating model.
- `DECISIONS.md` and `CONSTRAINTS.md` before changing direction.
- `IDEAS.md` for deferred or rejected approaches.
- `RISKS.md` for fragile parts of the current design.
