"""Deterministic multi-finding integrity validation for canonical memory."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from .canonical import is_canonical_memory
from .findings import Finding, ValidationResult
from .hashing import receipt_hash, record_hash, state_hash
from .schema import SchemaValidator, validate_memory_schema


_DIRECT_METHODS = {
    "user_statement",
    "direct_observation",
    "document_read",
    "code_inspection",
    "test_result",
    "tool_result",
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


def _duplicate_findings(
    items: list[dict[str, Any]],
    *,
    field: str,
    path: str,
) -> list[Finding]:
    findings: list[Finding] = []
    first_indexes: dict[str, int] = {}
    for index, item in enumerate(items):
        value = item[field]
        if value in first_indexes:
            findings.append(
                _finding(
                    "DUPLICATE_ID",
                    f"{path}[{index}].{field}",
                    f"ID {value!r} duplicates {path}[{first_indexes[value]}]",
                    value,
                )
            )
        else:
            first_indexes[value] = index
    return findings


def _check_duplicate_ids(memory: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(
        _duplicate_findings(
            memory["sources"],
            field="id",
            path="$.sources",
        )
    )
    findings.extend(
        _duplicate_findings(
            memory["records"],
            field="id",
            path="$.records",
        )
    )
    findings.extend(
        _duplicate_findings(
            memory["compilations"],
            field="id",
            path="$.compilations",
        )
    )
    findings.extend(
        _duplicate_findings(
            memory["compilations"],
            field="change_set_id",
            path="$.compilations",
        )
    )

    operations: list[dict[str, Any]] = []
    operation_paths: list[str] = []
    for receipt_index, receipt in enumerate(memory["compilations"]):
        for operation_index, operation in enumerate(receipt["operations"]):
            operations.append(operation)
            operation_paths.append(
                f"$.compilations[{receipt_index}].operations[{operation_index}]"
            )

    first_indexes: dict[str, int] = {}
    for index, operation in enumerate(operations):
        operation_id = operation["operation_id"]
        if operation_id in first_indexes:
            first_path = operation_paths[first_indexes[operation_id]]
            findings.append(
                _finding(
                    "DUPLICATE_ID",
                    f"{operation_paths[index]}.operation_id",
                    f"ID {operation_id!r} duplicates {first_path}",
                    operation_id,
                )
            )
        else:
            first_indexes[operation_id] = index
    return findings


def _check_references(memory: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    source_ids = {source["id"] for source in memory["sources"]}
    record_ids = {record["id"] for record in memory["records"]}
    compilation_ids = {
        receipt["id"] for receipt in memory["compilations"]
    }

    for source_index, source in enumerate(memory["sources"]):
        compilation_id = source["created_by"]
        if compilation_id not in compilation_ids:
            findings.append(
                _finding(
                    "UNKNOWN_COMPILATION_REFERENCE",
                    f"$.sources[{source_index}].created_by",
                    f"compilation {compilation_id!r} does not exist",
                    source["id"],
                    compilation_id,
                )
            )

    for record_index, record in enumerate(memory["records"]):
        record_id = record["id"]
        for field in ("created_by", "updated_by"):
            compilation_id = record[field]
            if compilation_id not in compilation_ids:
                findings.append(
                    _finding(
                        "UNKNOWN_COMPILATION_REFERENCE",
                        f"$.records[{record_index}].{field}",
                        f"compilation {compilation_id!r} does not exist",
                        record_id,
                        compilation_id,
                    )
                )

        for evidence_index, evidence in enumerate(record["evidence"]):
            source_id = evidence["source_id"]
            if source_id not in source_ids:
                findings.append(
                    _finding(
                        "UNKNOWN_SOURCE_REFERENCE",
                        (
                            f"$.records[{record_index}]"
                            f".evidence[{evidence_index}].source_id"
                        ),
                        f"source {source_id!r} does not exist",
                        record_id,
                        source_id,
                    )
                )

        for relation_index, relation in enumerate(record["relations"]):
            target_id = relation["target_id"]
            if target_id not in record_ids:
                findings.append(
                    _finding(
                        "UNKNOWN_RECORD_REFERENCE",
                        (
                            f"$.records[{record_index}]"
                            f".relations[{relation_index}].target_id"
                        ),
                        f"record {target_id!r} does not exist",
                        record_id,
                        target_id,
                    )
                )

    for receipt_index, receipt in enumerate(memory["compilations"]):
        for source_index, source_id in enumerate(receipt["input_source_ids"]):
            if source_id not in source_ids:
                findings.append(
                    _finding(
                        "UNKNOWN_SOURCE_REFERENCE",
                        (
                            f"$.compilations[{receipt_index}]"
                            f".input_source_ids[{source_index}]"
                        ),
                        f"source {source_id!r} does not exist",
                        receipt["id"],
                        source_id,
                    )
                )
    return findings


def _check_hashes(memory: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for index, record in enumerate(memory["records"]):
        expected = record_hash(record)
        if record["content_hash"] != expected:
            findings.append(
                _finding(
                    "RECORD_HASH_MISMATCH",
                    f"$.records[{index}].content_hash",
                    "stored hash differs from canonical record content",
                    record["id"],
                )
            )

    if memory["state_hash"] != state_hash(memory):
        findings.append(
            _finding(
                "STATE_HASH_MISMATCH",
                "$.state_hash",
                "stored hash differs from canonical memory state",
                memory["memory_id"],
            )
        )

    for index, receipt in enumerate(memory["compilations"]):
        if receipt["receipt_hash"] != receipt_hash(receipt):
            findings.append(
                _finding(
                    "RECEIPT_HASH_MISMATCH",
                    f"$.compilations[{index}].receipt_hash",
                    "stored hash differs from canonical receipt content",
                    receipt["id"],
                )
            )
    return findings


def _check_receipt_chain(memory: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    receipts = memory["compilations"]

    for index, receipt in enumerate(receipts):
        expected_base = index
        expected_result = index + 1
        if (
            receipt["base_revision"] != expected_base
            or receipt["result_revision"] != expected_result
        ):
            findings.append(
                _finding(
                    "RECEIPT_REVISION_SEQUENCE",
                    f"$.compilations[{index}]",
                    (
                        f"expected revision {expected_base} -> "
                        f"{expected_result}, found "
                        f"{receipt['base_revision']} -> "
                        f"{receipt['result_revision']}"
                    ),
                    receipt["id"],
                )
            )

        previous = receipts[index - 1] if index else None
        expected_receipt_hash = (
            previous["receipt_hash"] if previous is not None else None
        )
        if receipt["previous_receipt_hash"] != expected_receipt_hash:
            findings.append(
                _finding(
                    "RECEIPT_CHAIN_MISMATCH",
                    f"$.compilations[{index}].previous_receipt_hash",
                    "previous receipt hash does not match the preceding receipt",
                    receipt["id"],
                )
            )

        expected_state_hash = (
            previous["result_state_hash"] if previous is not None else None
        )
        if receipt["base_state_hash"] != expected_state_hash:
            findings.append(
                _finding(
                    "RECEIPT_CHAIN_MISMATCH",
                    f"$.compilations[{index}].base_state_hash",
                    "base state hash does not match the preceding result",
                    receipt["id"],
                )
            )

    if memory["revision"] != len(receipts):
        findings.append(
            _finding(
                "RECEIPT_REVISION_SEQUENCE",
                "$.revision",
                (
                    f"memory revision {memory['revision']} does not match "
                    f"{len(receipts)} compilation receipts"
                ),
                memory["memory_id"],
            )
        )

    if receipts and receipts[-1]["result_state_hash"] != memory["state_hash"]:
        findings.append(
            _finding(
                "RECEIPT_CHAIN_MISMATCH",
                f"$.compilations[{len(receipts) - 1}].result_state_hash",
                "latest receipt result does not match the memory state hash",
                receipts[-1]["id"],
                memory["memory_id"],
            )
        )
    return findings


def _check_canonical_order(memory: dict[str, Any]) -> list[Finding]:
    if is_canonical_memory(memory):
        return []
    return [
        _finding(
            "NONCANONICAL_ORDER",
            "$",
            "one or more canonical collections are not ordered",
            memory["memory_id"],
        )
    ]


def _parse_timestamp(
    value: str,
    path: str,
    entity_id: str,
    findings: list[Finding],
) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        findings.append(
            _finding(
                "TIMESTAMP_INVALID",
                path,
                f"timestamp {value!r} is not a real calendar instant",
                entity_id,
            )
        )
        return None


def _ordered_timestamps(
    start: datetime | None,
    end: datetime | None,
    *,
    path: str,
    message: str,
    entity_id: str,
) -> list[Finding]:
    if start is not None and end is not None and end < start:
        return [
            _finding(
                "TIMESTAMP_ORDER_INVALID",
                path,
                message,
                entity_id,
            )
        ]
    return []


def _check_timestamps(memory: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    memory_id = memory["memory_id"]
    project = memory["project"]
    project_created = _parse_timestamp(
        project["created_at"],
        "$.project.created_at",
        memory_id,
        findings,
    )
    project_updated = _parse_timestamp(
        project["updated_at"],
        "$.project.updated_at",
        memory_id,
        findings,
    )
    findings.extend(
        _ordered_timestamps(
            project_created,
            project_updated,
            path="$.project.updated_at",
            message="project update precedes project creation",
            entity_id=memory_id,
        )
    )

    for index, source in enumerate(memory["sources"]):
        _parse_timestamp(
            source["captured_at"],
            f"$.sources[{index}].captured_at",
            source["id"],
            findings,
        )

    for record_index, record in enumerate(memory["records"]):
        record_id = record["id"]
        created = _parse_timestamp(
            record["created_at"],
            f"$.records[{record_index}].created_at",
            record_id,
            findings,
        )
        updated = _parse_timestamp(
            record["updated_at"],
            f"$.records[{record_index}].updated_at",
            record_id,
            findings,
        )
        findings.extend(
            _ordered_timestamps(
                created,
                updated,
                path=f"$.records[{record_index}].updated_at",
                message="record update precedes record creation",
                entity_id=record_id,
            )
        )
        if record["kind"] == "event":
            _parse_timestamp(
                record["content"]["occurred_at"],
                f"$.records[{record_index}].content.occurred_at",
                record_id,
                findings,
            )
        for evidence_index, evidence in enumerate(record["evidence"]):
            _parse_timestamp(
                evidence["observed_at"],
                (
                    f"$.records[{record_index}]"
                    f".evidence[{evidence_index}].observed_at"
                ),
                record_id,
                findings,
            )

    previous: datetime | None = None
    for index, receipt in enumerate(memory["compilations"]):
        current = _parse_timestamp(
            receipt["compiled_at"],
            f"$.compilations[{index}].compiled_at",
            receipt["id"],
            findings,
        )
        findings.extend(
            _ordered_timestamps(
                previous,
                current,
                path=f"$.compilations[{index}].compiled_at",
                message="compilation timestamp precedes the previous receipt",
                entity_id=receipt["id"],
            )
        )
        if current is not None:
            previous = current
    return findings


def _check_evidence_and_relations(
    memory: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    incoming_blocks: set[str] = set()

    for record in memory["records"]:
        for relation in record["relations"]:
            if relation["type"] == "blocks":
                incoming_blocks.add(relation["target_id"])

    for record_index, record in enumerate(memory["records"]):
        record_id = record["id"]
        direct_support = [
            item
            for item in record["evidence"]
            if item["relation"] == "supports"
            and item["method"] in _DIRECT_METHODS
        ]
        direct_refutation = [
            item
            for item in record["evidence"]
            if item["relation"] == "refutes"
            and item["method"] in _DIRECT_METHODS
        ]
        verification = record["verification"]["status"]

        verification_invalid = (
            (verification == "verified" and not direct_support)
            or (verification == "verified" and bool(direct_refutation))
            or (
                verification == "partially_verified"
                and not record["evidence"]
            )
            or (
                verification == "contradicted"
                and not direct_refutation
            )
        )
        if verification_invalid:
            findings.append(
                _finding(
                    "VERIFICATION_EVIDENCE_INVALID",
                    f"$.records[{record_index}].verification.status",
                    (
                        f"verification status {verification!r} is not "
                        "supported by the record evidence"
                    ),
                    record_id,
                )
            )

        if (
            record["kind"] == "task"
            and record["state"] == "done"
            and not direct_support
        ):
            findings.append(
                _finding(
                    "TASK_COMPLETION_EVIDENCE_MISSING",
                    f"$.records[{record_index}].evidence",
                    "done task lacks direct supporting completion evidence",
                    record_id,
                )
            )

        if (
            record["kind"] == "task"
            and record["state"] == "blocked"
            and record_id not in incoming_blocks
        ):
            findings.append(
                _finding(
                    "BLOCKED_TASK_WITHOUT_BLOCKER",
                    f"$.records[{record_index}].state",
                    "blocked task has no incoming blocks relation",
                    record_id,
                )
            )

        seen_relations: dict[tuple[str, str], int] = {}
        for relation_index, relation in enumerate(record["relations"]):
            relation_path = (
                f"$.records[{record_index}].relations[{relation_index}]"
            )
            target_id = relation["target_id"]
            if target_id == record_id:
                findings.append(
                    _finding(
                        "RELATION_SELF_TARGET",
                        f"{relation_path}.target_id",
                        "relation targets its containing record",
                        record_id,
                    )
                )

            key = (relation["type"], target_id)
            if key in seen_relations:
                findings.append(
                    _finding(
                        "RELATION_DUPLICATE",
                        relation_path,
                        (
                            f"relation tuple {key!r} duplicates "
                            f"relations[{seen_relations[key]}]"
                        ),
                        record_id,
                        target_id,
                    )
                )
            else:
                seen_relations[key] = relation_index

        for evidence_index, evidence in enumerate(record["evidence"]):
            locator = evidence["locator"]
            if locator["kind"] == "lines":
                start = locator["start_line"]
                end = locator["end_line"]
            elif locator["kind"] == "page":
                start = locator["start_page"]
                end = locator["end_page"]
            else:
                continue
            if end < start:
                findings.append(
                    _finding(
                        "LOCATOR_RANGE_INVALID",
                        (
                            f"$.records[{record_index}]"
                            f".evidence[{evidence_index}].locator"
                        ),
                        f"range end {end} precedes start {start}",
                        record_id,
                    )
                )
    return findings


def _cycle_components(
    graph: dict[str, list[str]],
) -> list[tuple[str, ...]]:
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in sorted(graph.get(node, [])):
            if target not in indexes:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[target])

        if lowlinks[node] != indexes[node]:
            return
        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            components.append(tuple(sorted(component)))

    for node in sorted(graph):
        if node not in indexes:
            visit(node)
    return sorted(components)


def _check_supersession(memory: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    records = memory["records"]
    by_id = {record["id"]: record for record in records}
    path_by_id = {
        record["id"]: f"$.records[{index}]"
        for index, record in enumerate(records)
    }
    by_key: dict[str, list[str]] = defaultdict(list)
    graph: dict[str, list[str]] = defaultdict(list)
    incoming: Counter[str] = Counter()

    for record in records:
        by_key[record["key"]].append(record["id"])

    for record_index, record in enumerate(records):
        for relation_index, relation in enumerate(record["relations"]):
            if relation["type"] != "supersedes":
                continue
            target_id = relation["target_id"]
            if target_id not in by_id:
                continue
            path = (
                f"$.records[{record_index}]"
                f".relations[{relation_index}].target_id"
            )
            if by_id[target_id]["key"] != record["key"]:
                findings.append(
                    _finding(
                        "SUPERSESSION_KEY_MISMATCH",
                        path,
                        "supersession must connect records with the same key",
                        record["id"],
                        target_id,
                    )
                )
                continue
            graph[record["id"]].append(target_id)
            incoming[target_id] += 1

    for source_id, targets in sorted(graph.items()):
        if len(targets) > 1:
            findings.append(
                _finding(
                    "SUPERSESSION_BRANCH",
                    f"{path_by_id[source_id]}.relations",
                    "record supersedes more than one predecessor",
                    source_id,
                    *targets,
                )
            )
    for target_id, count in sorted(incoming.items()):
        if count > 1:
            successors = sorted(
                source_id
                for source_id, targets in graph.items()
                if target_id in targets
            )
            findings.append(
                _finding(
                    "SUPERSESSION_BRANCH",
                    path_by_id[target_id],
                    "record has more than one direct successor",
                    target_id,
                    *successors,
                )
            )

    for component in _cycle_components(graph):
        findings.append(
            _finding(
                "SUPERSESSION_CYCLE",
                path_by_id[component[0]],
                "supersession relations contain a cycle",
                *component,
            )
        )

    for key, record_ids in sorted(by_key.items()):
        if len(record_ids) < 2:
            continue
        historical = {
            target_id
            for source_id in record_ids
            for target_id in graph.get(source_id, [])
        }
        heads = sorted(set(record_ids) - historical)
        if len(heads) != 1:
            findings.append(
                _finding(
                    "MULTIPLE_KEY_HEADS",
                    "$.records",
                    (
                        f"key {key!r} requires exactly one chain head; "
                        f"found {len(heads)}"
                    ),
                    *record_ids,
                )
            )
    return findings


def _collect_integrity_findings(
    memory: dict[str, Any],
) -> Iterable[Finding]:
    checks = (
        _check_duplicate_ids,
        _check_references,
        _check_hashes,
        _check_receipt_chain,
        _check_canonical_order,
        _check_timestamps,
        _check_evidence_and_relations,
        _check_supersession,
    )
    for check in checks:
        yield from check(memory)


def validate_memory_integrity(
    memory: Any,
    *,
    schema_validator: SchemaValidator | None = None,
) -> ValidationResult:
    """Validate one memory and return every independently detectable finding."""

    schema_result = validate_memory_schema(
        memory,
        validator=schema_validator,
    )
    if not schema_result.ok:
        return schema_result
    return ValidationResult.from_findings(
        _collect_integrity_findings(memory)
    )
