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

from scripts.kiroku_core.hashing import sha256_hash


FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "pipeline"
NOW = "2026-06-08T12:00:00Z"
HASH = "sha256:" + "a1" * 32
MEMORY = json.loads(
    (
        ROOT / "tests" / "fixtures" / "memory" / "valid" / "minimal.json"
    ).read_text(encoding="utf-8")
)
LIFECYCLE_MEMORY = json.loads(
    (
        ROOT
        / "tests"
        / "fixtures"
        / "memory"
        / "valid"
        / "lifecycle-states.json"
    ).read_text(encoding="utf-8")
)


def actor() -> dict[str, Any]:
    return {
        "type": "agent",
        "name": "codex",
        "version": "1.0",
        "session_ref": "session-pipeline-fixtures",
    }


def finalize(value: dict[str, Any]) -> dict[str, Any]:
    value["artifact_hash"] = sha256_hash(
        {
            key: item
            for key, item in value.items()
            if key != "artifact_hash"
        }
    )
    return value


def captured_evidence() -> dict[str, Any]:
    return {
        "captured_source_id": "csrc_contract",
        "relation": "supports",
        "method": "document_read",
        "locator": {"kind": "section", "name": "Pipeline Contract"},
        "observed_at": NOW,
    }


def canonical_evidence() -> dict[str, Any]:
    return {
        "source_id": "src_pipeline_contract",
        "relation": "supports",
        "method": "document_read",
        "locator": {"kind": "section", "name": "Pipeline Contract"},
        "observed_at": NOW,
    }


def record_draft() -> dict[str, Any]:
    return {
        "id": "rec_pipeline_contract",
        "key": "pipeline-contract",
        "kind": "fact",
        "state": "active",
        "title": "Pipeline contract",
        "summary": "KirokuForge uses explicit pipeline artifacts.",
        "scope": ["project"],
        "tags": ["pipeline"],
        "verification": {"status": "unverified"},
        "evidence": [canonical_evidence()],
        "relations": [],
        "content": {
            "statement": "Pipeline stages exchange structured artifacts."
        },
    }


def capture_bundle() -> dict[str, Any]:
    return finalize(
        {
            "artifact_type": "capture_bundle",
            "schema_version": "1.0.0",
            "capture_bundle_id": "cap_pipeline",
            "artifact_hash": HASH,
            "generated_at": NOW,
            "actor": actor(),
            "selection_scope": {
                "description": "KirokuForge pipeline contracts",
                "included": ["references/contracts-v3.md"],
            },
            "sources": [
                {
                    "id": "csrc_contract",
                    "kind": "document",
                    "title": "KirokuForge contracts",
                    "uri": "file:references/contracts-v3.md",
                    "revision": "v3",
                    "status": "new",
                    "content_hash": HASH,
                    "captured_at": NOW,
                    "media_type": "text/markdown",
                    "material": {
                        "mode": "reference",
                        "uri": "file:references/contracts-v3.md",
                    },
                }
            ],
        }
    )


def candidate_bundle(capture: dict[str, Any]) -> dict[str, Any]:
    return finalize(
        {
            "artifact_type": "candidate_bundle",
            "schema_version": "1.0.0",
            "candidate_bundle_id": "cnd_pipeline",
            "artifact_hash": HASH,
            "generated_at": NOW,
            "actor": actor(),
            "capture_bundle": {
                "artifact_type": "capture_bundle",
                "artifact_id": capture["capture_bundle_id"],
                "artifact_hash": capture["artifact_hash"],
            },
            "classification_instructions": [
                "Preserve durable operational knowledge."
            ],
            "candidates": [
                {
                    "id": "can_pipeline_contract",
                    "proposed_key": "pipeline-contract",
                    "kind": "fact",
                    "proposed_state": "active",
                    "title": "Pipeline contract",
                    "summary": "KirokuForge uses explicit pipeline artifacts.",
                    "scope": ["project"],
                    "tags": ["pipeline"],
                    "content": {
                        "statement": (
                            "Pipeline stages exchange structured artifacts."
                        )
                    },
                    "evidence": [captured_evidence()],
                    "classification_rationale": (
                        "The normative contract directly defines the pipeline."
                    ),
                    "classification_confidence": "high",
                }
            ],
        }
    )


