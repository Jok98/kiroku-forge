# KirokuForge V3 Contracts

Status: normative design specification

This document defines the semantic contracts for KirokuForge v3. JSON Schemas,
CLI behavior, validators, tests, and user interfaces MUST conform to this
document. When a generated schema or implementation conflicts with this
document, this document is authoritative until the discrepancy is resolved.

## Contents

1. Normative language and product boundary
2. Artifact classes and actors
3. Pipeline contracts
4. Canonical memory
5. Sources, evidence, and records
6. Kind and lifecycle contracts
7. CandidateBundle and ChangeSet
8. Compilation and validation
9. ContextPack
10. Identity, failure semantics, and normative scenarios

## 1. Normative Language

The terms MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

- MUST and MUST NOT define conditions required for correctness.
- SHOULD and SHOULD NOT define the expected behavior unless a documented reason
  justifies an exception.
- MAY defines optional behavior.

## 2. Product Boundary

KirokuForge is a project-memory compiler. It converts selected project evidence
into durable operational knowledge that can be reused across sessions and
agents.

KirokuForge MUST:

- preserve atomic facts, decisions, assumptions, constraints, preferences,
  proposals, tasks, questions, risks, and significant events;
- retain provenance for canonical claims;
- reconcile new information with existing memory before changing it;
- apply canonical changes atomically;
- identify structural and semantic quality problems;
- generate focused context for a future session or agent.

KirokuForge MUST NOT:

- produce an encyclopedic project or codebase overview;
- treat a generic conversation summary as durable memory;
- require Git or derive correctness from Git state;
- store generated Markdown as canonical state;
- silently convert proposals into decisions or assumptions into facts;
- modify canonical memory outside the COMPILE stage.

Raw source content belongs to the project or user operating the skill.
Canonical memory stores source descriptors and hashes, not a mandatory copy of
the complete raw source.

## 3. Artifact Classes

KirokuForge defines the following artifacts:

| Artifact | Role | Persistence | Canonical |
|---|---|---|---|
| `CaptureBundle` | Selected source material | Temporary or user-managed | No |
| `CandidateBundle` | Classified candidate records | Temporary or user-managed | No |
| `ChangeSet` | Reconciled mutations | Temporary or user-managed | No |
| `Memory` | Durable project state | Persistent | Yes |
| `AuditReport` | Validation findings | Regenerable | No |
| `ContextPack` | Focused agent handoff | Regenerable | No |

Only `Memory` is canonical. Deleting any other artifact MUST NOT change the
meaning of canonical memory.

Each non-canonical pipeline artifact MUST declare:

- `artifact_type`;
- its own `schema_version`;
- a stable artifact ID;
- `artifact_hash`, except canonical `Memory`, which uses `state_hash`;
- `generated_at`;
- the actor that generated it.

The memory schema begins at `3.0.0`. Pipeline artifact schemas begin at
`1.0.0` and evolve independently.

A pipeline `artifact_hash` covers every artifact field except `artifact_hash`
itself using canonical JSON. References to pipeline artifacts contain the
artifact type, stable ID, and artifact hash.

## 4. Actors

An actor identifies responsibility for generated artifacts and compilations.

An actor contains:

- `type`: `human`, `agent`, or `tool`;
- `name`: non-empty identifier;
- `version`: optional implementation or model version;
- `session_ref`: optional external session identifier.

Actor metadata is provenance. It MUST NOT be interpreted as proof that a claim
is correct.

## 5. Pipeline Contract

The pipeline is:

```text
CAPTURE -> CLASSIFY -> RECONCILE -> COMPILE -> VALIDATE -> HANDOFF
```

Stages MAY be invoked separately. Their input and output contracts remain the
same when an orchestrator runs the complete pipeline.

### 5.1 CAPTURE

CAPTURE selects source material relevant to the requested memory operation.

Inputs:

- files, conversations, documents, URLs, tool results, or direct observations;
- selection scope;
- optional existing source descriptors used to detect unchanged content.

Output:

- one `CaptureBundle`.

A `CaptureBundle` contains its selection scope and one or more captured
sources. Each captured source contains a capture-local ID, source descriptor,
capture timestamp, status, and material:

- status is `new`, `changed`, `unchanged`, or `unavailable`;
- available material is inline content or a retrievable reference;
- unavailable material contains a reason and no content hash;
- `unchanged` identifies its matching canonical source;
- `changed` identifies the previous canonical source snapshot.

CAPTURE MUST:

- identify every selected item with a capture-local source ID;
- compute a content hash when content is available;
- record how and when the item was captured;
- preserve a reference to or an inline copy of material needed by CLASSIFY;
- distinguish unchanged, new, changed, and unavailable material.

CAPTURE MUST NOT modify canonical memory.

Changed content at the same URI is a new source snapshot. It MUST NOT overwrite
an earlier canonical source.

