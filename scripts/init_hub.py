#!/usr/bin/env python3
"""Initialize a KirokuForge Markdown memory hub from templates."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a KirokuForge kiroku/ hub from bundled templates."
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
        help="Overwrite existing standard hub files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned file operations without writing files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run scripts/check_hub.py after initialization.",
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


def validate_templates(template_dir: Path) -> list[Path]:
    if not template_dir.is_dir():
        raise SystemExit(f"Template directory not found: {template_dir}")

    missing = [name for name in REQUIRED_FILES if not (template_dir / name).is_file()]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(f"Template directory is missing required files: {names}")

    return [template_dir / name for name in REQUIRED_FILES]


def existing_targets(hub: Path, templates: list[Path]) -> list[Path]:
    return [hub / template.name for template in templates if (hub / template.name).exists()]


def copy_templates(hub: Path, templates: list[Path], overwrite: bool, dry_run: bool) -> None:
    for template in templates:
        target = hub / template.name
        action = "overwrite" if target.exists() and overwrite else "create"
        if dry_run:
            print(f"{action}: {display(target)}")
            continue
        shutil.copy2(template, target)
        print(f"{action}: {display(target)}")


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
    hub = resolve_hub(Path(args.path))
    templates = validate_templates(template_dir)
    existing = existing_targets(hub, templates)

    if existing and not args.overwrite:
        print("Refusing to overwrite existing hub files:")
        for path in existing:
            print(f"  - {display(path)}")
        print("Use --overwrite to replace standard hub files.")
        return 1

    if args.dry_run:
        print(f"Dry run for Kiroku hub: {display(hub)}")
    else:
        hub.mkdir(parents=True, exist_ok=True)

    copy_templates(hub, templates, args.overwrite, args.dry_run)

    if args.dry_run:
        return 0
    if args.check:
        return run_checker(hub, args.strict_warnings)

    print(f"Kiroku hub initialized: {display(hub)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
