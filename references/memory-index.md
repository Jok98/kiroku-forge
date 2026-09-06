# KirokuForge Memory Index Contract

This contract owns `memory.sqlite`, checkpoint publication, and the read commands
for search, graph navigation, and focused context. [SKILL.md](../SKILL.md) owns
mode selection and authorization; the [file](file-contract.md) and
[track](track-contract.md) contracts own the source Markdown.

## Authority And Lifecycle

Each hub has one portable SQLite database derived from its Markdown. Edit the
Markdown; never treat database rows as independently editable memory. A single
agent writes each hub. The index does not coordinate concurrent Markdown edits.

Ordinary memory reads use only the last published database. During task execution,
keep new working findings in the active context. At task/milestone completion or
an explicit handoff/pause, curate all durable Markdown changes, run applicable
structural checks, then publish once with `checkpoint`. Initialization and explicit
memory maintenance also end in checkpoints. The scaffolder only copies templates;
curated content is required before the first publication.

The [guided writer](guided-writes.md) saves Markdown without opening or rebuilding
SQLite. Its `saved` result means the source edit is complete, while publication is
still pending. Finish decisions, constraints, state, roadmap, log, and handoff
before invoking `checkpoint`; no memory edits belong after that publication.
`build` is a compatibility alias for the same publication operation.

Queries never read or hash Markdown, audit full database integrity, repair, or
rebuild. They validate the database's identity and supported interface, then read
its published contents. Pending Markdown edits do not change query results. This
deliberately replaces the former check of every source on every query.

Use `status` for an explicit full source/integrity audit after known manual memory
edits, checkout/merge, a restored source tree, or suspected damage, before treating
the snapshot as corresponding to that tree. It is not a query prerequisite on every
call or a required repeat immediately after a successful checkpoint. A detected
mismatch requires publication or explicit recovery. Unobserved external changes
are not detected by ordinary queries; there is no watcher or session cache.

Missing or incompatible databases fail without an automatic Markdown fallback.
Direct source reads belong to legacy bootstrap or explicit recovery. A read request
does not authorize publication. If a checkpoint fails before replacement, the
previous snapshot remains readable and saved source changes remain pending; never
describe those changes as already available through the database.

## Sources And Provenance

The builder indexes `*.md` files beneath the selected hub, excluding hidden
directories and `tracks/_template/`. It does not index referenced documents
outside the hub or external URLs. Paths in indexed content metadata are
hub-relative so the database can move with the same Markdown tree.

The database stores source fingerprints, document/section/entry nodes, typed
records and fields, explicit edges, and an FTS5 text index. Source provenance includes the relative path
and line positions; the source fingerprint identifies the Markdown revision
represented by the index. Source additions, edits, deletions, or renames make
the previous index differ from the working sources. `status` detects that drift;
queries intentionally continue reading the published checkpoint. Freshness describes
agreement with Markdown, not verification against project code or runtime behavior.

Document nodes use their relative path as ID. Section nodes use
`path#heading-anchor`, derived deterministically from the Markdown heading.
Renaming a path or heading can change its ID; obtain current IDs from command
results rather than preserving them as permanent identifiers. Sections keep
their original Markdown body, parent, line range, scope, and explicit status
when present. A document node is a container, not a second copy of every section.
Scope is `global` for shared Markdown and `tracks/<slug>` for track content,
including a track whose slug happens to be `global`.

[Structured decisions and constraints](structured-memory.md) use `entry:<ID>`
node IDs that survive title and path changes when the source ID is preserved.
Each entry is one complete, disjoint Markdown span including its delimiters.
The `entries` table identifies its type and stable memory ID; `entry_fields`
stores its named values. Untagged Markdown remains ordinary sections. Synthetic
gaps use `gap:<path>:<line>` IDs; like heading IDs these are not stable references.
Local Markdown anchors for tagged titles resolve to the corresponding entry.

## Explicit Graph

| Relation | Source evidence |
| --- | --- |
| `contains` | Document and heading hierarchy, from parent to child. |
| `references` | Local Markdown links, inline-code Markdown paths, or `Read:` targets resolving to indexed documents or sections. |
| `related` | Explicit `Related:` track slugs pointing to their indexed handoff. |
| `depends_on` | `M-xx` references in a milestone's `Dependencies:` field, resolved within the same roadmap. |
| `depends_on`, `supersedes`, `constrained_by`, `related` | Explicit structured-entry `links` targeting stable memory IDs. |

