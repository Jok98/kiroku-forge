# Ideas

## Open Ideas

- Add a tiny `init` helper that copies `assets/templates/kiroku/` into a
  target project.
- Add a lightweight checker that verifies required `kiroku/*.md` files exist
  and warns about empty template placeholders.
- Let each project choose the language of its memory hub instead of forcing
  English.

## Deferred Ideas

- Machine-readable indexes are deferred until there is a concrete repeated
  need.
- A richer CLI is deferred until the Markdown workflow has survived real use.

## Rejected Ideas

### Rejected: Canonical memory.json

Reason:
It makes Markdown feel like a projection instead of the primary memory, and it
pushes the design back toward schema-heavy bookkeeping.

Keep in mind:
Reconsider only if a future workflow clearly needs a machine-readable cache,
and keep it generated rather than canonical.

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
