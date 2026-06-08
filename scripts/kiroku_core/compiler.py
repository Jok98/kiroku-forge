"""Compilation of KirokuForge ChangeSets."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .canonical import canonical_bytes, canonicalize_memory
from .change_set import validate_change_set
from .findings import Finding, ValidationResult
from .hashing import receipt_hash, record_hash, state_hash
from .integrity import validate_memory_integrity


DEFAULT_COMPILER = {
    "name": "kiroku-compiler",
    "version": "3.0.0-dev",
}
STALE_CHANGESET = "STALE_CHANGESET"


class CompilePersistenceError(RuntimeError):
    """Raised when persistence fails outside artifact validation."""


class CompileLockError(CompilePersistenceError):
    """Raised when another compiler owns the memory lock."""


@dataclass(frozen=True)
class CompileResult:
    """Result of a pure compilation attempt."""

    memory: dict[str, Any] | None = None
    findings: tuple[Finding, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "findings",
            ValidationResult.from_findings(self.findings).findings,
        )

    @property
    def ok(self) -> bool:
        """Return whether compilation produced a complete valid Memory."""

        return self.memory is not None and not self.errors

    @property
    def errors(self) -> tuple[Finding, ...]:
        """Return blocking findings."""

        return tuple(
            finding
            for finding in self.findings
            if finding.severity == "error"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible diagnostic representation."""

        return {
            "ok": self.ok,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _finding_result(result: ValidationResult) -> CompileResult:
    return CompileResult(memory=None, findings=result.findings)


def _compile_finding(
    code: str,
    path: str,
    message: str,
    *entity_ids: str,
) -> Finding:
    return Finding(
        code=code,
        severity="error",
        path=path,
        message=f"{path}: {message}",
        entity_ids=tuple(entity_ids),
    )


def _remove_exact(items: list[Any], target: Any) -> None:
    try:
        items.remove(target)
    except ValueError:
        return


def _refresh_record_hash(record: dict[str, Any]) -> str:
    record["content_hash"] = record_hash(record)
    return record["content_hash"]


def _touch_record(
    record: dict[str, Any],
    *,
    compilation_id: str,
    compiled_at: str,
) -> None:
    record["updated_at"] = compiled_at
    record["updated_by"] = compilation_id


def _record_receipt(
    operation: dict[str, Any],
    affected_ids: list[str],
    hash_changes: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt = {
        "operation_id": operation["operation_id"],
        "operation_type": operation["operation_type"],
        "affected_ids": affected_ids,
        "hash_changes": hash_changes,
    }
    reason = operation.get("transition_reason") or operation.get("reason")
    if reason is not None:
        receipt["transition_reason"] = reason
    return receipt


def _record_hash_change(
    record_id: str,
    previous_hash: str | None,
    result_hash: str | None,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "previous_hash": previous_hash,
        "result_hash": result_hash,
    }


def _memory_hash_change(
    memory_id: str,
    previous_hash: str | None,
) -> dict[str, Any]:
    return {
        "id": memory_id,
        "previous_hash": previous_hash,
        "result_hash": None,
    }


def _make_initialized_memory(
    operation: dict[str, Any],
    *,
    compiled_at: str,
) -> dict[str, Any]:
    project = copy.deepcopy(operation["project"])
    project["created_at"] = compiled_at
    project["updated_at"] = compiled_at
    return {
        "artifact_type": "memory",
        "schema_version": "3.0.0",
        "memory_id": operation["memory_id"],
        "revision": 1,
        "state_hash": "sha256:" + "0" * 64,
        "project": project,
        "sources": [],
        "records": [],
        "compilations": [],
    }


def _copy_source(
    source: dict[str, Any],
    *,
    compilation_id: str,
) -> dict[str, Any]:
    result = copy.deepcopy(source)
    result["created_by"] = compilation_id
    return result


def _copy_new_record(
    record: dict[str, Any],
    *,
    compilation_id: str,
    compiled_at: str,
) -> dict[str, Any]:
    result = copy.deepcopy(record)
    result["created_at"] = compiled_at
    result["updated_at"] = compiled_at
    result["created_by"] = compilation_id
    result["updated_by"] = compilation_id
    result["content_hash"] = "sha256:" + "0" * 64
    _refresh_record_hash(result)
    return result


def _add_supersedes_relation(
    record: dict[str, Any],
    predecessor_id: str,
) -> None:
    if any(
        relation["type"] == "supersedes"
        and relation["target_id"] == predecessor_id
        for relation in record["relations"]
    ):
        return
    record["relations"].append(
        {"type": "supersedes", "target_id": predecessor_id}
    )


def _collect_input_source_ids(change_set: dict[str, Any]) -> list[str]:
    source_ids: set[str] = set()

    for resolution in change_set["source_resolutions"]:
        source_id = resolution.get("canonical_source_id")
        if isinstance(source_id, str):
            source_ids.add(source_id)

    def collect_evidence(items: Iterable[dict[str, Any]]) -> None:
        for evidence in items:
            source_ids.add(evidence["source_id"])

    for operation in change_set["operations"]:
        operation_type = operation["operation_type"]
        if operation_type == "add_source":
            source_ids.add(operation["source"]["id"])
        elif operation_type == "create_record":
            collect_evidence(operation["record"]["evidence"])
        elif operation_type in {"add_evidence", "remove_evidence"}:
            source_ids.add(operation["evidence"]["source_id"])
        elif operation_type == "supersede_record":
            collect_evidence(operation["successor"]["evidence"])

    return sorted(source_ids)


def _apply_operation(
    operation: dict[str, Any],
    prospective: dict[str, Any] | None,
    *,
    base_state_hash: str | None,
    compilation_id: str,
    compiled_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    operation_type = operation["operation_type"]

    if operation_type == "initialize_memory":
        initialized = _make_initialized_memory(
            operation,
            compiled_at=compiled_at,
        )
        operation_receipt = _record_receipt(
            operation,
            [operation["memory_id"]],
            [_memory_hash_change(operation["memory_id"], None)],
        )
        return initialized, operation_receipt

    if prospective is None:
        raise RuntimeError("non-initialization operation requires memory")

    records = {record["id"]: record for record in prospective["records"]}

    if operation_type == "update_project":
        prospective["project"].update(copy.deepcopy(operation["changes"]))
        prospective["project"]["updated_at"] = compiled_at
        operation_receipt = _record_receipt(
            operation,
            [prospective["memory_id"]],
            [_memory_hash_change(prospective["memory_id"], base_state_hash)],
        )
        return prospective, operation_receipt

    if operation_type == "add_source":
        source = _copy_source(
            operation["source"],
            compilation_id=compilation_id,
        )
        prospective["sources"].append(source)
        operation_receipt = _record_receipt(operation, [source["id"]], [])
        return prospective, operation_receipt

    if operation_type == "create_record":
        record = _copy_new_record(
            operation["record"],
            compilation_id=compilation_id,
            compiled_at=compiled_at,
        )
        prospective["records"].append(record)
        operation_receipt = _record_receipt(
            operation,
            [record["id"]],
            [_record_hash_change(record["id"], None, record["content_hash"])],
        )
        return prospective, operation_receipt

    if operation_type == "supersede_record":
        successor = _copy_new_record(
            operation["successor"],
            compilation_id=compilation_id,
            compiled_at=compiled_at,
        )
        _add_supersedes_relation(successor, operation["predecessor_id"])
        _refresh_record_hash(successor)
        prospective["records"].append(successor)
        operation_receipt = _record_receipt(
            operation,
            [operation["predecessor_id"], successor["id"]],
            [
                _record_hash_change(
                    successor["id"],
                    None,
                    successor["content_hash"],
                )
            ],
        )
        return prospective, operation_receipt

    record = records[operation["record_id"]]
    previous_hash = record["content_hash"]

    if operation_type == "amend_record":
        record.update(copy.deepcopy(operation["changes"]))
    elif operation_type == "add_evidence":
        evidence = copy.deepcopy(operation["evidence"])
        if evidence not in record["evidence"]:
            record["evidence"].append(evidence)
    elif operation_type == "remove_evidence":
        _remove_exact(record["evidence"], operation["evidence"])
    elif operation_type == "set_verification":
        record["verification"] = copy.deepcopy(operation["verification"])
    elif operation_type == "add_relation":
        relation = copy.deepcopy(operation["relation"])
        if relation not in record["relations"]:
            record["relations"].append(relation)
    elif operation_type == "remove_relation":
        _remove_exact(record["relations"], operation["relation"])
    elif operation_type == "transition_record":
        record["state"] = operation["target_state"]
        record["content"] = copy.deepcopy(operation["content"])
    else:
        raise RuntimeError(f"unsupported operation type {operation_type!r}")

    _touch_record(
        record,
        compilation_id=compilation_id,
        compiled_at=compiled_at,
    )
    result_hash = _refresh_record_hash(record)
    operation_receipt = _record_receipt(
        operation,
        [record["id"]],
        [_record_hash_change(record["id"], previous_hash, result_hash)],
    )
    return prospective, operation_receipt


def _set_final_memory_hashes(
    memory: dict[str, Any],
    operation_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    memory = canonicalize_memory(memory)
    for record in memory["records"]:
        _refresh_record_hash(record)
    memory["state_hash"] = state_hash(memory)

    for receipt in operation_receipts:
        for change in receipt["hash_changes"]:
            if change["id"] == memory["memory_id"]:
                change["result_hash"] = memory["state_hash"]
    return memory


def _build_receipt(
    *,
    change_set: dict[str, Any],
    base_memory: dict[str, Any] | None,
    result_memory: dict[str, Any],
    compilation_id: str,
    compiled_at: str,
    compiler: dict[str, Any],
    warnings: Sequence[str],
    operation_receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    previous_receipt_hash = None
    if base_memory is not None:
        previous_receipt_hash = base_memory["compilations"][-1]["receipt_hash"]

    receipt = {
        "id": compilation_id,
        "base_revision": 0 if base_memory is None else base_memory["revision"],
        "result_revision": result_memory["revision"],
        "base_state_hash": None if base_memory is None else base_memory["state_hash"],
        "result_state_hash": result_memory["state_hash"],
        "change_set_id": change_set["change_set_id"],
        "change_set_hash": change_set["artifact_hash"],
        "actor": copy.deepcopy(change_set["actor"]),
        "compiler": copy.deepcopy(compiler),
        "input_source_ids": _collect_input_source_ids(change_set),
        "operations": copy.deepcopy(operation_receipts),
        "compiled_at": compiled_at,
        "warnings": list(warnings),
        "previous_receipt_hash": previous_receipt_hash,
        "receipt_hash": "sha256:" + "0" * 64,
    }
    receipt["receipt_hash"] = receipt_hash(receipt)
    return receipt


def compile_change_set(
    change_set: Any,
    memory: dict[str, Any] | None,
    *,
    compilation_id: str,
    compiled_at: str,
    compiler: dict[str, Any] | None = None,
    warnings: Sequence[str] = (),
) -> CompileResult:
    """Compile one ChangeSet against a base Memory without persistence.

    The function validates the ChangeSet before creating a mutable prospective
    copy. It returns no Memory when preflight or prospective integrity fails.
    """

    preflight = validate_change_set(change_set, memory)
    if not preflight.ok:
        return _finding_result(preflight)

    active_compiler = copy.deepcopy(compiler or DEFAULT_COMPILER)
    base_memory = copy.deepcopy(memory) if memory is not None else None
    prospective = copy.deepcopy(base_memory)
    base_state_hash = None if base_memory is None else base_memory["state_hash"]
    operation_receipts: list[dict[str, Any]] = []

    for operation in change_set["operations"]:
        prospective, operation_receipt = _apply_operation(
            operation,
            prospective,
            base_state_hash=base_state_hash,
            compilation_id=compilation_id,
            compiled_at=compiled_at,
        )
        operation_receipts.append(operation_receipt)

    if prospective is None:
        raise RuntimeError("ChangeSet produced no prospective memory")

    if base_memory is not None:
        prospective["revision"] = base_memory["revision"] + 1

    prospective = _set_final_memory_hashes(prospective, operation_receipts)
    receipt = _build_receipt(
        change_set=change_set,
        base_memory=base_memory,
        result_memory=prospective,
        compilation_id=compilation_id,
        compiled_at=compiled_at,
        compiler=active_compiler,
        warnings=warnings,
        operation_receipts=operation_receipts,
    )
    prospective["compilations"].append(receipt)
    prospective = canonicalize_memory(prospective)

    integrity = validate_memory_integrity(prospective)
    if not integrity.ok:
        return _finding_result(integrity)

    return CompileResult(memory=prospective)


def _default_lock_path(memory_path: Path) -> Path:
    return memory_path.with_name(f"{memory_path.name}.lock")


@contextmanager
def _exclusive_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CompileLockError(
                f"memory compilation lock is already held: {lock_path}"
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_memory_file(memory_path: Path) -> dict[str, Any] | None:
    if not memory_path.exists():
        return None
    try:
        with memory_path.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise CompilePersistenceError(
            f"cannot read canonical memory {memory_path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise CompilePersistenceError(
            f"canonical memory {memory_path} must contain a JSON object"
        )
    return value


def _fsync_directory(path: Path) -> None:
    directory_fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _write_memory_atomic(memory_path: Path, memory: dict[str, Any]) -> None:
    parent = memory_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=parent,
            prefix=f".{memory_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(canonical_bytes(memory))
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, memory_path)
        temp_path = None
        _fsync_directory(parent)
    except OSError as exc:
        raise CompilePersistenceError(
            f"cannot atomically write canonical memory {memory_path}: {exc}"
        ) from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def compile_memory_file(
    memory_path: Path | str,
    change_set: Any,
    *,
    compilation_id: str,
    compiled_at: str,
    compiler: dict[str, Any] | None = None,
    warnings: Sequence[str] = (),
    lock_path: Path | str | None = None,
) -> CompileResult:
    """Compile a ChangeSet and atomically replace ``memory.json`` on success."""

    active_memory_path = Path(memory_path)
    active_lock_path = (
        Path(lock_path)
        if lock_path is not None
        else _default_lock_path(active_memory_path)
    )

    with _exclusive_lock(active_lock_path):
        base_memory = _load_memory_file(active_memory_path)
        result = compile_change_set(
            change_set,
            base_memory,
            compilation_id=compilation_id,
            compiled_at=compiled_at,
            compiler=compiler,
            warnings=warnings,
        )
        if not result.ok:
            return result

        if base_memory is None and active_memory_path.exists():
            return CompileResult(
                memory=None,
                findings=(
                    _compile_finding(
                        STALE_CHANGESET,
                        "$.target_memory_id",
                        "initialization expected no memory, but memory appeared",
                        change_set["change_set_id"],
                        result.memory["memory_id"] if result.memory else "",
                    ),
                ),
            )

        assert result.memory is not None
        _write_memory_atomic(active_memory_path, result.memory)
        return result
