from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.kiroku_core.capture import CaptureSourceInput, capture_sources
from scripts.kiroku_core.change_set import validate_change_set
from scripts.kiroku_core.reconcile import (
    candidate_bundle_hash,
    change_set_hash,
    reconcile_candidates,
)


ROOT = Path(__file__).resolve().parents[1]
MEMORY_ROOT = ROOT / "tests" / "fixtures" / "memory"
NOW = "2026-06-08T14:00:00Z"
ACTOR = {
    "type": "agent",
    "name": "codex",
    "version": "1.0",
    "session_ref": "session-reconcile-tests",
}
PROJECT = {
    "name": "KirokuForge",
    "description": "Durable project-memory compiler.",
    "goal": "Preserve operational project knowledge.",
    "status": "active",
    "boundaries": {
        "included": ["Project memory"],
        "excluded": ["Generated viewer UI"],
    },
}


def load_memory(relative_path: str) -> dict[str, Any]:
    return json.loads((MEMORY_ROOT / relative_path).read_text(encoding="utf-8"))


def artifact_hash(value: dict[str, Any]) -> str:
    from scripts.kiroku_core.hashing import sha256_hash

    return sha256_hash(
        {key: item for key, item in value.items() if key != "artifact_hash"}
    )


def make_capture(
    sources: list[CaptureSourceInput | dict[str, Any]],
    *,
    capture_bundle_id: str = "cap_reconcile",
    existing_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = capture_sources(
        capture_bundle_id=capture_bundle_id,
        generated_at=NOW,
        actor=ACTOR,
        selection_scope={"description": "Reconcile test sources."},
        sources=sources,
        existing_sources=existing_sources or [],
    )
    assert result.bundle is not None, result.to_dict()
    return result.bundle


def candidate(
    candidate_id: str,
    key: str,
    content: dict[str, Any],
    captured_source_id: str,
    *,
    title: str = "Reconciled fact",
    summary: str = "Candidate fact produced by tests.",
) -> dict[str, Any]:
    return {
        "id": candidate_id,
        "proposed_key": key,
        "kind": "fact",
        "proposed_state": "active",
        "title": title,
        "summary": summary,
        "scope": ["project"],
        "tags": ["reconcile"],
        "content": content,
        "evidence": [
            {
                "captured_source_id": captured_source_id,
                "relation": "supports",
                "method": "document_read",
                "locator": {"kind": "section", "name": "Reconcile"},
                "observed_at": NOW,
            }
        ],
        "classification_rationale": "The test source directly states the fact.",
        "classification_confidence": "high",
    }


def make_candidate_bundle(
    capture: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    candidate_bundle_id: str = "cnd_reconcile",
) -> dict[str, Any]:
    bundle = {
        "artifact_type": "candidate_bundle",
        "schema_version": "1.0.0",
        "candidate_bundle_id": candidate_bundle_id,
        "artifact_hash": "sha256:" + "0" * 64,
        "generated_at": NOW,
        "actor": ACTOR,
        "capture_bundle": {
            "artifact_type": "capture_bundle",
            "artifact_id": capture["capture_bundle_id"],
            "artifact_hash": capture["artifact_hash"],
        },
        "candidates": candidates,
    }
    bundle["artifact_hash"] = candidate_bundle_hash(bundle)
    return bundle


class ReconcileInitializationTest(unittest.TestCase):
    def test_initial_reconciliation_produces_valid_change_set(self) -> None:
        capture = make_capture(
            [
                CaptureSourceInput(
                    id="csrc_contract",
                    kind="document",
                    title="Contract",
                    uri="file:contract.md",
                    content="Pipeline stages exchange structured artifacts.",
                )
            ]
        )
        candidates = make_candidate_bundle(
            capture,
            [
                candidate(
                    "can_pipeline_contract",
                    "pipeline-contract",
                    {"statement": "Pipeline stages exchange structured artifacts."},
                    "csrc_contract",
                )
            ],
        )

        result = reconcile_candidates(
            change_set_id="chg_reconcile_initial",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=None,
            memory_id="mem_reconcile",
            project=PROJECT,
        )

        self.assertTrue(result.ok, result.to_dict())
        self.assertFalse(result.no_change)
        change_set = result.change_set
        assert change_set is not None
        self.assertEqual(change_set["artifact_hash"], change_set_hash(change_set))
        self.assertEqual(validate_change_set(change_set, None).findings, ())
        self.assertEqual(
            [operation["operation_type"] for operation in change_set["operations"]],
            ["initialize_memory", "add_source", "create_record"],
        )
        self.assertEqual(change_set["source_resolutions"][0]["resolution"], "add")
        self.assertEqual(change_set["candidate_resolutions"][0]["resolution"], "create")
        record = change_set["operations"][2]["record"]
        self.assertEqual(record["id"], "rec_pipeline_contract")
        self.assertEqual(record["evidence"][0]["source_id"], "src_contract")

    def test_reconciliation_does_not_mutate_inputs(self) -> None:
        capture = make_capture(
            [
                CaptureSourceInput(
                    id="csrc_source",
                    kind="document",
                    title="Source",
                    uri="file:source.md",
                    content="A durable fact.",
                )
            ]
        )
        candidates = make_candidate_bundle(
            capture,
            [candidate("can_source", "durable-fact", {"statement": "A durable fact."}, "csrc_source")],
        )
        original_capture = copy.deepcopy(capture)
        original_candidates = copy.deepcopy(candidates)

        result = reconcile_candidates(
            change_set_id="chg_reconcile_non_mutating",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=None,
            memory_id="mem_reconcile",
            project=PROJECT,
        )

        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(capture, original_capture)
        self.assertEqual(candidates, original_candidates)


class ReconcileExistingMemoryTest(unittest.TestCase):
    def test_already_represented_candidate_reports_no_change(self) -> None:
        memory = load_memory("valid/minimal.json")
        source = memory["sources"][0]
        record = memory["records"][0]
        capture = make_capture(
            [
                {
                    "id": "csrc_contract",
                    "kind": source["kind"],
                    "title": source["title"],
                    "uri": source["uri"],
                    "revision": source.get("revision"),
                    "reference_uri": source["uri"],
                    "content_hash": source["content_hash"],
                }
            ],
            existing_sources=memory["sources"],
        )
        candidates = make_candidate_bundle(
            capture,
            [
                candidate(
                    "can_existing_fact",
                    record["key"],
                    copy.deepcopy(record["content"]),
                    "csrc_contract",
                )
            ],
        )

        result = reconcile_candidates(
            change_set_id="chg_reconcile_no_change",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=memory,
        )

        self.assertTrue(result.ok, result.to_dict())
        self.assertTrue(result.no_change)
        self.assertIsNone(result.change_set)
        self.assertEqual(result.source_resolutions[0]["resolution"], "reuse")
        self.assertEqual(result.candidate_resolutions[0]["resolution"], "ignore")
        self.assertEqual(result.candidate_resolutions[0]["record_ids"], [record["id"]])

    def test_reuse_unchanged_source_for_new_candidate(self) -> None:
        memory = load_memory("valid/minimal.json")
        source = memory["sources"][0]
        capture = make_capture(
            [
                {
                    "id": "csrc_contract",
                    "kind": source["kind"],
                    "title": source["title"],
                    "uri": source["uri"],
                    "revision": source.get("revision"),
                    "reference_uri": source["uri"],
                    "content_hash": source["content_hash"],
                }
            ],
            existing_sources=memory["sources"],
        )
        candidates = make_candidate_bundle(
            capture,
            [candidate("can_new_fact", "new-fact", {"statement": "A new fact."}, "csrc_contract")],
        )

        result = reconcile_candidates(
            change_set_id="chg_reconcile_reuse_source",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=memory,
        )

        self.assertTrue(result.ok, result.to_dict())
        change_set = result.change_set
        assert change_set is not None
        self.assertEqual(validate_change_set(change_set, memory).findings, ())
        self.assertEqual([op["operation_type"] for op in change_set["operations"]], ["create_record"])
        self.assertEqual(change_set["source_resolutions"][0]["resolution"], "reuse")
        self.assertEqual(change_set["operations"][0]["record"]["evidence"][0]["source_id"], source["id"])

    def test_changed_source_is_added_for_new_candidate(self) -> None:
        memory = load_memory("valid/minimal.json")
        source = memory["sources"][0]
        capture = make_capture(
            [
                CaptureSourceInput(
                    id="csrc_contract_v2",
                    kind=source["kind"],
                    title=source["title"],
                    uri=source["uri"],
                    revision=source.get("revision"),
                    content="Changed source content.",
                )
            ],
            existing_sources=memory["sources"],
        )
        candidates = make_candidate_bundle(
            capture,
            [candidate("can_changed_fact", "changed-fact", {"statement": "A changed fact."}, "csrc_contract_v2")],
        )

        result = reconcile_candidates(
            change_set_id="chg_reconcile_changed_source",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=memory,
        )

        self.assertTrue(result.ok, result.to_dict())
        change_set = result.change_set
        assert change_set is not None
        self.assertEqual(validate_change_set(change_set, memory).findings, ())
        self.assertEqual(
            [operation["operation_type"] for operation in change_set["operations"]],
            ["add_source", "create_record"],
        )
        self.assertEqual(change_set["source_resolutions"][0]["resolution"], "add")
        self.assertEqual(change_set["source_resolutions"][0]["canonical_source_id"], "src_contract_v2")

    def test_needs_review_candidate_can_share_change_set_with_create(self) -> None:
        capture = make_capture(
            [
                CaptureSourceInput(
                    id="csrc_missing",
                    kind="document",
                    title="Missing source",
                    uri="file:missing.md",
                    unavailable_reason="The source could not be read.",
                ),
                CaptureSourceInput(
                    id="csrc_available",
                    kind="document",
                    title="Available source",
                    uri="file:available.md",
                    content="Available fact.",
                ),
            ],
            capture_bundle_id="cap_reconcile_review",
        )
        candidates = make_candidate_bundle(
            capture,
            [
                candidate("can_missing", "missing-fact", {"statement": "Unsupported fact."}, "csrc_missing"),
                candidate("can_available", "available-fact", {"statement": "Available fact."}, "csrc_available"),
            ],
            candidate_bundle_id="cnd_reconcile_review",
        )

        result = reconcile_candidates(
            change_set_id="chg_reconcile_review",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=None,
            memory_id="mem_reconcile_review",
            project=PROJECT,
        )

        self.assertTrue(result.ok, result.to_dict())
        change_set = result.change_set
        assert change_set is not None
        self.assertEqual(validate_change_set(change_set, None).findings, ())
        resolutions = {item["candidate_id"]: item for item in change_set["candidate_resolutions"]}
        self.assertEqual(resolutions["can_missing"]["resolution"], "needs_review")
        self.assertEqual(resolutions["can_available"]["resolution"], "create")
        self.assertEqual(len(change_set["findings"]), 1)
        self.assertEqual(change_set["findings"][0]["id"], resolutions["can_missing"]["finding_ids"][0])
        source_resolutions = {item["captured_source_id"]: item for item in change_set["source_resolutions"]}
        self.assertEqual(source_resolutions["csrc_missing"]["resolution"], "ignore")
        self.assertEqual(source_resolutions["csrc_available"]["resolution"], "add")

    def test_input_artifact_hash_mismatch_blocks_reconciliation(self) -> None:
        capture = make_capture(
            [
                CaptureSourceInput(
                    id="csrc_hash",
                    kind="document",
                    title="Hash source",
                    uri="file:hash.md",
                    content="Hash fact.",
                )
            ]
        )
        candidates = make_candidate_bundle(
            capture,
            [candidate("can_hash", "hash-fact", {"statement": "Hash fact."}, "csrc_hash")],
        )
        candidates["generated_at"] = "2026-06-08T14:01:00Z"

        result = reconcile_candidates(
            change_set_id="chg_reconcile_hash_mismatch",
            generated_at=NOW,
            capture_bundle=capture,
            candidate_bundle=candidates,
            memory=None,
            memory_id="mem_reconcile",
            project=PROJECT,
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.change_set)
        self.assertIn("ARTIFACT_HASH_MISMATCH", {finding.code for finding in result.findings})


if __name__ == "__main__":
    unittest.main()
