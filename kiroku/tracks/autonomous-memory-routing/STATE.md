# State

## Track Purpose

Restructure KirokuForge around verified project memory, independently resumable
task workspaces, selective reads, project onboarding, and bounded autonomous use.

## Current Status

- Status: closed.
- M-01 through M-07 are completed.
- The implementation remains uncommitted for user review.

## Final Outcome

- Agent-led `init` creates verified base project memory from project evidence.
- `start-task` reuses or creates a routed workspace with state, roadmap, work,
  decisions, risks, and handoff context.
- `read-task` and `read-project` provide non-mutating focused and global reads.
- Helpers scaffold roadmaps additively and reject malformed task workspaces.
- The repository's own Kiroku hub follows the resulting global/track model.
- Global Codex rules activate KirokuForge from durable project context while
  excluding trivial work and analysis-only writes.

## Final Verification

- The skill and strict project-hub validators pass.
- Helper smoke tests cover fresh hubs, task creation, additive completion, and
  invalid-roadmap rejection.
- Fresh-agent tests cover explicit workflows and context-driven global routing.
- Read-only fixture and repository hashes remained unchanged.
- The global policy SHA-256 is
  `0916162ae51526825324f2fa25da942a5602f9d7678f886e392c340eb5d8809e`.

## Open Questions

- None affecting this completed track.

## Watch Points

- Future changes must preserve selective activation, evidence priority, and
  global/task ownership boundaries.