### 5.2 CLASSIFY

CLASSIFY extracts reusable, atomic candidate knowledge from a `CaptureBundle`.

Inputs:

- one `CaptureBundle`;
- the normative taxonomy in this document;
- optional classification instructions supplied by the user.

Output:

- one `CandidateBundle`.

CLASSIFY MUST:

- create at most one durable claim or action per candidate;
- assign one candidate kind;
- propose an initial lifecycle state;
- attach source-based evidence;
- distinguish direct observation from inference;
- preserve uncertainty;
- include a classification rationale and classification confidence.

Classification confidence belongs only to candidates. It MUST NOT be copied
into canonical records.

CLASSIFY MUST NOT read a candidate as canonical merely because it appears in a
source. Statements about planned or hypothetical work remain proposals,
questions, or tasks according to their actual meaning.

CLASSIFY MUST NOT modify canonical memory.

### 5.3 RECONCILE

RECONCILE compares every candidate with the current canonical memory.

Inputs:

- one `CandidateBundle`;
- the current `Memory`, or an explicit indication that memory does not exist.

Output:

- one `ChangeSet`.

Every candidate MUST receive exactly one resolution:

- `create`: create a new canonical record;
- `merge`: enrich a compatible existing record;
- `supersede`: replace the semantic claim while preserving history;
- `ignore`: make no canonical change because the candidate is irrelevant,
  transient, or already represented;
- `conflict`: preserve the disagreement as a reconciliation finding;
- `needs_review`: defer because an automatic resolution is unsafe.

Each resolution MUST include a rationale and references to its candidate and
any affected canonical records.

RECONCILE MUST:

- prefer stable existing record IDs when meaning has not changed;
- distinguish metadata enrichment from semantic replacement;
- detect duplicate or near-duplicate candidates;
- detect contradictory active claims;
- produce explicit operations for every intended mutation;
- leave unresolved ambiguity visible.

RECONCILE MUST NOT modify canonical memory.

### 5.4 COMPILE

COMPILE is the only stage allowed to create or modify canonical memory.

Inputs:

- one `ChangeSet`;
- the expected base `Memory`, or no memory for initialization.

Output:

- a new `Memory`;
- one immutable compilation receipt embedded in that memory.

COMPILE MUST:

1. validate the ChangeSet structure;
2. load and structurally validate the base memory;
3. verify all base revision, state hash, and record hash preconditions;
4. evaluate every operation precondition against the base snapshot;
5. apply all operations to an in-memory prospective state;
6. validate the complete prospective state;
7. compute record and state hashes;
8. append a compilation receipt;
9. replace `memory.json` atomically.

If any step fails, COMPILE MUST leave canonical memory byte-for-byte unchanged.

COMPILE MUST use exclusive coordination sufficient to prevent two processes
from successfully compiling from the same base revision.

### 5.5 VALIDATE

VALIDATE has two layers:

- integrity validation;
- semantic audit.

Integrity validation is deterministic and blocking for COMPILE. Semantic audit
produces an `AuditReport` and does not modify memory.

VALIDATE MUST NOT automatically fix, transition, or supersede records. A
finding becomes canonical only through a later classified and reconciled
ChangeSet.

### 5.6 HANDOFF

HANDOFF selects canonical knowledge for a specific future goal.

Inputs:

- one valid `Memory`;
- a handoff request containing a goal;
- optional scopes, tags, record IDs, and size budget;
- an optional current `AuditReport`.

Output:

- one `ContextPack`.

HANDOFF MUST NOT modify memory. It MUST expose omitted counts and retrieval
hints when the requested budget excludes potentially relevant records.

## 6. Canonical Memory

`memory.json` is the single canonical artifact.

Its root contains:

- `artifact_type`: `memory`;
- `schema_version`: `3.0.0`;
- `memory_id`;
- `revision`;
- `state_hash`;
- `project`;
- `sources`;
- `records`;
- `compilations`.

### 6.1 Revision

The initial successful compilation creates revision `1`.

Every successful compilation MUST increment revision by exactly one. Failed
compilations MUST NOT consume a revision.

### 6.2 State Hash

`state_hash` authenticates the semantic state and concurrency base.

It is computed over:

- `memory_id`;
- `revision`;
- `project`;
- `sources`;
- `records`.

It excludes:

- `state_hash` itself;
- `compilations`.

Objects are serialized using canonical JSON: UTF-8, recursively sorted object
keys, no insignificant whitespace, and preserved array order. Canonical arrays
in memory MUST use these orders:

- sources by source ID;
- records by record ID;
- compilations by result revision.

Nested canonical collections MUST use these orders:

- project boundary values, scopes, and tags lexicographically;
- evidence by source ID, relation, method, and canonical locator;
- relations by type and target ID.

