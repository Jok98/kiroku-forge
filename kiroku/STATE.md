# State

## Project Purpose

KirokuForge is a Codex skill for maintaining durable project memory. Its new
purpose is to create and update a small Markdown hub that captures current
state, architecture, decisions, constraints, work, risks, and handoff context.

## Current Status

- KirokuForge is a Markdown-first memory skill.
- `kiroku/*.md` files are the project memory; `memory.json` is not canonical.
- `SKILL.md` defines agent behavior, and `references/file-contract.md` defines
  the hub file contract.
- `assets/templates/kiroku/*.md` initializes new project hubs.
- The hub guardrails are selective reading, strict `START_HERE.md`,
  compression on update, and separation of operational state from history.
- This repository intentionally has no v3 runtime, schema, or test suite.

## Recently Verified

- `python /home/mmoi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/mmoi/.agents/skills/kiroku-forge` returned `Skill is valid!`.
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
