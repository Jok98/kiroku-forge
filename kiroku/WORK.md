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

### Task: Decide whether an init script is needed

Status: todo
Completion:
Either add a tiny script that copies templates into `kiroku/`, or record the
decision that manual/template-based creation is sufficient.

Notes:
- Do this only after the format stabilizes.

## Blocked

- None known.

## Done

- Markdown-first KirokuForge foundation is in place.
- Hub guardrails are documented: selective reading, strict `START_HERE.md`,
  compression on update, and operational/history separation.
- Skill validation passes with `quick_validate.py`.

## Cancelled

- Continuing the v3 compiler/pipeline build is cancelled for the current
  product direction.