Lists whose order carries meaning, such as alternatives, acceptance criteria,
consequences, and mitigations, preserve authored order.

Canonicalization MUST be deterministic, idempotent, and non-mutating. It
produces a semantically equivalent copy, orders only the set-like collections
listed above, and preserves authored order everywhere else. Lexicographic
ordering uses Unicode code point order. Evidence locator ties use canonical
UTF-8 locator bytes.

Numbers with fractional values SHOULD NOT appear in canonical memory. Ordinal
enums SHOULD represent likelihood, impact, priority, and similar concepts.

### 6.3 Project

Project metadata contains:

- `name`;
- `description`;
- `goal`;
- `status`: `active`, `paused`, `completed`, or `archived`;
- `boundaries.included`;
- `boundaries.excluded`;
- `created_at`;
- `updated_at`.

The project description MUST identify the project, not attempt to document its
architecture. Boundaries SHOULD state what memory intentionally covers and
does not cover.

## 7. Sources And Provenance

A source is an immutable snapshot descriptor.

A source contains:

- `id`;
- `kind`;
- `title`;
- `uri`;
- optional `revision`;
- `integrity`: `verified` or `unverified`;
- optional `content_hash`;
- `captured_at`;
- optional `media_type`;
- optional metadata;
- `created_by` compilation ID.

Source kinds are:

- `conversation`;
- `repository_file`;
- `document`;
- `web_page`;
- `user_statement`;
- `tool_output`;
- `observation`;
- `other`.

A verified source MUST have a SHA-256 content hash. An unverified source MUST
explain through metadata why content integrity was unavailable.

After creation, a source MUST NOT be edited. Recapturing changed content MUST
create a new source with a new ID. Multiple sources MAY share a URI.

Canonical memory MUST NOT require Git commit IDs, branches, repositories, or
other Git metadata. A caller MAY store such values as opaque optional source
metadata, but no KirokuForge behavior may depend on them.

## 8. Evidence

Evidence connects a record to a source snapshot.

Evidence contains:

- `source_id`;
- `relation`;
- `method`;
- `locator`;
- `observed_at`;
- optional short `excerpt`;
- optional note.

Evidence relations are:

- `supports`;
- `refutes`;
- `contextualizes`.

Evidence methods are:

- `user_statement`;
- `direct_observation`;
- `document_read`;
- `code_inspection`;
- `test_result`;
- `tool_result`;
- `inference`.

Direct methods are all methods except `inference`. A contextualizing item is
not direct support even when its method is direct.

Locator kinds are:

- `whole_source`;
- `lines`;
- `section`;
- `message`;
- `page`;
- `selector`;
- `custom`.

Locator fields are:

| Kind | Required fields |
|---|---|
| `whole_source` | `kind` |
| `lines` | `kind`, `start_line`, `end_line` |
| `section` | `kind`, `name` |
| `message` | `kind`, `message_id` |
| `page` | `kind`, `start_page`, `end_page` |
| `selector` | `kind`, `expression` |
| `custom` | `kind`, `namespace`, `value` |

Locators MUST NOT contain fields belonging to another locator kind. Line and
page numbers are one-based positive integers. Range ends MUST be greater than
or equal to range starts.

An excerpt is a retrieval aid, not a replacement for the source. It MUST remain
within 500 Unicode characters and MUST NOT contain an unnecessary copy of raw
source content.

## 9. Canonical Records

Each record represents one reusable claim, choice, action, uncertainty, or
event.

A record contains:

- `id`;
- `key`;
- `kind`;
- `state`;
- `title`;
- `summary`;
- `scope`;
- `tags`;
- `verification`;
- `evidence`;
- `relations`;
- kind-specific `content`;
- `created_at`;
- `updated_at`;
- `created_by`;
- `updated_by`;
- `content_hash`.

IDs are opaque and immutable. They MUST NOT encode mutable meaning.

`key` is a stable human-readable logical identifier. It MUST be a lowercase
slug. Records in one supersession chain share the same key.

A key MUST have exactly one chain head. A chain head is the record with no
incoming `supersedes` relation from another record of the same key. Historical
records remain addressable.

A record's lineage status is derived:

- `current`: the record is the chain head;
- `historical`: another record supersedes it.

Lineage status is not stored as lifecycle state. Superseding a record MUST NOT
erase its previous kind-specific state, content, timestamps, or hash.

No canonical record may be deleted. Incorrect or replaced meaning is preserved
through lifecycle changes and supersession.

### 9.1 Kinds

Canonical kinds are:

| Kind | Meaning |
|---|---|
| `fact` | Observed or verifiable project truth |
| `decision` | Intentional choice already adopted |
| `assumption` | Belief still requiring validation |
| `constraint` | Mandatory limit or condition |
| `preference` | Desired but negotiable direction |
| `proposal` | Option not yet established as a decision |
| `task` | Operational work with a completion condition |
| `question` | Information still required |
| `risk` | Uncertain event or condition with impact |
| `event` | Significant occurrence worth retaining |

