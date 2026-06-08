---
name: kiroku-forge
description: Build and maintain durable project memory by capturing evidence, classifying reusable knowledge, reconciling it with existing state, compiling canonical records, validating quality, and generating focused handoffs. Use when project context must persist across sessions or agents. Do not use for generic summaries or project documentation.
---

# KirokuForge

KirokuForge is being rebuilt as a project-memory compiler.

## Product Boundary

- Preserve durable operational knowledge, not an encyclopedic project overview.
- Keep one structured canonical memory owned by the project using the skill.
- Keep raw source content outside canonical memory and reference it through provenance.
- Do not depend on Git.
- Treat human views and agent context packs as generated, read-only projections.

## Target Pipeline

1. `CAPTURE`: identify and register selected conversations, files, documents, and observations.
2. `CLASSIFY`: extract atomic candidate facts, decisions, assumptions, constraints, preferences, proposals, tasks, questions, risks, and events.
3. `RECONCILE`: compare candidates with current memory and produce an explicit change set.
4. `COMPILE`: apply the complete change set atomically to canonical memory.
5. `VALIDATE`: verify structural integrity and report semantic quality problems.
6. `HANDOFF`: generate a goal-focused context pack for the next session or agent.

Only `COMPILE` may modify canonical memory.

## Normative Contract

Read [references/contracts-v3.md](references/contracts-v3.md) before designing
schemas, commands, validators, storage, projections, or viewer behavior. It is
the semantic source of truth for v3. Reuse
[schemas/common-v1.schema.json](schemas/common-v1.schema.json) for shared IDs,
hashes, timestamps, actors, and evidence locators. Validate canonical
`memory.json` shape with
[schemas/memory-v3.schema.json](schemas/memory-v3.schema.json).
Validate pipeline artifacts with
[schemas/capture-bundle-v1.schema.json](schemas/capture-bundle-v1.schema.json),
[schemas/candidate-bundle-v1.schema.json](schemas/candidate-bundle-v1.schema.json),
[schemas/change-set-v1.schema.json](schemas/change-set-v1.schema.json),
[schemas/audit-report-v1.schema.json](schemas/audit-report-v1.schema.json), and
[schemas/context-pack-v1.schema.json](schemas/context-pack-v1.schema.json).
Their shared definitions are in
[schemas/pipeline-v1.schema.json](schemas/pipeline-v1.schema.json).
Use [tests/fixtures/memory/manifest.json](tests/fixtures/memory/manifest.json)
as the conformance matrix for schema and integrity behavior.
Use
[tests/fixtures/pipeline/manifest.json](tests/fixtures/pipeline/manifest.json)
as the pipeline artifact schema conformance matrix.
Use [scripts/kiroku_core/canonical.py](scripts/kiroku_core/canonical.py) and
[scripts/kiroku_core/hashing.py](scripts/kiroku_core/hashing.py) for canonical
serialization, memory ordering, and SHA-256 hashes.
Use [scripts/kiroku_core/schema.py](scripts/kiroku_core/schema.py) for offline
runtime schema validation and
[scripts/kiroku_core/findings.py](scripts/kiroku_core/findings.py) for stable
validation results.
Use [scripts/kiroku_core/integrity.py](scripts/kiroku_core/integrity.py) for
deterministic multi-finding integrity validation of canonical memory.
Use [scripts/kiroku_core/change_set.py](scripts/kiroku_core/change_set.py) to
validate ChangeSet hashes, base preconditions, immutable source identities, and
lifecycle transitions before compilation.

## Current State

The previous v2 implementation has been removed. The normative v3 contract and
all canonical and pipeline artifact schemas are defined. Runtime validation for
pipeline artifacts other than ChangeSet, plus the remaining executable
pipeline behavior, still need to be implemented. Canonical serialization,
ordering, hashing, offline schema validation, memory integrity validation, and
ChangeSet precondition and lifecycle validation are implemented. The fixture
corpora define expected schema and integrity outcomes.
