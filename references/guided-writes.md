# Guided Markdown Writes

Use these commands for authorized creation or updates of structured decisions
and constraints. Markdown remains authoritative and directly editable. The
[structured contract](structured-memory.md) defines record syntax and fields;
the [index contract](memory-index.md) defines the derived SQLite snapshot.

Use the writer while preparing the end of a task/milestone or an explicit
handoff/maintenance checkpoint. Save all changes, validate the memory, and run
`memory.py checkpoint <project-root>` once. During preparation, readers see the
previous published database. `build` is a compatibility alias for `checkpoint`.

The writer does not infer facts, choose whether a proposal has been adopted,
create project workspaces, or update handoffs and roadmaps automatically. Curate
those owner files within the existing skill workflow when their state changes.

## Commands

```bash
python scripts/memory.py add <project-root> --file DECISIONS.md --section "Active Decisions" --data <payload.json> --dry-run
python scripts/memory.py add <project-root> --file DECISIONS.md --section "Active Decisions" --data <payload.json>
python scripts/memory.py update <project-root> <entry-id> --data <patch.json> --dry-run
python scripts/memory.py update <project-root> <entry-id> --data <patch.json>
```

All commands accept `--hub-dir` for an exact custom hub directory. `--data -`
reads JSON from stdin, so a payload file need not be kept in the project. JSON
is an operation input, not another canonical memory store. Duplicate JSON keys,
unknown payload fields, unsupported values, and invalid records are rejected.

`add` requires an existing indexable Markdown owner file and the exact text of
one existing level-two heading, without `##`. Use the observed heading in the
hub's language; the program does not translate or guess it. It appends the
entry within that section, before the next level-one or level-two heading.
A section whose entire body is the literal empty note `- None.` has that note
replaced by the entry. Other prose and entries are preserved.

`update` locates one tagged entry by its stable ID, accepting either the bare
memory ID or `entry:<ID>`. It does not convert an untagged legacy entry or change
the ID, type, or owner file. An optional `--section "<heading>"` moves the entry
to another existing level-two section of the same file. Choose the destination
explicitly when a status change makes the current section misleading.

## Creation Payload

```json
{
  "id": "DEC-local-index",
  "type": "decision",
  "status": "active",
  "title": "Keep the project index derived",
  "fields": {
    "Decision": "Rebuild the index from the project's Markdown memory.",
    "Rationale": "The source remains directly editable and reviewable.",
    "Consequences": "- Refresh the index after changing the memory."
  }
}
```

Provide `type`, `status`, `title`, and `fields`. `id` and `links` are optional.
Use `Rule` and `Why` for a constraint. Field keys omit the colon; values are
strings containing the same prose, bullets, or fenced code allowed in Markdown.
Titles contain one line. The writer supplies the delimiters and version, and
emits a visible `Status:` consistent with the metadata.

When `id` is absent the writer generates a unique ID and returns `memory_id`.
To apply the same identity shown in a dry-run, include that ID explicitly in
the subsequent payload. Repeating an add without an ID creates a new identity;
it does not recognize semantic duplicates. An explicitly repeated ID is rejected.

`links`, when provided, uses the structured contract's array of `relation` and
`target` objects. Targets must exist in the proposed complete hub. The writer
does not add links based on similar wording.

## Update Payload

```json
{
  "fields": {
    "Consequences": "- Rebuild the index after editing or resolving Markdown conflicts."
  }
}
```

Updates accept only `title`, `status`, `fields`, and `links`:

- Omitted properties and fields retain their current values.
- `fields` patches individual values. `null` removes an optional field; required
  fields cannot be removed. A present field still needs meaningful content.
- Changing `status` also updates an existing visible `Status:` field. An
  explicitly supplied visible status must agree with the metadata.
- `links`, when supplied, replaces that entry's complete link list. Use `[]`
  to remove the links; omitting it preserves them.
- A patch that changes nothing preserves the original Markdown bytes and mtime.
  No-op writes also leave the database untouched; they do not establish that the
  current Markdown has already been published.

Only changed metadata, titles, or field spans are rewritten. Unspecified fields,
comments outside rewritten spans, and surrounding prose are preserved. Rewritten values use the local
newline convention and strip outer whitespace; the proposed result is parsed
again to confirm the intended values and reject structural injection.
If changing a title would remove comments embedded between its words, the
command rejects that edit; edit the title directly in Markdown to preserve them.

Changing a state records the caller's decision. It does not automatically retire
a linked entry, move records between files, or prove that the state is correct.

## Validation, Publication, And Recovery

The writer reads the canonical sources and validates the complete proposed
typed memory, including IDs and references, before publishing anything. It
requires an existing source within the indexed hub, rejects source symlinks,
and rechecks source fingerprints before replacement. Existing memory can be
edited without a ready database; the proposed typed records must be valid.

`--dry-run` returns `state: dry_run`, the entry ID, source path, and unified diff.
It creates no source, database, or temporary file. This previews only the Markdown
operation; database capability and publication checks belong to `checkpoint`.

A real command writes one temporary file beside the Markdown owner, preserves
its permission mode, flushes it, and atomically replaces that source. Temporary
writer files are hidden and cleaned after handled failures. It does not inspect,
open, create, or update SQLite; it can save canonical sources when no usable
database exists. Database checks occur at publication, after the complete edit set.

Successful execution returns `state: saved`, `markdown_changed`, `markdown_saved`,
`index_updated: false`, `checkpoint_required: true`, and a `next_action` pointing
to the final checkpoint. `markdown_saved` indicates that this call replaced a
Markdown file; a no-op reports false. `saved` has exit status 0 and does not mean
the entry is visible to database readers yet. This replaces the previous writer
behavior that rebuilt the index and returned `ready` after every edit.

The Markdown edits and database publication are separate operations. Once all
edits and applicable structural checks are complete, `checkpoint` validates
the typed sources and builds one complete, integrity-checked snapshot. Successful
publication returns `state: ready`; unchanged content returns `changed: false`
without rewriting the database. The command never modifies Markdown.

If preparation or publication fails, saved Markdown remains available and the
previous database remains the published checkpoint. Its content does not include
the pending edits. With no prior database, reads remain unavailable. Resolve the
reported error and retry `checkpoint`; do not repeat saved additions or describe
pending content as published. `status` can explicitly audit the source mismatch.

Directory-sync failures after successful replacement are reported as warnings;
the file was published but its persistence after a crash was not confirmed.
The writer does not silently roll back canonical memory or claim a transaction
covering both Markdown and SQLite.

These checks establish valid typed records and publication outcomes. Existing
hub checks and agent review still govern placeholders, handoffs, ownership,
semantic accuracy, and milestone readiness. No command commits or pushes files.