The following are not canonical kinds:

- `todo` and `done`: task views derived from task state;
- `conflict`: reconciliation or audit finding;
- `implementation_detail`: a fact with suitable scope and tags;
- `roadmap_item`: a task or proposal with horizon metadata;
- `rejected_idea`: a rejected proposal.

### 9.2 Verification

Verification contains:

- `status`: `unverified`, `partially_verified`, `verified`, or `contradicted`;
- optional note.

Rules:

- `verified` requires at least one direct supporting evidence item and no
  unresolved direct refuting evidence;
- `partially_verified` requires evidence but indicates incomplete, indirect, or
  mixed support;
- `contradicted` requires direct refuting evidence;
- `unverified` MUST NOT claim confirmation.

Conflicting direct support and refutation MUST produce an audit finding.

Verification is independent from lifecycle state. A record may remain active
while contradicted when reconciliation cannot safely resolve the conflict.

### 9.3 Relations

A relation contains:

- `type`;
- `target_id`;
- optional note.

Relation direction is from the containing record to `target_id`.

Supported relation types:

- `supersedes`: this record replaces the target;
- `depends_on`: this record depends on the target;
- `blocks`: this record blocks the target task;
- `answers`: this record answers the target question;
- `mitigates`: this record mitigates the target risk;
- `implements`: this record implements the target decision or proposal;
- `adopts`: this decision adopts the target proposal;
- `contradicts`: this record contradicts the target;
- `related_to`: explicit general association.

Relations MUST target existing records and MUST NOT target the containing
record. Duplicate relation tuples are invalid.

`supersedes` is managed only by `supersede_record`. It MUST connect records
with the same key and MUST form a linear, acyclic chain.

### 9.4 Scope And Tags

Scope identifies the project area in which the record applies. Tags identify
cross-cutting topics.

Both use lowercase slugs. A record MUST have at least one scope. `project` is
the default scope when no narrower area is justified.

Scope and tags MUST not be used to encode lifecycle state or record kind.

## 10. Kind Contracts

### 10.1 Fact

States:

```text
active -> obsolete
```

Content:

- required `statement`;
- optional `context`;
- optional `implications`.

### 10.2 Decision

States:

```text
active -> obsolete
```

Content:

- required `decision`;
- required `rationale`;
- optional `context`;
- optional `alternatives`;
- optional `consequences`.

A decision MUST describe an adopted choice. A choice under discussion is a
proposal.

### 10.3 Assumption

States:

```text
active -> invalidated
active -> obsolete
```

Content:

- required `assumption`;
- required `basis`;
- required `impact_if_false`;
- required `validation_plan`.

When an assumption is proven, a fact SHOULD supersede it. An invalidated
assumption requires direct refuting evidence.

### 10.4 Constraint

States:

```text
active -> obsolete
```

Content:

- required `constraint`;
- optional `rationale`;
- optional `consequences`.

### 10.5 Preference

States:

```text
active -> obsolete
```

Content:

- required `preference`;
- optional `rationale`;
- optional `applies_to`.

Preferences MUST NOT be represented as mandatory constraints.

### 10.6 Proposal

States:

```text
proposed -> accepted
proposed -> rejected
proposed -> cancelled
```

Content:

- required `proposal`;
- required `motivation`;
- optional `expected_value`;
- optional `tradeoffs`;
- optional `horizon`;
- `rejection_reason` required when rejected;
- `cancellation_reason` required when cancelled.

An accepted proposal SHOULD have an incoming `adopts` relation from a decision.
Acceptance does not itself create a decision.
`rejection_reason` MUST appear only while rejected. `cancellation_reason` MUST
appear only while cancelled.

### 10.7 Task

States:

```text
todo -> in_progress
todo -> blocked
todo -> done
todo -> cancelled
in_progress -> todo
in_progress -> blocked
in_progress -> done
in_progress -> cancelled
blocked -> todo
blocked -> in_progress
blocked -> done
blocked -> cancelled
done -> todo
cancelled -> todo
```

Content:

- required `objective`;
- required `priority`: `critical`, `high`, `medium`, or `low`;
- required non-empty `acceptance_criteria`;
- optional `owner`;
- optional `horizon`;
- `outcome` required when done;
- `cancellation_reason` required when cancelled.

A blocked task MUST have at least one incoming `blocks` relation.

A done task requires direct completion evidence. Reopening a done or cancelled
task requires an explicit transition reason in the compilation receipt.
State-specific fields such as `outcome` and `cancellation_reason` MUST be
removed when a transition leaves the state that defines them. Their previous
values remain recoverable from the compilation receipt and prior record hash.

Derived views:

