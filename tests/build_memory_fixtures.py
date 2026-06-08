from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kiroku_core.canonical import canonicalize_memory
from scripts.kiroku_core.hashing import receipt_hash, record_hash, state_hash


FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"
NOW = "2026-06-08T10:00:00Z"
LATER = "2026-06-08T11:00:00Z"
SOURCE_HASH = "sha256:" + "c3" * 32
CHANGESET_HASH = "sha256:" + "d4" * 32


def evidence(
    *,
    relation: str = "supports",
    method: str = "document_read",
    locator: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source_id": "src_contract",
        "relation": relation,
        "method": method,
        "locator": locator or {"kind": "section", "name": "Canonical memory"},
        "observed_at": NOW,
    }


def make_record(
    record_id: str,
    key: str,
    kind: str,
    state: str,
    content: dict[str, Any],
    *,
    verification: str = "unverified",
    evidence_items: list[dict[str, Any]] | None = None,
    relations: list[dict[str, Any]] | None = None,
    created_by: str = "cmp_initial",
    updated_by: str = "cmp_initial",
    created_at: str = NOW,
    updated_at: str = NOW,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "key": key,
        "kind": kind,
        "state": state,
        "title": f"{kind.title()} fixture",
        "summary": f"Canonical {kind} used by the fixture corpus.",
        "scope": ["project"],
        "tags": ["fixture"],
        "verification": {"status": verification},
        "evidence": evidence_items or [],
        "relations": relations or [],
        "content": content,
        "created_at": created_at,
        "updated_at": updated_at,
        "created_by": created_by,
        "updated_by": updated_by,
        "content_hash": "",
    }


def source() -> dict[str, Any]:
    return {
        "id": "src_contract",
        "kind": "document",
        "title": "KirokuForge contracts",
        "uri": "file:references/contracts-v3.md",
        "revision": "v3",
        "integrity": "verified",
        "content_hash": SOURCE_HASH,
        "captured_at": NOW,
        "media_type": "text/markdown",
        "metadata": {"purpose": "normative contract"},
        "created_by": "cmp_initial",
    }


def operation(
    operation_id: str,
    operation_type: str,
    affected_ids: list[str],
    *,
    hash_changes: list[dict[str, Any]] | None = None,
    transition_reason: str | None = None,
) -> dict[str, Any]:
    result = {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "affected_ids": affected_ids,
        "hash_changes": hash_changes or [],
    }
    if transition_reason:
        result["transition_reason"] = transition_reason
    return result


def receipt(
    compilation_id: str,
    base_revision: int,
    result_revision: int,
    operations: list[dict[str, Any]],
    *,
    base_state_hash: str | None,
    compiled_at: str,
) -> dict[str, Any]:
    return {
        "id": compilation_id,
        "base_revision": base_revision,
        "result_revision": result_revision,
        "base_state_hash": base_state_hash,
        "result_state_hash": "sha256:" + "0" * 64,
        "change_set_id": f"chg_{compilation_id.removeprefix('cmp_')}",
        "change_set_hash": CHANGESET_HASH,
        "actor": {
            "type": "agent",
            "name": "codex",
            "version": "1.0",
            "session_ref": "session-fixtures",
        },
        "compiler": {
            "name": "kiroku-compiler",
            "version": "3.0.0-dev",
        },
        "input_source_ids": ["src_contract"],
        "operations": operations,
        "compiled_at": compiled_at,
        "warnings": [],
        "previous_receipt_hash": None,
        "receipt_hash": "sha256:" + "0" * 64,
    }


