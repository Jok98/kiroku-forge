# Roadmap

## Milestones

### M-01: Analyze the current skill and memory

Status: completed

Objective:
Reconstruct the current architecture, verify the complete Kiroku hub, and
identify gaps against the requested workflows.

Scope:
- `SKILL.md`, contracts, helpers, templates, project memory, and global
  `/home/mmoi/.codex/AGENTS.md` behavior.

Expected artifacts:
- Evidence-backed analysis, findings, risks, and execution roadmap.

Dependencies:
- None.

Validation:
- Full memory read, contract comparison, helper smoke tests, and Git review.

Completion criteria:
- Every requested workflow is classified as implemented, partial, or missing.

Risks:
- Historical v3 memory could be mistaken for current architecture.

### M-02: Define the operating model

Status: completed

Objective:
Define project initialization, task workspace, focused task reading, and full
project onboarding as separate workflows.

Scope:
- Skill trigger, operating modes, file ownership, task routing, and roadmap
  contract.

Expected artifacts:
- `SKILL.md`, `references/file-contract.md`, and
  `references/track-contract.md`.

Dependencies:
- M-01.

Validation:
- Skill validation, terminology search, line-budget check, and diff review.

Completion criteria:
- Modes and ownership rules are explicit and non-overlapping.

Risks:
- Contract detail could make `SKILL.md` exceed its progressive-disclosure limit.

### M-03: Implement deterministic task scaffolding and validation

Status: completed

Objective:
Create roadmap files automatically and reject structurally invalid task
workspaces.

Scope:
- Track templates, `scripts/init_hub.py`, and `scripts/check_hub.py`.

Expected artifacts:
- `ROADMAP.md` template, additive track completion, roadmap checker rules.

Dependencies:
- M-02.

Validation:
- Fresh-hub, legacy-track, strict-placeholder, missing-roadmap, and multiple-
  in-progress milestone smoke tests.

Completion criteria:
- New and migrated tracks contain roadmaps; invalid roadmaps fail validation.

Risks:
- Legacy track completion could overwrite durable user memory.

### M-04: Migrate KirokuForge memory to its own task model

Status: completed

Objective:
Make this repository's hub accurately describe and route the current
restructuring work.

Scope:
- Global Kiroku files, `TRACKS.md`, and this task workspace.

Expected artifacts:
- Concise global memory and a complete `autonomous-memory-routing` track.

Dependencies:
- M-03.

Validation:
- Strict hub checker, placeholder search, line-budget review, and Git diff.

Completion criteria:
- Global memory contains only project-wide truth, the track owns initiative
  detail, no stale mode descriptions remain, and strict validation passes.

Risks:
- Progress may be duplicated between global and track files.

### M-05: Synchronize discovery surfaces and forward-test

Status: completed

Objective:
Align skill metadata and retained documentation, then prove the workflows with
fresh agents using isolated artifacts.

Scope:
- `agents/openai.yaml`, retained public documentation, and temporary projects
  for `init`, `start-task`, `read-task`, and `read-project`.

Expected artifacts:
- Aligned discovery metadata and independent forward-test evidence.

Dependencies:
- M-04.

Validation:
- Fresh-agent outputs, generated hub inspection, checker results, and diff
  review.

Completion criteria:
- Each workflow is selected and executed correctly without leaked conclusions.

Risks:
- Test prompts may accidentally reveal expected routing behavior.

### M-06: Enable context-driven autonomous use globally

Status: completed

Objective:
Teach Codex when to read, initialize, start, and update KirokuForge without an
explicit skill invocation.

Scope:
- `/home/mmoi/.codex/AGENTS.md` only after M-05 passes.

Expected artifacts:
- A global project-memory policy with triggers, exclusions, authority rules,
  conflict handling, and milestone update behavior.

Dependencies:
- M-05.

Validation:
- Instruction-priority review, trigger scenarios, exclusions, and final diff.

Completion criteria:
- The global policy autonomously uses KirokuForge when context warrants it and
  avoids writes in analysis-only or trivial tasks.

Risks:
- Over-triggering or global-policy conflicts could affect unrelated projects.

### M-07: Audit the complete objective

Status: completed

Objective:
Prove every explicit requirement from the user objective against current
files and executable behavior.

Scope:
- Skill, memory, helper behavior, forward-test evidence, and global policy.

Expected artifacts:
- Requirement-to-evidence completion audit.

Dependencies:
- M-06.

Validation:
- Re-run all relevant validators and inspect every authoritative artifact.

Completion criteria:
- No requirement is missing, contradicted, weakly evidenced, or unverified.

Risks:
- Narrow checks could be mistaken for proof of end-to-end behavior.