```text
TODO = task in todo, in_progress, or blocked
DONE = task in done
CANCELLED = task in cancelled
```

### 10.8 Question

States:

```text
open -> answered
open -> obsolete
answered -> open
obsolete -> open
```

Content:

- required `question`;
- required `why_it_matters`;
- optional `options`;
- `answer` required when answered.

An answered question requires direct supporting evidence or an incoming
`answers` relation. Reopening requires a transition reason.
`answer` MUST appear only while the question is answered.

### 10.9 Risk

States:

```text
open -> mitigated
open -> accepted
open -> closed
mitigated -> open
mitigated -> closed
accepted -> open
accepted -> closed
closed -> open
```

Content:

- required `description`;
- required `impact`: `critical`, `high`, `medium`, or `low`;
- required `likelihood`: `high`, `medium`, `low`, or `unknown`;
- optional `mitigations`;
- `acceptance_rationale` required when accepted;
- `resolution` required when closed.

A mitigated risk SHOULD have an incoming `mitigates` relation. Closing or
reopening a risk requires direct evidence and an explicit transition reason.
`acceptance_rationale` MUST appear only while accepted. `resolution` MUST
appear only while closed.

### 10.10 Event

States:

```text
occurred
```

Content:

- required `description`;
- required `occurred_at`;
- required `significance`.

Compiler executions, validation runs, and other KirokuForge mechanics are
compilation receipts, not event records.

## 11. Candidate Bundle

A `CandidateBundle` references its input `CaptureBundle` by ID and hash.
It contains optional classification instructions and an array of candidates.

Each candidate contains:

- candidate ID;
- proposed key;
- kind and proposed state;
- title and summary;
- scope and tags;
- kind-specific content;
- evidence referencing captured source IDs;
- classification rationale;
- classification confidence: `high`, `medium`, or `low`.

Every candidate MUST reference at least one captured source. Inferred
candidates use evidence method `inference` and MUST identify the source material
from which the inference was made.

Candidate IDs exist only inside pipeline artifacts and MUST NOT become
canonical record IDs.

## 12. ChangeSet

A ChangeSet contains:

- `change_set_id`;
- target `memory_id`, or null for initialization;
- `base_revision`, or null for initialization;
- `base_state_hash`, or null for initialization;
- actor;
- `input_bundles` references containing artifact type, ID, and hash;
- summary;
- candidate resolutions;
- ordered operations;
- reconciliation findings.

It also contains one source resolution for every captured source referenced by
a candidate or operation:

- `reuse`: map the captured source to an existing canonical source ID;
- `add`: map it to an `add_source` operation and its new canonical source ID;
- `ignore`: exclude it with a reason.

Record drafts and evidence operations MUST use canonical source IDs after this
mapping. A source selected as `ignore` MUST NOT be referenced by a canonical
operation.

A ChangeSet MUST contain at least one operation that changes canonical state.
When all candidates and sources resolve without a canonical change, RECONCILE
reports a no-change result and COMPILE is not invoked.

Canonical IDs for new sources and records MUST be allocated in the ChangeSet.
This allows operations and complete drafts in the same ChangeSet to reference
one another. COMPILE validates and preserves these IDs; it does not derive them
from candidate IDs.

### 12.1 Operations

Supported operations are:

- `initialize_memory`;
- `update_project`;
- `add_source`;
- `create_record`;
- `amend_record`;
- `add_evidence`;
- `remove_evidence`;
- `set_verification`;
- `add_relation`;
- `remove_relation`;
- `transition_record`;
- `supersede_record`.

`initialize_memory` is valid only when `memory.json` does not exist and MUST be
the first operation.

`amend_record` may change only:

- title;
- summary;
- scope;
- tags.

A semantic change to kind or content requires `supersede_record`, except for
state-specific fields supplied by `transition_record`, such as task outcome,
question answer, risk resolution, or cancellation reason.

Evidence and relations use their dedicated operations.

`set_verification` changes only the verification object. It MUST be accompanied
by evidence operations in the same ChangeSet or justified by evidence already
present in the base record.

Every operation targeting an existing record MUST include its base
`expected_record_hash`. All preconditions are evaluated against the base
snapshot, not against intermediate operation results.

Multiple operations MAY target the same base record when their effects do not
conflict. Operation order is significant after all base preconditions pass.

Operations MUST have stable operation IDs. Candidate resolutions reference the
operation IDs that implement them.

Operation payloads are:

| Operation | Payload |
|---|---|
| `initialize_memory` | preallocated memory ID and complete project draft |
| `update_project` | non-empty project metadata changes |
| `add_source` | complete canonical source draft without compilation metadata |
| `create_record` | complete canonical record draft without compilation metadata or hash |
| `amend_record` | record ID, expected hash, and title, summary, scope, or tag changes |
| `add_evidence`, `remove_evidence` | record ID, expected hash, and exact evidence item |
| `set_verification` | record ID, expected hash, and verification object |
| `add_relation`, `remove_relation` | record ID, expected hash, and exact relation |
| `transition_record` | record ID, expected hash, target state, reason, and complete target-state content |
| `supersede_record` | predecessor ID, expected hash, complete successor draft, and reason |