def change_set(
    capture: dict[str, Any],
    candidates: dict[str, Any],
) -> dict[str, Any]:
    return finalize(
        {
            "artifact_type": "change_set",
            "schema_version": "1.0.0",
            "change_set_id": "chg_pipeline",
            "artifact_hash": HASH,
            "generated_at": NOW,
            "actor": actor(),
            "target_memory_id": None,
            "base_revision": None,
            "base_state_hash": None,
            "input_bundles": [
                {
                    "artifact_type": "capture_bundle",
                    "artifact_id": capture["capture_bundle_id"],
                    "artifact_hash": capture["artifact_hash"],
                },
                {
                    "artifact_type": "candidate_bundle",
                    "artifact_id": candidates["candidate_bundle_id"],
                    "artifact_hash": candidates["artifact_hash"],
                },
            ],
            "summary": "Initialize memory from the pipeline contract.",
            "source_resolutions": [
                {
                    "captured_source_id": "csrc_contract",
                    "resolution": "add",
                    "canonical_source_id": "src_pipeline_contract",
                    "operation_id": "op_add_source",
                }
            ],
            "candidate_resolutions": [
                {
                    "candidate_id": "can_pipeline_contract",
                    "resolution": "create",
                    "rationale": "No canonical memory exists yet.",
                    "record_ids": ["rec_pipeline_contract"],
                    "operation_ids": ["op_create_record"],
                    "finding_ids": [],
                }
            ],
            "operations": [
                {
                    "operation_id": "op_initialize",
                    "operation_type": "initialize_memory",
                    "memory_id": "mem_pipeline",
                    "project": {
                        "name": "KirokuForge",
                        "description": "Durable project-memory compiler.",
                        "goal": "Preserve operational project knowledge.",
                        "status": "active",
                        "boundaries": {
                            "included": ["Project memory"],
                            "excluded": ["Encyclopedic documentation"],
                        },
                    },
                },
                {
                    "operation_id": "op_add_source",
                    "operation_type": "add_source",
                    "source": {
                        "id": "src_pipeline_contract",
                        "kind": "document",
                        "title": "KirokuForge contracts",
                        "uri": "file:references/contracts-v3.md",
                        "revision": "v3",
                        "integrity": "verified",
                        "content_hash": HASH,
                        "captured_at": NOW,
                        "media_type": "text/markdown",
                    },
                },
                {
                    "operation_id": "op_create_record",
                    "operation_type": "create_record",
                    "record": record_draft(),
                },
            ],
            "findings": [],
        }
    )


def existing_change_set(
    operations: list[dict[str, Any]],
    *,
    change_set_id: str,
) -> dict[str, Any]:
    return finalize(
        {
            "artifact_type": "change_set",
            "schema_version": "1.0.0",
            "change_set_id": change_set_id,
            "artifact_hash": HASH,
            "generated_at": NOW,
            "actor": actor(),
            "target_memory_id": LIFECYCLE_MEMORY["memory_id"],
            "base_revision": LIFECYCLE_MEMORY["revision"],
            "base_state_hash": LIFECYCLE_MEMORY["state_hash"],
            "input_bundles": [
                {
                    "artifact_type": "candidate_bundle",
                    "artifact_id": "cnd_pipeline",
                    "artifact_hash": HASH,
                }
            ],
            "summary": "Update an existing canonical memory.",
            "source_resolutions": [],
            "candidate_resolutions": [],
            "operations": operations,
            "findings": [],
        }
    )


def valid_task_completion_change_set() -> dict[str, Any]:
    task = next(
        record
        for record in LIFECYCLE_MEMORY["records"]
        if record["id"] == "rec_task_blocked"
    )
    evidence_item = {
        "source_id": "src_contract",
        "relation": "supports",
        "method": "test_result",
        "locator": {"kind": "section", "name": "Compiler tests"},
        "observed_at": NOW,
    }
    return existing_change_set(
        [
            {
                "operation_id": "op_completion_evidence",
                "operation_type": "add_evidence",
                "record_id": task["id"],
                "expected_record_hash": task["content_hash"],
                "evidence": evidence_item,
            },
            {
                "operation_id": "op_complete_task",
                "operation_type": "transition_record",
                "record_id": task["id"],
                "expected_record_hash": task["content_hash"],
                "target_state": "done",
                "transition_reason": "The compiler acceptance criteria passed.",
                "content": {
                    **copy.deepcopy(task["content"]),
                    "outcome": "The compiler tests passed.",
                },
            },
        ],
        change_set_id="chg_complete_task",
    )


