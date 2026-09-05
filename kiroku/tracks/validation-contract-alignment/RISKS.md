# Risks

## Open Risks

### Risk: Previously accepted malformed hubs need repair

Condition:
Existing hubs may contain invalid routing or Markdown forms outside the documented patterns.

Impact:
Stricter checks can reject content that used to pass accidentally.

Mitigation:
Follow the documented invariant fields and helper migration notes. Plain and
linked local handoff paths and valid counterparts were verified during this work.

### Risk: No persistent regression suite

Condition:
Validation uses focused runtime checks and review rather than checked-in tests.

Impact:
Future changes will need to repeat the relevant behavior checks deliberately.

Mitigation:
Preserve concise verified outcomes and keep helper behavior documented.

## Accepted Risks

- Semantic truth and completion quality still require project evidence and agent review.

## Closed Risks

- The demonstrated parser, routing, placeholder, and destination-shape failures
  were repaired and checked against valid counterparts and actual helper outputs.