def memory(records: list[dict[str, Any]]) -> dict[str, Any]:
    operations = [
        operation(
            "op_initialize",
            "initialize_memory",
            ["mem_fixture"],
            hash_changes=[
                {
                    "id": "mem_fixture",
                    "previous_hash": None,
                    "result_hash": "sha256:" + "0" * 64,
                }
            ],
        ),
        operation("op_source", "add_source", ["src_contract"]),
    ]
    if records:
        operations.append(
            operation(
                "op_records",
                "create_record",
                [item["id"] for item in records],
                hash_changes=[
                    {
                        "id": item["id"],
                        "previous_hash": None,
                        "result_hash": "sha256:" + "0" * 64,
                    }
                    for item in records
                ],
            )
        )
    return {
        "artifact_type": "memory",
        "schema_version": "3.0.0",
        "memory_id": "mem_fixture",
        "revision": 1,
        "state_hash": "sha256:" + "0" * 64,
        "project": {
            "name": "KirokuForge fixture project",
            "description": "Project used by the canonical memory fixture corpus.",
            "goal": "Define deterministic memory validation behavior.",
            "status": "active",
            "boundaries": {
                "included": ["Canonical project memory"],
                "excluded": ["Encyclopedic project documentation"],
            },
            "created_at": NOW,
            "updated_at": NOW,
        },
        "sources": [source()],
        "records": records,
        "compilations": [
            receipt(
                "cmp_initial",
                0,
                1,
                operations,
                base_state_hash=None,
                compiled_at=NOW,
            )
        ],
    }


def refresh_receipt_hashes(candidate: dict[str, Any]) -> None:
    previous_hash = None
    for item in candidate["compilations"]:
        item["previous_receipt_hash"] = previous_hash
        item["receipt_hash"] = receipt_hash(item)
        previous_hash = item["receipt_hash"]


def update_operation_hashes(candidate: dict[str, Any]) -> None:
    records = {item["id"]: item for item in candidate["records"]}
    final_receipt = candidate["compilations"][-1]
    for item in final_receipt["operations"]:
        for change in item["hash_changes"]:
            if change["id"] == candidate["memory_id"]:
                change["result_hash"] = candidate["state_hash"]
            elif change["id"] in records:
                change["result_hash"] = records[change["id"]]["content_hash"]


def finalize(
    candidate: dict[str, Any],
    *,
    sort_canonical: bool = True,
    refresh_records: bool = True,
) -> dict[str, Any]:
    if sort_canonical:
        candidate = canonicalize_memory(candidate)
    if refresh_records:
        for item in candidate["records"]:
            item["content_hash"] = record_hash(item)
    candidate["state_hash"] = state_hash(candidate)
    candidate["compilations"][-1]["result_state_hash"] = candidate["state_hash"]
    update_operation_hashes(candidate)
    refresh_receipt_hashes(candidate)
    return candidate


def minimal_memory() -> dict[str, Any]:
    fact = make_record(
        "rec_fact",
        "canonical-memory",
        "fact",
        "active",
        {"statement": "memory.json is the canonical project-memory artifact."},
        verification="verified",
        evidence_items=[evidence()],
    )
    return finalize(memory([fact]))


def all_record_kinds() -> dict[str, Any]:
    records = [
        make_record(
            "rec_assumption",
            "source-availability",
            "assumption",
            "active",
            {
                "assumption": "Referenced raw sources remain available.",
                "basis": "They are managed by the project.",
                "impact_if_false": "Evidence cannot be reopened.",
                "validation_plan": "Check source URIs before compilation.",
            },
        ),
        make_record(
            "rec_constraint",
            "no-git-dependency",
            "constraint",
            "active",
            {"constraint": "KirokuForge must not depend on Git."},
        ),
        make_record(
            "rec_decision",
            "canonical-json",
            "decision",
            "active",
            {
                "decision": "Use one structured memory.json as canonical state.",
                "rationale": "Agents and the viewer need the same source of truth.",
            },
        ),
        make_record(
            "rec_event",
            "contracts-approved",
            "event",
            "occurred",
            {
                "description": "The v3 contracts were approved.",
                "occurred_at": NOW,
                "significance": "Implementation can follow stable semantics.",
            },
        ),
        make_record(
            "rec_fact",
            "memory-compiler",
            "fact",
            "active",
            {"statement": "KirokuForge is a project-memory compiler."},
            verification="verified",
            evidence_items=[evidence()],
        ),
        make_record(
            "rec_preference",
            "compact-handoff",
            "preference",
            "active",
            {"preference": "Keep agent handoffs focused and compact."},
        ),
        make_record(
            "rec_proposal",
            "local-viewer",
            "proposal",
            "proposed",
            {
                "proposal": "Provide a local read-only memory viewer.",
                "motivation": "Users need direct structured-memory inspection.",
            },
        ),
        make_record(
            "rec_question",
            "audit-policy",
            "question",
            "open",
            {
                "question": "Which audit findings should be blocking?",
                "why_it_matters": "Compilation policy must be predictable.",
            },
        ),
        make_record(
            "rec_risk",
            "context-overflow",
            "risk",
            "open",
            {
                "description": "A handoff may exceed the agent context budget.",
                "impact": "high",
                "likelihood": "medium",
            },
        ),
        make_record(
            "rec_task",
            "implement-integrity",
            "task",
            "todo",
            {
                "objective": "Implement deterministic integrity validation.",
                "priority": "high",
                "acceptance_criteria": ["All integrity fixtures produce expected codes."],
            },
        ),
    ]
    return finalize(memory(records))


