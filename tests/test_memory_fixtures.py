from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

import fastjsonschema

from scripts.kiroku_core.hashing import receipt_hash, record_hash, state_hash


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "memory"
COMMON = json.loads(
    (ROOT / "schemas" / "common-v1.schema.json").read_text(encoding="utf-8")
)
MEMORY = json.loads(
    (ROOT / "schemas" / "memory-v3.schema.json").read_text(encoding="utf-8")
)
MANIFEST = json.loads(
    (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
)
CONTRACT = (ROOT / "references" / "contracts-v3.md").read_text(encoding="utf-8")


def load_schema(uri: str) -> dict[str, Any]:
    if uri == COMMON["$id"]:
        return COMMON
    raise ValueError(f"unexpected schema URI: {uri}")


VALIDATE = fastjsonschema.compile(MEMORY, handlers={"https": load_schema})


class MemoryFixtureCorpusTest(unittest.TestCase):
    def load_fixture(self, relative_path: str) -> dict[str, Any]:
        return json.loads(
            (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
        )

    def test_fixture_corpus_matches_deterministic_builder(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tests" / "build_memory_fixtures.py"),
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

    def test_valid_fixtures_pass_memory_schema(self) -> None:
        for item in MANIFEST["valid"]:
            with self.subTest(path=item["path"]):
                VALIDATE(self.load_fixture(item["path"]))

    def test_valid_fixture_hashes_match_canonical_content(self) -> None:
        for item in MANIFEST["valid"]:
            memory = self.load_fixture(item["path"])
            for record in memory["records"]:
                with self.subTest(
                    path=item["path"],
                    component="record",
                    record=record["id"],
                ):
                    self.assertEqual(
                        record["content_hash"],
                        record_hash(record),
                    )

            with self.subTest(path=item["path"], component="state"):
                self.assertEqual(memory["state_hash"], state_hash(memory))

            previous_hash = None
            for receipt in memory["compilations"]:
                with self.subTest(
                    path=item["path"],
                    component="receipt",
                    receipt=receipt["id"],
                ):
                    self.assertEqual(receipt["previous_receipt_hash"], previous_hash)
                    self.assertEqual(
                        receipt["receipt_hash"],
                        receipt_hash(receipt),
                    )
                previous_hash = receipt["receipt_hash"]

    def test_schema_invalid_fixtures_fail_memory_schema(self) -> None:
        cases = [
            item for item in MANIFEST["invalid"] if item["layer"] == "schema"
        ]
        self.assertTrue(cases)
        for item in cases:
            with self.subTest(path=item["path"], invariant=item["invariant"]):
                with self.assertRaises(fastjsonschema.JsonSchemaException):
                    VALIDATE(self.load_fixture(item["path"]))

    def test_integrity_invalid_fixtures_pass_memory_schema(self) -> None:
        cases = [
            item for item in MANIFEST["invalid"] if item["layer"] == "integrity"
        ]
        self.assertTrue(cases)
        for item in cases:
            with self.subTest(path=item["path"], code=item["code"]):
                VALIDATE(self.load_fixture(item["path"]))

    def test_integrity_fixture_codes_use_stable_registry_shape(self) -> None:
        cases = [
            item for item in MANIFEST["invalid"] if item["layer"] == "integrity"
        ]
        registered_codes = set(
            re.findall(r"^\| `([A-Z][A-Z0-9_]+)` \|", CONTRACT, re.MULTILINE)
        )
        for item in cases:
            with self.subTest(path=item["path"]):
                self.assertRegex(item["code"], r"^[A-Z][A-Z0-9_]+$")
                self.assertIn(item["code"], registered_codes)
                self.assertTrue(item["invariant"].strip())


if __name__ == "__main__":
    unittest.main()
