"""Deterministic validation of ChangeSet preconditions and transitions."""

from __future__ import annotations

import copy
from collections import Counter
from functools import lru_cache
from typing import Any, Iterable

import fastjsonschema

from .findings import Finding, ValidationResult
from .hashing import sha256_hash
from .integrity import validate_memory_integrity
from .schema import (
    SchemaValidator,
    compile_pipeline_definition,
    validate_change_set_schema,
)


ARTIFACT_HASH_MISMATCH = "ARTIFACT_HASH_MISMATCH"
STALE_CHANGESET = "STALE_CHANGESET"
SOURCE_MUTATED = "SOURCE_MUTATED"
INVALID_TRANSITION = "INVALID_TRANSITION"
MISSING_TRANSITION_REASON = "MISSING_TRANSITION_REASON"

_ALLOWED_TRANSITIONS = {
    "fact": {
        "active": {"obsolete"},
    },
    "decision": {
        "active": {"obsolete"},
    },
    "assumption": {
        "active": {"invalidated", "obsolete"},
    },
    "constraint": {
        "active": {"obsolete"},
    },
    "preference": {
        "active": {"obsolete"},
    },
    "proposal": {
        "proposed": {"accepted", "rejected", "cancelled"},
    },
    "task": {
        "todo": {"in_progress", "blocked", "done", "cancelled"},
        "in_progress": {"todo", "blocked", "done", "cancelled"},
        "blocked": {"todo", "in_progress", "done", "cancelled"},
        "done": {"todo"},
        "cancelled": {"todo"},
    },
    "question": {
        "open": {"answered", "obsolete"},
        "answered": {"open"},
        "obsolete": {"open"},
    },
    "risk": {
        "open": {"mitigated", "accepted", "closed"},
        "mitigated": {"open", "closed"},
        "accepted": {"open", "closed"},
        "closed": {"open"},
    },
    "event": {},
}

_DIRECT_METHODS = {
    "user_statement",
    "direct_observation",
    "document_read",
    "code_inspection",
    "test_result",
    "tool_result",
}

_RECORD_TARGET_FIELDS = {
    "amend_record": "record_id",
    "add_evidence": "record_id",
    "remove_evidence": "record_id",
    "set_verification": "record_id",
    "add_relation": "record_id",
    "remove_relation": "record_id",
    "transition_record": "record_id",
    "supersede_record": "predecessor_id",
}


