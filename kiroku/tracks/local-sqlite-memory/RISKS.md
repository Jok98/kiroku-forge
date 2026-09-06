# Risks

## Open Risks

### Risk: An indexed claim is mistaken for a verified fact

Condition:
A source fingerprint proves correspondence with Markdown, while the underlying
project behavior may have changed since that Markdown was curated.
Impact:
An agent could use an obsolete constraint or verification claim.
Mitigation:
Expose original sources and retain the existing requirement to revalidate
claims against current code and runtime evidence.

### Risk: A graph link loses its target after a rename

Condition:
Source paths and legacy heading-derived IDs change when files or headings are
renamed. Structured entries retain their explicit source IDs across those changes.
Impact:
Saved node identifiers or Markdown links can become unresolved.
Mitigation:
Rebuild after changes, expose unresolved references, and search again for the current ID.

### Risk: Lexical search misses language variants or ranks empty headings

Condition:
FTS matches literal words, so Italian queries may miss English memory; legacy
heading-only sections can still rank above substantive text.
Impact:
An agent may overlook relevant reasoning despite a current index.
Mitigation:
Use typed entries filters for migrated decisions and constraints, and reformulate
text queries in the hub language. Legacy text ranking remains separate work.

## Accepted Risks

- Source publication and index rebuild are separate operations. A crash or I/O
  failure between them leaves canonical Markdown pending while the previous DB
  stays published. Retry checkpoint after recovery, not saved additions.
- Ordinary queries deliberately do not detect source drift or audit complete DB
  integrity. Use status after known manual edits, checkout/merge, a restored tree,
  or suspected damage; a readable checkpoint need not match unpublished sources.
- Retrieval covers indexed Markdown and explicit links; it does not discover every
  semantic dependency or index the project's implementation automatically.
- The 22 persistent tests cover context and checkpoint behavior, including guided
  edit publication boundaries. Other parser/checker/scaffolder behaviors retain
  the focused checks in STATE.md rather than equivalent comprehensive coverage.
- Context v2 counts serialized Unicode characters, not model tokens, UTF-8 bytes,
  or the surrounding tool envelope; clients must adopt its changed response shape.
- Typed listings cover tagged entries only; untagged boundaries and historical
  prose remain available through complete Markdown reads and general search.

## Closed Risks

- M-04 corrected context response overflow: metadata, escapes, omission reporting,
  and the final newline now consume the same budget. Mandatory sources are whole
  or absent with an explicit minimum-budget diagnostic; 11 regression tests pass.
