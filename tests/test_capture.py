from __future__ import annotations

import copy
import hashlib
import unittest
from typing import Any

from scripts.kiroku_core.capture import (
    CaptureSourceInput,
    capture_bundle_hash,
    capture_sources,
    source_content_hash,
)
from scripts.kiroku_core.schema import validate_capture_bundle_schema


NOW = "2026-06-08T13:00:00Z"
ACTOR = {
    "type": "agent",
    "name": "codex",
    "version": "1.0",
    "session_ref": "session-capture-tests",
}
SCOPE = {
    "description": "Selected sources for CAPTURE tests.",
    "included": ["contracts", "notes"],
}


def existing_source(
    *,
    source_id: str,
    uri: str,
    content: str,
    revision: str | None = None,
    captured_at: str = "2026-06-08T10:00:00Z",
) -> dict[str, Any]:
    result = {
        "id": source_id,
        "kind": "document",
        "title": source_id,
        "uri": uri,
        "integrity": "verified",
        "content_hash": source_content_hash(content),
        "captured_at": captured_at,
        "created_by": "cmp_initial",
    }
    if revision is not None:
        result["revision"] = revision
    return result


class SourceContentHashTest(unittest.TestCase):
    def test_source_content_hash_uses_raw_utf8_bytes(self) -> None:
        expected = hashlib.sha256("é".encode("utf-8")).hexdigest()
        self.assertEqual(source_content_hash("é"), f"sha256:{expected}")
        self.assertEqual(source_content_hash("é".encode("utf-8")), f"sha256:{expected}")


class CaptureSourcesTest(unittest.TestCase):
    def test_capture_classifies_sources_and_computes_hashes(self) -> None:
        existing = [
            existing_source(
                source_id="src_contract_old",
                uri="file:contracts.md",
                content="old contract",
                revision="v1",
                captured_at="2026-06-08T09:00:00Z",
            ),
            existing_source(
                source_id="src_contract_latest",
                uri="file:contracts.md",
                content="old contract",
                revision="v1",
                captured_at="2026-06-08T10:00:00Z",
            ),
            existing_source(
                source_id="src_notes",
                uri="file:notes.md",
                content="same notes",
            ),
        ]
        sources = [
            CaptureSourceInput(
                id="csrc_unchanged",
                kind="document",
                title="Notes",
                uri="file:notes.md",
                content="same notes",
                media_type="text/markdown",
            ),
            CaptureSourceInput(
                id="csrc_changed",
                kind="document",
                title="Contracts",
                uri="file:contracts.md",
                revision="v1",
                content="new contract",
                media_type="text/markdown",
            ),
            CaptureSourceInput(
                id="csrc_new",
                kind="document",
                title="Roadmap",
                uri="file:roadmap.md",
                content="new roadmap",
            ),
            CaptureSourceInput(
                id="csrc_unavailable",
                kind="document",
                title="Missing",
                uri="file:missing.md",
                unavailable_reason="The source could not be read.",
            ),
        ]

        result = capture_sources(
            capture_bundle_id="cap_capture_test",
            generated_at=NOW,
            actor=ACTOR,
            selection_scope=SCOPE,
            sources=sources,
            existing_sources=existing,
        )

        self.assertTrue(result.ok, result.to_dict())
        bundle = result.bundle
        assert bundle is not None
        self.assertEqual(validate_capture_bundle_schema(bundle).findings, ())
        self.assertEqual(bundle["artifact_hash"], capture_bundle_hash(bundle))

        by_id = {source["id"]: source for source in bundle["sources"]}
        self.assertEqual(by_id["csrc_unchanged"]["status"], "unchanged")
        self.assertEqual(by_id["csrc_unchanged"]["matched_source_id"], "src_notes")
        self.assertEqual(
            by_id["csrc_unchanged"]["content_hash"],
            source_content_hash("same notes"),
        )

        self.assertEqual(by_id["csrc_changed"]["status"], "changed")
        self.assertEqual(by_id["csrc_changed"]["previous_source_id"], "src_contract_latest")
        self.assertEqual(by_id["csrc_changed"]["material"]["mode"], "inline")

        self.assertEqual(by_id["csrc_new"]["status"], "new")
        self.assertNotIn("matched_source_id", by_id["csrc_new"])
        self.assertNotIn("previous_source_id", by_id["csrc_new"])

        self.assertEqual(by_id["csrc_unavailable"]["status"], "unavailable")
        self.assertEqual(by_id["csrc_unavailable"]["material"]["mode"], "unavailable")
        self.assertNotIn("content_hash", by_id["csrc_unavailable"])

    def test_reference_material_uses_supplied_content_hash(self) -> None:
        result = capture_sources(
            capture_bundle_id="cap_reference_test",
            generated_at=NOW,
            actor=ACTOR,
            selection_scope=SCOPE,
            sources=[
                {
                    "id": "csrc_reference",
                    "kind": "document",
                    "title": "Referenced source",
                    "uri": "file:reference.md",
                    "reference_uri": "file:reference.md",
                    "content_hash": "sha256:" + "a1" * 32,
                }
            ],
        )

        self.assertTrue(result.ok, result.to_dict())
        assert result.bundle is not None
        source = result.bundle["sources"][0]
        self.assertEqual(source["material"], {"mode": "reference", "uri": "file:reference.md"})
        self.assertEqual(source["content_hash"], "sha256:" + "a1" * 32)
        self.assertEqual(source["status"], "new")

    def test_capture_does_not_mutate_inputs(self) -> None:
        source = {
            "id": "csrc_mutation",
            "kind": "document",
            "title": "Mutable input",
            "uri": "file:mutable.md",
            "content": "content",
            "metadata": {"nested": {"value": 1}},
        }
        actor = copy.deepcopy(ACTOR)
        scope = copy.deepcopy(SCOPE)
        original_source = copy.deepcopy(source)
        original_actor = copy.deepcopy(actor)
        original_scope = copy.deepcopy(scope)

        result = capture_sources(
            capture_bundle_id="cap_non_mutating",
            generated_at=NOW,
            actor=actor,
            selection_scope=scope,
            sources=[source],
        )

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(source, original_source)
        self.assertEqual(actor, original_actor)
        self.assertEqual(scope, original_scope)

    def test_invalid_capture_returns_no_bundle(self) -> None:
        result = capture_sources(
            capture_bundle_id="cap_invalid",
            generated_at=NOW,
            actor=ACTOR,
            selection_scope=SCOPE,
            sources=[
                CaptureSourceInput(
                    id="not_a_captured_source_id",
                    kind="document",
                    title="Invalid ID",
                    uri="file:invalid.md",
                    content="content",
                )
            ],
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.bundle)
        self.assertEqual({finding.code for finding in result.findings}, {"SCHEMA_VIOLATION"})

    def test_reference_without_hash_returns_no_bundle(self) -> None:
        result = capture_sources(
            capture_bundle_id="cap_missing_hash",
            generated_at=NOW,
            actor=ACTOR,
            selection_scope=SCOPE,
            sources=[
                CaptureSourceInput(
                    id="csrc_missing_hash",
                    kind="document",
                    title="Missing hash",
                    uri="file:missing-hash.md",
                    reference_uri="file:missing-hash.md",
                )
            ],
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.bundle)
        self.assertEqual({finding.code for finding in result.findings}, {"SCHEMA_VIOLATION"})


if __name__ == "__main__":
    unittest.main()
