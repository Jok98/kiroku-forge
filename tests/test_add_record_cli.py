from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kiroku.py"
sys.path.insert(0, str(ROOT / "scripts"))

from kiroku_core.io import record_hash  # noqa: E402


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


class AddRecordCliTests(unittest.TestCase):
    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Record Test",
            "--domain",
            "testing",
            "--goal",
            "Verify controlled record creation",
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
        uri: str = "conversation://record-test/message-1",
    ) -> str:
        result = run_cli(
            "add-source",
            "--dir",
            str(memory_dir),
            "--kind",
            "user_input",
            "--title",
            "User request",
            "--uri",
            uri,
            "--text",
            "Use canonical memory.",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return self.load(memory_dir)["sources"][-1]["id"]

    def start_run(self, root: Path, memory_dir: Path, source_id: str) -> str:
        result = run_cli(
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
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return self.load(memory_dir)["runs"][-1]["id"]

    def decision_draft(self, source_id: str, *, key: str = "canonical_memory") -> dict:
        return {
            "key": key,
            "type": "decision",
            "title": "Canonical project memory",
            "summary": "Structured JSON is the source of truth.",
            "confidence": "confirmed",
            "verification_status": "verified",
            "evidence": [
                {
                    "source_id": source_id,
                    "relation": "supports",
                    "method": "user_statement",
                    "target": "/payload/decision",
                    "locator": {
                        "kind": "message",
                        "message_id": "message-1",
                    },
                    "note": "The user selected canonical structured memory.",
                }
            ],
            "payload": {
                "decision": "Use structured JSON as canonical memory.",
                "context": "Generated views must not compete with canonical data.",
                "implications": ["Render user views from the canonical record store."],
            },
        }

    def add_draft_file(
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

    def test_add_record_from_file_manages_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)

            result = self.add_draft_file(
                root,
                memory_dir,
                run_id,
                self.decision_draft(source_id),
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            record = self.load(memory_dir)["records"][0]
            self.assertEqual("canonical_memory", record["key"])
            self.assertTrue(record["id"].startswith("rec_canonical_memory_"))
            self.assertEqual("active", record["status"])
            self.assertEqual(["record_test"], record["scope"])
            self.assertEqual([], record["tags"])
            self.assertEqual([], record["relations"])
            self.assertEqual(run_id, record["generated_by"])
            self.assertEqual(record["created_at"], record["updated_at"])
            self.assertIsNotNone(record["evidence"][0]["observed_at"])
            self.assertEqual(record_hash(record), record["content_hash"])

    def test_add_record_accepts_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = {
                "key": "memory_is_empty",
                "type": "fact",
                "title": "No prior records",
                "summary": "The initialized memory contained no durable records.",
                "confidence": "medium",
                "verification_status": "unverified",
                "payload": {"statement": "No durable records existed before this run."},
            }

            result = run_cli(
                "add-record",
                "--dir",
                str(memory_dir),
                "--run-id",
                run_id,
                "--stdin",
                cwd=root,
                stdin=json.dumps(draft).encode("utf-8"),
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            self.assertEqual("memory_is_empty", self.load(memory_dir)["records"][0]["key"])

    def test_identical_record_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.decision_draft(source_id)

            first = self.add_draft_file(root, memory_dir, run_id, draft)
            second = self.add_draft_file(root, memory_dir, run_id, draft)

            self.assertEqual(0, first.returncode)
            self.assertEqual(0, second.returncode)
            self.assertIn("[SAME]", second.stdout.decode())
            self.assertEqual(1, len(self.load(memory_dir)["records"]))

    def test_same_key_with_changed_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.decision_draft(source_id)
            self.assertEqual(
                0,
                self.add_draft_file(root, memory_dir, run_id, draft).returncode,
            )
            draft["summary"] = "Changed semantic content."

            result = self.add_draft_file(root, memory_dir, run_id, draft)

            self.assertEqual(2, result.returncode)
            self.assertIn("use update-record", result.stdout.decode())
            records = self.load(memory_dir)["records"]
            self.assertEqual(1, len(records))
            self.assertNotEqual("Changed semantic content.", records[0]["summary"])

    def test_equivalent_content_with_another_key_is_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            first = self.decision_draft(source_id)
            second = self.decision_draft(source_id, key="duplicate_key")
            self.assertEqual(
                0,
                self.add_draft_file(root, memory_dir, run_id, first).returncode,
            )

            result = self.add_draft_file(root, memory_dir, run_id, second)

            self.assertEqual(0, result.returncode)
            self.assertIn("Equivalent record", result.stdout.decode())
            self.assertEqual(1, len(self.load(memory_dir)["records"]))

    def test_invalid_payload_does_not_mutate_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.decision_draft(source_id)
            draft["payload"] = {"decision": "Missing required fields."}
            before = (memory_dir / "memory.json").read_bytes()

            result = self.add_draft_file(root, memory_dir, run_id, draft)

            self.assertEqual(2, result.returncode)
            self.assertIn("no changes written", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_record_requires_a_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            completed_run_id = self.load(memory_dir)["runs"][0]["id"]

            result = self.add_draft_file(
                root,
                memory_dir,
                completed_run_id,
                self.decision_draft(source_id),
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("is not running", result.stdout.decode())
            self.assertEqual([], self.load(memory_dir)["records"])

    def test_evidence_source_must_be_an_input_of_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            input_source = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, input_source)
            other_source = self.add_source(
                root,
                memory_dir,
                uri="conversation://record-test/message-2",
            )
            before = (memory_dir / "memory.json").read_bytes()

            result = self.add_draft_file(
                root,
                memory_dir,
                run_id,
                self.decision_draft(other_source),
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("is not an input of run", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_managed_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.decision_draft(source_id)
            draft["id"] = "rec_manual"
            before = (memory_dir / "memory.json").read_bytes()

            result = self.add_draft_file(root, memory_dir, run_id, draft)

            self.assertEqual(2, result.returncode)
            self.assertIn("unknown field", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
