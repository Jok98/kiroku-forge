# Architecture

## Main Flow

1. Resolve the project boundary and memory hub; choose a mode and global or track focus.
2. Read the relevant entrypoint and only the owner files needed for that mode.
3. For authorized writes, verify project evidence and read the applicable contracts.
4. Scaffold missing files if needed; curate Markdown directly and align task progress.
5. Validate structure, review semantic accuracy, and leave a focused handoff.

## Responsibilities

- `SKILL.md` owns authority, modes, selective reading, write workflow, and checklist.
- `references/file-contract.md` owns file responsibilities, language and entry
  syntax, handoff rules, helper commands, and validation boundaries.
- `references/track-contract.md` owns index entries, lifecycle, roadmap shape,
  promotion, and closure.
- `scripts/init_hub.py` plans template copies and index insertion before writing.
  It validates destination shapes and preserves existing files in additive mode.
- `scripts/check_hub.py` owns lightweight Markdown parsing and structural checks.
  The scaffolder reuses its heading and code-fence parsing for consistent index edits.
- `assets/templates/kiroku/` holds the base scaffold and optional track templates.
- This `kiroku/` hub records the skill project's shared context and task routing.

## Helper Behavior

- A positional path is a project root unless named `kiroku`; `--hub-dir`
  explicitly selects a custom hub directory. `START_HERE.md` alone is not detection.
- `--track` creates or completes task files; `--track-section` selects an observed
  level-two index heading. Missing or ambiguous sections fail before copies.
- Preflight rejects destination type collisions, dangling symlinks, and paths
  escaping the selected hub. An explicitly chosen hub may itself be an alias.
- The checker validates routing in both directions, required workspace files,
  actual local handoff targets, milestone identifiers and fields, and one in-progress milestone.
- Markdown field parsing respects section boundaries and fenced examples while
  allowing prose, bullets, and fenced content as values.
- Handoff targets are advisory; the checker enforces global/track caps with
  explicit file-specific exceptions for user-requested extended handoffs.
- The scripts use Python's standard library; no database, schema runtime, or Git dependency is required.

## Boundaries To Preserve

- Memory supplies context, never authority or permission.
- Initialization requires verified content; a successful copy is only scaffolding.
- Global files contain shared facts; detailed task progress stays local.
- Read modes and unrelated tracks remain untouched during focused memory work.
- Structural validity does not establish factual accuracy or semantic completion.
- Copies and index writes are not transactional; preflight prevents known
  structural failures, while later I/O failures can still leave partial scaffolding.

## Future Outputs

A future local UI should derive semantic views from Markdown entry patterns.
Generated IDs, tags, HTML, documentation, or query caches must remain disposable
or independently maintained outputs, never a competing memory source. Viewer
and documentation-mode design are not part of the implemented skill runtime.
