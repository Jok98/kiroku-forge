# Start Here

## Mission

- Rebuild KirokuForge as a lightweight Markdown project-memory skill.
- Keep project memory readable to developers and future agents.

## Current State

- Current source of truth: `SKILL.md`, `references/file-contract.md`,
  `scripts/init_hub.py`, `scripts/check_hub.py`, templates, and this
  `kiroku/` hub.
- Skill validation and the hub checker pass on this repository.
- The hub enforces selective reading, strict `START_HERE.md`, compression on
  update, operating modes, final checklist, and operational/history separation.
- Proposed extensions generate docs, HTML, tags, IDs, or query aids only as derived views.

## Next Action

- Design the semantic Markdown-to-HTML viewer contract if that starts.
- Forward-test with a fresh agent that reads only this file first.

## Hard Constraints

- Markdown files are the primary memory.
- Metadata must stay minimal and readable in plain text.
- Do not recreate `memory.json`, schemas, receipts, hashes, generated indexes,
  or the old pipeline unless the user explicitly changes direction.
- Do not make a database or generated HTML the source of truth.
- Initialization and validation are lightweight helper scripts, not the
  removed v3 runtime pipeline.

## Read Only If Needed

- `STATE.md` for current status.
- `WORK.md` for follow-up tasks.
- `ARCHITECTURE.md` before changing the operating model.
- `DECISIONS.md` and `CONSTRAINTS.md` before changing direction.
- `IDEAS.md` for deferred or rejected approaches.
- `RISKS.md` for fragile parts of the current design.