### 12.2 Supersession

`supersede_record` contains:

- predecessor ID and expected hash;
- a complete successor draft;
- a reason.

The compiler MUST:

- validate the preallocated successor record ID;
- preserve the key;
- add the managed `supersedes` relation;
- preserve the predecessor byte-for-byte;
- set the successor compilation references and timestamps;
- reject branching or cycles.

### 12.3 Findings

Reconciliation findings use:

- stable finding ID;
- severity: `error`, `warning`, or `info`;
- code;
- message;
- candidate IDs;
- record IDs;
- recommended action.

A `conflict` or `needs_review` resolution MUST have at least one finding.

## 13. Compilation Receipts

Every successful compilation appends one immutable receipt.

A receipt contains:

- compilation ID;
- base and result revision;
- base and result state hash;
- ChangeSet ID and hash;
- initiating actor;
- compiler name and version;
- input source IDs;
- operation receipts;
- compilation timestamp;
- warnings;
- previous receipt hash;
- receipt hash.

An operation receipt records:

- operation ID and type;
- affected IDs;
- previous hashes where applicable;
- result hashes where applicable;
- transition reason where applicable.

Receipt hashes form a linear chain. The first receipt has no previous receipt
hash. It records base revision `0`, base state hash `null`, and previous receipt
hash `null`. Later receipts require non-null base and previous receipt hashes.
`receipt_hash` covers every receipt field except `receipt_hash` itself using
canonical JSON. Receipt content MUST NOT duplicate complete records.

Completed receipts are immutable. Canonical memory MUST NOT contain a running
or incomplete compilation.

## 14. Integrity Validation

Integrity validation MUST reject:

- schema violations;
- duplicate IDs;
- malformed or mismatched hashes;
- revision or receipt-chain gaps;
- unknown source, record, or compilation references;
- mutable changes to existing sources;
- invalid kind/state combinations;
- forbidden lifecycle transitions;
- missing transition reasons where required;
- invalid state-specific content;
- multiple supersession heads for one key;
- supersession branches or cycles;
- relation self-targets or duplicates;
- verified claims without direct supporting evidence;
- contradicted claims without direct refuting evidence;
- done tasks without outcome and completion evidence;
- blocked tasks without a blocker relation;
- stale ChangeSet preconditions.

Integrity findings block COMPILE.

Integrity validators MUST report stable machine-readable codes. The initial
code registry is:

| Code | Meaning |
|---|---|
| `SCHEMA_VIOLATION` | An artifact does not satisfy its JSON Schema contract |
| `ARTIFACT_HASH_MISMATCH` | A pipeline artifact hash differs from canonical content |
| `DUPLICATE_ID` | An ID is repeated in a namespace that requires uniqueness |
| `UNKNOWN_SOURCE_REFERENCE` | Evidence or a receipt references an unknown source |
| `UNKNOWN_RECORD_REFERENCE` | A relation references an unknown record |
| `UNKNOWN_COMPILATION_REFERENCE` | Canonical data references an unknown compilation |
| `UNKNOWN_OPERATION_REFERENCE` | A ChangeSet resolution references an unknown operation |
| `UNKNOWN_FINDING_REFERENCE` | A ChangeSet resolution references an unknown finding |
| `RECORD_HASH_MISMATCH` | A stored record hash differs from canonical content |
| `STATE_HASH_MISMATCH` | The root state hash differs from canonical memory state |
| `RECEIPT_HASH_MISMATCH` | A receipt hash differs from canonical receipt content |
| `RECEIPT_CHAIN_MISMATCH` | A receipt does not reference the preceding receipt hash |
| `RECEIPT_REVISION_SEQUENCE` | Receipt revisions are missing, duplicated, or inconsistent |
| `SOURCE_MUTATED` | An existing immutable source was changed |
| `INVALID_TRANSITION` | A lifecycle transition is not permitted |
| `MISSING_TRANSITION_REASON` | A required lifecycle reason is absent |
| `MULTIPLE_KEY_HEADS` | A logical key has more than one current chain head |
| `SUPERSESSION_KEY_MISMATCH` | A supersession relation connects different logical keys |
| `SUPERSESSION_BRANCH` | One predecessor has multiple direct successors |
| `SUPERSESSION_CYCLE` | Supersession relations contain a cycle |
| `RELATION_SELF_TARGET` | A relation targets its containing record |
| `RELATION_DUPLICATE` | A record repeats the same relation type and target |
| `LOCATOR_RANGE_INVALID` | A locator range ends before it starts |
| `TIMESTAMP_INVALID` | A timestamp is not a real calendar instant |
| `TIMESTAMP_ORDER_INVALID` | Related timestamps are chronologically inconsistent |
| `NONCANONICAL_ORDER` | A canonical array or nested set is not canonically ordered |
| `VERIFICATION_EVIDENCE_INVALID` | Verification state is unsupported by evidence |
| `TASK_COMPLETION_EVIDENCE_MISSING` | A done task lacks direct completion evidence |
| `BLOCKED_TASK_WITHOUT_BLOCKER` | A blocked task has no incoming blocker relation |
| `STALE_CHANGESET` | A ChangeSet precondition does not match the base memory |

