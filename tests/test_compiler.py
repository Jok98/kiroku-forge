from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.kiroku_core.compiler import compile_change_set
from scripts.kiroku_core.hashing import receipt_hash, record_hash, sha256_hash, state_hash
from scripts.kiroku_core.integrity import validate_memory_integrity


ROOT = Path(__file__).resolve().parents[1]
MEMORY_ROOT = ROOT / "tests" / "fixtures" / "memory"
PIPELINE_ROOT = ROOT / "tests" / "fixtures" / "pipeline"
COMPILED_AT = "2026-06-08T12:30:00Z"
EXTRA_HASH = "sha256:" + "e5" * 32
INPUT_HASH = "sha256:" + "b1" * 32


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_memory(relative_path: str) -> dict[str, Any]:
    return load_json(MEMORY_ROOT / relative_path)


def load_pipeline(relative_path: str) -> dict[str, Any]:
    return load_json(PIPELINE_ROOT / relative_path)


def refresh_artifact_hash(change_set: dict[str, Any]) -> None:
    change_set["artifact_hash"] = sha256_hash(
        {key: value for key, value in change_set.items() if key != "artifact_hash"}
    )


def extra_evidence() -> dict[str, Any]:
    return {
        "source_id": "src_compile_extra",
        "relation": "supports",
        "method": "document_read",
        "locator": {"kind": "section", "name": "Compile"},
        "observed_at": COMPILED_AT,
    }


def record_by_id(memory: dict[str, Any], record_id: str) -> dict[str, Any]:
    return next(record for record in memory["records"] if record["id"] == record_id)


def build_all_operations_change_set(base: dict[str, Any]) -> dict[str, Any]:
    question = record_by_id(base, "rec_question_answered")
    predecessor = record_by_id(base, "rec_proposal_rejected")
    evidence = extra_evidence()
    relation = {"type": "related_to", "target_id": "rec_compile_fact"}
    open_question_content = copy.deepcopy(question["content"])
    open_question_content.pop("answer")

    change_set = {
        "artifact_type": "change_set",
        "schema_version": "1.0.0",
        "change_set_id": "chg_compile_all_ops",
        "artifact_hash": "sha256:" + "0" * 64,
        "generated_at": COMPILED_AT,
        "actor": {
            "type": "agent",
            "name": "codex",
            "version": "1.0",
            "session_ref": "session-compiler-tests",
        },
        "target_memory_id": base["memory_id"],
        "base_revision": base["revision"],
        "base_state_hash": base["state_hash"],
        "input_bundles": [
            {
                "artifact_type": "candidate_bundle",
                "artifact_id": "cnd_compile_all_ops",
                "artifact_hash": INPUT_HASH,
            }
        ],
        "summary": "Exercise every non-initialization compiler operation.",
        "source_resolutions": [
            {
                "captured_source_id": "csrc_compile_extra",
                "resolution": "add",
                "canonical_source_id": "src_compile_extra",
                "operation_id": "op_compile_add_source",
            }
        ],
        "candidate_resolutions": [],
        "operations": [
            {
                "operation_id": "op_compile_update_project",
                "operation_type": "update_project",
                "changes": {
                    "goal": "Compile ChangeSets into canonical memory.",
                    "boundaries": {
                        "included": ["Canonical project memory", "Compiler behavior"],
                        "excluded": ["Generated viewer UI"],
                    },
                },
            },
            {
                "operation_id": "op_compile_add_source",
                "operation_type": "add_source",
                "source": {
                    "id": "src_compile_extra",
                    "kind": "document",
                    "title": "Compiler notes",
                    "uri": "file:compiler-notes.md",
                    "integrity": "verified",
                    "content_hash": EXTRA_HASH,
                    "captured_at": COMPILED_AT,
                    "media_type": "text/markdown",
                },
            },
            {
                "operation_id": "op_compile_create_record",
                "operation_type": "create_record",
                "record": {
                    "id": "rec_compile_fact",
                    "key": "pure-compiler",
                    "kind": "fact",
                    "state": "active",
                    "title": "Pure compiler",
                    "summary": "COMPILE can run as a pure in-memory transformation.",
                    "scope": ["project"],
                    "tags": ["compiler"],
                    "verification": {"status": "unverified"},
                    "evidence": [evidence],
                    "relations": [],
                    "content": {
                        "statement": "compile_change_set returns a complete prospective Memory."
                    },
                },
            },
            {
                "operation_id": "op_compile_amend_record",
                "operation_type": "amend_record",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "changes": {
                    "title": "Markdown canonical question reopened",
                    "summary": "The canonical Markdown answer needs to remain reviewable.",
                    "scope": ["project", "compiler"],
                    "tags": ["compile"],
                },
            },
            {
                "operation_id": "op_compile_add_evidence",
                "operation_type": "add_evidence",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "evidence": evidence,
            },
            {
                "operation_id": "op_compile_remove_evidence",
                "operation_type": "remove_evidence",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "evidence": copy.deepcopy(question["evidence"][0]),
            },
            {
                "operation_id": "op_compile_set_verification",
                "operation_type": "set_verification",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "verification": {
                    "status": "partially_verified",
                    "note": "The answer was reopened during compilation tests.",
                },
            },
            {
                "operation_id": "op_compile_add_relation",
                "operation_type": "add_relation",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "relation": relation,
            },
            {
                "operation_id": "op_compile_remove_relation",
                "operation_type": "remove_relation",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "relation": relation,
            },
            {
                "operation_id": "op_compile_transition_record",
                "operation_type": "transition_record",
                "record_id": question["id"],
                "expected_record_hash": question["content_hash"],
                "target_state": "open",
                "transition_reason": "The answer needs renewed validation.",
                "content": open_question_content,
            },
            {
                "operation_id": "op_compile_supersede_record",
                "operation_type": "supersede_record",
                "predecessor_id": predecessor["id"],
                "expected_record_hash": predecessor["content_hash"],
                "successor": {
                    "id": "rec_compile_successor",
                    "key": predecessor["key"],
                    "kind": "decision",
                    "state": "active",
                    "title": "Structured memory is canonical",
                    "summary": "The rejected Markdown idea is superseded by structured memory.",
                    "scope": ["project"],
                    "tags": ["compile"],
                    "verification": {"status": "unverified"},
                    "evidence": [evidence],
                    "relations": [],
                    "content": {
                        "decision": "Keep memory.json as canonical structured state.",
                        "rationale": "COMPILE writes structured Memory, not Markdown.",
                    },
                },
                "reason": "Replace the rejected Markdown proposal with the adopted canonical form.",
            },
        ],
        "findings": [],
    }
    refresh_artifact_hash(change_set)
    return change_set


