from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.kiroku_core.integrity import validate_memory_integrity


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"
MANIFEST = json.loads(
    (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
)


def load_fixture(relative_path: str) -> dict:
    return json.loads(
        (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
    )


class IntegrityFixtureTest(unittest.TestCase):
    def test_valid_fixtures_have_no_findings(self) -> None:
        for item in MANIFEST["valid"]:
            with self.subTest(path=item["path"]):
                result = validate_memory_integrity(
                    load_fixture(item["path"])
                )
                self.assertTrue(result.ok, result.to_dict())
                self.assertEqual(result.findings, ())

    def test_integrity_fixtures_include_their_expected_code(self) -> None:
        cases = [
            item
            for item in MANIFEST["invalid"]
            if item["layer"] == "integrity"
        ]
        for item in cases:
            with self.subTest(path=item["path"], code=item["code"]):
                result = validate_memory_integrity(
                    load_fixture(item["path"])
                )
                codes = {finding.code for finding in result.findings}
                self.assertFalse(result.ok)
                self.assertIn(item["code"], codes, result.to_dict())

    def test_schema_failure_stops_integrity_checks(self) -> None:
        memory = load_fixture("invalid/schema/wrong-kind-state.json")
        memory["records"][0]["content_hash"] = "sha256:" + "f0" * 32
        result = validate_memory_integrity(memory)
        self.assertEqual(
            [finding.code for finding in result.findings],
            ["SCHEMA_VIOLATION"],
        )

    def test_validation_is_deterministic_and_does_not_mutate(self) -> None:
        memory = load_fixture(
            "invalid/integrity/unknown-compilation-reference.json"
        )
        original = copy.deepcopy(memory)
        first = validate_memory_integrity(memory)
        second = validate_memory_integrity(memory)
        self.assertEqual(first, second)
        self.assertEqual(memory, original)
        self.assertGreaterEqual(len(first.findings), 2)


class MultiFindingIntegrityTest(unittest.TestCase):
    def test_independent_problems_are_reported_together(self) -> None:
        memory = load_fixture("valid/minimal.json")
        record = memory["records"][0]
        record["created_by"] = "cmp_missing"
        record["updated_by"] = "cmp_missing"
        record["relations"] = [
            {"type": "related_to", "target_id": record["id"]},
            {
                "type": "related_to",
                "target_id": record["id"],
                "note": "Duplicate tuple with a different note.",
            },
        ]
        record["evidence"].append(
            {
                **copy.deepcopy(record["evidence"][0]),
                "relation": "refutes",
            }
        )

        result = validate_memory_integrity(memory)
        codes = [finding.code for finding in result.findings]

        self.assertIn("UNKNOWN_COMPILATION_REFERENCE", codes)
        self.assertIn("RELATION_SELF_TARGET", codes)
        self.assertIn("RELATION_DUPLICATE", codes)
        self.assertIn("VERIFICATION_EVIDENCE_INVALID", codes)
        self.assertIn("RECORD_HASH_MISMATCH", codes)
        self.assertIn("STATE_HASH_MISMATCH", codes)
        self.assertGreaterEqual(len(result.findings), 8)

    def test_receipt_hash_and_chain_failures_are_distinct(self) -> None:
        memory = load_fixture("valid/supersession-history.json")
        memory["compilations"][0]["warnings"] = ["Changed receipt."]
        memory["compilations"][1]["base_state_hash"] = "sha256:" + "f0" * 32

        result = validate_memory_integrity(memory)
        codes = {finding.code for finding in result.findings}
        self.assertIn("RECEIPT_HASH_MISMATCH", codes)
        self.assertIn("RECEIPT_CHAIN_MISMATCH", codes)

    def test_duplicate_relation_tuple_ignores_note(self) -> None:
        memory = load_fixture("valid/minimal.json")
        record = memory["records"][0]
        record["relations"] = [
            {"type": "related_to", "target_id": "rec_missing"},
            {
                "type": "related_to",
                "target_id": "rec_missing",
                "note": "Same tuple.",
            },
        ]
        result = validate_memory_integrity(memory)
        self.assertIn(
            "RELATION_DUPLICATE",
            {finding.code for finding in result.findings},
        )

    def test_supersession_cycle_and_branch_are_detected(self) -> None:
        cycle = load_fixture("valid/supersession-history.json")
        cycle["records"][0]["relations"] = [
            {"type": "supersedes", "target_id": "rec_storage_v2"}
        ]
        cycle_result = validate_memory_integrity(cycle)
        self.assertIn(
            "SUPERSESSION_CYCLE",
            {finding.code for finding in cycle_result.findings},
        )

        branch = load_fixture("valid/supersession-history.json")
        successor = copy.deepcopy(branch["records"][1])
        successor["id"] = "rec_storage_v3"
        branch["records"].append(successor)
        branch_result = validate_memory_integrity(branch)
        self.assertIn(
            "SUPERSESSION_BRANCH",
            {finding.code for finding in branch_result.findings},
        )

    def test_supersession_requires_matching_keys(self) -> None:
        memory = load_fixture("valid/supersession-history.json")
        memory["records"][1]["key"] = "different-key"
        result = validate_memory_integrity(memory)
        self.assertIn(
            "SUPERSESSION_KEY_MISMATCH",
            {finding.code for finding in result.findings},
        )


if __name__ == "__main__":
    unittest.main()
