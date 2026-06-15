# Work

## Ongoing

- Prepare a forward-test where a fresh agent reads only `START_HERE.md` first.

## TODO

### Task: Review the first Markdown hub

Status: todo
Completion:
The user and agent agree that the generated files are readable, compact, and
useful enough to keep as the base format.

Notes:
- Watch for over-explaining.
- Check whether every file has a clear owner role.

### Task: Forward-test with a fresh agent

Status: todo
Completion:
A separate agent can read `kiroku/START_HERE.md` and continue work without
needing the original conversation.

Notes:
- Use a realistic prompt and do not leak expected answers.
- Include a multi-repo scenario with two unrelated active tracks.

### Task: Design semantic HTML viewer contract

Status: todo
Completion:
The skill documents the minimum Markdown entry patterns, generated ID rules,
HTML `data-*` attributes, output location, and read-only behavior for a local
Kiroku viewer.

Notes:
- Keep Markdown canonical and pleasant to read.
- Prefer deterministic IDs; use optional explicit ID comments only when title
  changes would otherwise break links.
- Include diagnostics for missing completion conditions, missing rationales,
  unmitigated risks, duplicate headings, and broken links.

### Task: Define documentation mode boundaries

Status: todo
Completion:
The skill explains when documentation generation is allowed, where project
docs should be written, and what code or command evidence must be verified
before writing.

Notes:
- `kiroku/` remains memory and handoff context, not published docs.
- Generated docs should avoid duplicating maintained project files.

## Blocked

- None known.

## Done

- Markdown-first KirokuForge foundation is in place.
- Hub guardrails are documented: selective reading, strict `START_HERE.md`,
  compression on update, operating modes, final checklist, and
  operational/history separation.
- Lightweight hub checker added in `scripts/check_hub.py`; it verifies the
  default Markdown contract without reintroducing a runtime pipeline.
- Init helper added in `scripts/init_hub.py`; it copies bundled templates into
  a target hub and refuses overwrite unless explicitly requested.
- Skill validation passes with `quick_validate.py`.
- Product direction clarified: local HTML UI and project docs can be derived
  from structured Markdown, but no database or generated view is canonical.
- Phase 1 track routing added to `SKILL.md` and `references/file-contract.md`:
  agents choose `global` or a specific track before reading detailed memory.
- Phase 2 track contract added in `references/track-contract.md`, covering
  lifecycle, routing, promotion, closure, and entry patterns.
- Phase 3 track templates added in `assets/templates/kiroku/TRACKS.md` and
  `assets/templates/kiroku/tracks/_template/`.
- Phase 4 helper support added: `scripts/init_hub.py` can add `TRACKS.md` and
  concrete tracks, while `scripts/check_hub.py` validates track routing,
  required track files, track handoff length, TODO completion, and decision
  rationales.

## Cancelled

- Continuing the v3 compiler/pipeline build is cancelled for the current
  product direction.
