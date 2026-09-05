# Constraints

## Active Constraints

### Constraint: Markdown remains canonical

Status: active

Rule:
Keep readable Markdown as primary memory with minimal metadata. Do not introduce
canonical JSON, databases, schemas, receipts, hashes, or generated indexes by default.

Why:
A hidden machine layer would repeat the rejected compiler-style memory design
and make direct human editing less useful.

### Constraint: Evidence and authorization govern memory

Status: active

Rule:
Current instructions and verified project evidence override memory. Read modes
do not create, repair, or clean memory; writes require the current task's authority.

Why:
Stale notes and historical approvals cannot authorize new actions or establish
current runtime behavior.

### Constraint: Keep work within its owner scope

Status: active

Rule:
Store task details in their track, promote only shared conclusions, and compress
only changed owner files and directly affected references during a local update.

Why:
Unrelated track reads and global progress duplication inflate context and risk
modifying work outside the requested scope.

### Constraint: Readiness requires curated content

Status: active

Rule:
Do not report initialization complete with scaffold prose or unresolved strict
checker findings. Review translated placeholders and semantic accuracy separately.

Why:
Template copies and structurally valid text are not verified project knowledge.

### Constraint: Derived outputs remain secondary

Status: active

Rule:
Generated HTML, project documentation, tags, IDs, and caches must not become a
competing source of memory; a first viewer should be read-only.

Why:
Parallel editable representations create drift and unnecessary synchronization.

## Out Of Scope

- Rebuilding the removed v3 runtime, schemas, or compiler pipeline.
- Maintaining compatibility with removed v3 fixtures or test infrastructure.
- Building a full CLI, database layer, or editable web app before the need is established.

## Forbidden Changes

- Hidden canonical stores with generated Markdown projections.
- Generic conversation recaps or command chatter preserved as project knowledge.
- New or modified automated test artifacts without the user's required approval.
