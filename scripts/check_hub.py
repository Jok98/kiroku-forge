#!/usr/bin/env python3
"""Validate a KirokuForge Markdown memory hub."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from structured_memory import MARKER_RE, StructuredMemoryError, parse_entries, validate_entries


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
    "State why it matters",
    "State what reduces or monitors the risk",
    "Ideas postponed with the reason or trigger for reconsideration",
    "Ideas that violate project constraints or known failure modes",
    "List work intentionally excluded from current scope",
    "List changes that must not be made and why",
    "Move old decisions here when their history still matters",
    "Move old track decisions here when their history still matters",
    "Note whether anything should be promoted to top-level memory",
    "Summarize meaningful memory changes",
    "REPLACE_WITH_UNIQUE_ID",
)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
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
CONTRACT_LABELS = MILESTONE_REQUIRED_LABELS + (
    "Milestone:",
    "Status:",
    "Area:",
    "Decision:",
    "Rationale:",
    "Consequences:",
    "Completion:",
    "Notes:",
    "Rule:",
    "Why:",
    "Reason:",
    "Keep in mind:",
    "Condition:",
    "Impact:",
    "Mitigation:",
    "Purpose:",
    "Repos:",
    "Areas:",
    "Keywords:",
    "Read:",
    "Related:",
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
        "--hub-dir",
        action="store_true",
        help="Treat path as the exact hub directory, including a custom name.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Exit with status 1 when warnings are present.",
    )
    parser.add_argument(
        "--allow-long-handoff",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Allow a user-requested extended handoff at this hub-relative path. "
            "Repeat for each existing START_HERE.md to exempt from its length cap."
        ),
    )
    return parser.parse_args()


def resolve_hub(path: Path, hub_dir: bool = False) -> Path:
    candidate = path.resolve()
    if hub_dir or path.name == "kiroku" or candidate.name == "kiroku":
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


def markdown_lines(lines: list[str]) -> list[tuple[str, bool]]:
    """Mark fenced code without changing source offsets; omit fence delimiters."""
    parsed: list[tuple[str, bool]] = []
    fence_char: str | None = None
    fence_length = 0
    for line in lines:
        match = FENCE_RE.match(line)
        if fence_char is not None:
            if (
                match is not None
                and match.group(1)[0] == fence_char
                and len(match.group(1)) >= fence_length
                and not match.group(2).strip()
            ):
                fence_char = None
                parsed.append(("", True))
            else:
                parsed.append((line, True))
        elif match is not None and not (
            match.group(1)[0] == "`" and "`" in match.group(2)
        ):
            fence_char = match.group(1)[0]
            fence_length = len(match.group(1))
            parsed.append(("", True))
        else:
            parsed.append((line, False))
    return parsed


def label_value(block: list[str], label: str) -> str | None:
    parsed = markdown_lines(block)
    for index, (line, is_code) in enumerate(parsed):
        stripped = line.strip()
        if is_code or not stripped.startswith(label):
            continue

        inline_value = stripped[len(label) :].strip()
        if inline_value:
            return inline_value

        for following, following_is_code in parsed[index + 1 :]:
            candidate = following.strip()
            if not candidate:
                continue
            if not following_is_code and (
                HEADING_RE.match(following) or candidate.startswith(CONTRACT_LABELS)
                or MARKER_RE.search(following)
            ):
                return None
            return candidate

        return None

    return None


def heading_blocks(
    lines: list[str], prefix: str = "### "
) -> list[tuple[int, list[str]]]:
    blocks: list[tuple[int, list[str]]] = []
    start: int | None = None
    level = len(prefix.strip())

    for index, (line, is_code) in enumerate(markdown_lines(lines)):
        if not is_code and MARKER_RE.search(line):
            if start is not None:
                blocks.append((start, lines[start:index]))
                start = None
            continue
        match = None if is_code else HEADING_RE.match(line)
        if match is None or len(match.group(1)) > level:
            continue
        if start is not None:
            blocks.append((start, lines[start:index]))
            start = None
        if len(match.group(1)) == level:
            start = index

    if start is not None:
        blocks.append((start, lines[start:]))

    return blocks


def check_required_files(hub: Path) -> list[Issue]:
    issues: list[Issue] = []
    for name in REQUIRED_FILES:
        path = hub / name
        if not path.is_file():
            message = (
                "required hub path exists but is not a file"
                if path.exists() or path.is_symlink()
                else "required hub file is missing"
            )
            issues.append(Issue("error", path, None, message))
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
            if needle.casefold() in line.casefold():
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
    hard_cap: int,
    allow_long: bool = False,
) -> list[Issue]:
    line_count = len(lines)
    if line_count > hard_cap and not allow_long:
        return [
            Issue(
                "error",
                path,
                None,
                f"START_HERE.md has {line_count} lines; hard cap is {hard_cap}",
            )
        ]
    return []


def resolve_long_handoffs(
    hub: Path, requested_paths: list[str]
) -> tuple[set[Path], list[Issue]]:
    allowed: set[Path] = set()
    issues: list[Issue] = []
    for value in requested_paths:
        relative = Path(value)
        parts = relative.parts
        is_global = parts == ("START_HERE.md",)
        is_track = (
            len(parts) == 3
            and parts[0] == "tracks"
            and TRACK_SLUG_RE.fullmatch(parts[1]) is not None
            and parts[2] == "START_HERE.md"
        )
        if relative.is_absolute() or not (is_global or is_track):
            issues.append(
                Issue(
                    "error",
                    hub,
                    None,
                    f"--allow-long-handoff {value!r} must name START_HERE.md or "
                    "tracks/<slug>/START_HERE.md relative to the hub",
                )
            )
            continue
        path = hub / relative
        if not path.is_file():
            issues.append(
                Issue(
                    "error",
                    path,
                    None,
                    "--allow-long-handoff requires an existing handoff file",
                )
            )
            continue
        # Keep the named path distinct from aliases to other handoffs.
        allowed.add(path)
    return allowed, issues


def check_start_here(
    hub: Path,
    files: dict[str, list[str]],
    allowed_handoffs: set[Path] | None = None,
) -> list[Issue]:
    lines = files.get("START_HERE.md")
    if lines is None:
        return []
    path = hub / "START_HERE.md"
    return check_start_here_lines(path, lines, 60, path in (allowed_handoffs or set()))


def check_todo_completion_file(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for start, block in heading_blocks(lines):
        if (label_value(block, "Status:") or "").lower() == "todo":
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
        if (label_value(block, "Status:") or "").lower() == "active":
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
        except OSError as exc:
            issues.append(Issue("error", path, None, f"cannot read file: {exc}"))

    return files, issues


def load_optional_file(path: Path) -> tuple[list[str] | None, list[Issue]]:
    if not path.is_file():
        if path.exists() or path.is_symlink():
            return None, [Issue("error", path, None, "expected a file at this path")]
        return None, []
    try:
        return read_lines(path), []
    except UnicodeDecodeError as exc:
        return None, [Issue("error", path, None, f"file is not valid UTF-8: {exc}")]
    except OSError as exc:
        return None, [Issue("error", path, None, f"cannot read file: {exc}")]


def discover_track_dirs(hub: Path) -> list[Path]:
    tracks_dir = hub / "tracks"
    if not tracks_dir.is_dir():
        return []
    return sorted(
        path
        for path in tracks_dir.iterdir()
        if path.is_dir() and path.name != "_template"
    )


def local_read_target(value: str) -> str | None:
    """Extract a local path from a plain path, code span, or Markdown link."""
    if value.startswith("`"):
        match = re.fullmatch(r"(`+)(.+?)\1", value)
        if match is None:
            return None
        value = match.group(2)
    elif value.startswith("["):
        match = re.fullmatch(
            r"\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s()]+))"
            r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)",
            value,
        )
        if match is None:
            return None
        value = match.group(1) or match.group(2)
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc or parsed.query or not parsed.path:
        return None
    target = unquote(parsed.path)
    if any(character in target for character in ("\x00", "\n", "\r")):
        return None
    return target


def check_tracks_index(hub: Path, track_dirs: list[Path]) -> list[Issue]:
    path = hub / TRACK_INDEX_FILE
    lines, load_issues = load_optional_file(path)
    issues = list(load_issues)

    if lines is None:
        if track_dirs and not load_issues:
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
    indexed_slugs: set[str] = set()
    directory_slugs = {track_dir.name for track_dir in track_dirs}

    for start, block in blocks:
        heading = HEADING_RE.match(block[0])
        assert heading is not None
        slug = re.sub(r"[ \t]+#+[ \t]*$", "", heading.group(2)).strip()
        if not TRACK_SLUG_RE.fullmatch(slug):
            issues.append(
                Issue("error", path, start + 1, f"invalid track slug {slug!r}")
            )
            continue
        if slug in indexed_slugs:
            issues.append(
                Issue("error", path, start + 1, f"duplicate track entry {slug!r}")
            )
        indexed_slugs.add(slug)

        status = label_value(block, "Status:")
        normalized = status.lower() if status is not None else None
        if status is None:
            issues.append(
                Issue("error", path, start + 1, f"track {slug!r} is missing Status:")
            )
        elif normalized not in TRACK_STATUSES:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    f"track status {status!r} is not one of {sorted(TRACK_STATUSES)}",
                )
            )

        track_dir = hub / "tracks" / slug
        has_directory = slug in directory_slugs
        candidate_without_directory = normalized == "candidate" and not has_directory
        if not has_directory and (track_dir.exists() or track_dir.is_symlink()):
            issues.append(
                Issue(
                    "error",
                    track_dir,
                    None,
                    "expected a track directory at this path",
                )
            )
        elif not has_directory and not candidate_without_directory:
            issues.append(
                Issue(
                    "error", path, start + 1, f"track directory is missing for {slug!r}"
                )
            )

        read_value = label_value(block, "Read:")
        expected = f"tracks/{slug}/START_HERE.md"
        if read_value is None:
            if not candidate_without_directory:
                issues.append(
                    Issue(
                        "error",
                        path,
                        start + 1,
                        f"track {slug!r} is missing a Read: target",
                    )
                )
            continue

        target = local_read_target(read_value)
        try:
            resolved_target = (hub / target).resolve() if target is not None else None
            expected_target = (hub / expected).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            issues.append(
                Issue("error", path, start + 1, f"cannot resolve Read: target: {exc}")
            )
            continue
        if resolved_target != expected_target:
            issues.append(
                Issue(
                    "error",
                    path,
                    start + 1,
                    f"track {slug!r} Read: must target the local file {expected}",
                )
            )
        elif not candidate_without_directory and not resolved_target.is_file():
            issues.append(
                Issue(
                    "error", path, start + 1, f"track {slug!r} Read: target is not a file"
                )
            )

    for slug in sorted(directory_slugs - indexed_slugs):
        issues.append(
            Issue(
                "error", path, None, f"TRACKS.md is missing an entry for track {slug!r}"
            )
        )

    return issues


def check_track_dirs(
    track_dirs: list[Path], allowed_handoffs: set[Path] | None = None
) -> list[Issue]:
    issues: list[Issue] = []

    for track_dir in track_dirs:
        slug = track_dir.name
        if not TRACK_SLUG_RE.fullmatch(slug):
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
                message = (
                    "required track path exists but is not a file"
                    if path.exists() or path.is_symlink()
                    else "required track file is missing"
                )
                issues.append(Issue("error", path, None, message))

        files: dict[str, list[str]] = {}
        for name in TRACK_CHECK_FILES:
            path = track_dir / name
            if name in TRACK_REQUIRED_FILES and not path.is_file():
                continue
            lines, load_issues = load_optional_file(path)
            issues.extend(load_issues)
            if lines is not None:
                files[name] = lines
                issues.extend(check_file_placeholders(path, lines))

        start_here = files.get("START_HERE.md")
        if start_here is not None:
            handoff_path = track_dir / "START_HERE.md"
            issues.extend(
                check_start_here_lines(
                    handoff_path,
                    start_here,
                    50,
                    handoff_path in (allowed_handoffs or set()),
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


def iter_hub_markdown(hub: Path):
    """Share the same source boundary between structured checks and indexing."""
    def visit(directory: Path):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(hub).as_posix()
            if path.name.startswith(".") or relative == "tracks/_template":
                continue
            if path.is_symlink():
                if path.suffix == ".md" or path.is_dir():
                    raise ValueError(f"Markdown source symlinks are not supported: {relative}")
                continue
            if path.is_dir():
                yield from visit(path)
            elif path.suffix == ".md":
                if not path.is_file():
                    raise ValueError(f"Markdown source is not a regular file: {relative}")
                yield path
    yield from visit(hub)


def check_structured_entries(hub: Path) -> list[Issue]:
    entries: list[dict] = []
    issues: list[Issue] = []
    try:
        for path in iter_hub_markdown(hub):
            try:
                text = path.read_bytes().decode("utf-8")
                entries.extend(parse_entries(path.relative_to(hub).as_posix(), text))
            except (OSError, UnicodeError, StructuredMemoryError) as exc:
                issues.append(Issue("error", path, None, str(exc)))
        if not issues:
            validate_entries(entries)
    except (OSError, ValueError) as exc:
        issues.append(Issue("error", hub, None, str(exc)))
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
    try:
        hub = resolve_hub(Path(args.path), hub_dir=args.hub_dir)
    except (OSError, RuntimeError) as exc:
        print_issues(
            "Errors",
            [Issue("error", Path(args.path), None, f"cannot resolve hub: {exc}")],
        )
        return 1
    if not hub.is_dir():
        message = (
            "expected a hub directory at this path"
            if hub.exists() or hub.is_symlink()
            else "hub directory is missing"
        )
        print_issues("Errors", [Issue("error", hub, None, message)])
        return 1

    allowed_handoffs, issues = resolve_long_handoffs(hub, args.allow_long_handoff)
    issues.extend(check_required_files(hub))
    files, load_issues = load_existing_files(hub)
    issues.extend(load_issues)
    issues.extend(check_placeholders(hub, files))
    issues.extend(check_start_here(hub, files, allowed_handoffs))
    issues.extend(check_todo_completion(hub, files))
    issues.extend(check_active_decision_rationale(hub, files))
    tracks_path = hub / "tracks"
    if (tracks_path.exists() or tracks_path.is_symlink()) and not tracks_path.is_dir():
        issues.append(
            Issue("error", tracks_path, None, "expected a tracks directory at this path")
        )
    try:
        track_dirs = discover_track_dirs(hub)
    except OSError as exc:
        issues.append(Issue("error", tracks_path, None, f"cannot list tracks: {exc}"))
        track_dirs = []
    issues.extend(check_tracks_index(hub, track_dirs))
    issues.extend(check_track_dirs(track_dirs, allowed_handoffs))
    issues.extend(check_structured_entries(hub))

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
