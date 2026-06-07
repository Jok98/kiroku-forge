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


class UpdateRecordCliTests(unittest.TestCase):
    def load(self, memory_dir: Path) -> dict:
        return json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))

    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Update Test",
            "--domain",
            "testing",
            "--goal",
            "Verify controlled record updates",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return memory_dir

    def add_source(self, root: Path, memory_dir: Path) -> str:
        result = run_cli(
            "add-source",
            "--dir",
            str(memory_dir),
            "--kind",
            "user_input",
            "--title",
            "User decision",
            "--uri",
            "conversation://update-test/message-1",
            "--text",
            "Use canonical structured memory.",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return self.load(memory_dir)["sources"][0]["id"]

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

    def finish_run(self, root: Path, memory_dir: Path, run_id: str) -> None:
        result = run_cli(
            "finish-run",
            "--dir",
            str(memory_dir),
            "--run-id",
            run_id,
            "--summary",
            "Completed record operation.",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())

    def draft(self, source_id: str) -> dict:
        return {
            "key": "canonical_memory",
            "type": "decision",
            "status": "active",
            "title": "Canonical project memory",
            "summary": "Structured JSON is the source of truth.",
            "scope": ["update_test"],
            "tags": ["architecture"],
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
                    "note": "The user selected structured canonical memory.",
                }
            ],
            "relations": [],
            "payload": {
                "decision": "Use structured JSON as canonical memory.",
                "context": "Generated views must have one source of truth.",
                "implications": ["Generate all views from canonical JSON."],
            },
        }

    def write_draft(self, root: Path, draft: dict) -> Path:
        path = root / "update-draft.json"
        path.write_text(json.dumps(draft), encoding="utf-8")
        return path

    def add_initial_record(
        self,
        root: Path,
        memory_dir: Path,
        source_id: str,
    ) -> dict:
        run_id = self.start_run(root, memory_dir, source_id)
        path = self.write_draft(root, self.draft(source_id))
        result = run_cli(
            "add-record",
            "--dir",
            str(memory_dir),
            "--run-id",
            run_id,
            "--file",
            str(path),
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        self.finish_run(root, memory_dir, run_id)
        return self.load(memory_dir)["records"][0]

    def update(
        self,
        root: Path,
        memory_dir: Path,
        run_id: str,
        expected_hash: str,
        draft: dict,
    ) -> subprocess.CompletedProcess[bytes]:
        path = self.write_draft(root, draft)
        return run_cli(
            "update-record",
            "--dir",
            str(memory_dir),
            "--run-id",
            run_id,
            "--key",
            "canonical_memory",
            "--expect-hash",
            expected_hash,
            "--file",
            str(path),
            cwd=root,
        )

    def test_update_preserves_identity_and_refreshes_managed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.draft(source_id)
            draft["summary"] = "Canonical JSON now includes managed updates."
            draft["payload"]["implications"].append(
                "Updates use optimistic concurrency."
            )

            result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                draft,
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            updated = self.load(memory_dir)["records"][0]
            self.assertEqual(original["id"], updated["id"])
            self.assertEqual(original["key"], updated["key"])
            self.assertEqual(original["type"], updated["type"])
            self.assertEqual(original["created_at"], updated["created_at"])
            original_updated_at = datetime.fromisoformat(
                original["updated_at"].replace("Z", "+00:00")
            )
            updated_at = datetime.fromisoformat(
                updated["updated_at"].replace("Z", "+00:00")
            )
            self.assertGreater(updated_at, original_updated_at)
            self.assertEqual(run_id, updated["generated_by"])
            self.assertNotEqual(original["content_hash"], updated["content_hash"])
            self.assertEqual(record_hash(updated), updated["content_hash"])
            self.assertEqual(
                original["evidence"][0]["observed_at"],
                updated["evidence"][0]["observed_at"],
            )

    def test_update_accepts_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.draft(source_id)
            draft["summary"] = "Updated through standard input."

            result = run_cli(
                "update-record",
                "--dir",
                str(memory_dir),
                "--run-id",
                run_id,
                "--key",
                "canonical_memory",
                "--expect-hash",
                original["content_hash"],
                "--stdin",
                cwd=root,
                stdin=json.dumps(draft).encode("utf-8"),
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            self.assertEqual(
                "Updated through standard input.",
                self.load(memory_dir)["records"][0]["summary"],
            )

    def test_explicit_evidence_timestamp_can_be_corrected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.draft(source_id)
            corrected = "2026-01-01T10:00:00Z"
            draft["evidence"][0]["observed_at"] = corrected

            result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                draft,
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            updated = self.load(memory_dir)["records"][0]
            self.assertEqual(corrected, updated["evidence"][0]["observed_at"])

    def test_unchanged_update_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()

            result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                self.draft(source_id),
            )

            self.assertEqual(0, result.returncode)
            self.assertIn("[SAME]", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_stale_hash_rejects_update_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()
            draft = self.draft(source_id)
            draft["summary"] = "Attempted stale update."

            result = self.update(
                root,
                memory_dir,
                run_id,
                "sha256:" + "0" * 64,
                draft,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("changed since it was read", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_key_and_type_are_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()

            changed_key = self.draft(source_id)
            changed_key["key"] = "other_key"
            key_result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                changed_key,
            )
            self.assertEqual(2, key_result.returncode)
            self.assertIn("must match --key", key_result.stdout.decode())

            changed_type = self.draft(source_id)
            changed_type["type"] = "fact"
            changed_type["payload"] = {"statement": "Changed type."}
            type_result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                changed_type,
            )
            self.assertEqual(2, type_result.returncode)
            self.assertIn("type is immutable", type_result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_invalid_update_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()
            draft = self.draft(source_id)
            draft["payload"] = {"decision": "Incomplete payload."}

            result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                draft,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("no changes written", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_update_requires_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            completed_run = self.load(memory_dir)["runs"][-1]["id"]

            result = self.update(
                root,
                memory_dir,
                completed_run,
                original["content_hash"],
                self.draft(source_id),
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("is not running", result.stdout.decode())

    def test_superseded_status_requires_dedicated_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial_record(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            draft = self.draft(source_id)
            draft["status"] = "superseded"

            result = self.update(
                root,
                memory_dir,
                run_id,
                original["content_hash"],
                draft,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("use supersede-record", result.stdout.decode())


if __name__ == "__main__":
    unittest.main()
