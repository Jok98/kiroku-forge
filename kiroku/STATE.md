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
- `scripts/init_hub.py` copies bundled templates into a target `kiroku/` hub
  and refuses overwrite unless requested.
- `scripts/check_hub.py` validates required hub files, template placeholders,
  `START_HERE.md` length, TODO completion conditions, and active decision
  rationales.
- `assets/templates/kiroku/*.md` initializes new project hubs.
- New hubs use the dominant language of the project or request; existing hubs
  keep their current language unless the user asks to translate them.
- The hub guardrails are selective reading, strict `START_HERE.md`,
  compression on update, and separation of operational state from history.
- This repository intentionally has no v3 runtime, schema, or test suite.

## Recently Verified

- `python /home/jok/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/jok/.agents/skills/kiroku-forge` returned `Skill is valid!`.
- `python scripts/check_hub.py .` returned `Kiroku hub check passed: kiroku`.
- `python scripts/check_hub.py assets/templates/kiroku` warns on template
  placeholders as expected.
- `python scripts/init_hub.py <temp-project>` created the standard hub files,
  and rerunning it refused overwrite without `--overwrite`.
- `$kiroku-forge` has been exercised on this repository by updating the
  Markdown hub in place.

## Open Questions

- None known.

## Watch Points

- Do not let the Markdown hub become a verbose generated report.
- Do not duplicate the same decision or constraint across several files.
- Treat old memory notes about v2/v3 as historical context only; they no
  longer define the current product direction.
