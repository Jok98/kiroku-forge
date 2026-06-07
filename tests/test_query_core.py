from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kiroku_core.query import (  # noqa: E402
    MemoryIndex,
    RecordQuery,
    build_memory_index,
    compact_record,
    format_records,
    query_records,
)


def record(
    *,
    record_id: str,
    key: str,
    record_type: str,
    title: str,
    payload: dict,
    confidence: str = "confirmed",
    verification_status: str = "verified",
    scope: list[str] | None = None,
    tags: list[str] | None = None,
    relations: list[dict] | None = None,
    evidence: list[dict] | None = None,
    generated_by: str = "run_1",
    created_at: str = "2026-06-07T10:00:00Z",
) -> dict:
    return {
        "id": record_id,
        "key": key,
        "type": record_type,
        "status": "active",
        "title": title,
        "summary": f"Summary for {title}",
        "scope": scope or ["project"],
        "tags": tags or [],
        "confidence": confidence,
        "verification_status": verification_status,
        "evidence": evidence or [],
        "relations": relations or [],
        "payload": payload,
        "created_at": created_at,
        "updated_at": created_at,
        "generated_by": generated_by,
        "content_hash": "sha256:" + "0" * 64,
    }


class QueryCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = record(
            record_id="rec_decision",
            key="canonical_memory",
            record_type="decision",
            title="Canonical JSON memory",
            payload={
                "decision": "Use memory.json as canonical.",
                "context": "One truth",
                "implications": [],
            },
            tags=["architecture"],
            evidence=[{"source_id": "src_1"}],
        )
        self.task = record(
            record_id="rec_task",
            key="build_viewer",
            record_type="task",
            title="Build local viewer",
            payload={
                "action": "Render project memory for humans.",
                "owner": "agent",
                "priority": "high",
                "blocked_by": [],
                "acceptance_criteria": [],
            },
            confidence="medium",
            verification_status="unverified",
            scope=["viewer"],
            tags=["p2", "ui"],
            relations=[
                {
                    "type": "depends_on",
                    "target_id": "rec_decision",
                    "note": "Uses canonical memory.",
                }
            ],
            evidence=[{"source_id": "src_1"}, {"source_id": "src_2"}],
            created_at="2026-06-07T11:00:00Z",
        )
        self.memory = {
            "records": [self.task, self.decision],
            "sources": [{"id": "src_1"}, {"id": "src_2"}],
            "runs": [{"id": "run_1"}],
        }

    def test_filters_compose_and_relation_matches_same_item(self) -> None:
        records = query_records(
            self.memory,
            RecordQuery(
                record_type="task",
                scope="viewer",
                tag="p2",
                relation_type="depends_on",
                relation_target="rec_decision",
            ),
        )

        self.assertEqual(["build_viewer"], [item["key"] for item in records])

    def test_search_is_case_insensitive_and_includes_payload(self) -> None:
        records = query_records(
            self.memory,
            RecordQuery(search="PROJECT MEMORY FOR HUMANS"),
        )

        self.assertEqual(["build_viewer"], [item["key"] for item in records])

    def test_confidence_and_verification_filters(self) -> None:
        records = query_records(
            self.memory,
            RecordQuery(
                confidence="medium",
                verification_status="unverified",
            ),
        )

        self.assertEqual(["build_viewer"], [item["key"] for item in records])

    def test_sort_and_formats_are_transport_independent(self) -> None:
        records = query_records(
            self.memory,
            RecordQuery(sort="created_at", sort_direction="desc"),
        )

        self.assertEqual(["rec_task", "rec_decision"], format_records(records, "ids"))
        self.assertEqual(self.task, format_records(records, "full")[0])
        self.assertEqual(compact_record(self.task), format_records(records, "compact")[0])

    def test_unknown_enum_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown confidence"):
            query_records(
                self.memory,
                RecordQuery(confidence="certain"),
            )

    def test_memory_index_builds_reverse_lookups(self) -> None:
        index = build_memory_index(self.memory)

        self.assertIsInstance(index, MemoryIndex)
        self.assertIs(self.task, index.records_by_key["build_viewer"])
        self.assertEqual(
            [
                {
                    "source_id": "rec_task",
                    "type": "depends_on",
                    "note": "Uses canonical memory.",
                }
            ],
            index.incoming_relations["rec_decision"],
        )
        self.assertEqual(
            ["rec_task", "rec_decision"],
            index.record_ids_by_source["src_1"],
        )
        self.assertEqual(
            ["rec_task", "rec_decision"],
            index.record_ids_by_run["run_1"],
        )


if __name__ == "__main__":
    unittest.main()
