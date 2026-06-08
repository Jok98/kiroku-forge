from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.kiroku_core.hashing import (
    receipt_hash,
    record_hash,
    sha256_hash,
    state_hash,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"


def load_fixture(relative_path: str) -> dict[str, Any]:
    return json.loads(
        (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
    )


class CanonicalHashingTest(unittest.TestCase):
    def test_sha256_hash_matches_known_canonical_vector(self) -> None:
        self.assertEqual(
            sha256_hash({"b": "é", "a": 1}),
            "sha256:09ad9fd2fb648cb2f62141215828ea00"
            "a62c299db05d20aa9ade2f527a301cc6",
        )

    def test_record_hash_normalizes_set_like_arrays_without_mutating(self) -> None:
        memory = load_fixture("valid/minimal.json")
        record = memory["records"][0]
        expected = record["content_hash"]
        candidate = copy.deepcopy(record)
        candidate["scope"] = ["viewer", "project"]
        candidate["tags"] = ["zeta", "alpha"]
        candidate["evidence"] = list(reversed(candidate["evidence"]))
        original = copy.deepcopy(candidate)

        first = record_hash(candidate)
        candidate["scope"].reverse()
        candidate["tags"].reverse()
        second = record_hash(candidate)

        self.assertEqual(first, second)
        self.assertNotEqual(first, expected)
        self.assertEqual(original["scope"], ["viewer", "project"])

    def test_record_hash_ignores_only_stored_content_hash(self) -> None:
        record = load_fixture("valid/minimal.json")["records"][0]
        expected = record_hash(record)

        changed_stored_hash = copy.deepcopy(record)
        changed_stored_hash["content_hash"] = "sha256:" + "f0" * 32
        self.assertEqual(record_hash(changed_stored_hash), expected)

        changed_content = copy.deepcopy(record)
        changed_content["summary"] = "Changed semantic content."
        self.assertNotEqual(record_hash(changed_content), expected)

    def test_state_hash_matches_fixtures_and_excludes_receipts(self) -> None:
        memory = load_fixture("valid/supersession-history.json")
        self.assertEqual(state_hash(memory), memory["state_hash"])

        changed_receipts = copy.deepcopy(memory)
        changed_receipts["compilations"][0]["warnings"] = ["Non-semantic warning"]
        self.assertEqual(state_hash(changed_receipts), memory["state_hash"])

        changed_revision = copy.deepcopy(memory)
        changed_revision["revision"] += 1
        self.assertNotEqual(state_hash(changed_revision), memory["state_hash"])

    def test_receipt_hash_matches_fixture_and_ignores_stored_hash(self) -> None:
        receipt = load_fixture("valid/supersession-history.json")["compilations"][1]
        expected = receipt["receipt_hash"]
        self.assertEqual(receipt_hash(receipt), expected)

        changed_stored_hash = copy.deepcopy(receipt)
        changed_stored_hash["receipt_hash"] = "sha256:" + "f0" * 32
        self.assertEqual(receipt_hash(changed_stored_hash), expected)

        changed_warning = copy.deepcopy(receipt)
        changed_warning["warnings"] = ["Changed receipt content"]
        self.assertNotEqual(receipt_hash(changed_warning), expected)

    def test_hashing_does_not_mutate_memory_or_record(self) -> None:
        memory = load_fixture("valid/all-record-kinds.json")
        original = copy.deepcopy(memory)
        record_hash(memory["records"][0])
        state_hash(memory)
        receipt_hash(memory["compilations"][0])
        self.assertEqual(memory, original)


if __name__ == "__main__":
    unittest.main()
