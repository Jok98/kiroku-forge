# Log

## Updates

- 2026-06-12: Initialized the first Markdown-first KirokuForge memory hub for
  this skill repository after removing the old v3 implementation.
- 2026-06-12: Added selective reading rules so agents start from
  `START_HERE.md` and open other hub files only when the request needs them.
- 2026-06-12: Tightened `START_HERE.md` into a strict bootstrap with fixed
  sections and a 25-40 line target.
- 2026-06-12: Added a compression rule so memory updates remove stale text,
  merge duplicates, and avoid recap-style bloat.
- 2026-06-12: Exercised `$kiroku-forge` on this repository by updating
  `START_HERE.md`, `STATE.md`, `WORK.md`, and this log in place.
- 2026-06-12: Separated operational state from history by tightening
  `START_HERE.md`, `STATE.md`, and `WORK.md` around present-tense project
  context.
- 2026-06-12: Added operating modes (`read`, `update`, `handoff`, `cleanup`,
  `init`) to reduce ambiguity before agents read or edit the hub.
- 2026-06-12: Added a final checklist for memory writes covering
  `START_HERE.md` budget, TODO completion conditions, decision rationale,
  single log entry, duplication, present-tense operational files, and no hidden
  canonical store.
- 2026-06-13: Adopted the hub language rule: new hubs follow the project or
  request language, while existing hubs preserve their current language unless
  translation is requested.
- 2026-06-13: Added `scripts/check_hub.py` as a lightweight Markdown hub
  checker and documented when to run it after init, cleanup, or broad updates.
- 2026-06-13: Added `scripts/init_hub.py` to copy bundled templates into a
  target `kiroku/` hub while refusing overwrite unless explicitly requested.
- 2026-06-14: Recorded the next product direction: structured Markdown can
  drive a derived semantic HTML viewer and optional docs mode, while databases
  and generated views remain noncanonical.
- 2026-06-15: Added phase 1 track routing to separate global project memory
  from optional workstream memory inside the same Markdown hub.
- 2026-06-15: Added `references/track-contract.md` as the phase 2 detailed
  contract for workstream lifecycle, routing, promotion, closure, and patterns.
- 2026-06-15: Added phase 3 track templates for `TRACKS.md` and
  `tracks/_template/`.
- 2026-06-15: Added phase 4 helper support for additive track initialization
  and track-aware hub validation.