class CompileInitializationTest(unittest.TestCase):
    def test_initial_compilation_creates_revision_one_memory(self) -> None:
        change_set = load_pipeline("valid/change-set.json")
        original_change_set = copy.deepcopy(change_set)

        result = compile_change_set(
            change_set,
            None,
            compilation_id="cmp_compile_initial",
            compiled_at=COMPILED_AT,
        )

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(change_set, original_change_set)
        memory = result.memory
        assert memory is not None
        self.assertEqual(memory["memory_id"], "mem_pipeline")
        self.assertEqual(memory["revision"], 1)
        self.assertEqual(memory["project"]["created_at"], COMPILED_AT)
        self.assertEqual(memory["project"]["updated_at"], COMPILED_AT)
        self.assertEqual(memory["state_hash"], state_hash(memory))
        self.assertEqual(validate_memory_integrity(memory).findings, ())

        source = memory["sources"][0]
        record = memory["records"][0]
        receipt = memory["compilations"][0]
        self.assertEqual(source["created_by"], "cmp_compile_initial")
        self.assertEqual(record["created_by"], "cmp_compile_initial")
        self.assertEqual(record["updated_by"], "cmp_compile_initial")
        self.assertEqual(record["content_hash"], record_hash(record))
        self.assertEqual(receipt["base_revision"], 0)
        self.assertIsNone(receipt["base_state_hash"])
        self.assertIsNone(receipt["previous_receipt_hash"])
        self.assertEqual(receipt["result_state_hash"], memory["state_hash"])
        self.assertEqual(receipt["receipt_hash"], receipt_hash(receipt))
        self.assertEqual(receipt["input_source_ids"], ["src_pipeline_contract"])


