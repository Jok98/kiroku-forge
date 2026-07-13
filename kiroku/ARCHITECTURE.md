# Architecture

## Main Flow

1. The skill triggers when durable project context, task continuation, or
   project onboarding is needed.
2. The agent reads `SKILL.md`, locates `kiroku/`, and chooses one mode plus a
   global or track focus.
3. `init` inspects project evidence, scaffolds the base hub, replaces every
   placeholder, and validates with strict warnings.
4. `start-task` reads global routing, reuses a matching track, or scaffolds one
   with state, roadmap, work, and handoff context.
5. `read-task` reads one track plus only constraining global context;
   `read-project` reads global truth and active-track handoffs.
6. Write modes update only owner files, promote cross-track truth when needed,
   add one concise log entry, and run the final checklist.

## Optional Derived Views

- A future local viewer should parse the standard Markdown hub and generate
  semantic HTML with stable generated IDs and `data-*` attributes for type,
  status, area, and tags.
- The viewer should be read-only at first. If editing is ever added, it must
  write back to the canonical Markdown files.
- A future documentation mode may use `kiroku/` as context, but project docs
  should live outside `kiroku/` and must be verified against code, manifests,
  and runnable commands before writing.

## Boundaries

- `SKILL.md` defines how agents should behave.
- `references/file-contract.md` defines the default structure and ownership of
  files in a project memory hub.
- `references/track-contract.md` defines optional workstream routing,
  lifecycle, promotion, closure, and track entry patterns.
- `scripts/init_hub.py` scaffolds a target hub from bundled templates; it does
  not replace the evidence-gathering part of `init`.
- `scripts/check_hub.py` provides lightweight validation for the default hub
  contract.
- `scripts/init_hub.py --with-tracks` adds `TRACKS.md`; repeated `--track`
  creates or completes concrete track folders without implicit overwrite.
- `scripts/check_hub.py` validates routing, required track files, milestone
  fields and identifiers, allowed statuses, and the one-in-progress invariant.
- `assets/templates/kiroku/` contains starter files for a new hub.
- `assets/templates/kiroku/TRACKS.md` and
  `assets/templates/kiroku/tracks/_template/` contain starter files for the
  optional track layer.
- `kiroku/` is project memory for this repository and should be useful even
  without reading the conversation that produced it.
- Optional `TRACKS.md` and `tracks/<slug>/` folders isolate unrelated active
  workstreams inside the same project hub.
- Generated HTML, project documentation, and any query cache are outputs or
  aids, not project memory sources.

## Patterns To Preserve

- Use Markdown as the source of truth.
- Choose one operating mode before reading beyond `START_HERE.md`.
- Distinguish task reads from whole-project onboarding.
- Choose a focus before reading detailed memory: top-level global files for
  shared project truth, or one track for a specific workstream.
- Do not read sibling tracks unless the user asks or a direct dependency is
  visible.
- Use `scripts/init_hub.py` for deterministic template copying when creating a
  new hub or adding missing files to an existing track.
- Make the reason behind a decision as important as the decision itself.
- Keep `START_HERE.md` strict: target 25-40 lines, fixed sections, no copied
  detail.
- Avoid reading the whole hub unless the user asks for full review, migration,
  cleanup, or major restructuring.
- Compress memory during every update: merge duplicates, remove stale text,
  and keep detail in the owning file.
- Keep operational files current-tense; put chronological history in `LOG.md`
  unless it explains an active decision, constraint, risk, or rejected idea.
- Run the final checklist before finishing any write mode.
- Run `scripts/check_hub.py` after init, cleanup, or broad updates when the
  checker scope matches the change.
- Prefer updating existing sections to appending repeated summaries.
- Keep technical mechanisms out of the memory unless they directly help future
  work.
- Prefer semantic rendering from structured Markdown over a vanilla Markdown to
  HTML conversion when building a local UI.
- Promote track information to top-level files only when it affects multiple
  tracks, multiple repositories, shared architecture, or global constraints.

## Important Details

- The previous compiler pipeline, JSON schemas, and deterministic Python tests
  were removed intentionally.
- The new design is agentic and text-first. Scripts are acceptable when they
  provide small initialization, validation, or repetition wins without becoming
  the memory source of truth.
- The skill should not require Git, but Git status is useful while developing
  this skill repository.

## Integration Points

- `/home/mmoi/.codex/AGENTS.md` provides bounded context-driven activation,
  mode selection, authority, write-safety, and milestone-update rules.
- `skill-creator` is used to validate the shape of this skill.
- `references/track-contract.md` is the detailed contract for optional
  workstream tracks.
- `scripts/init_hub.py` scaffolds default hubs and task workspaces from templates.
- `scripts/check_hub.py` validates the Markdown hub shape.
- `agents/openai.yaml` exposes the skill with the short description
  "Initialize and resume Markdown project memory".
