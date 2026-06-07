# Kiroku Memory Data Model

## Contents

1. Canonical document
2. Project
3. Sources
4. Runs
5. Records
6. Record payloads
7. Lifecycle and relations
8. Hashing

## Canonical Document

`memory.json` is the only editable source of truth:

```json
{
  "schema_version": "2.0.0",
  "memory_id": "mem_example",
  "project": {},
  "sources": [],
  "runs": [],
  "records": []
}
```

Unknown fields are rejected unless placed under an `extensions` object.

## Project

The project contains stable identity and scope:

- `id`: stable project identifier.
- `name`: human-facing name.
- `description`: concise project description.
- `domain`: business or technical domain.
- `status`: `active`, `paused`, `completed`, or `archived`.
- `goal`: durable target.
- `scope`: repository, module, or product scopes.
- `created_at`, `updated_at`: RFC 3339 UTC timestamps.

## Sources

A source identifies an input artifact. It does not contain extracted conclusions.

Supported source kinds:

- `conversation`
- `user_input`
- `repository_file`
- `document`
- `command_output`
- `url`
- `test_result`
- `agent_observation`

Use `uri` as a stable locator. Repository files should use repository-relative
paths. Use `revision` for a commit, document version, message revision, or other
immutable identifier when available.

Set `integrity` to:

- `verified`: `content_hash` was computed from captured content.
- `unavailable`: no stable content hash could be obtained.

Register sources through the CLI:

```bash
python <skill-dir>/scripts/kiroku.py add-source \
  --dir ./kiroku \
  --kind document \
  --title "Planning notes" \
  --file docs/planning.md \
  --revision "v1" \
  --metadata 'language="en"'
```

Source identity is `kind + uri + revision`. Registering the same identity and
content is idempotent. Different content with the same identity is rejected;
provide a new revision or URI.

## Runs

A run records one create, update, review, or import operation:

- stable run ID;
- lifecycle status: `running` or `completed`;
- actor type and name;
- input source IDs;
- start and completion timestamps;
- concise summary;
- warnings.

Every record references the run that most recently generated or changed it.

Create and complete runs through the CLI:

```bash
python <skill-dir>/scripts/kiroku.py start-run \
  --dir ./kiroku \
  --operation update \
  --input src_planning_notes \
  --actor-name codex

python <skill-dir>/scripts/kiroku.py finish-run \
  --dir ./kiroku \
  --run-id run_update_example \
  --summary "Extracted current decisions and open work." \
  --warning "One assumption remains unverified."
```

Only one run may be `running`. A running run has null `completed_at` and
`summary`; a completed run requires both fields and is immutable. `build`
requires all runs to be completed.

## Records

Every record uses the common envelope:

```json
{
  "id": "rec_decision_service_only",
  "key": "decision_service_only",
  "type": "decision",
  "status": "active",
  "title": "Service-only data access",
  "summary": "Report data must come from services.",
  "scope": ["mas-jasper"],
  "tags": ["architecture"],
  "confidence": "confirmed",
  "verification_status": "verified",
  "evidence": [],
  "relations": [],
  "payload": {},
  "created_at": "2026-06-07T10:00:00Z",
  "updated_at": "2026-06-07T10:00:00Z",
  "generated_by": "run_initial",
  "content_hash": "sha256:..."
}
```

`key` is the stable logical identity supplied in a record draft. KirokuForge
derives `id` deterministically from it and rejects duplicate keys.

Create records only during a running run:

```bash
python <skill-dir>/scripts/kiroku.py add-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --file ./record-draft.json
```

See [record-draft.md](record-draft.md) for accepted fields and defaults.

Replace semantic content through `update-record`. It preserves record identity,
requires the current hash, and rejects stale concurrent writes:

```bash
python <skill-dir>/scripts/kiroku.py update-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --key decision_service_only \
  --expect-hash sha256:... \
  --file ./record-draft.json
```

Use `supersede-record` when the new record must retain a historical link:

```bash
python <skill-dir>/scripts/kiroku.py supersede-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --key decision_service_only \
  --expect-hash sha256:... \
  --file ./replacement-draft.json
```

Allowed lifecycle states:

- `proposed`
- `active`
- `resolved`
- `superseded`
- `obsolete`
- `completed`
- `cancelled`

Confidence:

- `confirmed`
- `high`
- `medium`
- `low`
- `unknown`

Verification:

- `verified`
- `partially_verified`
- `unverified`
- `contradicted`

## Record Payloads

### Fact

`statement`

### Decision

`decision`, `context`, `implications`

### Assumption

`basis`, `risk`, `validation_needed`

### Idea

`description`, optional `expected_value`

### Rejected idea

`idea`, `reason`, optional `reconsider_when`

### Task

`action`, `owner`, `priority`, `blocked_by`, `acceptance_criteria`

Priorities are `high`, `medium`, and `low`. `blocked_by` contains record IDs,
not free-form prose.

### Question

`question`, `category`, `why_matters`, `known_options`, `required_input`

### Risk

`description`, `category`, `impact`, `likelihood`, `mitigations`

### Preference

`preference`, `applies_to`, optional `reason`

### Constraint

`constraint`, `consequences`

### Implementation detail

`detail`, `components`

### Roadmap item

`outcome`, `horizon`, `priority`

Horizons are `now`, `next`, `later`, and `maybe`.

### Conflict

`claims`, optional `resolution`, `recommended_action`

### Event

`description`, `occurred_at`

## Lifecycle And Relations

Relations connect records:

- `depends_on`
- `blocks`
- `supersedes`
- `contradicts`
- `implements`
- `mitigates`
- `answers`
- `derived_from`
- `related_to`

Relation targets must exist. `supersedes` relations are managed by
`supersede-record`: their targets must have `superseded` status, each target
must have exactly one direct replacement, and replacement chains cannot cycle.

## Hashing

`content_hash` is generated by `add-record` and recalculated by `build`. It is
SHA-256 over the canonical JSON representation of the complete record excluding
`content_hash`.

Agents should preserve existing IDs and timestamps. They do not need to calculate
hashes manually.
