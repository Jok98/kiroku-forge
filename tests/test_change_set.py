from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.kiroku_core.change_set import validate_change_set
from scripts.kiroku_core.hashing import sha256_hash
from scripts.kiroku_core.schema import validate_change_set_schema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "pipeline"
MANIFEST = json.loads(
    (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture(relative_path: str) -> dict:
    return load_json(FIXTURE_ROOT / relative_path)


def load_base(item: dict) -> dict | None:
    path = item.get("base_memory")
    return load_json(ROOT / path) if path is not None else None


def refresh_artifact_hash(change_set: dict) -> None:
    change_set["artifact_hash"] = sha256_hash(
        {
            key: value
            for key, value in change_set.items()
            if key != "artifact_hash"
        }
    )


class ChangeSetFixtureTest(unittest.TestCase):
    def test_valid_change_sets_pass_semantic_validation(self) -> None:
        cases = [
            item
            for item in MANIFEST["valid"]
            if item["artifact_type"] == "change_set"
        ]
        for item in cases:
            with self.subTest(path=item["path"]):
                result = validate_change_set(
                    load_fixture(item["path"]),
                    load_base(item),
                )
                self.assertTrue(result.ok, result.to_dict())
                self.assertEqual(result.findings, ())

    def test_integrity_fixtures_include_expected_code(self) -> None:
        for item in MANIFEST["integrity_invalid"]:
            with self.subTest(path=item["path"], code=item["code"]):
                result = validate_change_set(
                    load_fixture(item["path"]),
                    load_base(item),
                )
                codes = {finding.code for finding in result.findings}
                self.assertFalse(result.ok)
                self.assertIn(item["code"], codes, result.to_dict())

    def test_validation_is_deterministic_and_non_mutating(self) -> None:
        item = MANIFEST["integrity_invalid"][0]
        change_set = load_fixture(item["path"])
        memory = load_base(item)
        original_change_set = copy.deepcopy(change_set)
        original_memory = copy.deepcopy(memory)

        first = validate_change_set(change_set, memory)
        second = validate_change_set(change_set, memory)

        self.assertEqual(first, second)
        self.assertEqual(change_set, original_change_set)
        self.assertEqual(memory, original_memory)

    def test_schema_failure_stops_semantic_checks(self) -> None:
        change_set = load_fixture(
            "invalid/change-set-initialize-existing-memory.json"
        )
        result = validate_change_set(change_set, None)
        self.assertEqual(
            [finding.code for finding in result.findings],
            ["SCHEMA_VIOLATION"],
        )


class ChangeSetPreconditionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.change_set = load_fixture(
            "valid/change-set-task-completion.json"
        )
        self.memory = load_json(
            ROOT
            / "tests"
            / "fixtures"
            / "memory"
            / "valid"
            / "lifecycle-states.json"
        )

    def test_initialization_fails_when_memory_appears(self) -> None:
        initialization = load_fixture("valid/change-set.json")
        result = validate_change_set(initialization, self.memory)
        self.assertIn(
            "STALE_CHANGESET",
            {finding.code for finding in result.findings},
        )

    def test_missing_target_memory_is_stale(self) -> None:
        result = validate_change_set(self.change_set, None)
        self.assertEqual(
            {finding.code for finding in result.findings},
            {"STALE_CHANGESET"},
        )

    def test_independent_precondition_failures_are_reported_together(self) -> None:
        change_set = copy.deepcopy(self.change_set)
        change_set["base_revision"] += 1
        change_set["base_state_hash"] = "sha256:" + "f0" * 32
        for operation in change_set["operations"]:
            operation["expected_record_hash"] = "sha256:" + "e0" * 32
        refresh_artifact_hash(change_set)

        result = validate_change_set(change_set, self.memory)
        stale_findings = [
            finding
            for finding in result.findings
            if finding.code == "STALE_CHANGESET"
        ]
        self.assertEqual(len(stale_findings), 4)

    def test_transition_evidence_may_be_supplied_in_same_change_set(self) -> None:
        result = validate_change_set(self.change_set, self.memory)
        self.assertTrue(result.ok, result.to_dict())

    def test_missing_transition_reason_has_specific_code(self) -> None:
        change_set = copy.deepcopy(self.change_set)
        del change_set["operations"][1]["transition_reason"]
        refresh_artifact_hash(change_set)

        self.assertTrue(validate_change_set_schema(change_set).ok)
        result = validate_change_set(change_set, self.memory)
        self.assertIn(
            "MISSING_TRANSITION_REASON",
            {finding.code for finding in result.findings},
        )

    def test_reusing_source_identity_is_source_mutation(self) -> None:
        item = next(
            item
            for item in MANIFEST["integrity_invalid"]
            if item["code"] == "SOURCE_MUTATED"
        )
        result = validate_change_set(
            load_fixture(item["path"]),
            load_base(item),
        )
        finding = next(
            finding
            for finding in result.findings
            if finding.code == "SOURCE_MUTATED"
        )
        self.assertEqual(finding.entity_ids, ("op_mutate_source", "src_contract"))


if __name__ == "__main__":
    unittest.main()