Schema validation runs before cross-entity integrity checks. A schema finding
MUST include code `SCHEMA_VIOLATION`, severity `error`, and a deterministic
JSONPath rooted at `$`. A validator MAY stop after the first schema violation
because later integrity checks require a structurally valid artifact. Failure
to load or resolve the local schema contract is a pipeline execution failure,
not a finding about the artifact.

ChangeSet validation evaluates all root and record preconditions against the
same immutable base `Memory`. A mismatch in target memory ID, base revision,
base state hash, or expected record hash produces `STALE_CHANGESET`. If the
target memory is absent or unexpectedly present, checks that depend on its
records and sources MUST NOT run.

An `add_source` operation that allocates an ID already present in base memory
produces `SOURCE_MUTATED`, even when some submitted fields match. Unchanged
sources use source resolution `reuse`; changed source content receives a new
canonical source ID.

Transition validation MUST check the kind-specific lifecycle edge and validate
the complete resulting record after all operations in the same ChangeSet are
applied in order. Evidence added in that ChangeSet may satisfy terminal-state
requirements. A missing explicit reason produces `MISSING_TRANSITION_REASON`;
a forbidden edge or invalid target-state record produces
`INVALID_TRANSITION`.

One malformed object MAY produce multiple findings when multiple invariants are
independently violated. Conformance fixtures SHOULD isolate one primary code.

## 15. Semantic Audit

Semantic audit produces an `AuditReport`.

Each audit finding contains:

- stable fingerprint;
- severity;
- category;
- code;
- message;
- record IDs;
- source IDs;
- detector name, type, and version;
- recommended action.

An `AuditReport` references the exact memory ID, revision, and state hash it
audited. It contains the applied audit policy and an ordered finding array.
Age-based TODO staleness is enabled only when the policy declares
`stale_todo_after_days`.

Detector types are:

- `rule`;
- `heuristic`;
- `agent`.

Audit SHOULD detect:

- active contradictory claims;
- likely semantic duplicates;
- decisions with weak or circular rationale;
- accepted proposals without an adopting decision;
- tasks whose acceptance criteria are not testable;
- potentially stale TODO items;
- blocked tasks whose blocker is resolved;
- answered questions still marked open;
- risks closed without convincing resolution evidence;
- obsolete assumptions;
- unsupported active knowledge;
- relations that no longer match record lifecycle.

Age-based staleness MUST be opt-in through audit policy. There is no universal
default age after which a task becomes stale.

Audit findings do not block COMPILE unless an explicit policy promotes a
specific finding code to an integrity rule.

## 16. Context Pack

A handoff request contains:

- required goal;
- optional scopes;
- optional tags;
- optional seed record IDs;
- optional inclusion or exclusion rules;
- optional maximum records or estimated token budget.

A `ContextPack` contains these ordered sections:

1. mission;
2. active decisions;
3. active constraints;
4. applicable preferences;
5. TODO;
6. open risks;
7. open questions;
8. relevant facts and assumptions;
9. recent DONE;
10. recent significant events;
11. recent compilation changes;
12. relevant audit findings;
13. selected sources;
14. omitted record counts and retrieval hints.

The structured artifact stores this order in the constant `section_order`
array and stores section payloads in the `sections` object. This avoids relying
on JSON object member order. It also embeds the handoff request and the exact
memory snapshot reference used for selection.

Selection MUST consider:

- explicit IDs, scope, and tags;
- direct and reverse relations;
- lifecycle state;
- relevance to the requested goal;
- recency only after semantic relevance.

The budget SHOULD be distributed across sections. A large task list MUST NOT
silently crowd out applicable decisions and constraints.

A selected record entry MUST retain:

- canonical record ID and key;
- kind and state;
- title and summary;
- relevant content;
- relation references;
- evidence source IDs.

Generated explanations or relevance reasons MUST be marked as generated and
MUST NOT be confused with canonical record content.

The ContextPack is an agent projection. The viewer MAY consume Memory,
AuditReport, and ContextPack directly. Markdown is optional and never
canonical.

## 17. Identity, Time, And Hashes

Canonical IDs use opaque prefixed values:

