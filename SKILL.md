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

## Current State

The previous v2 implementation has been removed. No executable command or data
contract is currently defined. Specify and validate the v3 contracts before
adding implementation code.