def lifecycle_states() -> dict[str, Any]:
    records = [
        make_record(
            "rec_blocker",
            "schema-stability",
            "constraint",
            "active",
            {"constraint": "Schema contracts must stabilize before implementation."},
            relations=[{"type": "blocks", "target_id": "rec_task_blocked"}],
        ),
        make_record(
            "rec_assumption_invalid",
            "markdown-required",
            "assumption",
            "invalidated",
            {
                "assumption": "Generated Markdown is required.",
                "basis": "The previous viewer consumed Markdown.",
                "impact_if_false": "The viewer can read JSON directly.",
                "validation_plan": "Verify the viewer data source.",
            },
            verification="contradicted",
            evidence_items=[evidence(relation="refutes")],
        ),
        make_record(
            "rec_proposal_cancelled",
            "interim-viewer",
            "proposal",
            "cancelled",
            {
                "proposal": "Build an interim v2-compatible viewer.",
                "motivation": "Inspect early development state.",
                "cancellation_reason": "The v2 implementation was removed.",
            },
        ),
        make_record(
            "rec_proposal_rejected",
            "canonical-markdown",
            "proposal",
            "rejected",
            {
                "proposal": "Use Markdown as canonical memory.",
                "motivation": "Improve direct readability.",
                "rejection_reason": "Structured JSON must remain authoritative.",
            },
        ),
        make_record(
            "rec_question_answered",
            "markdown-canonical",
            "question",
            "answered",
            {
                "question": "Is Markdown canonical?",
                "why_it_matters": "Writers require one source of truth.",
                "answer": "No. memory.json is canonical.",
            },
            evidence_items=[evidence()],
        ),
        make_record(
            "rec_risk_accepted",
            "audit-false-positive",
            "risk",
            "accepted",
            {
                "description": "Heuristic audit may report false positives.",
                "impact": "low",
                "likelihood": "medium",
                "acceptance_rationale": "Heuristic findings remain non-blocking.",
            },
        ),
        make_record(
            "rec_risk_closed",
            "missing-done-evidence",
            "risk",
            "closed",
            {
                "description": "Done tasks may be recorded without evidence.",
                "impact": "high",
                "likelihood": "medium",
                "resolution": "The schema requires direct evidence.",
            },
            evidence_items=[evidence()],
        ),
        make_record(
            "rec_task_blocked",
            "implement-compiler",
            "task",
            "blocked",
            {
                "objective": "Implement the compiler.",
                "priority": "high",
                "acceptance_criteria": ["ChangeSets compile atomically."],
            },
        ),
        make_record(
            "rec_task_cancelled",
            "maintain-v2",
            "task",
            "cancelled",
            {
                "objective": "Maintain the v2 implementation.",
                "priority": "low",
                "acceptance_criteria": ["The v2 CLI remains operational."],
                "cancellation_reason": "The product is being rebuilt as v3.",
            },
        ),
        make_record(
            "rec_task_done",
            "define-memory-schema",
            "task",
            "done",
            {
                "objective": "Define canonical memory shape.",
                "priority": "high",
                "acceptance_criteria": ["The schema covers every record kind."],
                "outcome": "memory-v3.schema.json was validated.",
            },
            evidence_items=[evidence()],
        ),
    ]
    return finalize(memory(records))