def audit_report() -> dict[str, Any]:
    return finalize(
        {
            "artifact_type": "audit_report",
            "schema_version": "1.0.0",
            "audit_report_id": "aud_pipeline",
            "artifact_hash": HASH,
            "generated_at": NOW,
            "actor": actor(),
            "memory": {
                "memory_id": MEMORY["memory_id"],
                "revision": MEMORY["revision"],
                "state_hash": MEMORY["state_hash"],
            },
            "policy": {
                "enabled_detectors": ["unsupported-active-knowledge"]
            },
            "findings": [
                {
                    "fingerprint": HASH,
                    "severity": "info",
                    "category": "evidence-quality",
                    "code": "UNSUPPORTED_ACTIVE_KNOWLEDGE",
                    "message": "Review active records with limited evidence.",
                    "record_ids": ["rec_fact"],
                    "source_ids": ["src_contract"],
                    "detector": {
                        "name": "unsupported-active-knowledge",
                        "type": "rule",
                        "version": "1.0.0",
                    },
                    "recommended_action": "Review the referenced evidence.",
                }
            ],
        }
    )


def context_record() -> dict[str, Any]:
    record = MEMORY["records"][0]
    return {
        "id": record["id"],
        "key": record["key"],
        "kind": record["kind"],
        "state": record["state"],
        "title": record["title"],
        "summary": record["summary"],
        "content": record["content"],
        "relations": record["relations"],
        "evidence_source_ids": [
            item["source_id"] for item in record["evidence"]
        ],
        "relevance": {
            "generated": True,
            "reason": "Directly supports the requested implementation goal.",
        },
    }


def context_pack(audit: dict[str, Any]) -> dict[str, Any]:
    order = [
        "mission",
        "active_decisions",
        "active_constraints",
        "applicable_preferences",
        "todo",
        "open_risks",
        "open_questions",
        "facts_and_assumptions",
        "recent_done",
        "recent_events",
        "recent_compilation_changes",
        "audit_findings",
        "selected_sources",
        "omissions",
    ]
    return finalize(
        {
            "artifact_type": "context_pack",
            "schema_version": "1.0.0",
            "context_pack_id": "ctx_pipeline",
            "artifact_hash": HASH,
            "generated_at": NOW,
            "actor": actor(),
            "memory": {
                "memory_id": MEMORY["memory_id"],
                "revision": MEMORY["revision"],
                "state_hash": MEMORY["state_hash"],
            },
            "audit_report": {
                "artifact_id": audit["audit_report_id"],
                "artifact_hash": audit["artifact_hash"],
            },
            "request": {
                "goal": "Implement the next KirokuForge pipeline stage.",
                "scopes": ["project"],
                "max_records": 20,
                "estimated_token_budget": 4000,
            },
            "section_order": order,
            "sections": {
                "mission": {
                    "generated": True,
                    "text": "Implement the next pipeline stage.",
                },
                "active_decisions": [],
                "active_constraints": [],
                "applicable_preferences": [],
                "todo": [],
                "open_risks": [],
                "open_questions": [],
                "facts_and_assumptions": [context_record()],
                "recent_done": [],
                "recent_events": [],
                "recent_compilation_changes": [
                    {
                        "id": "cmp_initial",
                        "result_revision": 1,
                        "compiled_at": "2026-06-08T10:00:00Z",
                        "summary": "Initialized canonical memory.",
                    }
                ],
                "audit_findings": [
                    {
                        "fingerprint": HASH,
                        "severity": "info",
                        "code": "UNSUPPORTED_ACTIVE_KNOWLEDGE",
                        "message": (
                            "Review active records with limited evidence."
                        ),
                        "record_ids": ["rec_fact"],
                    }
                ],
                "selected_sources": [
                    {
                        "id": "src_contract",
                        "kind": "document",
                        "title": "KirokuForge contracts",
                        "uri": "file:references/contracts-v3.md",
                        "revision": "v3",
                    }
                ],
                "omissions": {
                    "counts": {"records": 0, "sources": 0},
                    "retrieval_hints": [],
                },
            },
        }
    )


