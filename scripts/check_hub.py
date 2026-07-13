#!/usr/bin/env python3
"""Validate a KirokuForge Markdown memory hub."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_FILES = (
    "START_HERE.md",
    "STATE.md",
    "ARCHITECTURE.md",
    "DECISIONS.md",
    "WORK.md",
    "CONSTRAINTS.md",
    "IDEAS.md",
    "RISKS.md",
    "LOG.md",
)

TRACK_INDEX_FILE = "TRACKS.md"
TRACK_REQUIRED_FILES = (
    "START_HERE.md",
    "STATE.md",
    "ROADMAP.md",
    "WORK.md",
)
TRACK_CHECK_FILES = (
    "START_HERE.md",
    "STATE.md",
    "ROADMAP.md",
    "WORK.md",
    "DECISIONS.md",
    "RISKS.md",
    "LOG.md",
)
TRACK_STATUSES = {"active", "paused", "closed", "candidate"}

PLACEHOLDER_NEEDLES = (
    "State the current project goal",
    "State where the project stands now",
    "Name the next concrete action",
    "List only the constraints",
    "Write the project purpose",
    "Summarize what is currently true",
    "Record facts verified by",
    "Track questions that affect",
    "Track fragile areas",
    "Describe the main runtime",
    "Describe module, responsibility",
    "Document project-specific",
    "Keep details that future code changes",
    "Document external systems",
    "Decision: Example",
    "State the adopted choice",
    "Explain why it was adopted",
    "State what future work must respect",
    "Constraint: Example",
    "State the constraint",
    "Explain what breaks or becomes risky",
    "Ideas worth considering",
    "Risk: Example",
    "State what could happen",
    "Risks accepted intentionally",
    "Closed risks whose history still matters",
    "YYYY-MM-DD",
    "Task: Example",
    "Keep this short and current",
    "State what makes this task done",
    "Add context needed to continue",
    "State blocker and unblock condition",
    "State completed work and outcome",
    "State cancelled work only when",
    "Rejected: Example",
    "Explain why this was rejected",
    "State when, if ever",
    "track-slug",
    "State the durable workstream purpose",
    "terms that identify this track",
    "State the workstream goal",
    "State what is true now for this track",
    "Name the next concrete action for this track",
    "List only constraints or global decisions",
    "Write the workstream purpose",
    "Summarize what is currently true for this track",
    "State what belongs to this track",
    "State what should stay global",
    "Track questions that affect this workstream",
    "Keep this short and current for this track",
    "State what makes this track task done",
    "Add context needed to continue this workstream",
    "State completed track work and outcome",
    "State cancelled track work only",
    "M-01: Example milestone",
    "State the outcome this milestone must achieve",
    "State what is included in this milestone",
    "Name the files, modules, or deliverables",
    "State prerequisites or `None`",
    "State the command, review, or evidence required",
    "State the evidence that proves completion",
    "State material risks or `None known`",
    "State the adopted choice for this track",
    "State what future work in this track must respect",
    "State what could happen in this track",
    "Track risks accepted intentionally",
    "Closed track risks whose history still matters",
    "Summarize meaningful track memory changes",
    "TODO: describe this workstream",
    "Repos: TBD",
    "Areas: TBD",
)

FIELD_RE = re.compile(r"^[A-Z][A-Za-z ]+:\s*(.*)$")
HEADING_RE = re.compile(r"^#{1,6}\s+")
ACTIVE_RE = re.compile(r"^Status:\s*active\s*$", re.IGNORECASE)
TODO_RE = re.compile(r"^Status:\s*todo\s*$", re.IGNORECASE)
TRACK_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MILESTONE_HEADING_RE = re.compile(r"^###\s+(M-[0-9]{2,}):\s+\S")
MILESTONE_STATUSES = {"pending", "in_progress", "completed", "blocked"}
MILESTONE_REQUIRED_LABELS = (
    "Objective:",
    "Scope:",
    "Expected artifacts:",
    "Dependencies:",
    "Validation:",
    "Completion criteria:",
    "Risks:",
)


@dataclass(frozen=True)
class Issue:
    severity: str
    path: Path
    line: int | None
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check a KirokuForge Markdown memory hub."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project root or kiroku/ hub directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Exit with status 1 when warnings are present.",
    )
    return parser.parse_args()


def resolve_hub(path: Path) -> Path:
    candidate = path.resolve()
    if candidate.name == "kiroku" or (candidate / "START_HERE.md").exists():
        return candidate
    return candidate / "kiroku"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def display(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def has_label_content(block: list[str], label: str) -> bool:
    return label_value(block, label) is not None


def label_value(block: list[str], label: str) -> str | None:
    for index, line in enumerate(block):
        stripped = line.strip()
        if not stripped.startswith(label):
            continue

        inline_value = stripped[len(label) :].strip()
        if inline_value:
            return inline_value

        for following in block[index + 1 :]:
            candidate = following.strip()
            if not candidate:
                continue
            if HEADING_RE.match(candidate) or FIELD_RE.match(candidate):
                return None
            return candidate

        return None

    return None


def heading_blocks(lines: list[str], prefix: str = "### ") -> list[tuple[int, list[str]]]:
    blocks: list[tuple[int, list[str]]] = []
    start: int | None = None

    for index, line in enumerate(lines):
        if line.startswith(prefix):
            if start is not None:
                blocks.append((start, lines[start:index]))
            start = index

    if start is not None:
        blocks.append((start, lines[start:]))

    return blocks


def check_required_files(hub: Path) -> list[Issue]:
    issues: list[Issue] = []
    for name in REQUIRED_FILES:
        path = hub / name
        if not path.is_file():
            issues.append(Issue("error", path, None, "required hub file is missing"))
    return issues


def check_placeholders(hub: Path, files: dict[str, list[str]]) -> list[Issue]:
    issues: list[Issue] = []
    for name, lines in files.items():
        path = hub / name
        issues.extend(check_file_placeholders(path, lines))
    return issues


def check_file_placeholders(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    needles = sorted(PLACEHOLDER_NEEDLES, key=len, reverse=True)
    for line_number, line in enumerate(lines, start=1):
        for needle in needles:
            if needle in line:
                issues.append(
                    Issue(
                        "warning",
                        path,
                        line_number,
                        f"template placeholder remains: {needle!r}",
                    )
                )
                break
    return issues


def check_start_here_lines(
    path: Path,
    lines: list[str],
    target_min: int,
    target_max: int,
    hard_cap: int,
) -> list[Issue]:
    line_count = len(lines)
    if line_count > hard_cap:
        return [
            Issue(
                "error",
                path,
                None,
                f"START_HERE.md has {line_count} lines; hard cap is {hard_cap}",
            )
        ]
    if line_count < target_min or line_count > target_max:
        return [
            Issue(
                "warning",
                path,
                None,
                f"START_HERE.md has {line_count} lines; target is {target_min}-{target_max}",
            )
        ]
    return []


def check_start_here(hub: Path, files: dict[str, list[str]]) -> list[Issue]:
    lines = files.get("START_HERE.md")
    if lines is None:
        return []
    return check_start_here_lines(hub / "START_HERE.md", lines, 25, 40, 60)


def check_todo_completion_file(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for start, block in heading_blocks(lines):
        if any(TODO_RE.match(line.strip()) for line in block):
            if not has_label_content(block, "Completion:"):
                issues.append(
                    Issue(
                        "error",
                        path,
                        start + 1,
                        "todo task is missing a non-empty Completion: condition",
                    )
                )
    return issues


def check_todo_completion(hub: Path, files: dict[str, list[str]]) -> list[Issue]:
    lines = files.get("WORK.md")
    if lines is None:
        return []
    return check_todo_completion_file(hub / "WORK.md", lines)


def check_active_decision_rationale_file(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for start, block in heading_blocks(lines):
        if any(ACTIVE_RE.match(line.strip()) for line in block):
            if not has_label_content(block, "Rationale:"):
                issues.append(
                    Issue(
                        "error",
                        path,
                        start + 1,
                        "active decision is missing a non-empty Rationale:",
                    )
                )
    return issues


def check_active_decision_rationale(
    hub: Path, files: dict[str, list[str]]
) -> list[Issue]:
    lines = files.get("DECISIONS.md")
    if lines is None:
        return []
    return check_active_decision_rationale_file(hub / "DECISIONS.md", lines)


def check_roadmap_file(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    blocks = heading_blocks(lines)
    milestone_ids: set[str] = set()
    valid_milestones = 0
    in_progress_count = 0

    for start, block in blocks:
        heading = block[0].strip()
        match = MILESTONE_HEADING_RE.match(heading)
        if match is None:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    "roadmap level-three heading must match '### M-01: Outcome'",
                )
            )
            continue

        valid_milestones += 1
        milestone_id = match.group(1)
        if milestone_id in milestone_ids:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    f"duplicate roadmap milestone identifier {milestone_id!r}",
                )
            )
        milestone_ids.add(milestone_id)

        status = label_value(block, "Status:")
        if status is None:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    "roadmap milestone is missing a non-empty Status:",
                )
            )
        else:
            normalized = status.lower()
            if normalized not in MILESTONE_STATUSES:
                issues.append(
                    Issue(
                        "error",
                        path,
                        start + 1,
                        f"milestone status {status!r} is not one of "
                        f"{sorted(MILESTONE_STATUSES)}",
                    )
                )
            elif normalized == "in_progress":
                in_progress_count += 1

        for label in MILESTONE_REQUIRED_LABELS:
            if not has_label_content(block, label):
                issues.append(
                    Issue(
                        "error",
                        path,
                        start + 1,
                        f"roadmap milestone is missing non-empty {label}",
                    )
                )

    if valid_milestones == 0:
        issues.append(
            Issue(
                "error",
                path,
                None,
                "roadmap must contain at least one valid milestone",
            )
        )
    if in_progress_count > 1:
        issues.append(
            Issue(
                "error",
                path,
                None,
                f"roadmap has {in_progress_count} in_progress milestones; at most one is allowed",
            )
        )

    return issues


def load_existing_files(hub: Path) -> tuple[dict[str, list[str]], list[Issue]]:
    files: dict[str, list[str]] = {}
    issues: list[Issue] = []

    for name in REQUIRED_FILES:
        path = hub / name
        if not path.is_file():
            continue
        try:
            files[name] = read_lines(path)
        except UnicodeDecodeError as exc:
            issues.append(Issue("error", path, None, f"file is not valid UTF-8: {exc}"))

    return files, issues


def load_optional_file(path: Path) -> tuple[list[str] | None, list[Issue]]:
    if not path.is_file():
        return None, []
    try:
        return read_lines(path), []
    except UnicodeDecodeError as exc:
        return None, [Issue("error", path, None, f"file is not valid UTF-8: {exc}")]


def discover_track_dirs(hub: Path) -> list[Path]:
    tracks_dir = hub / "tracks"
    if not tracks_dir.is_dir():
        return []
    return sorted(
        path
        for path in tracks_dir.iterdir()
        if path.is_dir() and path.name != "_template"
    )


def check_tracks_index(hub: Path, track_dirs: list[Path]) -> list[Issue]:
    path = hub / TRACK_INDEX_FILE
    lines, load_issues = load_optional_file(path)
    issues = list(load_issues)

    if lines is None:
        if track_dirs:
            issues.append(
                Issue(
                    "error",
                    path,
                    None,
                    "TRACKS.md is required when tracks/ contains track folders",
                )
            )
        return issues

    issues.extend(check_file_placeholders(path, lines))
    blocks = heading_blocks(lines)
    blocks_by_slug = {
        block[0].removeprefix("### ").strip(): (start, block)
        for start, block in blocks
    }

    for start, block in blocks:
        status = label_value(block, "Status:")
        if status is None:
            continue
        normalized = status.lower()
        if normalized not in TRACK_STATUSES:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    f"track status {status!r} is not one of {sorted(TRACK_STATUSES)}",
                )
            )

    for track_dir in track_dirs:
        slug = track_dir.name
        entry = blocks_by_slug.get(slug)
        if entry is None:
            issues.append(
                Issue(
                    "error",
                    path,
                    None,
                    f"TRACKS.md is missing an entry for track {slug!r}",
                )
            )
            continue

        start, block = entry
        read_value = label_value(block, "Read:")
        expected = f"tracks/{slug}/START_HERE.md"
        if read_value is None:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    f"track {slug!r} is missing a Read: target",
                )
            )
        elif expected not in read_value:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    f"track {slug!r} Read: should point to {expected}",
                )
            )

    return issues


def check_track_dirs(track_dirs: list[Path]) -> list[Issue]:
    issues: list[Issue] = []

    for track_dir in track_dirs:
        slug = track_dir.name
        if not TRACK_SLUG_RE.match(slug):
            issues.append(
                Issue(
                    "error",
                    track_dir,
                    None,
                    "track folder name must use lowercase letters, digits, and hyphens",
                )
            )

        for name in TRACK_REQUIRED_FILES:
            path = track_dir / name
            if not path.is_file():
                issues.append(
                    Issue("error", path, None, "required track file is missing")
                )

        files: dict[str, list[str]] = {}
        for name in TRACK_CHECK_FILES:
            path = track_dir / name
            if not path.is_file():
                continue
            lines, load_issues = load_optional_file(path)
            issues.extend(load_issues)
            if lines is not None:
                files[name] = lines
                issues.extend(check_file_placeholders(path, lines))

        start_here = files.get("START_HERE.md")
        if start_here is not None:
            issues.extend(
                check_start_here_lines(
                    track_dir / "START_HERE.md", start_here, 20, 35, 50
                )
            )

        work = files.get("WORK.md")
        if work is not None:
            issues.extend(check_todo_completion_file(track_dir / "WORK.md", work))

        roadmap = files.get("ROADMAP.md")
        if roadmap is not None:
            issues.extend(check_roadmap_file(track_dir / "ROADMAP.md", roadmap))

        decisions = files.get("DECISIONS.md")
        if decisions is not None:
            issues.extend(
                check_active_decision_rationale_file(
                    track_dir / "DECISIONS.md", decisions
                )
            )

    return issues


def print_issues(title: str, issues: list[Issue]) -> None:
    if not issues:
        return

    print(f"{title}:")
    for issue in issues:
        location = display(issue.path)
        if issue.line is not None:
            location = f"{location}:{issue.line}"
        print(f"  - {location}: {issue.message}")


def main() -> int:
    args = parse_args()
    hub = resolve_hub(Path(args.path))

    issues = check_required_files(hub)
    files, load_issues = load_existing_files(hub)
    issues.extend(load_issues)
    issues.extend(check_placeholders(hub, files))
    issues.extend(check_start_here(hub, files))
    issues.extend(check_todo_completion(hub, files))
    issues.extend(check_active_decision_rationale(hub, files))
    track_dirs = discover_track_dirs(hub)
    issues.extend(check_tracks_index(hub, track_dirs))
    issues.extend(check_track_dirs(track_dirs))

    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]

    if not errors and not warnings:
        print(f"Kiroku hub check passed: {display(hub)}")
        return 0

    print_issues("Errors", errors)
    print_issues("Warnings", warnings)

    if errors or (warnings and args.strict_warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
