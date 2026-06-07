from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

import fastjsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"
COMMON_PATH = ROOT / "schemas" / "common-v1.schema.json"
MEMORY_PATH = ROOT / "schemas" / "memory-v3.schema.json"
COMMON = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
MEMORY = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
MINIMAL = json.loads(
    (FIXTURE_ROOT / "valid" / "minimal.json").read_text(encoding="utf-8")
)
HASH = "sha256:" + "a1" * 32
NOW = "2026-06-08T10:00:00Z"


def load_schema(uri: str) -> dict[str, Any]:
    if uri == COMMON["$id"]:
        return COMMON
    raise ValueError(f"unexpected schema URI: {uri}")


VALIDATE = fastjsonschema.compile(MEMORY, handlers={"https": load_schema})


def direct_evidence(relation: str = "supports") -> dict[str, Any]:
    return {
        "source_id": "src_contract",
        "relation": relation,
        "method": "document_read",
        "locator": {"kind": "section", "name": "Canonical memory"},
        "observed_at": NOW,
    }


def record(
    kind: str = "fact",
    state: str = "active",
    content: dict[str, Any] | None = None,
    *,
    verification: str = "unverified",
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"rec_{kind}",
        "key": f"{kind}-contract",
        "kind": kind,
        "state": state,
        "title": f"{kind.title()} contract",
        "summary": f"Canonical {kind} used by the schema tests.",
        "scope": ["project"],
        "tags": ["contract"],
        "verification": {"status": verification},
        "evidence": evidence or [],
        "relations": [],
        "content": content or {"statement": "Canonical memory is structured."},
        "created_at": NOW,
        "updated_at": NOW,
        "created_by": "cmp_initial",
        "updated_by": "cmp_initial",
        "content_hash": HASH,
    }


def valid_memory() -> dict[str, Any]:
    return copy.deepcopy(MINIMAL)


