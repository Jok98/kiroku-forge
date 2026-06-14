# Risks

## Open Risks

### Risk: Markdown hub becomes too verbose

Condition:
Agents may over-document every turn or duplicate details across files.

Impact:
Future agents will spend too much context reading generated clutter.

Mitigation:
Keep `START_HERE.md` selective, update existing sections, and log only
meaningful memory changes.

### Risk: Too little structure for consistent updates

Condition:
Without JSON schemas or IDs, different agents may format entries
inconsistently.

Impact:
The hub could become harder to scan over time.

Mitigation:
Use `references/file-contract.md` and stable section patterns before adding
any machine layer.

### Risk: Old v3 assumptions leak back in

Condition:
Prior memory and repository history still mention v3 pipeline concepts.

Impact:
Future work could accidentally rebuild the discarded architecture.

Mitigation:
Keep the obsolete decision and constraints visible in `DECISIONS.md`,
`CONSTRAINTS.md`, and `IDEAS.md`.

### Risk: Generated UI becomes a second source of truth

Condition:
A local HTML viewer, tags, IDs, or generated docs become editable or preserved
as authoritative state.

Impact:
Markdown and generated views can drift, making agents and humans disagree
about current project memory.

Mitigation:
Keep generated outputs read-only and regenerable until editing can write
directly back to canonical Markdown.

### Risk: Semantic Markdown becomes too rigid

Condition:
The renderer requires too much metadata, manual IDs, or strict formatting for
ordinary memory entries.

Impact:
The hub becomes unpleasant to read and maintain, repeating the schema-heavy
failure mode of the old design.

Mitigation:
Use stable headings and light field patterns first; generate IDs
deterministically and add explicit markers only when stability requires them.

## Accepted Risks

- The current skill has no runtime test suite because the old runtime was
  removed. Skill validation, the lightweight hub checker, and practical testing
  are the current feedback mechanisms.

## Closed Risks

- The risk of continuing the overly heavy v3 direction was closed by deleting
  the v3 implementation and documenting the Markdown-first direction.
