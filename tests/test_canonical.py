from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path
from typing import Any

from scripts.kiroku_core.canonical import (
    CanonicalizationError,
    canonical_bytes,
    canonical_dumps,
    canonicalize_memory,
    is_canonical_memory,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"


def load_fixture(relative_path: str) -> dict[str, Any]:
    return json.loads(
        (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
    )


class CanonicalSerializationTest(unittest.TestCase):
    def test_canonical_dumps_sorts_keys_and_uses_compact_unicode_json(self) -> None:
        value = {"z": 1, "nested": {"b": "✓", "a": "é"}}
        self.assertEqual(
            canonical_dumps(value),
            '{"nested":{"a":"é","b":"✓"},"z":1}',
        )
        self.assertEqual(
            canonical_bytes(value),
            '{"nested":{"a":"é","b":"✓"},"z":1}'.encode("utf-8"),
        )

    def test_canonical_dumps_rejects_non_json_values(self) -> None:
        for value in (
            {"value": math.nan},
            {"value": math.inf},
            {"value": ("tuple",)},
            {1: "non-string key"},
        ):
            with self.subTest(value=value):
                with self.assertRaises(CanonicalizationError):
                    canonical_dumps(value)


class CanonicalMemoryOrderingTest(unittest.TestCase):
    def test_valid_fixture_is_already_canonical_and_idempotent(self) -> None:
        memory = load_fixture("valid/all-record-kinds.json")
        normalized = canonicalize_memory(memory)
        self.assertEqual(normalized, memory)
        self.assertEqual(canonicalize_memory(normalized), normalized)
        self.assertTrue(is_canonical_memory(memory))

    def test_canonicalization_does_not_mutate_input(self) -> None:
        memory = load_fixture("valid/all-record-kinds.json")
        memory["records"].reverse()
        original = copy.deepcopy(memory)
        normalized = canonicalize_memory(memory)

        self.assertEqual(memory, original)
        self.assertNotEqual(normalized["records"], memory["records"])
        self.assertFalse(is_canonical_memory(memory))
        self.assertTrue(is_canonical_memory(normalized))

    def test_canonicalization_orders_only_contract_defined_sets(self) -> None:
        memory = load_fixture("valid/minimal.json")
        base = memory["records"][0]
        base["scope"] = ["viewer", "project"]
        base["tags"] = ["zeta", "alpha"]
        base["content"]["implications"] = ["second", "first"]
        base["evidence"] = [
            {
                "source_id": "src_contract",
                "relation": "supports",
                "method": "tool_result",
                "locator": {"kind": "section", "name": "B"},
                "observed_at": "2026-06-08T10:00:00Z",
            },
            {
                "source_id": "src_contract",
                "relation": "supports",
                "method": "document_read",
                "locator": {"kind": "section", "name": "A"},
                "observed_at": "2026-06-08T10:00:00Z",
            },
        ]
        normalized = canonicalize_memory(memory)
        record = normalized["records"][0]

        self.assertEqual(record["scope"], ["project", "viewer"])
        self.assertEqual(record["tags"], ["alpha", "zeta"])
        self.assertEqual(record["content"]["implications"], ["second", "first"])
        self.assertEqual(
            [item["method"] for item in record["evidence"]],
            ["document_read", "tool_result"],
        )

    def test_canonicalization_orders_relations_and_locator_ties(self) -> None:
        memory = load_fixture("valid/minimal.json")
        record = memory["records"][0]
        record["relations"] = [
            {"type": "related_to", "target_id": "rec_z"},
            {"type": "depends_on", "target_id": "rec_z"},
            {"type": "depends_on", "target_id": "rec_a"},
        ]
        record["evidence"] = [
            {
                "source_id": "src_contract",
                "relation": "supports",
                "method": "document_read",
                "locator": {"kind": "section", "name": "Z"},
                "observed_at": "2026-06-08T10:00:00Z",
            },
            {
                "source_id": "src_contract",
                "relation": "supports",
                "method": "document_read",
                "locator": {"kind": "section", "name": "A"},
                "observed_at": "2026-06-08T10:00:00Z",
            },
        ]
        normalized = canonicalize_memory(memory)
        record = normalized["records"][0]

        self.assertEqual(
            [(item["type"], item["target_id"]) for item in record["relations"]],
            [
                ("depends_on", "rec_a"),
                ("depends_on", "rec_z"),
                ("related_to", "rec_z"),
            ],
        )
        self.assertEqual(
            [item["locator"]["name"] for item in record["evidence"]],
            ["A", "Z"],
        )

    def test_canonicalization_orders_root_arrays(self) -> None:
        memory = load_fixture("valid/supersession-history.json")
        memory["records"].reverse()
        memory["compilations"].reverse()
        memory["sources"].append(
            {
                **copy.deepcopy(memory["sources"][0]),
                "id": "src_alpha",
            }
        )
        normalized = canonicalize_memory(memory)

        self.assertEqual(
            [item["id"] for item in normalized["sources"]],
            ["src_alpha", "src_contract"],
        )
        self.assertEqual(
            [item["id"] for item in normalized["records"]],
            ["rec_storage_v1", "rec_storage_v2"],
        )
        self.assertEqual(
            [item["result_revision"] for item in normalized["compilations"]],
            [1, 2],
        )

    def test_noncanonical_fixture_is_normalized_without_semantic_changes(self) -> None:
        memory = load_fixture("invalid/integrity/noncanonical-record-order.json")
        normalized = canonicalize_memory(memory)

        self.assertFalse(is_canonical_memory(memory))
        self.assertTrue(is_canonical_memory(normalized))
        self.assertCountEqual(memory["records"], normalized["records"])


if __name__ == "__main__":
    unittest.main()
