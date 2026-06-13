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
)

FIELD_RE = re.compile(r"^[A-Z][A-Za-z ]+:\s*(.*)$")
HEADING_RE = re.compile(r"^#{1,6}\s+")
ACTIVE_RE = re.compile(r"^Status:\s*active\s*$", re.IGNORECASE)
TODO_RE = re.compile(r"^Status:\s*todo\s*$", re.IGNORECASE)


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
    for index, line in enumerate(block):
        stripped = line.strip()
        if not stripped.startswith(label):
            continue

        inline_value = stripped[len(label) :].strip()
        if inline_value:
            return True

        for following in block[index + 1 :]:
            candidate = following.strip()
            if not candidate:
                continue
            if HEADING_RE.match(candidate) or FIELD_RE.match(candidate):
                return False
            return True

        return False

    return False


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
        for line_number, line in enumerate(lines, start=1):
            for needle in PLACEHOLDER_NEEDLES:
                if needle in line:
                    issues.append(
                        Issue(
                            "warning",
                            path,
                            line_number,
                            f"template placeholder remains: {needle!r}",
                        )
                    )
    return issues


def check_start_here(hub: Path, files: dict[str, list[str]]) -> list[Issue]:
    lines = files.get("START_HERE.md")
    if lines is None:
        return []

    path = hub / "START_HERE.md"
    line_count = len(lines)
    if line_count > 60:
        return [
            Issue(
                "error",
                path,
                None,
                f"START_HERE.md has {line_count} lines; hard cap is 60",
            )
        ]
    if line_count < 25 or line_count > 40:
        return [
            Issue(
                "warning",
                path,
                None,
                f"START_HERE.md has {line_count} lines; target is 25-40",
            )
        ]
    return []


def check_todo_completion(hub: Path, files: dict[str, list[str]]) -> list[Issue]:
    lines = files.get("WORK.md")
    if lines is None:
        return []

    issues: list[Issue] = []
    path = hub / "WORK.md"
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


def check_active_decision_rationale(hub: Path, files: dict[str, list[str]]) -> list[Issue]:
    lines = files.get("DECISIONS.md")
    if lines is None:
        return []

    issues: list[Issue] = []
    path = hub / "DECISIONS.md"
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
