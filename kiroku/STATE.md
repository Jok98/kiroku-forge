# State

## Project Purpose

KirokuForge is a Codex skill for maintaining durable project memory. Its new
purpose is to create and update a small Markdown hub that captures current
state, architecture, decisions, constraints, work, risks, and handoff context.

## Current Status

- The previous v3 implementation has been intentionally deleted.
- The new skill no longer treats `memory.json` as canonical state.
- The new `SKILL.md` instructs agents to maintain `kiroku/*.md` files directly.
- The file contract is intentionally lightweight and avoids frontmatter by
  default.
- Template files exist for initializing a project memory hub.
- The hub now has guardrails for selective reading, strict `START_HERE.md`,
  and compression during updates.

## Recently Verified

- `python /home/mmoi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/mmoi/.agents/skills/kiroku-forge` returned `Skill is valid!`.
- The active skill files are `SKILL.md`, `agents/openai.yaml`,
  `references/file-contract.md`, and `assets/templates/kiroku/*.md`.
- The v3 folders `schemas/`, `scripts/kiroku_core/`, and `tests/` have been
  removed from the worktree.
- `$kiroku-forge` has been exercised on this repository by updating the
  Markdown hub in place.

## Open Questions

- Whether the first real `kiroku/` hub should be in Italian, English, or follow
  the language of the project being documented.
- Whether a tiny `init` script is useful later for copying templates, or
  whether agents can keep doing this manually.
- Whether to add a lightweight checker for required files after the format has
  survived practical use.

## Watch Points

- Do not let the Markdown hub become a verbose generated report.
- Do not duplicate the same decision or constraint across several files.
- Treat old memory notes about v2/v3 as historical context only; they no
  longer define the current product direction.
