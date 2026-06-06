from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kiroku_core.io import record_hash  # noqa: E402
from kiroku_core.validation import validate_memory  # noqa: E402


SCHEMA = ROOT / "schemas" / "memory-v2.schema.json"
FIXTURE = ROOT / "tests" / "fixtures" / "valid-memory.json"


def fixture() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for record in data["records"]:
        record["content_hash"] = record_hash(record)
    return data


class ValidationTests(unittest.TestCase):
    def test_valid_memory(self) -> None:
        result = validate_memory(fixture(), SCHEMA)
        self.assertEqual([], result.errors)

    def test_unknown_property_is_rejected(self) -> None:
        data = fixture()
        data["unknown"] = True
        result = validate_memory(data, SCHEMA)
        self.assertTrue(any("unknown property" in error for error in result.errors))

    def test_duplicate_ids_are_rejected(self) -> None:
        data = fixture()
        data["records"][1]["id"] = data["records"][0]["id"]
        data["records"][1]["content_hash"] = record_hash(data["records"][1])
        result = validate_memory(data, SCHEMA)
        self.assertTrue(any("duplicate ID" in error for error in result.errors))

    def test_verified_record_requires_direct_evidence(self) -> None:
        data = fixture()
        record = data["records"][0]
        record["evidence"][0]["method"] = "inference"
        record["content_hash"] = record_hash(record)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("direct supporting evidence" in error for error in result.errors)
        )

    def test_unknown_relation_target_is_rejected(self) -> None:
        data = fixture()
        record = data["records"][1]
        record["relations"][0]["target_id"] = "rec_missing_target"
        record["content_hash"] = record_hash(record)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("unknown relation target" in error for error in result.errors)
        )

    def test_hash_mismatch_is_rejected(self) -> None:
        data = fixture()
        data["records"][0]["summary"] = "Changed without rehashing."
        result = validate_memory(data, SCHEMA)
        self.assertTrue(any("content_hash mismatch" in error for error in result.errors))

    def test_input_is_not_mutated(self) -> None:
        data = fixture()
        original = copy.deepcopy(data)
        validate_memory(data, SCHEMA)
        self.assertEqual(original, data)

    def test_completed_task_requires_direct_evidence(self) -> None:
        data = fixture()
        record = data["records"][1]
        record["status"] = "completed"
        record["content_hash"] = record_hash(record)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("direct completion evidence" in error for error in result.errors)
        )

    def test_line_locator_order_is_validated(self) -> None:
        data = fixture()
        evidence = data["records"][0]["evidence"][0]
        evidence["locator"] = {
            "kind": "lines",
            "start_line": 20,
            "end_line": 10,
        }
        data["records"][0]["content_hash"] = record_hash(data["records"][0])
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("end_line precedes start_line" in error for error in result.errors)
        )


if __name__ == "__main__":
    unittest.main()
