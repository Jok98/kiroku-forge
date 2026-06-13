# Architecture

## Main Flow

1. The user invokes `$kiroku-forge` when project context should persist.
2. The agent reads `SKILL.md`.
3. The agent chooses one mode: `read`, `update`, `handoff`, `cleanup`, or
   `init`.
4. For new hubs or broad updates, the agent reads `references/file-contract.md`.
5. The agent reads `kiroku/START_HERE.md` first when a hub already exists.
6. The agent opens only the hub files needed for the mode and request.
7. The agent inspects only the project evidence needed for the update.
8. The agent edits the owning Markdown files directly.
9. The agent records one meaningful update in `kiroku/LOG.md`.
10. The agent runs the final checklist before responding.

## Boundaries

- `SKILL.md` defines how agents should behave.
- `references/file-contract.md` defines the default structure and ownership of
  files in a project memory hub.
- `scripts/init_hub.py` initializes a target hub from bundled templates.
- `scripts/check_hub.py` provides lightweight validation for the default hub
  contract.
- `assets/templates/kiroku/` contains starter files for a new hub.
- `kiroku/` is project memory for this repository and should be useful even
  without reading the conversation that produced it.

## Patterns To Preserve

- Use Markdown as the source of truth.
- Choose one operating mode before reading beyond `START_HERE.md`.
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
- `scripts/init_hub.py` initializes default hubs from templates.
- `scripts/check_hub.py` validates the Markdown hub shape.
- `agents/openai.yaml` exposes the skill with the short description
  "Maintain a Markdown project memory hub".
