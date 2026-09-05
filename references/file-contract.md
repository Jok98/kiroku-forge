# KirokuForge File Contract

This contract owns file responsibilities, Markdown syntax, language, handoff
limits, and helper behavior. [SKILL.md](../SKILL.md) owns operating modes,
reading order, write scope, compression, and the final checklist. The
[track contract](track-contract.md) owns routing entries, lifecycle, promotion,
closure, and roadmaps.

## Layout

The base hub has nine required Markdown files. The optional track layer keeps
independent work inside the same project memory:

```text
kiroku/
  START_HERE.md
  STATE.md
  ARCHITECTURE.md
  DECISIONS.md
  WORK.md
  CONSTRAINTS.md
  IDEAS.md
  RISKS.md
  LOG.md
  TRACKS.md                 # required when track folders exist
  tracks/
    <track-slug>/
      START_HERE.md
      STATE.md
      ROADMAP.md
      WORK.md
      DECISIONS.md          # optional
      RISKS.md              # optional
      LOG.md                # optional
```

Every existing track folder retains its four required files, including paused
and closed tracks. A candidate without a folder follows the
[track index contract](track-contract.md#track-index). The bundled
[hub templates](../assets/templates/kiroku) and
[track template](../assets/templates/kiroku/tracks/_template) are scaffolds;
`_template` is not an operational track.

## Language And Entry Syntax

- For a new hub, use the dominant language of the project or the user's request.
  Preserve an existing hub's language and terminology unless translation is requested.
- Translate descriptive headings and prose while preserving section meanings.
  Keep file names, track slugs, milestone IDs, technical field labels from the
  templates, and status values unchanged. Examples include `Status:`,
  `Completion:`, `Rationale:`, `Read:`, and the roadmap/index labels.
- Use recognizable lowercase hyphenated slugs, such as `tax-migration`.
  Letters `a-z` and digits are allowed; hyphens separate non-empty segments.
- Use level-three headings for task, decision, roadmap, and index entries.
  A heading at the same or a higher level ends the entry. Roadmap headings
  follow the [roadmap contract](track-contract.md#roadmap-contract).
- Put examples inside fenced code blocks. Headings and field labels inside a
  fence do not create operational entries or fields.
- Fields may contain inline text, following prose, bullets, or a non-empty
  fenced code block. Another known field or a heading ends an empty field;
  content from the next entry cannot satisfy it.
- Use compact, project-specific prose and visible status. Prefer bullets for
  facts and short paragraphs for rationale. Include paths, commands, dates,
  and module names when they help continuation. Avoid frontmatter unless the
  user explicitly wants machine parsing.

## File Ownership

Global files own project-wide and shared context. Track files own the same
kind of information only for their workstream; use links instead of repeating
local detail globally. Operational files describe the present. Chronological
history belongs in `LOG.md` unless it explains an active decision, constraint,
risk, or rejected direction.

| File | Responsibility |
| --- | --- |
| `START_HERE.md` | Entry and next continuation, scoped globally or to one track; follows the handoff contract below. |
| `STATE.md` | Current scope, what works, incomplete work, verified facts, and questions affecting the next action. |
| `ARCHITECTURE.md` | Global flows, module boundaries, patterns, integrations, and implementation details that guide future changes; not an exhaustive code map. |
| `DECISIONS.md` | Adopted choices. Every active decision needs a non-empty `Rationale:`; keep consequences, alternatives, or replaced choices when they explain future constraints. |
| `WORK.md` | Granular ongoing, TODO, blocked, done, and cancelled work. Ongoing means currently in flight. Every TODO needs a non-empty `Completion:`. Done items state outcomes; blocked/cancelled items remain when they affect future choices. |
| `CONSTRAINTS.md` | Shared rules, out-of-scope boundaries, forbidden changes, and what must not break; explain what each rule prevents and why. |
| `IDEAS.md` | Open, deferred, rejected, and forbidden ideas. Give rejection reasons and explain which failure mode or rule makes an idea forbidden. |
| `RISKS.md` | Open, accepted, mitigated, and still-relevant closed risks; state condition, impact, and mitigation or a signal to watch. |
| `LOG.md` | Concise meaningful memory-update history. Track logs cover local changes; the global log covers global memory and track lifecycle changes. |
| `TRACKS.md` | Compact routing and lifecycle index governed by the [track contract](track-contract.md#track-index). |
| `tracks/<slug>/ROADMAP.md` | Outcome-oriented milestones governed by the [roadmap contract](track-contract.md#roadmap-contract); granular execution work stays in `WORK.md`. |

Local decisions and risks may use their optional track files. Shared
architecture, constraints, and ideas retain their global owners. Apply the
[promotion rules](track-contract.md#promotion-and-closure) when a local fact
acquires wider impact.

## Handoff Contract

Every global or track `START_HERE.md` uses only these sections, or their direct
equivalents in the hub language: `Mission`, `Current State`, `Next Action`,
`Hard Constraints`, and `Read Only If Needed`.

Write bullets containing only what an agent needs before opening another
file. Keep one concrete next action and link to detail. A goal-specific
handoff changes the relevant handoff; a track handoff covers only that track
and the shared constraints it needs. Use the
[global](../assets/templates/kiroku/START_HERE.md) or
[track](../assets/templates/kiroku/tracks/_template/START_HERE.md) skeleton.

| Handoff | Advisory target | Enforced cap |
| --- | --- | --- |
| Global `START_HERE.md` | 25-40 lines | 60 lines |
| Track `START_HERE.md` | 20-35 lines | 50 lines |

Targets are editorial guidance and do not generate checker warnings. Exceed a
cap only when the user explicitly requests a longer handoff. For that file,
run the checker with `--allow-long-handoff <hub-relative-path>`, naming either
`START_HERE.md` or `tracks/<slug>/START_HERE.md`. The file must exist. Repeat
this option only for other separately authorized handoffs; all other caps
and checks remain enforced. The flag records a checker exception, not user
authorization.

## Entry Patterns

Use each shape in its owner file. Replace example prose with verified context;
translate prose and descriptive titles, keeping field labels.

Decision:

```md
### Decision: Short name

Status: active
Area: module-or-topic
Decision: State the adopted choice.
Rationale: Explain why it was adopted.
Consequences:
- State a consequence or tradeoff that affects future work.
```

Task:

```md
### Task: Short name

Status: todo
Completion: State the condition that makes the task done.
Notes:
- Add context needed to continue.
```

Constraint:

```md
### Constraint: Short name

Status: active
Rule: State the constraint.
Why: Explain what breaks or becomes risky if ignored.
```

Rejected idea:

```md
### Rejected: Short name

Reason: Explain why this was rejected.
Keep in mind: State when, if ever, to reconsider it.
```

## Helper Commands

Run helpers from the skill directory, or use their absolute script paths:

```bash
python scripts/init_hub.py <project-root>
python scripts/init_hub.py <project-root> --track <slug>
python scripts/check_hub.py <project-root> --strict-warnings
python scripts/check_hub.py <custom-hub> --hub-dir
```

Without a path, both helpers use the current directory. A project-root path
selects its `kiroku/`; a path named `kiroku` selects that hub directly. Use
`--hub-dir` to select the exact directory with a custom name; `START_HERE.md`
alone never identifies a hub. An explicitly selected hub may itself be a
directory alias.

[The scaffolder](../scripts/init_hub.py) only copies templates and adds routing
scaffolds; the agent must fill and verify them before initialization is complete.

- Base scaffolding refuses to overwrite existing standard files unless
  `--overwrite` is explicit. `--with-tracks` adds a missing index; `--track <slug>`
  adds or completes a track and its routing entry and may be repeated.
- Track operations preserve existing standard hub files even with `--overwrite`.
  Existing track files are preserved unless overwrite is explicit.
  `--with-tracks --overwrite` also replaces the selected index.
- The helper copies all seven track template files. Only four are structurally
  required; optional decision, risk, and log files must still be curated when present.
- To insert missing entries into a translated index, pass
  `--track-section "<existing level-two heading text>"` without `##`.
  The default is `Active`. The selected section must exist exactly once in
  the existing or selected template index. Unknown prose is preserved; curate
  localized empty-section notes when filling the scaffold.
- Before copying, preflight rejects missing/duplicate insertion sections,
  unreadable index sources, destination type collisions, dangling symlinks,
  and destinations resolving outside the selected hub. It does not make later
  filesystem writes transactional.
- `--dry-run` shows the plan without writing. `--check` runs the checker after
  scaffolding; add `--strict-warnings` to fail on its warnings. A fresh scaffold
  still contains placeholders, so this is not a readiness guarantee. Invoke
  the checker directly when a handoff needs an authorized length exception.
- `--template-dir` and `--track-template-dir` select alternate templates.
  Use each helper's `--help` for its complete argument syntax.

## Validation Contract

[The checker](../scripts/check_hub.py) checks required file shapes, recognized
bundled placeholder prose, handoff caps, TODO completion conditions, active
decision rationales, roadmap fields/statuses, and index-to-folder routing.
It reads the selected hub; it does not edit memory.

Treat checker errors as blocking for the affected scope and inspect warnings.
`--strict-warnings` also returns failure for warnings; completed initialization
requires strict validation after curation. A failure elsewhere in the hub does
not authorize editing another track: report its scope separately.

A passing check proves only these structural checks. The agent must review
translated or rewritten placeholders, semantic accuracy, evidence freshness,
required handoff section meanings, duplication, and cross-file consistency.
The checker recognizes the documented entry conventions; it is not a general
Markdown parser or proof that the project itself works.
