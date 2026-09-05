# Roadmap

## Milestones

### M-01: Reliable structural validation and destination handling

Status: completed

Objective:
Reject the malformed routing, field boundaries, incomplete scaffolds, and unsafe
destination shapes demonstrated in the skill review.

Scope:
- Checker routing, Markdown field parsing, and bundled placeholder coverage.
- Scaffolder hub selection, target preflight, and track slug validation.

Expected artifacts:
- Updated `scripts/check_hub.py` and `scripts/init_hub.py`.
- Current task memory and routing.

Dependencies:
- Verified review findings F-01, F-02, F-03, F-05, and F-06.

Validation:
- Exercise reported failures and valid counterparts in memory or isolated CLI runs.
- Run syntax checks, the existing strict hub checker, and diff review.

Completion criteria:
- Invalid routes, field attribution, and destinations are rejected before success.
- Valid content and additive existing-file preservation remain supported.
- Bundled template placeholder prose is detected.

Risks:
- Tighter validation can reveal previously accepted malformed hubs.
- Custom hub paths need an explicit selection flag rather than name guessing.

### M-02: Consistent language, handoff, and update rules

Status: completed

Objective:
Make operational instructions and helper behavior agree for translated hubs,
handoff limits, and focused memory updates.

Scope:
- Translatable prose versus invariant fields, and translated track index insertion.
- Advisory handoff targets, enforced caps, and explicit user-authorized exceptions.
- Compression boundaries, memory authority, and reading tasks without tracks.

Expected artifacts:
- Updated script options and operational contracts.
- Aligned skill guidance and task state.

Dependencies:
- M-01 structural validation and hub path semantics.

Validation:
- Exercise translated index insertion and authorized handoff length overrides.
- Review local update and task-read scenarios against every normative instruction.

Completion criteria:
- Translated hubs remain usable without duplicate lifecycle sections.
- Handoff checks express the documented limits and explicit exceptions.
- Focused updates and read-only fallback do not broaden scope.

Risks:
- Ambiguous localized sections require explicit selection before insertion.
- Handwritten hubs may need to preserve documented technical field names.

### M-03: Concise instructions and verified project memory

Status: completed

Objective:
Reduce duplicate rules and replace stale operational memory with verified current
behavior and clearly separated historical evidence.

Scope:
- Skill entrypoint, references, README accuracy, and project memory.
- Final requirement-by-requirement review across all milestones.

Expected artifacts:
- Concise `SKILL.md` with discoverable authoritative references.
- Updated global owner files and completed task handoff.

Dependencies:
- M-01 and M-02 verified implementation and final CLI behavior.

Validation:
- Check reference targets, instruction ownership, hub structure, and final diff.
- Run the general skill validator with an available compatible runtime if possible.
- Independently review the completed behavior and remaining limitations.

Completion criteria:
- Essential invariants remain discoverable without conflicting duplicate rules.
- Current memory cites this checkout's behavior rather than old environment claims.
- Every approved milestone is verified and the task is closed in routing.

Risks:
- Excessive compression could remove a non-obvious behavioral constraint.
- Historical validation claims must not be presented as current verification.