Each edge carries its source path and line. Unresolved targets are reported
with provenance instead of creating an invented destination. Fenced examples
do not create operational headings or relationships.
HTML-commented headings and links do not contribute graph targets or edges;
their original text is still preserved in source reads.
Invalid structured links or duplicate IDs block a build; they are not merely
unresolved legacy references. Both the checker and builder validate the tagged
contract before accepting those records.

Markdown links resolve relative to their source document. Inline-code Markdown
paths try the document directory first, then the hub; `Read:` tries the hub
first according to the routing contract. `Read:` and inline paths also accept
the literal `kiroku/` prefix independently of the hub's physical directory name.

The graph does not infer relationships from similar wording or shared keywords.
A reference records what the Markdown links to; it does not prove causality,
dependency completion, or implementation. Read the source section and its
rationale before interpreting a connection. A graph result does not expand the
authorized task or make unrelated tracks part of a memory update.

## Commands

Use Python 3.9+ with its standard library `sqlite3` module and SQLite FTS5.
Usual Python SQLite builds provide FTS5; if unavailable, the command reports
the missing capability. No Redis service, embeddings, or external Python
dependency is required.

Run from the installed skill directory, or use an absolute script path:

```bash
python scripts/memory.py checkpoint <project-root> [--hub-dir]
python scripts/memory.py build <project-root> [--hub-dir]  # compatibility alias
python scripts/memory.py status <project-root> [--hub-dir]
python scripts/memory.py search <project-root> "query" [--track SLUG] [--limit N] [--hub-dir]
python scripts/memory.py entries <project-root> [--type decision|constraint] [--status active] [--track SLUG] [--limit N] [--offset N] [--hub-dir]
python scripts/memory.py show <project-root> <node-id> [--hub-dir]
python scripts/memory.py related <project-root> <node-id> [--depth N] [--limit N] [--hub-dir]
python scripts/memory.py context <project-root> --track SLUG [--query TEXT] [--max-chars N] [--hub-dir]
```

The write commands `add` and `update`, their JSON inputs, dry-run diffs, and
recovery behavior are documented separately in [guided writes](guided-writes.md).

Every command requires a path. A project root selects its `kiroku/`; a path
named `kiroku` selects that hub directly. Pass `--hub-dir` to select an exact
custom hub directory. Commands return JSON, including operational failures.
Argument errors also return JSON on stderr; `--help` displays ordinary help text.

- `checkpoint` validates typed sources, derives the complete index, checks its
  integrity, and publishes it atomically. Run the applicable hub checker and semantic
  review before publication; this command does not establish whole-hub readiness.
  If sources and format are unchanged, it returns `changed: false` without rewriting
  the database. `build` has identical behavior.
- `status` explicitly reads all Markdown and checks database integrity without
  writing. Its `state` is `ready` for an index matching current sources,
  `missing` when absent, `stale` when its sources changed, or `invalid` when it
  cannot be used as a supported index.
- `search` searches section and complete entry text with FTS5. Query words are combined with OR
  and results are ranked; this is lexical search, not inferred similarity.
  Queries accept at most 64 distinct words. `--track` includes the selected
  track and shared global memory. `--limit` defaults to 8 results (range 1-100).
- `entries` lists only tagged records, with optional exact type and status
  filters (`proposed`, `active`, `superseded`, `retired`). With no status filter
  every state is returned explicitly. `--track` includes global memory and the
  selected track. Results omit full bodies; `show` retrieves the detail. The
  default limit is 20 (range 1-100); use `next_offset` when `truncated` is true.
- `show` opens a node by its returned ID with its source provenance; document
  results reconstruct complete source text from disjoint sections and entries.
  Entry results also expose the stable memory ID, type, and named field values.
- `related` follows stored edges in either direction, preserving each edge's
  original direction and provenance. Depth defaults to 1 (range 1-3); the result
  limit defaults to 20 (range 1-100). `truncated` reports a result-limit omission.
- `context` returns compact format-version 2 JSON under a complete-response
  character budget. Other commands keep their existing output formats.

Content-read commands require a supported published snapshot, not a full source
audit. Their success describes that checkpoint only. `status: stale` can coexist
with readable previous-checkpoint content while source edits await publication.
Do not use that content as evidence for unpublished changes or a changed checkout.
Missing or unsupported snapshots fail without writes. Full integrity checks run
at publication and during explicit `status` audits, not normal content reads.

## Context Selection And Budget

`context --track SLUG` always requires these complete Markdown files:

- Global `START_HERE.md` and `CONSTRAINTS.md`.
- The track's `START_HERE.md`, `STATE.md`, `ROADMAP.md`, and `WORK.md`.

