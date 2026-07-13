#!/usr/bin/env python3
"""Scaffold a KirokuForge Markdown memory hub from templates."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


STANDARD_FILES = (
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
TRACK_FILES = (
    "START_HERE.md",
    "STATE.md",
    "ROADMAP.md",
    "WORK.md",
    "DECISIONS.md",
    "RISKS.md",
    "LOG.md",
)
TRACK_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class CopyOperation:
    source: Path
    target: Path
    action: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a KirokuForge kiroku/ hub from bundled templates."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project root or kiroku/ hub directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        help="Template directory to copy. Defaults to assets/templates/kiroku.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Overwrite selected existing files. Existing standard hub files are "
            "still preserved when adding tracks."
        ),
    )
    parser.add_argument(
        "--with-tracks",
        action="store_true",
        help="Also create TRACKS.md from the bundled template when missing.",
    )
    parser.add_argument(
        "--track",
        action="append",
        default=[],
        metavar="SLUG",
        help=(
            "Create or complete a track folder from "
            "assets/templates/kiroku/tracks/_template while preserving existing "
            "track files unless --overwrite is passed. Can be repeated."
        ),
    )
    parser.add_argument(
        "--track-template-dir",
        type=Path,
        help=(
            "Track template directory. Defaults to "
            "assets/templates/kiroku/tracks/_template."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned file operations without writing files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run scripts/check_hub.py after scaffolding.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="With --check, exit non-zero when checker warnings are present.",
    )
    return parser.parse_args()


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_template_dir() -> Path:
    return skill_root() / "assets" / "templates" / "kiroku"


def default_track_template_dir(template_dir: Path) -> Path:
    return template_dir / "tracks" / "_template"


def resolve_hub(path: Path) -> Path:
    candidate = path.resolve()
    if candidate.name == "kiroku" or (candidate / "START_HERE.md").exists():
        return candidate
    return candidate / "kiroku"


def display(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def validate_template_files(template_dir: Path, names: tuple[str, ...]) -> list[Path]:
    if not template_dir.is_dir():
        raise SystemExit(f"Template directory not found: {template_dir}")

    missing = [name for name in names if not (template_dir / name).is_file()]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"Template directory is missing required files: {names}")

    return [template_dir / name for name in names]


def validate_track_slugs(slugs: list[str]) -> list[str]:
    unique_slugs = list(dict.fromkeys(slugs))
    invalid = [slug for slug in unique_slugs if not TRACK_SLUG_RE.match(slug)]
    if invalid:
        names = ", ".join(invalid)
        raise SystemExit(
            "Invalid track slug(s): "
            f"{names}. Use lowercase letters, digits, and hyphens."
        )
    return unique_slugs


def plan_templates(
    templates: list[Path],
    target_dir: Path,
    overwrite: bool,
    skip_existing: bool,
) -> tuple[list[CopyOperation], list[Path], list[Path]]:
    operations: list[CopyOperation] = []
    skipped: list[Path] = []
    conflicts: list[Path] = []

    for template in templates:
        target = target_dir / template.name
        if target.exists():
            if skip_existing:
                skipped.append(target)
            elif overwrite:
                operations.append(CopyOperation(template, target, "overwrite"))
            else:
                conflicts.append(target)
        else:
            operations.append(CopyOperation(template, target, "create"))

    return operations, skipped, conflicts


def print_paths(title: str, paths: list[Path]) -> None:
    if not paths:
        return
    print(title, flush=True)
    for path in paths:
        print(f"  - {display(path)}", flush=True)


def copy_operations(operations: list[CopyOperation], dry_run: bool) -> None:
    for operation in operations:
        if dry_run:
            print(f"{operation.action}: {display(operation.target)}", flush=True)
            continue
        operation.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(operation.source, operation.target)
        print(f"{operation.action}: {display(operation.target)}", flush=True)


def track_entry(slug: str) -> list[str]:
    keywords = slug.replace("-", ", ")
    return [
        f"### {slug}",
        "",
        "Status: active",
        "Purpose: TODO: describe this workstream in one line.",
        "Repos: TBD",
        "Areas: TBD",
        f"Keywords: {keywords}",
        f"Read: tracks/{slug}/START_HERE.md",
        "Related: none",
    ]


def ensure_track_entries(hub: Path, slugs: list[str], dry_run: bool) -> None:
    if not slugs:
        return

    path = hub / TRACK_INDEX_FILE
    if dry_run:
        for slug in slugs:
            print(f"ensure-entry: {display(path)} -> {slug}", flush=True)
        return

    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    existing_slugs = {
        line.removeprefix("### ").strip()
        for line in lines
        if line.startswith("### ")
    }
    missing_slugs = [slug for slug in slugs if slug not in existing_slugs]
    if not missing_slugs:
        return

    if "## Active" not in lines:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["## Active", ""])

    active_index = lines.index("## Active")
    insert_index = len(lines)
    for index in range(active_index + 1, len(lines)):
        if lines[index].startswith("## "):
            insert_index = index
            break

    active_block = lines[active_index + 1 : insert_index]
    active_block = [line for line in active_block if line.strip() != "- None."]

    entries: list[str] = []
    for slug in missing_slugs:
        if entries:
            entries.append("")
        entries.extend(track_entry(slug))

    replacement = active_block
    while replacement and not replacement[0].strip():
        replacement.pop(0)
    while replacement and not replacement[-1].strip():
        replacement.pop()

    if replacement:
        replacement.extend([""])
    replacement.extend(entries)
    if replacement:
        replacement.append("")

    lines = lines[: active_index + 1] + [""] + replacement + lines[insert_index:]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    for slug in missing_slugs:
        print(f"ensure-entry: {display(path)} -> {slug}", flush=True)


def run_checker(hub: Path, strict_warnings: bool) -> int:
    checker = skill_root() / "scripts" / "check_hub.py"
    command = [sys.executable, str(checker), str(hub)]
    if strict_warnings:
        command.append("--strict-warnings")
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    args = parse_args()
    template_dir = (args.template_dir or default_template_dir()).resolve()
    track_template_dir = (
        args.track_template_dir or default_track_template_dir(template_dir)
    ).resolve()
    hub = resolve_hub(Path(args.path))
    track_slugs = validate_track_slugs(args.track)
    additive_mode = args.with_tracks or bool(track_slugs)

    standard_templates = validate_template_files(template_dir, STANDARD_FILES)
    operations, skipped, conflicts = plan_templates(
        standard_templates,
        hub,
        overwrite=args.overwrite and not additive_mode,
        skip_existing=additive_mode,
    )

    if args.with_tracks or track_slugs:
        track_index_template = validate_template_files(
            template_dir, (TRACK_INDEX_FILE,)
        )
        index_operations, index_skipped, index_conflicts = plan_templates(
            track_index_template,
            hub,
            overwrite=args.overwrite and args.with_tracks,
            skip_existing=not (args.overwrite and args.with_tracks),
        )
        operations.extend(index_operations)
        skipped.extend(index_skipped)
        conflicts.extend(index_conflicts)

    if track_slugs:
        track_templates = validate_template_files(track_template_dir, TRACK_FILES)
        for slug in track_slugs:
            target_dir = hub / "tracks" / slug
            track_operations, track_skipped, track_conflicts = plan_templates(
                track_templates,
                target_dir,
                overwrite=args.overwrite,
                skip_existing=not args.overwrite,
            )
            operations.extend(track_operations)
            skipped.extend(track_skipped)
            conflicts.extend(track_conflicts)

    if conflicts:
        print_paths("Refusing to overwrite existing files:", conflicts)
        print("Use --overwrite to replace selected files.", flush=True)
        return 1

    if args.dry_run:
        print(f"Dry run for Kiroku hub: {display(hub)}", flush=True)
    else:
        hub.mkdir(parents=True, exist_ok=True)

    if skipped:
        print_paths("Preserving existing files:", skipped)

    if not operations:
        print("No files to create.", flush=True)
    else:
        copy_operations(operations, args.dry_run)

    ensure_track_entries(hub, track_slugs, args.dry_run)

    if args.dry_run:
        return 0
    if args.check:
        return run_checker(hub, args.strict_warnings)

    print(f"Kiroku hub scaffold created: {display(hub)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
