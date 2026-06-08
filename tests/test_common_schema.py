from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Callable

import fastjsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "common-v1.schema.json"
COMMON = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validator(definition: str) -> Callable[[Any], Any]:
    schema = {
        "$schema": COMMON["$schema"],
        "$defs": COMMON["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    return fastjsonschema.compile(schema)


class CommonSchemaTest(unittest.TestCase):
    def assert_valid(self, definition: str, value: Any) -> None:
        validator(definition)(value)

    def assert_invalid(self, definition: str, value: Any) -> None:
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            validator(definition)(value)

    def test_schema_declares_draft_2020_12_and_stable_id(self) -> None:
        self.assertEqual(
            COMMON["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertEqual(
            COMMON["$id"],
            "https://kiroku-forge.local/schemas/common-v1.schema.json",
        )

    def test_sha256_accepts_only_lowercase_canonical_form(self) -> None:
        self.assert_valid("sha256", "sha256:" + "a1" * 32)
        self.assert_invalid("sha256", "a1" * 32)
        self.assert_invalid("sha256", "sha256:" + "A1" * 32)
        self.assert_invalid("sha256", "sha256:" + "a1" * 31)

    def test_finding_code_uses_stable_machine_readable_form(self) -> None:
        self.assert_valid("findingCode", "STALE_CHANGESET")
        self.assert_invalid("findingCode", "stale_changeset")
        self.assert_invalid("findingCode", "STALE-CHANGESET")

    def test_timestamp_requires_utc_z_form(self) -> None:
        self.assert_valid("utcTimestamp", "2026-06-08T12:34:56Z")
        self.assert_valid("utcTimestamp", "2026-06-08T12:34:56.123Z")
        self.assert_invalid("utcTimestamp", "2026-06-08T12:34:56+02:00")
        self.assert_invalid("utcTimestamp", "2026-06-08 12:34:56Z")

    def test_all_id_contracts_enforce_their_prefix(self) -> None:
        values = {
            "memoryId": "mem_alpha",
            "sourceId": "src_alpha",
            "recordId": "rec_alpha",
            "compilationId": "cmp_alpha",
            "captureBundleId": "cap_alpha",
            "candidateBundleId": "cnd_alpha",
            "changeSetId": "chg_alpha",
            "auditReportId": "aud_alpha",
            "contextPackId": "ctx_alpha",
            "capturedSourceId": "csrc_alpha",
            "candidateId": "can_alpha",
            "operationId": "op_alpha",
            "findingId": "fnd_alpha",
        }
        for definition, value in values.items():
            with self.subTest(definition=definition):
                self.assert_valid(definition, value)
                self.assert_invalid(definition, "wrong_alpha")
                self.assert_invalid(definition, value.upper())

    def test_artifact_id_excludes_nested_entity_ids(self) -> None:
        for value in (
            "mem_alpha",
            "cap_alpha",
            "cnd_alpha",
            "chg_alpha",
            "aud_alpha",
            "ctx_alpha",
        ):
            with self.subTest(value=value):
                self.assert_valid("artifactId", value)
        self.assert_invalid("artifactId", "rec_alpha")
        self.assert_invalid("artifactId", "op_alpha")

    def test_actor_is_closed_and_requires_type_and_name(self) -> None:
        self.assert_valid(
            "actor",
            {
                "type": "agent",
                "name": "codex",
                "version": "1.0",
                "session_ref": "session-123",
            },
        )
        self.assert_invalid("actor", {"type": "agent"})
        self.assert_invalid("actor", {"type": "service", "name": "compiler"})
        self.assert_invalid(
            "actor",
            {"type": "tool", "name": "compiler", "unexpected": True},
        )

    def test_locator_variants_are_discriminated_and_closed(self) -> None:
        valid_locators = [
            {"kind": "whole_source"},
            {"kind": "lines", "start_line": 10, "end_line": 20},
            {"kind": "section", "name": "Architecture"},
            {"kind": "message", "message_id": "msg-12"},
            {"kind": "page", "start_page": 1, "end_page": 3},
            {"kind": "selector", "expression": "#main > article"},
            {"kind": "custom", "namespace": "cell", "value": "B12"},
        ]
        for locator in valid_locators:
            with self.subTest(locator=locator):
                self.assert_valid("locator", locator)

        invalid_locators = [
            {"kind": "lines", "start_line": 0, "end_line": 1},
            {"kind": "lines", "start_line": 1},
            {"kind": "section", "name": " "},
            {"kind": "page", "start_page": 1, "end_page": 2, "name": "extra"},
            {"kind": "custom", "namespace": "Cell Value", "value": "B12"},
            {"kind": "unknown"},
        ]
        for locator in invalid_locators:
            with self.subTest(locator=locator):
                self.assert_invalid("locator", locator)

    def test_cross_field_range_order_remains_an_integrity_rule(self) -> None:
        self.assert_valid(
            "locator",
            {"kind": "lines", "start_line": 20, "end_line": 10},
        )
        self.assert_valid(
            "locator",
            {"kind": "page", "start_page": 4, "end_page": 2},
        )


if __name__ == "__main__":
    unittest.main()