class CompileExistingMemoryTest(unittest.TestCase):
    def test_multiple_operations_on_same_record_chain_hash_receipts(self) -> None:
        base = load_memory("valid/lifecycle-states.json")
        change_set = load_pipeline("valid/change-set-task-completion.json")
        original_base = copy.deepcopy(base)
        original_change_set = copy.deepcopy(change_set)
        task = record_by_id(base, "rec_task_blocked")

        result = compile_change_set(
            change_set,
            base,
            compilation_id="cmp_complete_task",
            compiled_at=COMPILED_AT,
        )

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(base, original_base)
        self.assertEqual(change_set, original_change_set)
        memory = result.memory
        assert memory is not None
        self.assertEqual(memory["revision"], base["revision"] + 1)
        self.assertEqual(memory["state_hash"], state_hash(memory))
        self.assertEqual(validate_memory_integrity(memory).findings, ())

        compiled_task = record_by_id(memory, task["id"])
        self.assertEqual(compiled_task["state"], "done")
        self.assertEqual(compiled_task["content"]["outcome"], "The compiler tests passed.")
        self.assertEqual(compiled_task["updated_by"], "cmp_complete_task")

        receipt = memory["compilations"][-1]
        self.assertEqual(receipt["base_revision"], base["revision"])
        self.assertEqual(receipt["base_state_hash"], base["state_hash"])
        self.assertEqual(
            receipt["previous_receipt_hash"],
            base["compilations"][-1]["receipt_hash"],
        )
        self.assertEqual(receipt["result_state_hash"], memory["state_hash"])
        self.assertEqual(receipt["receipt_hash"], receipt_hash(receipt))
        self.assertEqual(receipt["input_source_ids"], ["src_contract"])

        first_change = receipt["operations"][0]["hash_changes"][0]
        second_change = receipt["operations"][1]["hash_changes"][0]
        self.assertEqual(first_change["previous_hash"], task["content_hash"])
        self.assertEqual(second_change["previous_hash"], first_change["result_hash"])
        self.assertEqual(second_change["result_hash"], compiled_task["content_hash"])

    def test_compilation_applies_every_non_initialization_operation(self) -> None:
        base = load_memory("valid/lifecycle-states.json")
        change_set = build_all_operations_change_set(base)
        predecessor_before = copy.deepcopy(record_by_id(base, "rec_proposal_rejected"))

        result = compile_change_set(
            change_set,
            base,
            compilation_id="cmp_compile_all_ops",
            compiled_at=COMPILED_AT,
        )

        self.assertTrue(result.ok, result.to_dict())
        memory = result.memory
        assert memory is not None
        self.assertEqual(validate_memory_integrity(memory).findings, ())
        self.assertEqual(
            memory["project"]["goal"],
            "Compile ChangeSets into canonical memory.",
        )
        self.assertEqual(memory["project"]["updated_at"], COMPILED_AT)

        source_ids = {source["id"] for source in memory["sources"]}
        self.assertIn("src_compile_extra", source_ids)
        added_source = next(source for source in memory["sources"] if source["id"] == "src_compile_extra")
        self.assertEqual(added_source["created_by"], "cmp_compile_all_ops")

        created = record_by_id(memory, "rec_compile_fact")
        self.assertEqual(created["created_by"], "cmp_compile_all_ops")
        self.assertEqual(created["content_hash"], record_hash(created))

        question = record_by_id(memory, "rec_question_answered")
        self.assertEqual(question["state"], "open")
        self.assertNotIn("answer", question["content"])
        self.assertEqual(question["verification"]["status"], "partially_verified")
        self.assertEqual(question["scope"], ["compiler", "project"])
        self.assertEqual(question["tags"], ["compile"])
        self.assertIn(extra_evidence(), question["evidence"])
        self.assertNotIn(
            record_by_id(base, "rec_question_answered")["evidence"][0],
            question["evidence"],
        )
        self.assertNotIn(
            {"type": "related_to", "target_id": "rec_compile_fact"},
            question["relations"],
        )

        predecessor_after = record_by_id(memory, "rec_proposal_rejected")
        successor = record_by_id(memory, "rec_compile_successor")
        self.assertEqual(predecessor_after, predecessor_before)
        self.assertIn(
            {"type": "supersedes", "target_id": predecessor_before["id"]},
            successor["relations"],
        )
        self.assertEqual(successor["created_by"], "cmp_compile_all_ops")

        receipt = memory["compilations"][-1]
        self.assertEqual(
            [operation["operation_type"] for operation in receipt["operations"]],
            [operation["operation_type"] for operation in change_set["operations"]],
        )
        self.assertEqual(
            receipt["operations"][-1]["transition_reason"],
            "Replace the rejected Markdown proposal with the adopted canonical form.",
        )

    def test_stale_change_set_is_refused_without_partial_memory(self) -> None:
        base = load_memory("valid/lifecycle-states.json")
        change_set = load_pipeline("valid/change-set-task-completion.json")
        change_set["base_revision"] += 1
        refresh_artifact_hash(change_set)

        result = compile_change_set(
            change_set,
            base,
            compilation_id="cmp_stale_change_set",
            compiled_at=COMPILED_AT,
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.memory)
        self.assertIn("STALE_CHANGESET", {finding.code for finding in result.findings})

    def test_invalid_prospective_memory_is_refused(self) -> None:
        base = load_memory("valid/lifecycle-states.json")
        change_set = load_pipeline("valid/change-set-task-completion.json")

        result = compile_change_set(
            change_set,
            base,
            compilation_id="cmp_initial",
            compiled_at=COMPILED_AT,
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.memory)
        self.assertIn("DUPLICATE_ID", {finding.code for finding in result.findings})


if __name__ == "__main__":
    unittest.main()