def _finding(
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


def _artifact_hash(change_set: dict[str, Any]) -> str:
    return sha256_hash(
        {
            key: value
            for key, value in change_set.items()
            if key != "artifact_hash"
        }
    )


def _check_artifact_hash(change_set: dict[str, Any]) -> list[Finding]:
    if change_set["artifact_hash"] == _artifact_hash(change_set):
        return []
    return [
        _finding(
            ARTIFACT_HASH_MISMATCH,
            "$.artifact_hash",
            "stored hash differs from canonical ChangeSet content",
            change_set["change_set_id"],
        )
    ]


def _check_base_preconditions(
    change_set: dict[str, Any],
    memory: dict[str, Any] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    change_set_id = change_set["change_set_id"]
    target_memory_id = change_set["target_memory_id"]

    if target_memory_id is None:
        if memory is not None:
            findings.append(
                _finding(
                    STALE_CHANGESET,
                    "$.target_memory_id",
                    "initialization expected no memory, but memory exists",
                    change_set_id,
                    memory["memory_id"],
                )
            )
        return findings

    if memory is None:
        findings.append(
            _finding(
                STALE_CHANGESET,
                "$.target_memory_id",
                "ChangeSet targets a memory that does not exist",
                change_set_id,
                target_memory_id,
            )
        )
        return findings

    checks = (
        (
            "$.target_memory_id",
            target_memory_id,
            memory["memory_id"],
            "target memory ID",
        ),
        (
            "$.base_revision",
            change_set["base_revision"],
            memory["revision"],
            "base revision",
        ),
        (
            "$.base_state_hash",
            change_set["base_state_hash"],
            memory["state_hash"],
            "base state hash",
        ),
    )
    for path, actual, expected, label in checks:
        if actual != expected:
            findings.append(
                _finding(
                    STALE_CHANGESET,
                    path,
                    f"{label} does not match the loaded memory",
                    change_set_id,
                    memory["memory_id"],
                )
            )
    return findings


def _check_operation_ids(
    change_set: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    first_index: dict[str, int] = {}
    for index, operation in enumerate(change_set["operations"]):
        operation_id = operation["operation_id"]
        if operation_id in first_index:
            findings.append(
                _finding(
                    "DUPLICATE_ID",
                    f"$.operations[{index}].operation_id",
                    (
                        f"operation ID {operation_id!r} duplicates "
                        f"operations[{first_index[operation_id]}]"
                    ),
                    operation_id,
                )
            )
        else:
            first_index[operation_id] = index
    return findings


def _new_entities(
    change_set: dict[str, Any],
) -> tuple[dict[str, int], dict[str, int]]:
    source_indexes: dict[str, int] = {}
    record_indexes: dict[str, int] = {}
    for index, operation in enumerate(change_set["operations"]):
        operation_type = operation["operation_type"]
        if operation_type == "add_source":
            source_indexes.setdefault(operation["source"]["id"], index)
        elif operation_type == "create_record":
            record_indexes.setdefault(operation["record"]["id"], index)
        elif operation_type == "supersede_record":
            record_indexes.setdefault(operation["successor"]["id"], index)
    return source_indexes, record_indexes


def _check_new_entity_ids(
    change_set: dict[str, Any],
    memory: dict[str, Any] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    existing_source_ids = (
        {source["id"] for source in memory["sources"]}
        if memory is not None
        else set()
    )
    existing_record_ids = (
        {record["id"] for record in memory["records"]}
        if memory is not None
        else set()
    )
    new_source_ids: Counter[str] = Counter()
    new_record_ids: Counter[str] = Counter()

    for index, operation in enumerate(change_set["operations"]):
        operation_type = operation["operation_type"]
        if operation_type == "add_source":
            source_id = operation["source"]["id"]
            new_source_ids[source_id] += 1
            if source_id in existing_source_ids:
                findings.append(
                    _finding(
                        SOURCE_MUTATED,
                        f"$.operations[{index}].source.id",
                        (
                            f"source ID {source_id!r} already identifies an "
                            "immutable canonical source"
                        ),
                        operation["operation_id"],
                        source_id,
                    )
                )
        elif operation_type == "create_record":
            record_id = operation["record"]["id"]
            new_record_ids[record_id] += 1
            if record_id in existing_record_ids:
                findings.append(
                    _finding(
                        "DUPLICATE_ID",
                        f"$.operations[{index}].record.id",
                        f"record ID {record_id!r} already exists",
                        operation["operation_id"],
                        record_id,
                    )
                )
        elif operation_type == "supersede_record":
            record_id = operation["successor"]["id"]
            new_record_ids[record_id] += 1
            if record_id in existing_record_ids:
                findings.append(
                    _finding(
                        "DUPLICATE_ID",
                        f"$.operations[{index}].successor.id",
                        f"successor record ID {record_id!r} already exists",
                        operation["operation_id"],
                        record_id,
                    )
                )

    for entity_id, count in sorted(new_source_ids.items()):
        if count > 1:
            findings.append(
                _finding(
                    "DUPLICATE_ID",
                    "$.operations",
                    f"source ID {entity_id!r} is allocated {count} times",
                    entity_id,
                )
            )
    for entity_id, count in sorted(new_record_ids.items()):
        if count > 1:
            findings.append(
                _finding(
                    "DUPLICATE_ID",
                    "$.operations",
                    f"record ID {entity_id!r} is allocated {count} times",
                    entity_id,
                )
            )
    return findings


def _check_record_preconditions(
    change_set: dict[str, Any],
    memory: dict[str, Any] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    records = (
        {record["id"]: record for record in memory["records"]}
        if memory is not None
        else {}
    )
    for index, operation in enumerate(change_set["operations"]):
        target_field = _RECORD_TARGET_FIELDS.get(
            operation["operation_type"]
        )
        if target_field is None:
            continue
        record_id = operation[target_field]
        record = records.get(record_id)
        path = f"$.operations[{index}].{target_field}"
        if record is None:
            findings.append(
                _finding(
                    "UNKNOWN_RECORD_REFERENCE",
                    path,
                    f"target record {record_id!r} does not exist",
                    operation["operation_id"],
                    record_id,
                )
            )
            continue
        if operation["expected_record_hash"] != record["content_hash"]:
            findings.append(
                _finding(
                    STALE_CHANGESET,
                    f"$.operations[{index}].expected_record_hash",
                    (
                        f"expected hash for record {record_id!r} does not "
                        "match the base snapshot"
                    ),
                    operation["operation_id"],
                    record_id,
                )
            )
    return findings


def _check_references(
    change_set: dict[str, Any],
    memory: dict[str, Any] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    source_indexes, record_indexes = _new_entities(change_set)
    source_ids = set(source_indexes)
    record_ids = set(record_indexes)
    if memory is not None:
        source_ids.update(source["id"] for source in memory["sources"])
        record_ids.update(record["id"] for record in memory["records"])

    operation_ids = {
        operation["operation_id"] for operation in change_set["operations"]
    }
    finding_ids = {
        finding["id"] for finding in change_set["findings"]
    }

    for index, resolution in enumerate(change_set["source_resolutions"]):
        canonical_source_id = resolution.get("canonical_source_id")
        if (
            resolution["resolution"] == "reuse"
            and canonical_source_id not in source_ids
        ):
            findings.append(
                _finding(
                    "UNKNOWN_SOURCE_REFERENCE",
                    f"$.source_resolutions[{index}].canonical_source_id",
                    f"source {canonical_source_id!r} does not exist",
                    canonical_source_id,
                )
            )
        operation_id = resolution.get("operation_id")
        if operation_id is not None and operation_id not in operation_ids:
            findings.append(
                _finding(
                    "UNKNOWN_OPERATION_REFERENCE",
                    f"$.source_resolutions[{index}].operation_id",
                    f"operation {operation_id!r} does not exist",
                    operation_id,
                )
            )

    for index, resolution in enumerate(change_set["candidate_resolutions"]):
        for item_index, operation_id in enumerate(
            resolution["operation_ids"]
        ):
            if operation_id not in operation_ids:
                findings.append(
                    _finding(
                        "UNKNOWN_OPERATION_REFERENCE",
                        (
                            f"$.candidate_resolutions[{index}]"
                            f".operation_ids[{item_index}]"
                        ),
                        f"operation {operation_id!r} does not exist",
                        resolution["candidate_id"],
                        operation_id,
                    )
                )
        for item_index, finding_id in enumerate(resolution["finding_ids"]):
            if finding_id not in finding_ids:
                findings.append(
                    _finding(
                        "UNKNOWN_FINDING_REFERENCE",
                        (
                            f"$.candidate_resolutions[{index}]"
                            f".finding_ids[{item_index}]"
                        ),
                        f"finding {finding_id!r} does not exist",
                        resolution["candidate_id"],
                        finding_id,
                    )
                )

    def check_evidence(
        evidence: dict[str, Any],
        path: str,
        owner_id: str,
    ) -> None:
        source_id = evidence["source_id"]
        if source_id not in source_ids:
            findings.append(
                _finding(
                    "UNKNOWN_SOURCE_REFERENCE",
                    f"{path}.source_id",
                    f"source {source_id!r} does not exist",
                    owner_id,
                    source_id,
                )
            )

    def check_relation(
        relation: dict[str, Any],
        path: str,
        owner_id: str,
    ) -> None:
        target_id = relation["target_id"]
        if target_id not in record_ids:
            findings.append(
                _finding(
                    "UNKNOWN_RECORD_REFERENCE",
                    f"{path}.target_id",
                    f"record {target_id!r} does not exist",
                    owner_id,
                    target_id,
                )
            )

    for index, operation in enumerate(change_set["operations"]):
        path = f"$.operations[{index}]"
        operation_id = operation["operation_id"]
        operation_type = operation["operation_type"]
        if operation_type == "create_record":
            record = operation["record"]
            for item_index, evidence in enumerate(record["evidence"]):
                check_evidence(
                    evidence,
                    f"{path}.record.evidence[{item_index}]",
                    record["id"],
                )
            for item_index, relation in enumerate(record["relations"]):
                check_relation(
                    relation,
                    f"{path}.record.relations[{item_index}]",
                    record["id"],
                )
        elif operation_type == "supersede_record":
            record = operation["successor"]
            for item_index, evidence in enumerate(record["evidence"]):
                check_evidence(
                    evidence,
                    f"{path}.successor.evidence[{item_index}]",
                    record["id"],
                )
            for item_index, relation in enumerate(record["relations"]):
                check_relation(
                    relation,
                    f"{path}.successor.relations[{item_index}]",
                    record["id"],
                )
        elif operation_type in {"add_evidence", "remove_evidence"}:
            check_evidence(operation["evidence"], f"{path}.evidence", operation_id)
        elif operation_type in {"add_relation", "remove_relation"}:
            check_relation(operation["relation"], f"{path}.relation", operation_id)
    return findings


@lru_cache(maxsize=1)
def _record_draft_validator() -> SchemaValidator:
    return compile_pipeline_definition("recordDraft")


def _record_draft(record: dict[str, Any]) -> dict[str, Any]:
    excluded = {
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "content_hash",
    }
    return {
        key: copy.deepcopy(value)
        for key, value in record.items()
        if key not in excluded
    }


def _remove_exact(items: list[Any], target: Any) -> None:
    try:
        items.remove(target)
    except ValueError:
        return


def _apply_record_operations(
    draft: dict[str, Any],
    record_id: str,
    operations: Iterable[dict[str, Any]],
) -> None:
    for operation in operations:
        operation_type = operation["operation_type"]
        if operation.get("record_id") != record_id:
            continue
        if operation_type == "amend_record":
            draft.update(copy.deepcopy(operation["changes"]))
        elif operation_type == "add_evidence":
            evidence = copy.deepcopy(operation["evidence"])
            if evidence not in draft["evidence"]:
                draft["evidence"].append(evidence)
        elif operation_type == "remove_evidence":
            _remove_exact(draft["evidence"], operation["evidence"])
        elif operation_type == "set_verification":
            draft["verification"] = copy.deepcopy(operation["verification"])
        elif operation_type == "add_relation":
            relation = copy.deepcopy(operation["relation"])
            if relation not in draft["relations"]:
                draft["relations"].append(relation)
        elif operation_type == "remove_relation":
            _remove_exact(draft["relations"], operation["relation"])
        elif operation_type == "transition_record":
            draft["state"] = operation["target_state"]
            draft["content"] = copy.deepcopy(operation["content"])


def _has_direct_evidence(
    record: dict[str, Any],
    relation: str | None = None,
) -> bool:
    return any(
        evidence["method"] in _DIRECT_METHODS
        and (relation is None or evidence["relation"] == relation)
        for evidence in record["evidence"]
    )


def _has_incoming_answer(
    record_id: str,
    memory: dict[str, Any],
    operations: Iterable[dict[str, Any]],
) -> bool:
    incoming_answers = {
        (record["id"], relation["target_id"], relation.get("note"))
        for record in memory["records"]
        for relation in record["relations"]
        if relation["type"] == "answers"
    }

    for operation in operations:
        operation_type = operation["operation_type"]
        if operation_type in {"add_relation", "remove_relation"}:
            relation = operation["relation"]
            if relation["type"] != "answers":
                continue
            item = (
                operation["record_id"],
                relation["target_id"],
                relation.get("note"),
            )
            if operation_type == "add_relation":
                incoming_answers.add(item)
            else:
                incoming_answers.discard(item)
        elif operation_type in {"create_record", "supersede_record"}:
            field = (
                "record"
                if operation_type == "create_record"
                else "successor"
            )
            owner_id = operation[field]["id"]
            incoming_answers.update(
                (owner_id, relation["target_id"], relation.get("note"))
                for relation in operation[field]["relations"]
                if relation["type"] == "answers"
            )
    return any(target_id == record_id for _, target_id, _ in incoming_answers)


def _terminal_evidence_problem(
    record: dict[str, Any],
    base_state: str,
    memory: dict[str, Any],
    operations: Iterable[dict[str, Any]],
) -> str | None:
    kind = record["kind"]
    state = record["state"]

    if (
        kind == "assumption"
        and state == "invalidated"
        and not _has_direct_evidence(record, "refutes")
    ):
        return "invalidated assumption lacks direct refuting evidence"
    if (
        kind == "task"
        and state == "done"
        and not _has_direct_evidence(record, "supports")
    ):
        return "done task lacks direct supporting completion evidence"
    if (
        kind == "question"
        and state == "answered"
        and not _has_direct_evidence(record, "supports")
        and not _has_incoming_answer(record["id"], memory, operations)
    ):
        return (
            "answered question lacks direct supporting evidence or an "
            "incoming answers relation"
        )
    if (
        kind == "risk"
        and state == "closed"
        and not _has_direct_evidence(record, "supports")
    ):
        return "closed risk lacks direct supporting evidence"
    if (
        kind == "risk"
        and base_state == "closed"
        and state == "open"
        and not _has_direct_evidence(record)
    ):
        return "reopened risk lacks direct evidence"
    return None


def _check_transitions(
    change_set: dict[str, Any],
    memory: dict[str, Any] | None,
    record_validator: SchemaValidator,
) -> list[Finding]:
    findings: list[Finding] = []
    records = (
        {record["id"]: record for record in memory["records"]}
        if memory is not None
        else {}
    )
    transitions: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, operation in enumerate(change_set["operations"]):
        if operation["operation_type"] != "transition_record":
            continue
        transitions.setdefault(operation["record_id"], []).append(
            (index, operation)
        )

    for record_id, items in sorted(transitions.items()):
        if len(items) > 1:
            findings.append(
                _finding(
                    INVALID_TRANSITION,
                    f"$.operations[{items[1][0]}]",
                    "multiple transitions target the same base record",
                    record_id,
                    *(item["operation_id"] for _, item in items),
                )
            )

        record = records.get(record_id)
        if record is None:
            continue
        base_state = record["state"]
        kind = record["kind"]
        for index, operation in items:
            operation_path = f"$.operations[{index}]"
            reason = operation.get("transition_reason")
            if not isinstance(reason, str) or not reason.strip():
                findings.append(
                    _finding(
                        MISSING_TRANSITION_REASON,
                        f"{operation_path}.transition_reason",
                        "transition requires an explicit non-empty reason",
                        operation["operation_id"],
                        record_id,
                    )
                )

            target_state = operation["target_state"]
            allowed = _ALLOWED_TRANSITIONS.get(kind, {}).get(
                base_state,
                set(),
            )
            if target_state not in allowed:
                findings.append(
                    _finding(
                        INVALID_TRANSITION,
                        f"{operation_path}.target_state",
                        (
                            f"{kind} transition {base_state!r} -> "
                            f"{target_state!r} is not permitted"
                        ),
                        operation["operation_id"],
                        record_id,
                    )
                )

        draft = _record_draft(record)
        _apply_record_operations(
            draft,
            record_id,
            change_set["operations"],
        )
        try:
            record_validator(draft)
        except fastjsonschema.JsonSchemaException:
            first_index, first_operation = items[0]
            findings.append(
                _finding(
                    INVALID_TRANSITION,
                    f"$.operations[{first_index}].content",
                    "resulting record violates its target-state contract",
                    first_operation["operation_id"],
                    record_id,
                )
            )
            continue

        evidence_problem = _terminal_evidence_problem(
            draft,
            base_state,
            memory,
            change_set["operations"],
        )
        if evidence_problem is not None:
            first_index, first_operation = items[0]
            findings.append(
                _finding(
                    INVALID_TRANSITION,
                    f"$.operations[{first_index}].target_state",
                    evidence_problem,
                    first_operation["operation_id"],
                    record_id,
                )
            )
    return findings


def _check_supersession(
    change_set: dict[str, Any],
    memory: dict[str, Any] | None,
) -> list[Finding]:
    if memory is None:
        return []
    findings: list[Finding] = []
    records = {record["id"]: record for record in memory["records"]}
    historical = {
        relation["target_id"]
        for record in memory["records"]
        for relation in record["relations"]
        if relation["type"] == "supersedes"
    }
    for index, operation in enumerate(change_set["operations"]):
        if operation["operation_type"] != "supersede_record":
            continue
        predecessor = records.get(operation["predecessor_id"])
        if predecessor is None:
            continue
        successor = operation["successor"]
        if successor["key"] != predecessor["key"]:
            findings.append(
                _finding(
                    "SUPERSESSION_KEY_MISMATCH",
                    f"$.operations[{index}].successor.key",
                    "successor key differs from predecessor key",
                    operation["operation_id"],
                    predecessor["id"],
                    successor["id"],
                )
            )
        if predecessor["id"] in historical:
            findings.append(
                _finding(
                    "SUPERSESSION_BRANCH",
                    f"$.operations[{index}].predecessor_id",
                    "predecessor already has a canonical successor",
                    operation["operation_id"],
                    predecessor["id"],
                    successor["id"],
                )
            )
    return findings


def validate_change_set(
    change_set: Any,
    memory: dict[str, Any] | None,
    *,
    schema_validator: SchemaValidator | None = None,
    record_validator: SchemaValidator | None = None,
) -> ValidationResult:
    """Validate one ChangeSet against its expected immutable base snapshot."""

    schema_result = validate_change_set_schema(
        change_set,
        validator=schema_validator,
    )
    if not schema_result.ok:
        return schema_result

    if memory is not None:
        memory_result = validate_memory_integrity(memory)
        if not memory_result.ok:
            return memory_result

    active_record_validator = record_validator or _record_draft_validator()
    artifact_findings = _check_artifact_hash(change_set)
    base_findings = _check_base_preconditions(change_set, memory)
    initialization = change_set["target_memory_id"] is None
    memory_missing = memory is None
    if initialization != memory_missing:
        return ValidationResult.from_findings(
            [*artifact_findings, *base_findings]
        )

    checks = (
        artifact_findings,
        base_findings,
        _check_operation_ids(change_set),
        _check_new_entity_ids(change_set, memory),
        _check_record_preconditions(change_set, memory),
        _check_references(change_set, memory),
        _check_transitions(
            change_set,
            memory,
            active_record_validator,
        ),
        _check_supersession(change_set, memory),
    )
    return ValidationResult.from_findings(
        finding
        for group in checks
        for finding in group
    )
