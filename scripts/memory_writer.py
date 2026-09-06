"""Save validated Markdown edits for a single explicit checkpoint publication."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath

from memory_edit import plan_edit
from memory_store import MemoryIndexError, _hub_path, _read_sources
from structured_memory import StructuredMemoryError, _reject_constant, _unique_object


def load_payload(text: str) -> dict:
    """Use the same strict JSON rules as the Markdown metadata parser."""
    try:
        payload = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise MemoryIndexError(f"Invalid write payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise MemoryIndexError("The write payload must be a JSON object")
    return payload


def _destination(hub: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if (not parts or PurePosixPath(relative).is_absolute() or ".." in parts
            or any(part.startswith(".") for part in parts)
            or relative.startswith("tracks/_template/")
            or PurePosixPath(relative).as_posix() != relative):
        raise MemoryIndexError("The writer requires a canonical, indexed hub-relative Markdown path")
    target = hub
    for part in parts:
        target = target / part
        if target.is_symlink():
            raise MemoryIndexError("The writer does not follow source symlinks")
    if target.suffix != ".md" or not target.is_file():
        raise MemoryIndexError("The writer requires an existing Markdown owner file")
    return target


def _publish_source(hub: Path, plan: dict, sources: list) -> list[str]:
    target = _destination(hub, plan["source_file"])
    expected = {source.path: source.sha256 for source in sources}
    temporary: Path | None = None
    descriptor: int | None = None
    warnings: list[str] = []
    try:
        descriptor, name = tempfile.mkstemp(prefix=".kiroku-write.", suffix=".tmp", dir=target.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            mode = stat.S_IMODE(target.stat().st_mode)
            if hasattr(os, "fchmod"):
                os.fchmod(stream.fileno(), mode)
            else:
                os.chmod(temporary, mode)
            stream.write(plan["after"].encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        # This is a single-writer workflow. Recheck the observed sources before
        # publication to avoid applying a plan over an intervening manual edit.
        if {source.path: source.sha256 for source in _read_sources(hub)} != expected:
            raise MemoryIndexError("Markdown changed while preparing the edit; nothing was published")
        _destination(hub, plan["source_file"])
        os.replace(temporary, target)
        temporary = None
        if os.name == "posix":
            directory_descriptor = None
            try:
                directory_descriptor = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                os.fsync(directory_descriptor)
            except OSError as exc:
                warnings.append(f"Markdown was saved, but directory sync failed; crash durability is unconfirmed: {exc}")
            finally:
                if directory_descriptor is not None:
                    try:
                        os.close(directory_descriptor)
                    except OSError as exc:
                        warnings.append(f"Markdown was saved, but closing its directory descriptor failed: {exc}")
    except OSError as exc:
        raise MemoryIndexError(f"Cannot publish the Markdown edit: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return warnings


def _unified_diff(before: str, after: str, path: str) -> str:
    def lines(text: str) -> list[str]:
        # Unified diffs are LF-delimited; keep any CR characters as source data.
        parts = text.split("\n")
        return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])
    result = []
    for line in difflib.unified_diff(lines(before), lines(after), fromfile=path, tofile=path):
        result.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(result)


def write_entry(hub: Path, operation: str, payload: dict, *, source_file: str | None = None,
                section: str | None = None, entry_id: str | None = None,
                dry_run: bool = False) -> dict:
    resolved = _hub_path(hub)
    sources = _read_sources(resolved)
    try:
        plan = plan_edit(sources, operation, payload, source_file=source_file,
                         section=section, entry_id=entry_id)
    except (StructuredMemoryError, ValueError) as exc:
        raise MemoryIndexError(str(exc)) from exc
    _destination(resolved, plan["source_file"])
    result = {
        "operation": operation, "id": "entry:" + plan["id"], "memory_id": plan["id"],
        "source_path": plan["source_file"], "markdown_changed": plan["changed"],
        "source_sha256": hashlib.sha256(plan["after"].encode("utf-8")).hexdigest(),
    }
    if dry_run:
        result.update(state="dry_run", markdown_saved=False,
                      diff=_unified_diff(plan["before"], plan["after"], plan["source_file"]))
        return result

    if not plan["changed"] and (
        {source.path: source.sha256 for source in _read_sources(resolved)}
        != {source.path: source.sha256 for source in sources}
    ):
        raise MemoryIndexError("Markdown changed while preparing the edit; nothing was published")
    warnings = _publish_source(resolved, plan, sources) if plan["changed"] else []
    result.update(
        state="saved", markdown_saved=plan["changed"], index_updated=False,
        checkpoint_required=True,
        next_action="Finish the checkpoint's Markdown edits and validation, then run memory.py checkpoint for this hub once.",
    )
    if warnings:
        result["warnings"] = warnings
    return result