def supersession_history() -> dict[str, Any]:
    predecessor = make_record(
        "rec_storage_v1",
        "canonical-storage",
        "fact",
        "obsolete",
        {"statement": "Generated Markdown is the canonical project memory."},
        verification="contradicted",
        evidence_items=[evidence(relation="refutes")],
    )
    revision_one = finalize(memory([predecessor]))

    successor = make_record(
        "rec_storage_v2",
        "canonical-storage",
        "fact",
        "active",
        {"statement": "memory.json is the canonical project memory."},
        verification="verified",
        evidence_items=[evidence()],
        relations=[{"type": "supersedes", "target_id": "rec_storage_v1"}],
        created_by="cmp_second",
        updated_by="cmp_second",
        created_at=LATER,
        updated_at=LATER,
    )
    candidate = copy.deepcopy(revision_one)
    candidate["revision"] = 2
    candidate["records"].append(successor)
    candidate["compilations"].append(
        receipt(
            "cmp_second",
            1,
            2,
            [
                operation(
                    "op_supersede",
                    "supersede_record",
                    ["rec_storage_v1", "rec_storage_v2"],
                    hash_changes=[
                        {
                            "id": "rec_storage_v2",
                            "previous_hash": None,
                            "result_hash": "sha256:" + "0" * 64,
                        }
                    ],
                    transition_reason="Correct the canonical storage claim.",
                )
            ],
            base_state_hash=revision_one["state_hash"],
            compiled_at=LATER,
        )
    )
    return finalize(candidate)


def refresh_after_mutation(
    candidate: dict[str, Any],
    *,
    sort_canonical: bool = True,
    refresh_records: bool = True,
) -> dict[str, Any]:
    return finalize(
        candidate,
        sort_canonical=sort_canonical,
        refresh_records=refresh_records,
    )


def build_schema_invalid(base: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}

    wrong_state = copy.deepcopy(base)
    wrong_state["records"][0]["state"] = "todo"
    cases["wrong-kind-state.json"] = wrong_state

    missing_rationale = copy.deepcopy(base)
    target = missing_rationale["records"][0]
    target["kind"] = "decision"
    target["state"] = "active"
    target["content"] = {"decision": "Use JSON."}
    cases["missing-decision-rationale.json"] = missing_rationale

    missing_outcome = copy.deepcopy(base)
    target = missing_outcome["records"][0]
    target["kind"] = "task"
    target["state"] = "done"
    target["content"] = {
        "objective": "Compile memory.",
        "priority": "high",
        "acceptance_criteria": ["Compilation succeeds."],
    }
    cases["done-task-missing-outcome.json"] = missing_outcome

    missing_hash = copy.deepcopy(base)
    del missing_hash["sources"][0]["content_hash"]
    cases["verified-source-missing-hash.json"] = missing_hash

    extra_root = copy.deepcopy(base)
    extra_root["unexpected"] = True
    cases["extra-root-property.json"] = extra_root

    return cases


