# Architecture

## Main Flow

1. The user invokes `$kiroku-forge` when project context should persist.
2. The agent reads `SKILL.md`.
3. For new hubs or broad updates, the agent reads `references/file-contract.md`.
4. The agent reads `kiroku/START_HERE.md` first when a hub already exists.
5. The agent opens only the hub files needed for the request.
6. The agent inspects only the project evidence needed for the update.
7. The agent edits the owning Markdown files directly.
8. The agent records one meaningful update in `kiroku/LOG.md`.

## Boundaries

- `SKILL.md` defines how agents should behave.
- `references/file-contract.md` defines the default structure and ownership of
  files in a project memory hub.
- `assets/templates/kiroku/` contains starter files for a new hub.
- `kiroku/` is project memory for this repository and should be useful even
  without reading the conversation that produced it.

## Patterns To Preserve

- Use Markdown as the source of truth.
- Make the reason behind a decision as important as the decision itself.
- Keep `START_HERE.md` strict: target 25-40 lines, fixed sections, no copied
  detail.
- Avoid reading the whole hub unless the user asks for full review, migration,
  cleanup, or major restructuring.
- Compress memory during every update: merge duplicates, remove stale text,
  and keep detail in the owning file.
- Prefer updating existing sections to appending repeated summaries.
- Keep technical mechanisms out of the memory unless they directly help future
  work.

## Important Details

- The previous compiler pipeline, JSON schemas, and deterministic Python tests
  were removed intentionally.
- The new design is agentic and text-first. Scripts may be added later only
  when repetition or validation needs justify them.
- The skill should not require Git, but Git status is useful while developing
  this skill repository.

## Integration Points

- `skill-creator` is used to validate the shape of this skill.
- `agents/openai.yaml` exposes the skill with the short description
  "Maintain a Markdown project memory hub".