- `mem_` for memory;
- `src_` for source;
- `rec_` for record;
- `cmp_` for compilation.

Pipeline artifact IDs use:

- `cap_` for CaptureBundle;
- `cnd_` for CandidateBundle;
- `chg_` for ChangeSet;
- `aud_` for AuditReport;
- `ctx_` for ContextPack.

Nested pipeline entities use:

- `csrc_` for a captured source;
- `can_` for a candidate;
- `op_` for a ChangeSet operation;
- `fnd_` for a reconciliation or audit finding.

Implementations MUST generate globally unique IDs. Callers MUST treat IDs as
opaque. An ID suffix starts with a lowercase ASCII letter or digit and MAY
continue with lowercase ASCII letters, digits, underscores, or hyphens. A
suffix contains at most 128 characters.

Timestamps use calendar-valid RFC 3339 UTC with a `Z` suffix. JSON Schema
constrains their lexical form; integrity validation MUST reject impossible
calendar dates even when a schema implementation treats `format` as an
annotation. A compiler MUST NOT change a timestamp solely because memory was
read, validated, queried, rendered, or handed off.

Hashes use lowercase SHA-256 with the form:

```text
sha256:<64 lowercase hexadecimal characters>
```

Record `content_hash` covers all record fields except `content_hash`. It
includes provenance, relations, lifecycle state, and compilation references.

## 18. Failure Semantics

Pipeline failures MUST be explicit.

- CAPTURE failure produces no valid CaptureBundle.
- CLASSIFY failure produces no valid CandidateBundle.
- RECONCILE failure produces no valid ChangeSet.
- COMPILE failure leaves canonical memory unchanged.
- VALIDATE failure leaves canonical memory unchanged.
- HANDOFF failure produces no partial ContextPack.

Partial diagnostic artifacts MAY be emitted separately, but MUST be marked
invalid and MUST NOT be accepted by downstream stages.

## 19. Normative Scenarios

### 19.1 First Compilation

When memory does not exist:

1. CAPTURE produces source snapshots.
2. CLASSIFY produces candidates.
3. RECONCILE resolves them and emits a ChangeSet whose first operation is
   `initialize_memory`.
4. COMPILE creates revision `1`, canonical records, and the first receipt.

COMPILE MUST fail if memory appears before the atomic creation step.

### 19.2 Unchanged Source

When CAPTURE computes the same URI, revision, and content hash as an existing
source, it marks the item unchanged. RECONCILE SHOULD avoid `add_source` and
SHOULD resolve candidates already represented in memory as `ignore` or `merge`.

### 19.3 Changed Source

When content at a known URI changes, CAPTURE creates a new source snapshot.
RECONCILE determines whether new evidence enriches, contradicts, or supersedes
existing records. The previous source remains immutable.

### 19.4 Completing A Task

A task transition to done MUST include:

- expected base record hash;
- transition reason;
- outcome;
- direct completion evidence.

If any requirement is missing, integrity validation rejects the ChangeSet.

### 19.5 Semantic Correction

Correcting the meaning of a fact or decision MUST use `supersede_record`.
Editing its content in place is invalid. The previous record remains in the
same key chain and the successor becomes the chain head.

### 19.6 Contradictory Evidence

When new direct evidence refutes an active record and automatic replacement is
unsafe, RECONCILE resolves the candidate as `conflict` or `needs_review`.
Canonical memory may receive the refuting evidence through an explicit
operation, but the disagreement remains visible in reconciliation and audit
findings.

### 19.7 Concurrent ChangeSets

If two ChangeSets use the same base revision, only the first successfully
compiled ChangeSet may commit. The second MUST fail because its base revision
or state hash is stale. It must be reconciled again against the new memory.

### 19.8 Reopening Work

Reopening a done task, answered question, or closed risk requires:

- an allowed transition;
- expected base hash;
- explicit reason;
- evidence where required by the kind contract.

The receipt preserves the reason and both state hashes.

## 20. Acceptance Criteria

The v3 contract is implementable when schemas and deterministic validators can
answer all of these questions without relying on undocumented behavior:

- Is each pipeline artifact structurally valid?
- Is a record kind and state combination valid?
- Is a requested lifecycle transition allowed?
- Is a change metadata enrichment or semantic supersession?
- Does every candidate have one explicit reconciliation outcome?
- Are all mutations tied to the expected base snapshot?
- Can a compilation either commit completely or leave memory unchanged?
- Can every verified claim be traced to direct evidence?
- Is there exactly one head for each logical record key?
- Can an agent generate a bounded handoff without reading all raw sources?
- Can a user inspect TODO, DONE, decisions, risks, questions, evidence, and
  history from structured canonical data?

JSON Schemas MUST be derived from this document. They MUST NOT introduce new
semantic categories, states, transitions, or mutation behavior without first
updating this contract.
