# Constraints

## Active Constraints

<!-- kiroku:entry {"version":1,"id":"CON-001","type":"constraint","status":"active"} -->
### Constraint: Markdown remains canonical

Status: active

Rule:
Keep readable Markdown as primary memory with minimal metadata. The approved
`memory.sqlite` is a derived per-hub snapshot; its schema and fingerprints serve
retrieval and freshness only. Do not make the database independently editable
or introduce a canonical JSON store.

Why:
A hidden machine layer would repeat the rejected compiler-style memory design
and make direct human editing less useful.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"CON-002","type":"constraint","status":"active"} -->
### Constraint: Evidence and authorization govern memory

Status: active

Rule:
Current instructions and verified project evidence override memory. Read modes
do not create, repair, or clean memory; writes require the current task's authority.

Why:
Stale notes and historical approvals cannot authorize new actions or establish
current runtime behavior.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"CON-003","type":"constraint","status":"active"} -->
### Constraint: Keep work within its owner scope

Status: active

Rule:
Store task details in their track, promote only shared conclusions, and compress
only changed owner files and directly affected references during a local update.

Why:
Unrelated track reads and global progress duplication inflate context and risk
modifying work outside the requested scope.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"CON-004","type":"constraint","status":"active"} -->
### Constraint: Readiness requires curated content

Status: active

Rule:
Do not report initialization complete with scaffold prose or unresolved strict
checker findings. Review translated placeholders and semantic accuracy separately.

Why:
Template copies and structurally valid text are not verified project knowledge.
<!-- kiroku:end -->

<!-- kiroku:entry {"version":1,"id":"CON-005","type":"constraint","status":"active"} -->
### Constraint: Derived outputs remain secondary

Status: active

Rule:
Generated HTML, project documentation, and caches must not become a competing
source of memory; a first viewer should be read-only. Stable entry IDs and typed
metadata live in the authoritative Markdown and are copied into derived views.

Why:
Parallel editable representations create drift and unnecessary synchronization.
<!-- kiroku:end -->

## Out Of Scope

- Rebuilding the removed v3 runtime or canonical JSON compiler pipeline.
- Maintaining compatibility with removed v3 fixtures or test infrastructure.
- Building an editable web app, shared memory service, or custom storage engine.

## Forbidden Changes

- Hidden canonical stores with generated Markdown projections.
- Generic conversation recaps or command chatter preserved as project knowledge.