def fixtures() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    capture = capture_bundle()
    candidates = candidate_bundle(capture)
    changes = change_set(capture, candidates)
    audit = audit_report()
    context = context_pack(audit)

    valid = {
        "valid/capture-bundle.json": capture,
        "valid/candidate-bundle.json": candidates,
        "valid/change-set.json": changes,
        "valid/change-set-task-completion.json": (
            valid_task_completion_change_set()
        ),
        "valid/audit-report.json": audit,
        "valid/context-pack.json": context,
    }

    bad_capture = copy.deepcopy(capture)
    bad_capture["sources"][0]["status"] = "unavailable"

    bad_candidate = copy.deepcopy(candidates)
    bad_candidate["candidates"][0]["proposed_state"] = "done"

    bad_change_set = copy.deepcopy(changes)
    bad_change_set["target_memory_id"] = "mem_fixture"
    bad_change_set["base_revision"] = 1
    bad_change_set["base_state_hash"] = MEMORY["state_hash"]

    bad_audit = copy.deepcopy(audit)
    del bad_audit["findings"][0]["detector"]["version"]

    bad_context = copy.deepcopy(context)
    bad_context["section_order"][0:2] = list(
        reversed(bad_context["section_order"][0:2])
    )

    invalid = {
        "invalid/capture-unavailable-with-content.json": bad_capture,
        "invalid/candidate-kind-state-mismatch.json": bad_candidate,
        "invalid/change-set-initialize-existing-memory.json": bad_change_set,
        "invalid/audit-detector-missing-version.json": bad_audit,
        "invalid/context-section-order.json": bad_context,
    }

    valid_existing = valid["valid/change-set-task-completion.json"]

    stale_revision = copy.deepcopy(valid_existing)
    stale_revision["base_revision"] += 1
    finalize(stale_revision)

    stale_state_hash = copy.deepcopy(valid_existing)
    stale_state_hash["base_state_hash"] = "sha256:" + "f0" * 32
    finalize(stale_state_hash)

    stale_record_hash = copy.deepcopy(valid_existing)
    stale_record_hash["operations"][0]["expected_record_hash"] = (
        "sha256:" + "f0" * 32
    )
    finalize(stale_record_hash)

    invalid_transition = copy.deepcopy(valid_existing)
    transition = invalid_transition["operations"][1]
    transition["target_state"] = "obsolete"
    transition["content"] = copy.deepcopy(
        next(
            record["content"]
            for record in LIFECYCLE_MEMORY["records"]
            if record["id"] == "rec_task_blocked"
        )
    )
    finalize(invalid_transition)

    missing_reason = copy.deepcopy(valid_existing)
    del missing_reason["operations"][1]["transition_reason"]
    finalize(missing_reason)

    invalid_target_content = copy.deepcopy(valid_existing)
    invalid_target_content["operations"] = [
        copy.deepcopy(invalid_target_content["operations"][1])
    ]
    invalid_target_content["operations"][0]["content"].pop("outcome")
    finalize(invalid_target_content)

    missing_completion_evidence = copy.deepcopy(valid_existing)
    missing_completion_evidence["operations"] = [
        copy.deepcopy(missing_completion_evidence["operations"][1])
    ]
    finalize(missing_completion_evidence)

    source_mutated = existing_change_set(
        [
            {
                "operation_id": "op_mutate_source",
                "operation_type": "add_source",
                "source": {
                    key: copy.deepcopy(value)
                    for key, value in LIFECYCLE_MEMORY["sources"][0].items()
                    if key != "created_by"
                }
                | {"title": "Mutated source title"},
            }
        ],
        change_set_id="chg_mutate_source",
    )

    artifact_hash_mismatch = copy.deepcopy(valid_existing)
    artifact_hash_mismatch["summary"] = "Changed after hashing."

    integrity_invalid = {
        "invalid/integrity/change-set-stale-revision.json": stale_revision,
        "invalid/integrity/change-set-stale-state-hash.json": stale_state_hash,
        "invalid/integrity/change-set-stale-record-hash.json": stale_record_hash,
        "invalid/integrity/change-set-invalid-transition.json": (
            invalid_transition
        ),
        "invalid/integrity/change-set-missing-transition-reason.json": (
            missing_reason
        ),
        "invalid/integrity/change-set-invalid-target-content.json": (
            invalid_target_content
        ),
        "invalid/integrity/change-set-missing-completion-evidence.json": (
            missing_completion_evidence
        ),
        "invalid/integrity/change-set-source-mutated.json": source_mutated,
        "invalid/integrity/change-set-artifact-hash-mismatch.json": (
            artifact_hash_mismatch
        ),
    }
    return valid, invalid, integrity_invalid


def manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "generated_by": "tests/build_pipeline_fixtures.py",
        "valid": [
            {
                "artifact_type": "capture_bundle",
                "schema": "schemas/capture-bundle-v1.schema.json",
                "path": "valid/capture-bundle.json",
            },
            {
                "artifact_type": "candidate_bundle",
                "schema": "schemas/candidate-bundle-v1.schema.json",
                "path": "valid/candidate-bundle.json",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "valid/change-set.json",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "valid/change-set-task-completion.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
            },
            {
                "artifact_type": "audit_report",
                "schema": "schemas/audit-report-v1.schema.json",
                "path": "valid/audit-report.json",
            },
            {
                "artifact_type": "context_pack",
                "schema": "schemas/context-pack-v1.schema.json",
                "path": "valid/context-pack.json",
            },
        ],
        "invalid": [
            {
                "artifact_type": "capture_bundle",
                "schema": "schemas/capture-bundle-v1.schema.json",
                "path": "invalid/capture-unavailable-with-content.json",
            },
            {
                "artifact_type": "candidate_bundle",
                "schema": "schemas/candidate-bundle-v1.schema.json",
                "path": "invalid/candidate-kind-state-mismatch.json",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/change-set-initialize-existing-memory.json",
            },
            {
                "artifact_type": "audit_report",
                "schema": "schemas/audit-report-v1.schema.json",
                "path": "invalid/audit-detector-missing-version.json",
            },
            {
                "artifact_type": "context_pack",
                "schema": "schemas/context-pack-v1.schema.json",
                "path": "invalid/context-section-order.json",
            },
        ],
        "integrity_invalid": [
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-stale-revision.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "STALE_CHANGESET",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-stale-state-hash.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "STALE_CHANGESET",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-stale-record-hash.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "STALE_CHANGESET",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-invalid-transition.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "INVALID_TRANSITION",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-missing-transition-reason.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "MISSING_TRANSITION_REASON",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-invalid-target-content.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "INVALID_TRANSITION",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-missing-completion-evidence.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "INVALID_TRANSITION",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-source-mutated.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "SOURCE_MUTATED",
            },
            {
                "artifact_type": "change_set",
                "schema": "schemas/change-set-v1.schema.json",
                "path": "invalid/integrity/change-set-artifact-hash-mismatch.json",
                "base_memory": "tests/fixtures/memory/valid/lifecycle-states.json",
                "code": "ARTIFACT_HASH_MISMATCH",
            },
        ],
    }


def render(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def expected_files() -> dict[Path, str]:
    valid, invalid, integrity_invalid = fixtures()
    files = {
        FIXTURE_ROOT / path: render(value)
        for path, value in {
            **valid,
            **invalid,
            **integrity_invalid,
        }.items()
    }
    files[FIXTURE_ROOT / "manifest.json"] = render(manifest())
    return files


def check() -> int:
    failures: list[str] = []
    expected = expected_files()
    actual = set(FIXTURE_ROOT.rglob("*.json")) if FIXTURE_ROOT.exists() else set()
    if actual != set(expected):
        failures.append("fixture file set differs from builder output")
    for path, content in expected.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            failures.append(str(path.relative_to(ROOT)))
    if failures:
        print("Pipeline fixture corpus is stale:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Pipeline fixture corpus is current ({len(expected) - 1} files)")
    return 0


def write() -> None:
    expected = expected_files()
    for path in sorted(expected):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected[path], encoding="utf-8")
    for path in FIXTURE_ROOT.rglob("*.json"):
        if path not in expected:
            path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check()
    write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