def build_integrity_invalid(
    minimal: dict[str, Any],
    all_kinds: dict[str, Any],
    history: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}

    duplicate = copy.deepcopy(minimal)
    second = copy.deepcopy(duplicate["records"][0])
    second["key"] = "duplicate-id-other-key"
    second["content"]["statement"] = "A second record incorrectly reuses an ID."
    duplicate["records"].append(second)
    cases["duplicate-record-id.json"] = refresh_after_mutation(duplicate)

    unknown_source = copy.deepcopy(minimal)
    unknown_source["records"][0]["evidence"][0]["source_id"] = "src_missing"
    cases["unknown-evidence-source.json"] = refresh_after_mutation(unknown_source)

    unknown_compilation = copy.deepcopy(minimal)
    target = unknown_compilation["records"][0]
    target["created_by"] = "cmp_missing"
    target["updated_by"] = "cmp_missing"
    cases["unknown-compilation-reference.json"] = refresh_after_mutation(
        unknown_compilation
    )

    bad_record_hash = copy.deepcopy(minimal)
    bad_record_hash["records"][0]["content"]["statement"] = "Content changed."
    cases["record-hash-mismatch.json"] = refresh_after_mutation(
        bad_record_hash,
        refresh_records=False,
    )

    bad_state_hash = copy.deepcopy(minimal)
    bad_state_hash["state_hash"] = "sha256:" + "f0" * 32
    bad_state_hash["compilations"][-1]["result_state_hash"] = bad_state_hash[
        "state_hash"
    ]
    update_operation_hashes(bad_state_hash)
    refresh_receipt_hashes(bad_state_hash)
    cases["state-hash-mismatch.json"] = bad_state_hash

    multiple_heads = copy.deepcopy(minimal)
    second = copy.deepcopy(multiple_heads["records"][0])
    second["id"] = "rec_second_head"
    second["content"]["statement"] = "A competing current claim."
    multiple_heads["records"].append(second)
    cases["multiple-key-heads.json"] = refresh_after_mutation(multiple_heads)

    noncanonical = copy.deepcopy(all_kinds)
    noncanonical["records"].reverse()
    cases["noncanonical-record-order.json"] = refresh_after_mutation(
        noncanonical,
        sort_canonical=False,
    )

    bad_locator = copy.deepcopy(minimal)
    bad_locator["records"][0]["evidence"][0]["locator"] = {
        "kind": "lines",
        "start_line": 20,
        "end_line": 10,
    }
    cases["locator-range-invalid.json"] = refresh_after_mutation(bad_locator)

    bad_timestamp = copy.deepcopy(minimal)
    bad_timestamp["project"]["created_at"] = "2026-02-30T10:00:00Z"
    bad_timestamp["project"]["updated_at"] = "2026-02-30T10:00:00Z"
    cases["invalid-calendar-timestamp.json"] = refresh_after_mutation(bad_timestamp)

    blocked = copy.deepcopy(all_kinds)
    target = next(item for item in blocked["records"] if item["kind"] == "task")
    target["state"] = "blocked"
    cases["blocked-task-without-blocker.json"] = refresh_after_mutation(blocked)

    self_target = copy.deepcopy(minimal)
    self_target["records"][0]["relations"] = [
        {"type": "related_to", "target_id": "rec_fact"}
    ]
    cases["relation-self-target.json"] = refresh_after_mutation(self_target)

    unknown_target = copy.deepcopy(minimal)
    unknown_target["records"][0]["relations"] = [
        {"type": "related_to", "target_id": "rec_missing"}
    ]
    cases["unknown-record-reference.json"] = refresh_after_mutation(unknown_target)

    revision_gap = copy.deepcopy(history)
    revision_gap["revision"] = 3
    revision_gap["compilations"][-1]["result_revision"] = 3
    cases["receipt-revision-gap.json"] = refresh_after_mutation(revision_gap)

    bad_receipt_hash = copy.deepcopy(minimal)
    bad_receipt_hash["compilations"][0]["warnings"] = [
        "Receipt changed without refreshing its hash."
    ]
    cases["receipt-hash-mismatch.json"] = bad_receipt_hash

    bad_receipt_chain = copy.deepcopy(history)
    bad_receipt_chain["compilations"][1]["base_state_hash"] = (
        "sha256:" + "f0" * 32
    )
    refresh_receipt_hashes(bad_receipt_chain)
    cases["receipt-chain-mismatch.json"] = bad_receipt_chain

    duplicate_relation = copy.deepcopy(history)
    duplicate_relation["records"][1]["relations"].extend(
        [
            {"type": "related_to", "target_id": "rec_storage_v1"},
            {
                "type": "related_to",
                "target_id": "rec_storage_v1",
                "note": "Same tuple with a different note.",
            },
        ]
    )
    cases["relation-duplicate.json"] = refresh_after_mutation(
        duplicate_relation
    )

    timestamp_order = copy.deepcopy(minimal)
    timestamp_order["records"][0]["updated_at"] = "2026-06-08T09:00:00Z"
    cases["timestamp-order-invalid.json"] = refresh_after_mutation(
        timestamp_order
    )

    verification_conflict = copy.deepcopy(minimal)
    verification_conflict["records"][0]["evidence"].append(
        evidence(relation="refutes")
    )
    cases["verification-evidence-invalid.json"] = refresh_after_mutation(
        verification_conflict
    )

    supersession_key = copy.deepcopy(history)
    supersession_key["records"][1]["key"] = "different-key"
    cases["supersession-key-mismatch.json"] = refresh_after_mutation(
        supersession_key
    )

    supersession_cycle = copy.deepcopy(history)
    supersession_cycle["records"][0]["relations"] = [
        {"type": "supersedes", "target_id": "rec_storage_v2"}
    ]
    cases["supersession-cycle.json"] = refresh_after_mutation(
        supersession_cycle
    )

    supersession_branch = copy.deepcopy(history)
    competing_successor = copy.deepcopy(supersession_branch["records"][1])
    competing_successor["id"] = "rec_storage_v3"
    competing_successor["content"]["statement"] = (
        "A competing record supersedes the same predecessor."
    )
    supersession_branch["records"].append(competing_successor)
    cases["supersession-branch.json"] = refresh_after_mutation(
        supersession_branch
    )

    return cases


def manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "memory_schema": "schemas/memory-v3.schema.json",
        "generated_by": "tests/build_memory_fixtures.py",
        "valid": [
            {
                "path": "valid/minimal.json",
                "description": "Revision-one memory with one verified fact.",
            },
            {
                "path": "valid/all-record-kinds.json",
                "description": "One current record for every canonical kind.",
            },
            {
                "path": "valid/lifecycle-states.json",
                "description": "State-specific content and terminal evidence.",
            },
            {
                "path": "valid/supersession-history.json",
                "description": "Two revisions with one linear supersession chain.",
            },
        ],
        "invalid": [
            {
                "path": "invalid/schema/wrong-kind-state.json",
                "layer": "schema",
                "code": "SCHEMA_VIOLATION",
                "invariant": "Record state must belong to its kind.",
            },
            {
                "path": "invalid/schema/missing-decision-rationale.json",
                "layer": "schema",
                "code": "SCHEMA_VIOLATION",
                "invariant": "Decision content requires rationale.",
            },
            {
                "path": "invalid/schema/done-task-missing-outcome.json",
                "layer": "schema",
                "code": "SCHEMA_VIOLATION",
                "invariant": "Done task content requires outcome.",
            },
            {
                "path": "invalid/schema/verified-source-missing-hash.json",
                "layer": "schema",
                "code": "SCHEMA_VIOLATION",
                "invariant": "Verified source requires content_hash.",
            },
            {
                "path": "invalid/schema/extra-root-property.json",
                "layer": "schema",
                "code": "SCHEMA_VIOLATION",
                "invariant": "Canonical memory root is closed.",
            },
            {
                "path": "invalid/integrity/duplicate-record-id.json",
                "layer": "integrity",
                "code": "DUPLICATE_ID",
                "invariant": "Canonical record IDs are unique.",
            },
            {
                "path": "invalid/integrity/unknown-evidence-source.json",
                "layer": "integrity",
                "code": "UNKNOWN_SOURCE_REFERENCE",
                "invariant": "Evidence source IDs must exist.",
            },
            {
                "path": "invalid/integrity/unknown-record-reference.json",
                "layer": "integrity",
                "code": "UNKNOWN_RECORD_REFERENCE",
                "invariant": "Relation targets must exist.",
            },
            {
                "path": "invalid/integrity/unknown-compilation-reference.json",
                "layer": "integrity",
                "code": "UNKNOWN_COMPILATION_REFERENCE",
                "invariant": "Record compilation IDs must exist.",
            },
            {
                "path": "invalid/integrity/record-hash-mismatch.json",
                "layer": "integrity",
                "code": "RECORD_HASH_MISMATCH",
                "invariant": "Stored record hash must match canonical content.",
            },
            {
                "path": "invalid/integrity/state-hash-mismatch.json",
                "layer": "integrity",
                "code": "STATE_HASH_MISMATCH",
                "invariant": "Root state hash must match canonical memory state.",
            },
            {
                "path": "invalid/integrity/multiple-key-heads.json",
                "layer": "integrity",
                "code": "MULTIPLE_KEY_HEADS",
                "invariant": "A logical key has exactly one current head.",
            },
            {
                "path": "invalid/integrity/noncanonical-record-order.json",
                "layer": "integrity",
                "code": "NONCANONICAL_ORDER",
                "invariant": "Canonical records are sorted by ID.",
            },
            {
                "path": "invalid/integrity/locator-range-invalid.json",
                "layer": "integrity",
                "code": "LOCATOR_RANGE_INVALID",
                "invariant": "Locator ranges are ordered.",
            },
            {
                "path": "invalid/integrity/invalid-calendar-timestamp.json",
                "layer": "integrity",
                "code": "TIMESTAMP_INVALID",
                "invariant": "Timestamps represent real calendar instants.",
            },
            {
                "path": "invalid/integrity/blocked-task-without-blocker.json",
                "layer": "integrity",
                "code": "BLOCKED_TASK_WITHOUT_BLOCKER",
                "invariant": "Blocked tasks have an incoming blocks relation.",
            },
            {
                "path": "invalid/integrity/relation-self-target.json",
                "layer": "integrity",
                "code": "RELATION_SELF_TARGET",
                "invariant": "Relations cannot target their containing record.",
            },
            {
                "path": "invalid/integrity/receipt-revision-gap.json",
                "layer": "integrity",
                "code": "RECEIPT_REVISION_SEQUENCE",
                "invariant": "Compilation revisions are contiguous.",
            },
            {
                "path": "invalid/integrity/receipt-hash-mismatch.json",
                "layer": "integrity",
                "code": "RECEIPT_HASH_MISMATCH",
                "invariant": "Stored receipt hashes match canonical content.",
            },
            {
                "path": "invalid/integrity/receipt-chain-mismatch.json",
                "layer": "integrity",
                "code": "RECEIPT_CHAIN_MISMATCH",
                "invariant": "Receipt base state hashes form a linear chain.",
            },
            {
                "path": "invalid/integrity/relation-duplicate.json",
                "layer": "integrity",
                "code": "RELATION_DUPLICATE",
                "invariant": "Relation type and target tuples are unique.",
            },
            {
                "path": "invalid/integrity/timestamp-order-invalid.json",
                "layer": "integrity",
                "code": "TIMESTAMP_ORDER_INVALID",
                "invariant": "Record updates do not precede creation.",
            },
            {
                "path": "invalid/integrity/verification-evidence-invalid.json",
                "layer": "integrity",
                "code": "VERIFICATION_EVIDENCE_INVALID",
                "invariant": "Verified records have no direct refutation.",
            },
            {
                "path": "invalid/integrity/supersession-key-mismatch.json",
                "layer": "integrity",
                "code": "SUPERSESSION_KEY_MISMATCH",
                "invariant": "Supersession connects records with one key.",
            },
            {
                "path": "invalid/integrity/supersession-cycle.json",
                "layer": "integrity",
                "code": "SUPERSESSION_CYCLE",
                "invariant": "Supersession chains are acyclic.",
            },
            {
                "path": "invalid/integrity/supersession-branch.json",
                "layer": "integrity",
                "code": "SUPERSESSION_BRANCH",
                "invariant": "Supersession chains remain linear.",
            },
        ],
    }


