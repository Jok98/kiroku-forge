# State

## Project Purpose

KirokuForge preserves curated project knowledge in Markdown so developers and
agents can resume a whole project or a focused task across sessions.

## Current Status

- The skill supports `init`, `start-task`, `read-task`, `read-project`, `update`,
  `handoff`, and `cleanup`; read modes never mutate memory.
- Global files own shared context; tracks own local state, roadmap, work, and handoff.
- The scaffolder preserves existing files in additive mode, selects custom hubs
  explicitly, and validates destinations and index sections before writing.
- The checker validates the documented Markdown patterns, routing, milestones,
  bundled placeholders, and handoff caps; it does not prove semantic truth.
- Translated prose and headings coexist with invariant technical labels and statuses.
- The reliability and contract-alignment task completed all three milestones
  and is closed; instructions now have explicit owners without conflicting duplicates.
- The current repository has no automated test suite or external runtime dependency.
- A semantic HTML viewer and a documentation mode remain backlog proposals;
  neither is implemented. Any future view or cache must remain derived from Markdown.

## Verified On 2026-09-05

- The hub passes `python -B scripts/check_hub.py . --strict-warnings`.
- Both helper scripts pass Python syntax checks and targeted behavior checks.
- Dry-runs confirm additive preservation, explicit hub selection, and index planning.
- Focused checks cover routing failures, Markdown field boundaries and fences,
  scaffold text, translated section selection, and isolated handoff exceptions.
- Real temporary scaffolding created the expected files and preserved all bytes
  on rerun; translated insertion and directory-collision rejection were verified.
- Final independent script and instruction reviews found no blocking issue.
- The general `quick_validate.py` returned `Skill is valid!` with PyYAML supplied
  from a temporary tooling directory, without adding a dependency to the skill.
- The entrypoint and contracts were reduced from 1,086 to 555 lines while
  preserving the reviewed behavioral invariants.

## Open Questions

- What minimum semantic contract should a future read-only HTML viewer use?
- What authorization and output boundaries should a future documentation mode use?

## Evidence Boundaries

Historical forward-testing and global-policy installation results belong to
`LOG.md` and the closed `autonomous-memory-routing` track. They are not current
runtime evidence or proof of an installation on this machine. Applicable
AGENTS instructions govern automatic activation in the current session.
