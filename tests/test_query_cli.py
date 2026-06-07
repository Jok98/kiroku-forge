from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kiroku.py"
sys.path.insert(0, str(ROOT / "scripts"))


def run_cli(
    *args: str,
    cwd: Path,
    stdin: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        check=False,
    )


class QueryCliTests(unittest.TestCase):
    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Query Test",
            "--domain",
            "testing",
            "--goal",
            "Verify record query.",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return memory_dir

    def load(self, memory_dir: Path) -> dict:
        return json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))

    def add_source(
        self,
        root: Path,
        memory_dir: Path,
        *,
        uri: str = "conversation://query-test/message-1",
    ) -> str:
        run_cli(
            "add-source",
            "--dir",
            str(memory_dir),
            "--kind",
            "user_input",
            "--title",
            "Test source",
            "--uri",
            uri,
            "--text",
            "Test content.",
            cwd=root,
        )
        return self.load(memory_dir)["sources"][-1]["id"]

    def start_run(self, root: Path, memory_dir: Path, source_id: str) -> str:
        run_cli(
            "start-run",
            "--dir",
            str(memory_dir),
            "--operation",
            "update",
            "--input",
            source_id,
            "--actor-name",
            "test-agent",
            cwd=root,
        )
        return self.load(memory_dir)["runs"][-1]["id"]

    def add_record(
        self,
        root: Path,
        memory_dir: Path,
        run_id: str,
        draft: dict,
    ) -> subprocess.CompletedProcess[bytes]:
        path = root / "record-draft.json"
        path.write_text(json.dumps(draft), encoding="utf-8")
        return run_cli(
            "add-record",
            "--dir",
            str(memory_dir),
            "--run-id",
            run_id,
            "--file",
            str(path),
            cwd=root,
        )

    def finish_run(
        self,
        root: Path,
        memory_dir: Path,
        run_id: str,
    ) -> None:
        run_cli(
            "finish-run",
            "--dir",
            str(memory_dir),
            "--run-id",
            run_id,
            "--summary",
            "Added test records.",
            cwd=root,
        )

    def build(self, root: Path, memory_dir: Path) -> None:
        run_cli(
            "build",
            "--dir",
            str(memory_dir),
            "--no-render",
            cwd=root,
        )

    def populated_dir(self, root: Path) -> Path:
        memory_dir = self.initialize(root)
        source_id = self.add_source(root, memory_dir)
        run_id = self.start_run(root, memory_dir, source_id)

        add_canonical = self.add_record(
            root,
            memory_dir,
            run_id,
            {
                "key": "canonical_memory",
                "type": "decision",
                "title": "Canonical JSON memory",
                "summary": "Use canonical memory.",
                "confidence": "confirmed",
                "verification_status": "verified",
                "scope": ["query_test"],
                "tags": ["architecture"],
                "evidence": [
                    {
                        "source_id": source_id,
                        "relation": "supports",
                        "method": "user_statement",
                        "target": "/payload/decision",
                        "locator": {"kind": "message", "message_id": "m1"},
                    }
                ],
                "payload": {
                    "decision": "Use kiroku/memory.json as canonical.",
                    "context": "Need one truth.",
                    "implications": ["Generated files are projections."],
                },
            },
        )
        self.assertEqual(0, add_canonical.returncode, add_canonical.stdout.decode())

        canonical_id = self.load(memory_dir)["records"][-1]["id"]
        self.assertIn("rec_canonical_memory_", canonical_id)

        add_query = self.add_record(
            root,
            memory_dir,
            run_id,
            {
                "key": "query_command_p1",
                "type": "roadmap_item",
                "title": "Add selective agent queries",
                "summary": "Filter records without loading all memory.",
                "confidence": "medium",
                "verification_status": "unverified",
                "scope": ["kiroku-forge"],
                "tags": ["p1", "query"],
                "relations": [
                    {
                        "type": "depends_on",
                        "target_id": canonical_id,
                    }
                ],
                "payload": {
                    "outcome": "Provide a query command.",
                    "horizon": "next",
                    "priority": "high",
                },
            },
        )
        self.assertEqual(0, add_query.returncode, add_query.stdout.decode())

        add_fact = self.add_record(
            root,
            memory_dir,
            run_id,
            {
                "key": "test_fact",
                "type": "fact",
                "title": "Tests pass",
                "summary": "All tests pass.",
                "confidence": "confirmed",
                "verification_status": "verified",
                "scope": ["query_test"],
                "tags": ["testing", "quality"],
                "evidence": [
                    {
                        "source_id": source_id,
                        "relation": "supports",
                        "method": "user_statement",
                        "target": "/payload/statement",
                        "locator": {"kind": "message", "message_id": "m2"},
                    }
                ],
                "payload": {"statement": "62 tests pass."},
            },
        )
        self.assertEqual(0, add_fact.returncode, add_fact.stdout.decode())

        self.finish_run(root, memory_dir, run_id)
        self.build(root, memory_dir)
        return memory_dir

    def test_query_default_compact_format(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli("query", "--dir", str(memory_dir), cwd=root)

            self.assertEqual(0, result.returncode, result.stderr.decode())
            output = json.loads(result.stdout)
            self.assertEqual(3, len(output))
            self.assertIn("id", output[0])
            self.assertIn("key", output[0])
            self.assertIn("payload", output[0])
            self.assertIn("evidence_source_ids", output[0])

    def test_query_filter_by_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--key",
                "canonical_memory",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("canonical_memory", output[0]["key"])

    def test_query_filter_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--type",
                "fact",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("fact", output[0]["type"])

    def test_query_filter_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--status",
                "active",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(3, len(output))

    def test_query_filter_by_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--scope",
                "kiroku-forge",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("query_command_p1", output[0]["key"])

    def test_query_filter_by_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--tag",
                "architecture",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("canonical_memory", output[0]["key"])

    def test_query_viewer_filters_share_cli_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--confidence",
                "medium",
                "--verification-status",
                "unverified",
                "--search",
                "selective agent queries",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("query_command_p1", output[0]["key"])

    def test_query_filter_by_relation_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            canonical_id = next(
                r["id"]
                for r in self.load(memory_dir)["records"]
                if r["key"] == "canonical_memory"
            )

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--relation-target",
                canonical_id,
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("query_command_p1", output[0]["key"])

    def test_query_filter_by_relation_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--relation-type",
                "depends_on",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("query_command_p1", output[0]["key"])

    def test_query_combined_filters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--type",
                "decision",
                "--scope",
                "query_test",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertEqual("canonical_memory", output[0]["key"])

    def test_query_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--count",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual("3\n", result.stdout.decode())

    def test_query_full_format(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--format",
                "full",
                "--key",
                "canonical_memory",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(1, len(output))
            self.assertIn("content_hash", output[0])
            self.assertIn("created_at", output[0])

    def test_query_ids_format(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--format",
                "ids",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(3, len(output))
            self.assertIsInstance(output[0], str)

    def test_query_sort_by_type_desc(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--sort",
                "type",
                "--sort-dir",
                "desc",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(3, len(output))
            self.assertEqual("roadmap_item", output[0]["type"])

    def test_query_no_matches_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--key",
                "nonexistent",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual([], output)

    def test_query_invalid_memory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            memory = self.load(memory_dir)
            memory["records"].append(
                {"id": "rec_bad", "invalid": "record"}
            )
            (memory_dir / "memory.json").write_text(
                json.dumps(memory, indent=2)
            )

            result = run_cli("query", "--dir", str(memory_dir), cwd=root)

            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR", result.stdout.decode())

    def test_query_combined_relation_must_match_single_relation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            canonical_id = next(
                r["id"]
                for r in self.load(memory_dir)["records"]
                if r["key"] == "canonical_memory"
            )

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--relation-type",
                "implements",
                "--relation-target",
                canonical_id,
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(
                0,
                len(output),
                "no relation has both implements type and the canonical target",
            )

    def test_query_invalid_record_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--type",
                "does_not_exist",
                "--count",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR", result.stdout.decode())
            self.assertIn("unknown record type", result.stdout.decode())

    def test_query_invalid_status_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--status",
                "does_not_exist",
                "--count",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR", result.stdout.decode())
            self.assertIn("unknown record status", result.stdout.decode())

    def test_query_invalid_relation_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--relation-type",
                "does_not_exist",
                "--count",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("ERROR", result.stdout.decode())
            self.assertIn("unknown relation type", result.stdout.decode())

    def test_query_sort_by_created_at(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.populated_dir(root)

            result = run_cli(
                "query",
                "--dir",
                str(memory_dir),
                "--sort",
                "created_at",
                "--format",
                "ids",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual(3, len(output))
            records = self.load(memory_dir)["records"]
            ids_by_created = sorted(
                records,
                key=lambda r: datetime.fromisoformat(
                    r["created_at"].replace("Z", "+00:00")
                ),
            )
            self.assertEqual(
                [r["id"] for r in ids_by_created],
                output,
                "should sort by datetime not string",
            )


if __name__ == "__main__":
    unittest.main()
