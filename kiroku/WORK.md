# Work

## Ongoing

- None.

## TODO

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

- Markdown-first hub, selective reading, strict handoffs, compression, and
  operational/history ownership are established.
- Global and track contracts define routing, lifecycle, promotion, closure,
  and stable entry patterns.
- Scaffolding and checker helpers support base hubs, task tracks, roadmaps, and
  safe additive completion of legacy tracks.
- Global Codex rules activate KirokuForge autonomously for durable non-trivial
  work while keeping analysis-only reads non-mutating and trivial work excluded.
- The autonomous-memory-routing restructuring is complete: all requested modes,
  task ownership, validation, memory migration, and global activation are
  implemented and independently exercised.
- Product direction keeps generated views and documentation derived from
  Markdown and rejects a canonical database or JSON store.

## Cancelled

- Continuing the v3 compiler/pipeline build is cancelled for the current
  product direction.
