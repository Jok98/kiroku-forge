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
