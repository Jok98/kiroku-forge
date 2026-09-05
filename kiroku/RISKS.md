# Risks

## Open Risks

### Risk: Memory becomes stale or repetitive

Condition:
Agents can retain old verification claims or duplicate task progress globally.

Impact:
Future work consumes irrelevant context or relies on an obsolete premise.

Mitigation:
Revalidate facts that can drift, keep each fact in its owner file, and separate
historical evidence from current state. Use focused compression during updates.

### Risk: Structural validation is mistaken for semantic proof

Condition:
A clean checker result can be treated as proof that content is accurate or complete.

Impact:
Translated placeholders, unsupported prose conventions, or unjustified completion
claims could be overlooked despite valid structure.

Mitigation:
Document the supported entry patterns and require agent review of evidence,
translated scaffold text, and consistency between owner files.

### Risk: Later I/O failures leave partial scaffolding

Condition:
Preflight succeeds but a copy or index write subsequently fails.

Impact:
The hub can contain only part of the planned files or an incomplete routing update.

Mitigation:
Inspect the result and rerun additive scaffolding after fixing the cause; the
helper preserves existing files. Preflight is not a transaction or rollback mechanism.

### Risk: Automatic activation or cleanup broadens scope

Condition:
A trivial task or local update is treated as justification for global maintenance.

Impact:
Unnecessary hubs, tracks, or edits add noise and can affect unrelated work.

Mitigation:
Apply current AGENTS authority, exclude trivial work unless requested, and limit
compression to the changed owner files and direct references.

### Risk: A future viewer recreates a second source of truth

Condition:
Derived HTML or a query cache becomes independently editable or authoritative.

Impact:
Memory representations drift and the product returns to a schema-heavy design.

Mitigation:
Keep initial views read-only and derived from the existing Markdown entry patterns.

## Accepted Risks

- There is no persistent automated test suite. Focused behavior checks, helper
  validation, and review must be repeated for relevant changes; adding test
  artifacts requires separate approval under the user's policy.
- Translated headings need explicit section selection when the helper cannot
  identify their lifecycle meaning from the default English name.

## Closed Risks

- Known routing, field-boundary, bundled-placeholder, and destination-shape defects
  were repaired in `validation-contract-alignment`; its roadmap records verification.
