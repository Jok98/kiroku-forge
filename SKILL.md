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

## Current State

The previous v2 implementation has been removed. The normative v3 contract and
canonical memory schema are defined. Pipeline artifact schemas, integrity
validation, and executable behavior still need to be implemented and validated.
