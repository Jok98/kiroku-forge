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

## Accepted Risks

- The current skill has no runtime test suite because the old runtime was
  removed. Skill validation and practical testing are the current feedback
  mechanisms.

## Closed Risks

- The risk of continuing the overly heavy v3 direction was closed by deleting
  the v3 implementation and documenting the Markdown-first direction.