class MemorySchemaTest(unittest.TestCase):
    def assert_valid(self, memory: dict[str, Any]) -> None:
        VALIDATE(memory)

    def assert_invalid(self, memory: dict[str, Any]) -> None:
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            VALIDATE(memory)

    def with_record(self, candidate: dict[str, Any]) -> dict[str, Any]:
        memory = valid_memory()
        memory["records"] = [candidate]
        return memory

    def test_schema_declares_canonical_v3_contract(self) -> None:
        self.assertEqual(
            MEMORY["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertEqual(
            MEMORY["$id"],
            "https://kiroku-forge.local/schemas/memory-v3.schema.json",
        )
        self.assert_valid(valid_memory())

    def test_all_canonical_kinds_accept_their_base_state_and_content(self) -> None:
        cases = [
            ("fact", "active", {"statement": "A fact."}),
            (
                "decision",
                "active",
                {"decision": "Use JSON.", "rationale": "It is structured."},
            ),
            (
                "assumption",
                "active",
                {
                    "assumption": "The source remains available.",
                    "basis": "It is stored locally.",
                    "impact_if_false": "Evidence cannot be reopened.",
                    "validation_plan": "Check the URI.",
                },
            ),
            ("constraint", "active", {"constraint": "Do not depend on Git."}),
            ("preference", "active", {"preference": "Keep handoffs compact."}),
            (
                "proposal",
                "proposed",
                {
                    "proposal": "Add an audit command.",
                    "motivation": "Expose memory quality.",
                },
            ),
            (
                "task",
                "todo",
                {
                    "objective": "Implement canonical validation.",
                    "priority": "high",
                    "acceptance_criteria": ["The valid fixture passes."],
                },
            ),
            (
                "question",
                "open",
                {
                    "question": "Which sources changed?",
                    "why_it_matters": "Only changed sources need classification.",
                },
            ),
            (
                "risk",
                "open",
                {
                    "description": "The context pack may be too large.",
                    "impact": "medium",
                    "likelihood": "low",
                },
            ),
            (
                "event",
                "occurred",
                {
                    "description": "The v3 contract was approved.",
                    "occurred_at": NOW,
                    "significance": "Implementation can begin.",
                },
            ),
        ]

        for kind, state, content in cases:
            with self.subTest(kind=kind):
                self.assert_valid(self.with_record(record(kind, state, content)))

    def test_state_specific_content_contracts(self) -> None:
        cases = [
            record(
                "proposal",
                "rejected",
                {
                    "proposal": "Store Markdown canonically.",
                    "motivation": "Make it easy to read.",
                    "rejection_reason": "Structured memory is authoritative.",
                },
            ),
            record(
                "proposal",
                "cancelled",
                {
                    "proposal": "Build an interim viewer.",
                    "motivation": "Inspect early records.",
                    "cancellation_reason": "The data contract must stabilize first.",
                },
            ),
            record(
                "task",
                "done",
                {
                    "objective": "Define common primitives.",
                    "priority": "high",
                    "acceptance_criteria": ["The common schema compiles."],
                    "outcome": "The schema and tests were added.",
                },
                evidence=[direct_evidence()],
            ),
            record(
                "task",
                "cancelled",
                {
                    "objective": "Maintain the v2 renderer.",
                    "priority": "low",
                    "acceptance_criteria": ["The renderer supports v2."],
                    "cancellation_reason": "The v2 implementation was removed.",
                },
            ),
            record(
                "question",
                "answered",
                {
                    "question": "Is Markdown canonical?",
                    "why_it_matters": "Writers need one source of truth.",
                    "answer": "No, memory.json is canonical.",
                },
            ),
            record(
                "risk",
                "accepted",
                {
                    "description": "Heuristic audit may report false positives.",
                    "impact": "low",
                    "likelihood": "medium",
                    "acceptance_rationale": "Findings are non-blocking.",
                },
            ),
            record(
                "risk",
                "closed",
                {
                    "description": "The schema may permit invalid done tasks.",
                    "impact": "high",
                    "likelihood": "medium",
                    "resolution": "Done tasks require direct evidence.",
                },
                evidence=[direct_evidence()],
            ),
            record(
                "assumption",
                "invalidated",
                {
                    "assumption": "Generated Markdown is required.",
                    "basis": "The previous viewer used it.",
                    "impact_if_false": "The viewer can read JSON directly.",
                    "validation_plan": "Inspect the viewer contract.",
                },
                verification="contradicted",
                evidence=[direct_evidence("refutes")],
            ),
        ]

        for candidate in cases:
            with self.subTest(kind=candidate["kind"], state=candidate["state"]):
                self.assert_valid(self.with_record(candidate))

    def test_kind_state_and_content_must_match(self) -> None:
        invalid = record(
            "decision",
            "todo",
            {
                "objective": "Choose canonical storage.",
                "priority": "high",
                "acceptance_criteria": ["A decision exists."],
            },
        )
        self.assert_invalid(self.with_record(invalid))

        missing_rationale = record(
            "decision",
            "active",
            {"decision": "Use JSON."},
        )
        self.assert_invalid(self.with_record(missing_rationale))

    def test_state_specific_fields_are_required_and_exclusive(self) -> None:
        done_without_outcome = record(
            "task",
            "done",
            {
                "objective": "Compile memory.",
                "priority": "high",
                "acceptance_criteria": ["Compilation succeeds."],
            },
            evidence=[direct_evidence()],
        )
        self.assert_invalid(self.with_record(done_without_outcome))

        proposed_with_rejection = record(
            "proposal",
            "proposed",
            {
                "proposal": "Generate Markdown.",
                "motivation": "Human readability.",
                "rejection_reason": "Not canonical.",
            },
        )
        self.assert_invalid(self.with_record(proposed_with_rejection))

        open_question_with_answer = record(
            "question",
            "open",
            {
                "question": "Is the source verified?",
                "why_it_matters": "Verification affects trust.",
                "answer": "Yes.",
            },
        )
        self.assert_invalid(self.with_record(open_question_with_answer))

    def test_verification_and_terminal_states_require_direct_evidence(self) -> None:
        verified_inference = record(
            verification="verified",
            evidence=[
                {
                    **direct_evidence(),
                    "method": "inference",
                }
            ],
        )
        self.assert_invalid(self.with_record(verified_inference))

        done_without_evidence = record(
            "task",
            "done",
            {
                "objective": "Compile memory.",
                "priority": "high",
                "acceptance_criteria": ["Compilation succeeds."],
                "outcome": "Compilation succeeded.",
            },
        )
        self.assert_invalid(self.with_record(done_without_evidence))

    def test_source_integrity_controls_content_hash(self) -> None:
        missing_hash = valid_memory()
        del missing_hash["sources"][0]["content_hash"]
        self.assert_invalid(missing_hash)

        unverified_with_hash = valid_memory()
        source = unverified_with_hash["sources"][0]
        source["integrity"] = "unverified"
        self.assert_invalid(unverified_with_hash)

        valid_unverified = valid_memory()
        source = valid_unverified["sources"][0]
        source["integrity"] = "unverified"
        del source["content_hash"]
        source["metadata"] = {"integrity_reason": "Raw content unavailable"}
        self.assert_valid(valid_unverified)

    def test_memory_and_nested_objects_are_closed(self) -> None:
        root_extra = valid_memory()
        root_extra["unexpected"] = True
        self.assert_invalid(root_extra)

        record_extra = valid_memory()
        record_extra["records"][0]["confidence"] = "high"
        self.assert_invalid(record_extra)

        receipt_extra = valid_memory()
        receipt_extra["compilations"][0]["status"] = "completed"
        self.assert_invalid(receipt_extra)

    def test_receipt_shape_rejects_unknown_operations_and_empty_hash_change(self) -> None:
        unknown_operation = valid_memory()
        unknown_operation["compilations"][0]["operations"][0][
            "operation_type"
        ] = "delete_record"
        self.assert_invalid(unknown_operation)

        empty_hash_change = valid_memory()
        empty_hash_change["compilations"][0]["operations"][0]["hash_changes"][0] = {
            "id": "mem_example",
            "previous_hash": None,
            "result_hash": None,
        }
        self.assert_invalid(empty_hash_change)

    def test_receipt_base_shape_and_transition_reason_are_enforced(self) -> None:
        invalid_first = valid_memory()
        invalid_first["compilations"][0]["base_state_hash"] = HASH
        self.assert_invalid(invalid_first)

        invalid_later = valid_memory()
        receipt = invalid_later["compilations"][0]
        receipt["base_revision"] = 1
        receipt["result_revision"] = 2
        receipt["base_state_hash"] = HASH
        receipt["previous_receipt_hash"] = None
        self.assert_invalid(invalid_later)

        missing_reason = valid_memory()
        operation = missing_reason["compilations"][0]["operations"][0]
        operation["operation_type"] = "transition_record"
        self.assert_invalid(missing_reason)

        with_reason = valid_memory()
        operation = with_reason["compilations"][0]["operations"][0]
        operation["operation_type"] = "transition_record"
        operation["transition_reason"] = "Work resumed after new evidence."
        self.assert_valid(with_reason)

    def test_cross_record_invariants_are_not_encoded_as_shape_rules(self) -> None:
        memory = valid_memory()
        duplicate = copy.deepcopy(memory["records"][0])
        duplicate["id"] = "rec_duplicate"
        memory["records"].append(duplicate)
        self.assert_valid(memory)


if __name__ == "__main__":
    unittest.main()
