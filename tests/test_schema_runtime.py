from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.kiroku_core.schema import (
    SCHEMA_VIOLATION,
    SchemaContractError,
    compile_memory_schema,
    validate_memory_schema,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"
MANIFEST = json.loads(
    (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
)


def load_fixture(relative_path: str) -> dict:
    return json.loads(
        (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
    )


class RuntimeSchemaValidationTest(unittest.TestCase):
    def test_valid_and_integrity_invalid_fixtures_pass_shape_validation(self) -> None:
        cases = list(MANIFEST["valid"]) + [
            item
            for item in MANIFEST["invalid"]
            if item["layer"] == "integrity"
        ]
        for item in cases:
            with self.subTest(path=item["path"]):
                result = validate_memory_schema(load_fixture(item["path"]))
                self.assertTrue(result.ok, result.to_dict())
                self.assertEqual(result.findings, ())

    def test_schema_invalid_fixtures_return_stable_findings(self) -> None:
        cases = [
            item
            for item in MANIFEST["invalid"]
            if item["layer"] == "schema"
        ]
        for item in cases:
            memory = load_fixture(item["path"])
            with self.subTest(path=item["path"]):
                result = validate_memory_schema(memory)
                self.assertFalse(result.ok)
                self.assertEqual(len(result.findings), 1)
                finding = result.findings[0]
                self.assertEqual(finding.code, SCHEMA_VIOLATION)
                self.assertEqual(finding.severity, "error")
                self.assertTrue(finding.path.startswith("$"))
                self.assertTrue(finding.message.startswith(finding.path))

    def test_schema_validation_is_deterministic_and_does_not_mutate(self) -> None:
        memory = load_fixture("invalid/schema/wrong-kind-state.json")
        original = copy.deepcopy(memory)

        first = validate_memory_schema(memory)
        second = validate_memory_schema(memory)

        self.assertEqual(first, second)
        self.assertEqual(memory, original)
        self.assertEqual(first.findings[0].path, "$.records[0].state")
        self.assertEqual(first.findings[0].entity_ids, ("rec_fact",))

    def test_root_violation_identifies_the_memory(self) -> None:
        memory = load_fixture("invalid/schema/extra-root-property.json")
        finding = validate_memory_schema(memory).findings[0]
        self.assertEqual(finding.path, "$")
        self.assertEqual(finding.entity_ids, ("mem_fixture",))
        self.assertIn('["unexpected"]', finding.message)

    def test_default_schema_resolution_does_not_use_network(self) -> None:
        memory = load_fixture("valid/minimal.json")
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=AssertionError("network access attempted"),
        ):
            validator = compile_memory_schema()
            self.assertTrue(
                validate_memory_schema(memory, validator=validator).ok
            )

    def test_non_local_schema_reference_is_rejected_before_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common_path = root / "common.json"
            memory_path = root / "memory.json"
            common_path.write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "https://kiroku-forge.local/test/common.json",
                        "type": "object",
                    }
                ),
                encoding="utf-8",
            )
            memory_path.write_text(
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "$id": "https://kiroku-forge.local/test/memory.json",
                        "$ref": "https://example.invalid/remote.json",
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("network access attempted"),
            ):
                with self.assertRaisesRegex(
                    SchemaContractError,
                    "non-local document",
                ):
                    compile_memory_schema(memory_path, common_path)


if __name__ == "__main__":
    unittest.main()
