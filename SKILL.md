---
name: kiroku-forge
description: Transform conversations, planning sessions, repository evidence, notes, and technical investigations into durable, provenance-backed project memory. Use when Codex must create, update, review, validate, or render reusable project knowledge such as decisions, facts, assumptions, tasks, risks, constraints, preferences, open questions, rejected ideas, and implementation context. Do not use for generic summaries unless the result is intended to become persistent project memory.
license: MIT
metadata:
  project: KirokuForge
  format: kiroku-memory-2
---

# KirokuForge

Create durable project memory, not a generic summary.

The canonical artifact is `kiroku/memory.json`. Markdown files and the agent
bootstrap are generated projections and must never be edited as sources.

## Read First

- Read [references/data-model.md](references/data-model.md) before creating or
  changing records.
- Read [references/provenance.md](references/provenance.md) when collecting
  evidence or assigning confidence.
- Read [references/record-draft.md](references/record-draft.md) before using
  `add-record`.
- The normative machine contract is
  [schemas/memory-v2.schema.json](schemas/memory-v2.schema.json).

## Operating Modes

- **Create**: initialize new memory and extract durable records.
- **Update**: preserve record IDs, add evidence, supersede instead of deleting.
- **Review**: report stale, unsupported, duplicated, or contradictory records.
- **Compact**: generate only the agent bootstrap or a concise inline result.

## Workflow

1. Determine project scope, goal, current phase, and requested mode.
2. Read existing `kiroku/memory.json` when present.
3. Register every input with `add-source`.
4. Start the extraction or update with `start-run`.
5. Create or replace durable information with `add-record` or `update-record`.
6. Attach evidence to each claim and distinguish observation from inference.
7. Preserve existing IDs during updates.
8. Use relations for dependencies, contradictions, and supersession.
9. Finish the operation with `finish-run`.
10. Write only the canonical `memory.json`.
11. Run:

```bash
python <skill-dir>/scripts/kiroku.py build --dir ./kiroku
```

12. Fix all validation errors. Warnings may remain only when they represent
    explicit uncertainty.
13. Report the canonical file, generated views, important changes, and remaining
    uncertainty.

## Initializing Memory

For a new project:

```bash
python <skill-dir>/scripts/kiroku.py init \
  --dir ./kiroku \
  --name "Project name" \
  --domain "Project domain" \
  --goal "Durable project goal"
```

Then register sources, start a run, add records, and finish the run before
running `build`.

Register a source from a local file:

```bash
python <skill-dir>/scripts/kiroku.py add-source \
  --dir ./kiroku \
  --kind repository_file \
  --title "Security configuration" \
  --file src/main/java/example/SecurityConfiguration.java \
  --revision "<git-commit>"
```

For conversations, URLs, or tool output, provide a stable `--uri`. Use `--text`
or `--stdin` when captured content is available; otherwise the source is
registered with unavailable integrity.

Start a run after registering its sources:

```bash
python <skill-dir>/scripts/kiroku.py start-run \
  --dir ./kiroku \
  --operation update \
  --input src_example \
  --actor-name codex
```

Use the returned run ID for generated records, then complete the run:

```bash
python <skill-dir>/scripts/kiroku.py add-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --file ./record-draft.json
```

The draft contract is documented in
[references/record-draft.md](references/record-draft.md). Use `--stdin` to avoid
temporary files when the agent already has the JSON payload.

To replace an existing record, read its current `content_hash` and run:

```bash
python <skill-dir>/scripts/kiroku.py update-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --key canonical_memory \
  --expect-hash sha256:... \
  --file ./record-draft.json
```

Complete the run after all records have been added:

```bash
python <skill-dir>/scripts/kiroku.py finish-run \
  --dir ./kiroku \
  --run-id run_update_example \
  --summary "Updated project decisions and tasks."
```

`build` refuses to generate projections while a run is still active.

## Record Rules

Use one atomic record for one reusable claim or action.

Supported types:

- `fact`
- `decision`
- `assumption`
- `idea`
- `rejected_idea`
- `task`
- `question`
- `risk`
- `preference`
- `constraint`
- `implementation_detail`
- `roadmap_item`
- `conflict`
- `event`

Never convert brainstorming into a decision. Never mark an inference as directly
observed. Never delete unresolved work during an update.

Use:

- `verification_status: verified` only with direct supporting evidence.
- `partially_verified` when evidence covers only part of the claim.
- `unverified` when no reliable evidence is available.
- `contradicted` when evidence refutes the record.

Use `confidence: confirmed` only for verified records.

## Provenance Rules

Every verified or partially verified record must have evidence.

Evidence must identify:

- source;
- relationship to the claim;
- observation method;
- locator inside the source;
- observation time.

Prefer repository-relative paths and immutable revisions. Preserve raw input
outside generated views and reference it through `sources`.

## Update Rules

- Keep record IDs stable.
- Update `updated_at` only when the record changes.
- Mark replaced records `superseded` or `obsolete`.
- Add a `supersedes` relation from the replacement record.
- Record unresolved disagreement as a `conflict`.
- Mark tasks `completed` only with explicit completion evidence.
- Do not regenerate timestamps merely because rendering ran.

## Validation And Projections

Available commands:

```bash
python <skill-dir>/scripts/kiroku.py validate --dir ./kiroku
python <skill-dir>/scripts/kiroku.py add-source --help
python <skill-dir>/scripts/kiroku.py start-run --help
python <skill-dir>/scripts/kiroku.py add-record --help
python <skill-dir>/scripts/kiroku.py update-record --help
python <skill-dir>/scripts/kiroku.py finish-run --help
python <skill-dir>/scripts/kiroku.py render --dir ./kiroku
python <skill-dir>/scripts/kiroku.py bootstrap --dir ./kiroku
python <skill-dir>/scripts/kiroku.py build --dir ./kiroku
```

`build` recalculates record hashes, validates memory, and generates:

```text
kiroku/
├── memory.json
├── agent-bootstrap.json
└── views/
    ├── INDEX.md
    ├── overview.md
    ├── decisions.md
    ├── actions.md
    ├── risks-and-questions.md
    ├── preferences.md
    ├── history.md
    └── sources.md
```

Use `bootstrap --scope <scope>` for focused agent context. Generated files are
written only when their content changes.

## Quality Bar

- Do not invent facts, decisions, dates, owners, or evidence.
- Keep temporary command results as `event` records or source evidence, not
  stable facts.
- Use concise titles and payloads.
- Use repository terminology exactly where compatibility matters.
- Prefer explicit uncertainty over false precision.
- Ensure another agent can answer both "what is true?" and "why do we believe
  it?" without rereading the full conversation.

## User Response

Keep the completion response concise:

- canonical memory created or updated;
- generated projections;
- key decisions and actions;
- unresolved conflicts or unverified claims;
- validation result.

Do not paste all generated files unless requested.
