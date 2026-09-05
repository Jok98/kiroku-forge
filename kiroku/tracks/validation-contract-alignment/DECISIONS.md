# Decisions

## Active Decisions

### Decision: Name translated sections and handoff exceptions explicitly

Status: active

Decision:
Use `--track-section` for an observed index heading and repeated
`--allow-long-handoff` paths only for user-requested extended handoffs.

Rationale:
Section names cannot be inferred reliably across languages; a length exception
must not suppress diagnostics for other handoffs or unrelated content.

Consequences:
- Technical field labels and status values remain invariant while prose is translated.
- Handoff length targets are advisory; only hard caps are enforced by default.
- Local updates compress only the owner files and directly affected references.

### Decision: Select custom hub directories explicitly

Status: active

Decision:
Treat the positional path as a project root unless it is named `kiroku` or the
caller supplies `--hub-dir` to select the hub directory itself.

Rationale:
A project or track may contain an unrelated `START_HERE.md`. That single file
cannot safely identify where global memory should be created.

Consequences:
- Existing custom hub names require an explicit flag.
- The checker and scaffolder must use the same path semantics.
- This local CLI change is reversible and needs no new dependency.

### Decision: Preserve the existing validation approach

Status: active

Decision:
Use focused runtime checks, isolated helper executions, structural validation,
and independent review without adding automated test artifacts.

Rationale:
The repository intentionally has no test suite and the user's policy requires
separate approval before creating or modifying tests.

Consequences:
- Record actual validation and its limits at each checkpoint.
- A future persistent regression suite remains a separate approval decision.
