# Architecture

## Main Flow

1. The user invokes `$kiroku-forge` when project context should persist.
2. The agent reads `SKILL.md`.
3. The agent chooses one mode: `read`, `update`, `handoff`, `cleanup`, or
   `init`.
4. The agent chooses the focus: global hub or a specific workstream track.
5. For new hubs or broad updates, the agent reads `references/file-contract.md`.
6. The agent reads `kiroku/START_HERE.md` first when a hub already exists.
7. If several tracks may match, the agent reads `kiroku/TRACKS.md` and then the
   selected track `START_HERE.md`.
8. The agent opens only the hub or track files needed for the mode and request.
9. The agent inspects only the project evidence needed for the update.
10. The agent edits the owning Markdown files directly.
11. The agent records one meaningful update in the relevant `LOG.md`.
12. The agent runs the final checklist before responding.

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
- `scripts/init_hub.py` initializes a target hub from bundled templates.
- `scripts/check_hub.py` provides lightweight validation for the default hub
  contract.
- `scripts/init_hub.py --with-tracks` adds `TRACKS.md`; repeated
  `--track <slug>` creates concrete track folders from `_template`.
- `scripts/check_hub.py` validates track index routing and track folders when
  `TRACKS.md` or `tracks/` exists.
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
- Choose a focus before reading detailed memory: top-level global files for
  shared project truth, or one track for a specific workstream.
- Do not read sibling tracks unless the user asks or a direct dependency is
  visible.
- Use `scripts/init_hub.py` for deterministic template copying when creating a
  new hub.
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

- `skill-creator` is used to validate the shape of this skill.
- `references/track-contract.md` is the detailed contract for optional
  workstream tracks.
- `scripts/init_hub.py` initializes default hubs from templates.
- `scripts/check_hub.py` validates the Markdown hub shape.
- `agents/openai.yaml` exposes the skill with the short description
  "Maintain a Markdown project memory hub".
