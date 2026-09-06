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
- `local-sqlite-memory` delivered a versionable per-hub snapshot, lexical search,
  explicit graph navigation, source retrieval, and bounded task context.
- Its M-02 pilot added tagged decisions/constraints, stable IDs, named fields,
  validated record links, and typed retrieval.
- M-03 added guided creation and patch updates with dry-run diffs and explicit
  source/index recovery. M-04 added verified complete-response context budgeting
  in format v2. M-05 made ordinary reads database-only and defers publication until
  all checkpoint Markdown edits are complete; all five milestones are complete.
- The runtime uses Python's standard library and SQLite FTS5, with no external
  Python package. Standard-library context and checkpoint regression suites are included.
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
- SQLite verification preserved all 31 original Markdown documents byte-for-byte,
  including full document reconstruction; reads and unchanged builds preserved
  snapshot bytes and modification time.
- Relocating the hub retained freshness and results; independent builds under
  different directory names produced identical database bytes.
- Missing/stale reads, rebuild after edits, budget rejection, foreign database
  preservation, and symlink rejection passed focused CLI verification.
- Independent retrieval found the adopted SQLite rationale and the historic
  operating-model milestone through source-backed search and graph traversal.
- The structured-entry pilot extracted 9 decisions and 5 constraints, preserved
  all 31 source documents, rejected invalid input before publication, and retained
  IDs across moves/renames. Strict validation and independent review passed.
- Guided writes were used on this hub and verified in project copies. Runtime
  checks covered preservation, no-op behavior, rejected inputs, permission failures,
  index recovery, and an independent proposal/update exercise.
- Context v2 passed 11 regression tests and independent review for full-output
  bounds, source preservation, exact minimum budgets, and graph selection.
- All 22 context/checkpoint tests pass. An independent maintenance exercise used
  multiple source edits, one publication, and successful retrieval of the saved proposals.

## Open Questions

- What minimum semantic contract should a future read-only HTML viewer use?
- How much does indexed retrieval improve continuation on real downstream projects?
- What authorization and output boundaries should a future documentation mode use?

## Evidence Boundaries

Historical forward-testing and global-policy installation results belong to
`LOG.md` and the closed `autonomous-memory-routing` track. They are not current
runtime evidence or proof of an installation on this machine. Applicable
AGENTS instructions govern automatic activation in the current session.
