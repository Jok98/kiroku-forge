# Ideas

## Open Ideas

### Idea: Semantic local HTML viewer

Build a local, read-only UI from `kiroku/*.md` that exposes sidebar
navigation, search, status/type filters, relationship hints, and quality
diagnostics while keeping Markdown canonical.

Useful signals:
- TODO entries without `Completion:`.
- Active decisions without rationale.
- Risks without mitigation.
- Broken links, duplicate headings, or nonstandard entry shapes.

### Idea: Documentation mode

Add a separate mode for project documentation generation. It should use
`kiroku/` as context, write outside `kiroku/` into project docs such as
`README.md`, `docs/`, runbooks, or ADRs, and verify code, manifests, and
commands before writing.

## Deferred Ideas

- Machine-readable indexes are deferred until there is a concrete repeated
  need.
- A richer CLI is deferred until the Markdown workflow has survived real use.
- SQLite or another derived query cache is deferred until the semantic HTML
  viewer needs faster search or richer relationship queries.

## Rejected Ideas

### Rejected: Canonical memory.json

Reason:
It makes Markdown feel like a projection instead of the primary memory, and it
pushes the design back toward schema-heavy bookkeeping.

Keep in mind:
Reconsider only if a future workflow clearly needs a machine-readable cache,
and keep it generated rather than canonical.

### Rejected: Canonical database

Reason:
It would make Markdown a generated projection, introduce schema and migration
work, worsen review and sync behavior, and reduce the narrative context that
agents need.

Keep in mind:
Reconsider only for a much larger multi-user or API-backed product; for local
use, prefer Markdown canonical with generated views.

### Rejected: Rebuild v3 incrementally

Reason:
The desired product direction changed from compiler-style formal memory to a
manual Markdown knowledge hub.

Keep in mind:
Individual implementation ideas from v3 can be reconsidered later only if they
serve the Markdown-first workflow.

## Forbidden Ideas

- Hidden canonical store with generated Markdown views.
- Heavy frontmatter for every entry.
- Append-only logs as the main memory format.
- Editable HTML UI that saves anywhere except the canonical Markdown files.
