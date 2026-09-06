# Architecture

## Main Flow

1. Resolve the project boundary and memory hub; choose a mode and global or track focus.
2. Read the relevant entrypoint and owner documents exclusively through the published DB.
3. During a task, retain working findings in active context and verify project evidence.
4. At a task/milestone or explicit handoff/maintenance checkpoint, curate all durable
   Markdown changes, including task state, roadmap, log, and handoff.
5. Validate structure and review semantic accuracy before one snapshot publication.
6. Use status for an explicit audit after known external source changes or suspected damage.

## Responsibilities

- `SKILL.md` owns authority, modes, selective reading, write workflow, and checklist.
- `references/file-contract.md` owns file responsibilities, language and entry
  syntax, handoff rules, helper commands, and validation boundaries.
- `references/track-contract.md` owns index entries, lifecycle, roadmap shape,
  promotion, and closure.
- `references/memory-index.md` owns snapshot authority, explicit graph relationships,
  freshness, retrieval commands, character budgets, and repository portability.
- `references/structured-memory.md` owns versioned decision/constraint entries,
  stable source IDs, typed fields, lifecycle values, and declared relationships.
- `scripts/structured_memory.py` parses and validates these records for both
  the checker and index; untagged prose retains the legacy reading path.
- `references/guided-writes.md` owns typed creation/update inputs, previews,
  source preservation, and partial source/index publication recovery.
- `scripts/memory_edit.py` plans validated changes in memory. `memory_writer.py`
  saves one Markdown source atomically, without opening or updating SQLite.
- `scripts/init_hub.py` plans template copies and index insertion before writing.
  It validates destination shapes and preserves existing files in additive mode.
- `scripts/check_hub.py` owns lightweight Markdown parsing and structural checks.
  The scaffolder reuses its heading and code-fence parsing for consistent index edits.
- `scripts/memory_store.py` owns source discovery, parsing, graph extraction, SQLite
  snapshot construction, lightweight reads, and explicit full source/integrity audits.
- `scripts/memory.py` exposes checkpoint/build, explicit status, and lexical search, source retrieval,
  explicit graph navigation, and focused track-context assembly as JSON commands.
  Its add/update commands accept operation JSON while preserving Markdown ownership.
- `assets/templates/kiroku/` holds the base scaffold and optional track templates.
- This `kiroku/` hub records the skill project's shared context and task routing.

## Helper Behavior

- A positional path is a project root unless named `kiroku`; `--hub-dir`
  explicitly selects a custom hub directory. `START_HERE.md` alone is not detection.
- `--track` creates or completes task files; `--track-section` selects an observed
  level-two index heading. Missing or ambiguous sections fail before copies.
- Preflight rejects destination type collisions, dangling symlinks, and paths
  escaping the selected hub. An explicitly chosen hub may itself be an alias.
- The checker validates routing in both directions, required workspace files,
  actual local handoff targets, milestone identifiers and fields, and one in-progress milestone.
- Markdown field parsing respects section boundaries and fenced examples while
  allowing prose, bullets, and fenced content as values.
- Handoff targets are advisory; the checker enforces global/track caps with
  explicit file-specific exceptions for user-requested extended handoffs.
- The scripts use Python's standard library; indexing requires SQLite FTS5.
  No server, embedding provider, or Git runtime dependency is required.

## Derived Retrieval

- Each hub has one `memory.sqlite` containing original Markdown sections and
  complete tagged entries, typed field records, relative source paths, source
  fingerprints, explicit edges, and full-text search data.
- Hidden directories and track templates are excluded; references outside the
  hub are not automatically indexed. Nested source symlinks are rejected.
- The index records documented links, milestone dependencies, and declared entry
  relationships. Structured entry IDs survive renames; ordinary heading-derived
  identifiers can change. No semantic relationships are inferred.
- A build constructs and validates a separate database with DELETE journaling,
  closes it, and replaces the snapshot; unchanged sources do not rewrite it.
- Ordinary reads require a supported published snapshot and never read Markdown,
  audit full integrity, or repair it. They expose original checkpoint sources,
  selection reasons, and bounded retrieval omissions. Status explicitly detects drift.
- `context` reserves complete continuation and constraint sources before optional
  text matches and one outgoing relationship hop. Its v2 budget counts the complete
  compact JSON response, including metadata, escaping, and final LF. Required files
  appear once; omitted candidates are counted and details remain available on demand.
  Characters are not model tokens or UTF-8 bytes. An insufficient budget returns
  no source content and reports the minimum needed for the mandatory documents.
- SQLite is derived and versionable with matching Markdown. Binary conflicts
  are resolved by rebuilding after the source Markdown is resolved.
- Guided edits use source Markdown and report saved while leaving the index intact.
  Dry-runs return a diff without writes. A checkpoint publishes all completed edits;
  failure preserves pending Markdown and the prior DB. Recovery retries checkpoint,
  not saved additions. No-op writes do not establish source/index correspondence.

## Boundaries To Preserve

- Memory supplies context, never authority or permission.
- Initialization requires verified content; a successful copy is only scaffolding.
- Global files contain shared facts; detailed task progress stays local.
- Read modes and unrelated tracks remain untouched during focused memory work.
- Structural validity does not establish factual accuracy or semantic completion.
- Copies and index writes are not transactional; preflight prevents known
  structural failures, while later I/O failures can still leave partial scaffolding.

## Future Outputs

A future local UI should derive semantic views from Markdown entry patterns.
Entry IDs and tags belong to Markdown; query caches remain disposable. HTML and documentation
outputs must retain explicit source ownership rather than becoming competing
memory. Viewer and documentation-mode design remain separate proposals.
