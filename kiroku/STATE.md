# State

## Project Purpose

KirokuForge is a Codex skill for durable project memory. It maintains a
project-wide Markdown hub and focused task workspaces so developers and agents
can resume work without reconstructing context from prior conversations.

## Current Status

- KirokuForge is a Markdown-first memory skill.
- `kiroku/*.md` files are the project memory; `memory.json` is not canonical.
- `SKILL.md` defines agent behavior; `references/file-contract.md` defines the
  base hub contract; `references/track-contract.md` defines task routing,
  roadmaps, lifecycle, and ownership.
- `init` is an agent-led workflow that inspects the project, scaffolds the hub,
  replaces placeholders with verified context, and validates strict readiness.
- `start-task` reuses or creates a track containing `START_HERE.md`, `STATE.md`,
  `ROADMAP.md`, and `WORK.md`, plus decisions, risks, and log when useful.
- `read-task` resumes one task; `read-project` onboards a session to global
  truth and active-track handoffs without loading every track detail.
- `scripts/init_hub.py` safely scaffolds hubs and completes existing tracks with
  missing contract files unless overwrite is explicit.
- `scripts/check_hub.py` validates required hub files, template placeholders,
  handoff length, TODO completion, active decision rationale, track routing,
  and roadmap structure and status.
- `assets/templates/kiroku/*.md` initializes new project hubs.
- `assets/templates/kiroku/TRACKS.md` and
  `assets/templates/kiroku/tracks/_template/` initialize the optional track
  layer.
- New hubs use the dominant language of the project or request; existing hubs
  keep their current language unless the user asks to translate them.
- Top-level files hold global or cross-track truth; task progress belongs in
  `tracks/<slug>/` and is promoted only when it changes shared direction.
- `/home/mmoi/.codex/AGENTS.md` autonomously routes durable project-memory work
  through KirokuForge while preserving read-only and small-task exclusions.
- `TRACKS.md` preserves the closed `autonomous-memory-routing` outcome for
  future routing and audit context.
- Any future local HTML UI should be generated from structured Markdown as a
  read-only derived view, not maintained as primary memory.
- A database is not part of the current direction; if a query cache is ever
  added, it must be disposable and generated from Markdown.
- This repository intentionally has no v3 runtime, schema, or test suite.

## Recently Verified

- `python /home/mmoi/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/mmoi/.agents/skills/kiroku-forge` returned `Skill is valid!`.
- `python scripts/check_hub.py . --strict-warnings` passed before this broad
  memory migration.
- Fresh task scaffolds include `ROADMAP.md`; strict validation rejects their
  placeholders until an agent replaces them.
- Legacy tracks can receive a missing roadmap while all existing files remain
  unchanged.
- Missing roadmaps and multiple `in_progress` milestones fail validation.
- Four isolated fresh-agent workflows passed for project initialization, task
  creation, focused task reading, and whole-project onboarding.
- Both read workflows left the complete fixture byte-for-byte unchanged.
- The installed global Codex policy exactly matched its approved proposal at
  SHA-256 `0916162ae51526825324f2fa25da942a5602f9d7678f886e392c340eb5d8809e`.
- Final autonomous-policy tests covered task reading, project onboarding,
  trivial-task exclusion, and automatic base-hub plus task initialization.
- Final script smoke tests covered base scaffolding, task roadmaps, additive
  legacy completion, strict placeholders, missing roadmaps, and multiple
  in-progress milestones.

## Open Questions

- What exact Markdown entry contract should a semantic HTML renderer require
  beyond the current decision, task, constraint, and rejected-idea patterns?
- Should the global `START_HERE.md` hard cap change from 60 to 50 while keeping
  the target at 25-40?
- Should a future documentation mode write project docs outside `kiroku/`
  after verifying code and commands, or remain an external workflow?

## Watch Points

- Do not let the Markdown hub become a verbose generated report.
- Do not duplicate the same decision or constraint across several files.
- Do not let autonomous activation create hubs or tracks for trivial work.
- Treat old memory notes about v2/v3 as historical context only; they no
  longer define the current product direction.