`--max-chars` defaults to 16000 and accepts 256-1000000. It limits the
**complete compact JSON response**, including metadata, escaped characters,
`used_chars` itself, and one final LF newline. The unit is Unicode characters
in that serialized output, not source-body characters, UTF-8 bytes, model tokens,
or a surrounding tool envelope. Previously this option limited only source text;
callers relying on the old response shape must adopt `format_version: 2`.
Budgets below 256 are rejected as invalid arguments so a meaningful diagnostic
can always fit within every accepted budget.

A successful response includes:

| Field | Meaning |
| --- | --- |
| `format_version` | `2`, identifying the compact context contract. |
| `state` | `ready` when all mandatory source content is present. |
| `budget_unit` | `serialized_json_characters`. |
| `max_chars` | The requested complete-response limit. |
| `used_chars` | Exact length of the emitted JSON plus final LF. |
| `required_chars` | Minimum sufficient budget for the mandatory-only ready response with the same track, query, and source snapshot. |
| `items` | Complete required documents, followed by optional complete sections or entries that fit. |
| `omitted_count` | Number of considered, deduplicated optional items excluded by the budget. |
| `search_limited` | Whether more text hits exist beyond the 64 considered search results. |

Each mandatory document appears once as `{id, body, reason: "required"}`, with
its hub-relative document ID and exact original text. Optional items contain
`id`, `path`, `start_line`, `end_line`, `body`, and a `reason` of `search` or
`related`. A relationship-selected item also carries one deterministic `via`
object with `source`, `relation`, `source_path`, and `source_line`. Its source
can be a section within a mandatory document; retrieve it with `show` if needed.
No item repeats content from a mandatory document, and entry bodies are not cut.

Selection still considers at most 64 text matches and one outgoing explicit
graph hop from those matches and the mandatory documents and their sections.
The first selection reason and, when applicable, first relationship provenance
are retained for each candidate. A smaller later candidate may fit after a larger
one is omitted. The result does not expand incoming links or infer relations
from shared keywords. It does not recurse into another hop.

The output omits repeated query text, a standalone edge inventory, and detailed
lists of excluded items. `omitted_count` covers considered candidates, not every
possible fact in the hub or unconsidered hits beyond the search cap. Use `search`,
`show`, and `related` to inspect further material and relationships on demand.
The selection reason, provenance, and omission count all consume the same budget.

If mandatory content does not fit, `state: budget_exceeded` returns no content
(`items: []`) and reports `required_chars`. Retrying at that limit fits the
mandatory sources when the track, query, and sources are unchanged; if it exceeds
the maximum supported budget, retrieve required documents separately with `show`.
No required
file is silently truncated, summarized, or reported as a complete partial result.

Operational failures for valid `context` arguments also return bounded compact
JSON with `used_chars`. Only an overlong diagnostic message may be shortened,
with `error_truncated: true`; source content is never shortened to make it fit.
Argument-parser errors and `--help` are outside the context-result contract.
Missing or incompatible snapshots fail without any implicit rebuild. Pending
Markdown edits do not affect the context assembled from the published snapshot.

A bounded result is a reading aid, not proof of semantic completeness, current
source-code truth, or fit within a model's token budget.

## Portability And Recovery

A checkpoint prepares a temporary database, uses `journal_mode=DELETE`, checks its
integrity, and replaces `memory.sqlite` atomically only after successful
construction. It leaves no WAL dependency to copy with the database. This
protects publication of the index; it does not make Markdown edits transactional.
If syncing the directory fails after replacement, the successful result includes
`durability_warning`: the new snapshot is usable, but crash durability of that
replacement was not confirmed. No rollback is implied.

The database is a versionable derived artifact. When a Git action is already
authorized, include it with the exact Markdown revision from which it was
built. Database creation never authorizes a commit, push, or merge by itself.
Resolve a binary database conflict by resolving the Markdown first and then
running `checkpoint`; do not merge database rows or promote the database to canonical
memory. Copying a hub to another project or machine preserves usability when
the source tree and supported database format agree.

Rebuild an identified Kiroku snapshot with an old schema or damaged contents from
verified Markdown during an authorized write workflow. The builder preserves
unidentified or foreign databases, symlink targets, and snapshots with runtime
sidecars; inspect and move them aside or close their external writer before
building. Never delete an active WAL file to force a build. A successful build and integrity
check establish a usable derived index, not structural completeness of the hub
or factual accuracy of its contents. Run the applicable structural checker and
retain the skill's evidence review.
