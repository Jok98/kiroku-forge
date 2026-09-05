# Start Here

## Mission

- Maintain a curated Markdown memory skill for project and task continuation.
- Keep project knowledge readable without a generated storage layer.

## Current State

- Skill instructions own modes, authority, reading, and update behavior.
- File and track contracts own Markdown structure, helper usage, and lifecycle.
- Structural checker and scaffolder repairs are implemented and verified.
- `validation-contract-alignment` is complete and closed; no task is active.

## Next Action

- Select the next durable backlog item from `WORK.md` when new work is requested.

## Hard Constraints

- Markdown remains canonical; metadata stays minimal.
- Memory does not override current instructions or verified project evidence.
- Read modes do not initialize, repair, or otherwise write memory.
- Preserve unrelated work and keep task details in their owning track.
- Scaffolding is incomplete until an agent replaces placeholders with evidence.
- Derived views must not become a hidden canonical store.

## Read Only If Needed

- `TRACKS.md` for task routing; `STATE.md` and `WORK.md` for global status.
- `ARCHITECTURE.md`, `DECISIONS.md`, and `CONSTRAINTS.md` for shared direction.
- `RISKS.md` and `IDEAS.md` for limitations and deferred approaches.
