# State

## Purpose

Add a usable local retrieval layer to the existing Markdown memory workflow.
The user chose one SQLite database per hub, suitable for committing alongside
its Markdown sources. The project has a single memory writer.

## Current Status

- M-01 through M-05 are complete. Ordinary reads use only the published database;
  guided edits save Markdown and one final checkpoint publishes the complete edit set.
- Context v2 preserves its complete-response budget and mandatory sources.
- The hub tags 10 global decisions and 5 constraints with stable IDs. Typed
  records, named fields, and declared links are derived into the same hub index.
- Existing Markdown-only hubs must remain readable without migration.
- Graph extraction uses documented structure and explicit references only.

## Verification

- Existing strict hub validation, general skill validation, syntax checks, and diff review passed.
- Real builds and reads preserved all original Markdown bytes and reconstructed all 31 documents exactly.
- Unchanged builds and read commands preserved snapshot bytes and modification time.
- Relocated hubs stayed usable; fresh builds under different directory names were byte-identical.
- Missing/stale reads, rebuilds, mandatory budget limits, foreign databases, and source symlinks were exercised.
- A track named `global` remains isolated, and local source references resolve within their track.
- Independent navigation recovered the SQLite decision and a historic milestone's dependency.
- The store's focused checks also covered CRLF text, read-only SQL, sidecars, and interrupted publication.
- M-01 through M-03 used focused runtime checks without a persistent test suite.
- M-02 preserved exact reconstruction of all 31 source documents, including
  tagged spans; typed filters, pagination, full rationale, and explicit links passed.
- Rejected malformed tags, missing fields, duplicate IDs, invalid targets/types,
  and inconsistent status without replacing the existing snapshot in a project copy.
- Stable entry retrieval survived title/path changes. Untouched reads and builds
  preserved source and snapshot bytes; uncurated template IDs blocked publication.
- Independent retrieval found the adopted SQLite decision, its governing constraint,
  and all 5 tagged active constraints without omissions in those typed results.
- Review corrected legacy field boundaries at markers and hidden HTML headings/links;
  the follow-up review found no remaining actionable defect in the pilot scope.
- M-03 create/update/dry-run commands passed real project-copy exercises; patch
  updates retained unspecified fields and unrelated files, including bytes and mtimes
  on no-ops. Rewritten owner files retained their permission modes.
- Real permission failures preserved sources before publication and reported saved
  Markdown with a stale index after failed database publication; build recovered it.
- Invalid payloads, duplicate JSON keys, unsupported statuses, malformed field
  injection, CRLF handling, comments, moves, and stable preview IDs were checked.
- Review corrected invalid-status error handling and missing-final-newline diffs.
- Independent guided writing preserved a proposal's state and rationale across
  creation and update, rebuilt an initially stale index, and passed the strict checker.
- The writer created DEC-guided-source-publication in this hub and updated DEC-009;
  the former records the source-first publication and recovery behavior.
- M-04 passed 11 standard-library regression tests covering full JSON plus LF,
  exact retry budgets, Unicode/escaping, mandatory coverage, graph deduplication,
  omissions, errors, and preservation of source/index bytes and modification times.
- Independent review also checked exact boundaries, deterministic output, and
  one outgoing graph hop from mandatory sections without incoming expansion.
- Real CLI measurements confirmed the 24000-character response fits its budget;
  insufficient budgets return only a compact diagnostic with the minimum required.
- M-05 passed all 22 context/checkpoint regression tests, Python 3.9 syntax,
  skill validation, and independent code/contract review without actionable findings.
- Tests prohibit Markdown traversal/reads and full integrity checks in ordinary
  queries; missing/malformed sources leave the published results unchanged.
- Multiple guided edits, no-ops, and failed publications preserve the old DB;
  one checkpoint exposes the complete edit set. Explicit status detects source drift.
- An independent copy-based exercise saved two proposed decisions plus handoff
  updates, passed the strict checker, published once, and retrieved both from SQLite.
- This checkpoint used the guided writer for DEC-010 and the source-publication
  decision; both saved Markdown while preserving the actual database bytes and mtime.
- A local warm-process sample on 31 sources measured median open-plus-lookup
  at 0.442 ms versus 5.137 ms with a full source/integrity audit (30 runs each).
  This is not an end-to-end CLI or agent-continuation benchmark.

## Open Questions

- None blocking the approved local implementation.
- No further milestone is scheduled. Additional record families and legacy
  lexical ranking/language gaps remain outside the completed scope.