def expected_files() -> dict[Path, Any]:
    minimal = minimal_memory()
    all_kinds = all_record_kinds()
    lifecycle = lifecycle_states()
    history = supersession_history()
    files: dict[Path, Any] = {
        FIXTURE_ROOT / "manifest.json": manifest(),
        FIXTURE_ROOT / "valid" / "minimal.json": minimal,
        FIXTURE_ROOT / "valid" / "all-record-kinds.json": all_kinds,
        FIXTURE_ROOT / "valid" / "lifecycle-states.json": lifecycle,
        FIXTURE_ROOT / "valid" / "supersession-history.json": history,
    }
    for name, value in build_schema_invalid(minimal).items():
        files[FIXTURE_ROOT / "invalid" / "schema" / name] = value
    for name, value in build_integrity_invalid(minimal, all_kinds, history).items():
        files[FIXTURE_ROOT / "invalid" / "integrity" / name] = value
    return files


def rendered(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_fixtures() -> int:
    for path, value in expected_files().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered(value), encoding="utf-8")
    return 0


def check_fixtures() -> int:
    expected = expected_files()
    actual_paths = set(FIXTURE_ROOT.rglob("*.json"))
    expected_paths = set(expected)
    errors: list[str] = []
    for path in sorted(expected_paths | actual_paths):
        if path not in expected:
            errors.append(f"unexpected fixture: {path.relative_to(ROOT)}")
            continue
        if not path.exists():
            errors.append(f"missing fixture: {path.relative_to(ROOT)}")
            continue
        if path.read_text(encoding="utf-8") != rendered(expected[path]):
            errors.append(f"stale fixture: {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Fixture corpus is current ({len(expected)} files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical memory fixtures")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    return check_fixtures() if args.check else write_fixtures()


if __name__ == "__main__":
    raise SystemExit(main())
