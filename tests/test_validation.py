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

    def test_duplicate_record_keys_are_rejected(self) -> None:
        data = fixture()
        data["records"][1]["key"] = data["records"][0]["key"]
        data["records"][1]["content_hash"] = record_hash(data["records"][1])
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("duplicate record key" in error for error in result.errors)
        )

    def test_evidence_source_must_be_a_run_input(self) -> None:
        data = fixture()
        source = copy.deepcopy(data["sources"][0])
        source["id"] = "src_unlisted_input"
        source["uri"] = "conversation://example/message-2"
        data["sources"].append(source)
        record = data["records"][0]
        record["evidence"][0]["source_id"] = source["id"]
        record["content_hash"] = record_hash(record)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("is not an input of run" in error for error in result.errors)
        )

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

    def test_running_run_rejects_completion_fields(self) -> None:
        data = fixture()
        run = data["runs"][0]
        run["status"] = "running"
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("running run cannot have completed_at" in error for error in result.errors)
        )
        self.assertTrue(
            any("running run cannot have summary" in error for error in result.errors)
        )

    def test_completed_run_requires_completion_fields(self) -> None:
        data = fixture()
        run = data["runs"][0]
        run["completed_at"] = None
        run["summary"] = None
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("completed run requires completed_at" in error for error in result.errors)
        )
        self.assertTrue(
            any("completed run requires summary" in error for error in result.errors)
        )

    def test_multiple_running_runs_are_rejected(self) -> None:
        data = fixture()
        first = data["runs"][0]
        first["status"] = "running"
        first["completed_at"] = None
        first["summary"] = None
        second = copy.deepcopy(first)
        second["id"] = "run_second"
        data["runs"].append(second)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("multiple running runs" in error for error in result.errors)
        )

    def test_superseded_record_requires_replacement(self) -> None:
        data = fixture()
        record = data["records"][0]
        record["status"] = "superseded"
        record["content_hash"] = record_hash(record)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("requires one direct replacement" in error for error in result.errors)
        )

    def test_supersedes_relation_requires_target_status(self) -> None:
        data = fixture()
        replacement = data["records"][1]
        replacement["relations"].append(
            {
                "type": "supersedes",
                "target_id": data["records"][0]["id"],
            }
        )
        replacement["content_hash"] = record_hash(replacement)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any(
                "supersedes relation requires superseded status" in error
                for error in result.errors
            )
        )

    def test_multiple_direct_replacements_are_rejected(self) -> None:
        data = fixture()
        target = data["records"][0]
        target["status"] = "superseded"
        target["content_hash"] = record_hash(target)
        for replacement in data["records"][1:]:
            replacement["relations"].append(
                {
                    "type": "supersedes",
                    "target_id": target["id"],
                }
            )
            replacement["content_hash"] = record_hash(replacement)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("multiple direct replacements" in error for error in result.errors)
        )

    def test_replacement_cannot_supersede_multiple_predecessors(self) -> None:
        data = fixture()
        first, second, replacement = data["records"]
        first["status"] = "superseded"
        second["status"] = "superseded"
        replacement["relations"].extend(
            [
                {"type": "supersedes", "target_id": first["id"]},
                {"type": "supersedes", "target_id": second["id"]},
            ]
        )
        for record in data["records"]:
            record["content_hash"] = record_hash(record)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any(
                "supersedes multiple direct predecessors" in error
                for error in result.errors
            )
        )

    def test_supersession_cycles_are_rejected(self) -> None:
        data = fixture()
        first, second = data["records"][:2]
        first["status"] = "superseded"
        second["status"] = "superseded"
        first["relations"].append(
            {"type": "supersedes", "target_id": second["id"]}
        )
        second["relations"].append(
            {"type": "supersedes", "target_id": first["id"]}
        )
        first["content_hash"] = record_hash(first)
        second["content_hash"] = record_hash(second)
        result = validate_memory(data, SCHEMA)
        self.assertTrue(
            any("supersession cycle detected" in error for error in result.errors)
        )


if __name__ == "__main__":
    unittest.main()
