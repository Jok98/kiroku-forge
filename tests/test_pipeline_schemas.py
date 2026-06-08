from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Callable

import fastjsonschema

from scripts.kiroku_core.hashing import sha256_hash


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "pipeline"
PIPELINE = json.loads(
    (SCHEMA_ROOT / "pipeline-v1.schema.json").read_text(encoding="utf-8")
)
SCHEMAS = {
    value["$id"]: value
    for path in SCHEMA_ROOT.glob("*.schema.json")
    for value in [json.loads(path.read_text(encoding="utf-8"))]
}
MANIFEST = json.loads(
    (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
)
HASH = "sha256:" + "a1" * 32
NOW = "2026-06-08T12:00:00Z"


def load_schema(uri: str) -> dict[str, Any]:
    document_uri = uri.split("#", 1)[0]
    try:
        return SCHEMAS[document_uri]
    except KeyError as exc:
        raise ValueError(f"unexpected schema URI: {uri}") from exc


def compile_schema(schema: dict[str, Any]) -> Callable[[Any], Any]:
    return fastjsonschema.compile(
        schema,
        handlers={"http": load_schema, "https": load_schema},
        use_default=False,
    )


def definition_validator(name: str) -> Callable[[Any], Any]:
    return compile_schema(
        {
            "$schema": PIPELINE["$schema"],
            "$id": f"https://kiroku-forge.local/tests/{name}.schema.json",
            "$ref": f"{PIPELINE['$id']}#/$defs/{name}",
        }
    )


def load_fixture(relative_path: str) -> dict[str, Any]:
    return json.loads(
        (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
    )


class PipelineFixtureCorpusTest(unittest.TestCase):
    def test_fixture_corpus_matches_deterministic_builder(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tests" / "build_pipeline_fixtures.py"),
                "--check",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_lists_every_fixture_exactly_once(self) -> None:
        listed = {
            item["path"]
            for group in ("valid", "invalid")
            for item in MANIFEST[group]
        }
        actual = {
            str(path.relative_to(FIXTURE_ROOT))
            for path in FIXTURE_ROOT.rglob("*.json")
            if path.name != "manifest.json"
        }
        self.assertEqual(listed, actual)
        self.assertEqual(
            len(listed),
            len(MANIFEST["valid"]) + len(MANIFEST["invalid"]),
        )

    def test_valid_fixtures_pass_their_public_schema(self) -> None:
        for item in MANIFEST["valid"]:
            schema = json.loads(
                (ROOT / item["schema"]).read_text(encoding="utf-8")
            )
            with self.subTest(path=item["path"]):
                compile_schema(schema)(load_fixture(item["path"]))

    def test_invalid_fixtures_fail_their_public_schema(self) -> None:
        for item in MANIFEST["invalid"]:
            schema = json.loads(
                (ROOT / item["schema"]).read_text(encoding="utf-8")
            )
            with self.subTest(path=item["path"]):
                with self.assertRaises(
                    fastjsonschema.JsonSchemaException
                ):
                    compile_schema(schema)(load_fixture(item["path"]))

    def test_valid_fixture_artifact_hashes_match_content(self) -> None:
        for item in MANIFEST["valid"]:
            artifact = load_fixture(item["path"])
            expected = sha256_hash(
                {
                    key: value
                    for key, value in artifact.items()
                    if key != "artifact_hash"
                }
            )
            with self.subTest(path=item["path"]):
                self.assertEqual(artifact["artifact_hash"], expected)


class PipelineSchemaContractTest(unittest.TestCase):
    def test_public_schemas_have_stable_ids_and_shared_definitions(self) -> None:
        names = (
            "capture-bundle-v1",
            "candidate-bundle-v1",
            "change-set-v1",
            "audit-report-v1",
            "context-pack-v1",
        )
        for name in names:
            schema = json.loads(
                (SCHEMA_ROOT / f"{name}.schema.json").read_text(
                    encoding="utf-8"
                )
            )
            with self.subTest(name=name):
                self.assertEqual(
                    schema["$id"],
                    f"https://kiroku-forge.local/schemas/{name}.schema.json",
                )
                self.assertTrue(
                    schema["$ref"].startswith("pipeline-v1.schema.json#/$defs/")
                )
                compile_schema(schema)

    def test_candidate_contract_accepts_every_canonical_kind_and_state(self) -> None:
        validate = definition_validator("candidate")
        memories = [
            json.loads(
                (
                    ROOT
                    / "tests"
                    / "fixtures"
                    / "memory"
                    / "valid"
                    / name
                ).read_text(encoding="utf-8")
            )
            for name in ("all-record-kinds.json", "lifecycle-states.json")
        ]
        for memory in memories:
            for record in memory["records"]:
                candidate = {
                    "id": f"can_{record['id'].removeprefix('rec_')}",
                    "proposed_key": record["key"],
                    "kind": record["kind"],
                    "proposed_state": record["state"],
                    "title": record["title"],
                    "summary": record["summary"],
                    "scope": record["scope"],
                    "tags": record["tags"],
                    "content": record["content"],
                    "evidence": [
                        {
                            "captured_source_id": "csrc_contract",
                            "relation": evidence["relation"],
                            "method": evidence["method"],
                            "locator": evidence["locator"],
                            "observed_at": evidence["observed_at"],
                        }
                        for evidence in record["evidence"]
                    ]
                    or [
                        {
                            "captured_source_id": "csrc_contract",
                            "relation": "contextualizes",
                            "method": "document_read",
                            "locator": {"kind": "whole_source"},
                            "observed_at": NOW,
                        }
                    ],
                    "classification_rationale": "Fixture conversion.",
                    "classification_confidence": "high",
                }
                with self.subTest(
                    kind=record["kind"],
                    state=record["state"],
                ):
                    validate(candidate)

    def test_capture_status_controls_material_and_source_links(self) -> None:
        validate = definition_validator("capturedSource")
        base = load_fixture("valid/capture-bundle.json")["sources"][0]

        unavailable = copy.deepcopy(base)
        unavailable["status"] = "unavailable"
        unavailable["material"] = {
            "mode": "unavailable",
            "reason": "Source could not be read.",
        }
        del unavailable["content_hash"]
        validate(unavailable)

        unchanged = copy.deepcopy(base)
        unchanged["status"] = "unchanged"
        unchanged["matched_source_id"] = "src_contract"
        validate(unchanged)

        changed = copy.deepcopy(base)
        changed["status"] = "changed"
        changed["previous_source_id"] = "src_contract"
        validate(changed)

        for invalid in (
            {**copy.deepcopy(unchanged), "matched_source_id": None},
            {**copy.deepcopy(changed), "previous_source_id": None},
        ):
            with self.assertRaises(fastjsonschema.JsonSchemaException):
                validate(invalid)

    def test_all_change_set_operation_payloads_are_discriminated(self) -> None:
        validate = definition_validator("operation")
        change_set = load_fixture("valid/change-set.json")
        initialize, add_source, create_record = change_set["operations"]
        record = create_record["record"]
        evidence = record["evidence"][0]
        relation = {"type": "related_to", "target_id": "rec_other"}

        cases = [
            initialize,
            {
                "operation_id": "op_project",
                "operation_type": "update_project",
                "changes": {"goal": "Updated goal."},
            },
            add_source,
            create_record,
            {
                "operation_id": "op_amend",
                "operation_type": "amend_record",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "changes": {"summary": "Updated summary."},
            },
            {
                "operation_id": "op_add_evidence",
                "operation_type": "add_evidence",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "evidence": evidence,
            },
            {
                "operation_id": "op_remove_evidence",
                "operation_type": "remove_evidence",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "evidence": evidence,
            },
            {
                "operation_id": "op_verify",
                "operation_type": "set_verification",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "verification": {"status": "verified"},
            },
            {
                "operation_id": "op_add_relation",
                "operation_type": "add_relation",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "relation": relation,
            },
            {
                "operation_id": "op_remove_relation",
                "operation_type": "remove_relation",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "relation": relation,
            },
            {
                "operation_id": "op_transition",
                "operation_type": "transition_record",
                "record_id": record["id"],
                "expected_record_hash": HASH,
                "target_state": "obsolete",
                "transition_reason": "The fact is no longer current.",
                "content_changes": {},
            },
            {
                "operation_id": "op_supersede",
                "operation_type": "supersede_record",
                "predecessor_id": record["id"],
                "expected_record_hash": HASH,
                "successor": {
                    **copy.deepcopy(record),
                    "id": "rec_pipeline_contract_v2",
                },
                "reason": "Replace the semantic claim.",
            },
        ]

        for operation in cases:
            with self.subTest(operation=operation["operation_type"]):
                validate(operation)

        invalid = copy.deepcopy(cases[4])
        invalid["changes"]["content"] = {"statement": "Semantic change."}
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            validate(invalid)

    def test_initialization_contract_declares_first_operation_constraint(self) -> None:
        operations = PIPELINE["$defs"]["changeSet"]["allOf"][0]["then"][
            "properties"
        ]["operations"]
        self.assertEqual(
            operations["prefixItems"][0]["$ref"],
            "#/$defs/initializeMemoryOperation",
        )

    def test_conflict_resolution_requires_a_finding(self) -> None:
        validate = definition_validator("candidateResolution")
        resolution = {
            "candidate_id": "can_conflict",
            "resolution": "conflict",
            "rationale": "Direct evidence disagrees.",
            "record_ids": ["rec_existing"],
            "operation_ids": [],
            "finding_ids": [],
        }
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            validate(resolution)
        resolution["finding_ids"] = ["fnd_conflict"]
        validate(resolution)

    def test_context_sections_reject_records_in_the_wrong_view(self) -> None:
        validate = definition_validator("contextPack")
        context = load_fixture("valid/context-pack.json")
        context["sections"]["todo"] = copy.deepcopy(
            context["sections"]["facts_and_assumptions"]
        )
        with self.assertRaises(fastjsonschema.JsonSchemaException):
            validate(context)


if __name__ == "__main__":
    unittest.main()
