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


class SupersedeRecordCliTests(unittest.TestCase):
    def load(self, memory_dir: Path) -> dict:
        return json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))

    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Supersede Test",
            "--domain",
            "testing",
            "--goal",
            "Verify historical record replacement",
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
            "Architecture decision",
            "--uri",
            "conversation://supersede-test/message-1",
            "--text",
            "Replace the original memory architecture.",
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

    def draft(self, source_id: str, key: str, version: str) -> dict:
        return {
            "key": key,
            "type": "decision",
            "title": f"Canonical memory {version}",
            "summary": f"{version} is the selected canonical memory design.",
            "confidence": "confirmed",
            "verification_status": "verified",
            "evidence": [
                {
                    "source_id": source_id,
                    "relation": "supports",
                    "method": "user_statement",
                    "locator": {
                        "kind": "message",
                        "message_id": "message-1",
                    },
                }
            ],
            "payload": {
                "decision": f"Use canonical memory design {version}.",
                "context": "The architecture evolved.",
                "implications": [f"Retain {version} as the current design."],
            },
        }

    def write_draft(self, root: Path, draft: dict) -> Path:
        path = root / "replacement.json"
        path.write_text(json.dumps(draft), encoding="utf-8")
        return path

    def add_initial(
        self,
        root: Path,
        memory_dir: Path,
        source_id: str,
    ) -> dict:
        run_id = self.start_run(root, memory_dir, source_id)
        path = self.write_draft(
            root,
            self.draft(source_id, "canonical_memory_v1", "Version 1"),
        )
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

    def supersede(
        self,
        root: Path,
        memory_dir: Path,
        run_id: str,
        key: str,
        expected_hash: str,
        draft: dict,
        *,
        stdin: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        arguments = [
            "supersede-record",
            "--dir",
            str(memory_dir),
            "--run-id",
            run_id,
            "--key",
            key,
            "--expect-hash",
            expected_hash,
        ]
        if stdin:
            return run_cli(
                *arguments,
                "--stdin",
                cwd=root,
                stdin=json.dumps(draft).encode("utf-8"),
            )
        path = self.write_draft(root, draft)
        return run_cli(*arguments, "--file", str(path), cwd=root)

    def test_supersede_atomically_creates_history_and_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)

            result = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                self.draft(source_id, "canonical_memory_v2", "Version 2"),
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            records = self.load(memory_dir)["records"]
            self.assertEqual(2, len(records))
            predecessor, replacement = records
            self.assertEqual(original["id"], predecessor["id"])
            self.assertEqual("superseded", predecessor["status"])
            self.assertEqual(run_id, predecessor["generated_by"])
            self.assertEqual(record_hash(predecessor), predecessor["content_hash"])
            self.assertEqual("canonical_memory_v2", replacement["key"])
            self.assertEqual("active", replacement["status"])
            self.assertEqual(run_id, replacement["generated_by"])
            self.assertEqual(
                [{"type": "supersedes", "target_id": predecessor["id"]}],
                replacement["relations"],
            )
            self.assertEqual(record_hash(replacement), replacement["content_hash"])

    def test_supersede_accepts_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)

            result = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                self.draft(source_id, "canonical_memory_v2", "Version 2"),
                stdin=True,
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            self.assertEqual(
                "canonical_memory_v2",
                self.load(memory_dir)["records"][-1]["key"],
            )

    def test_stale_hash_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()

            result = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                "sha256:" + "0" * 64,
                self.draft(source_id, "canonical_memory_v2", "Version 2"),
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("changed since it was read", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_replacement_requires_a_new_unused_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()

            result = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                self.draft(source_id, original["key"], "Version 2"),
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("different key", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_second_direct_replacement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            first = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                self.draft(source_id, "canonical_memory_v2", "Version 2"),
            )
            self.assertEqual(0, first.returncode, first.stdout.decode())
            before = (memory_dir / "memory.json").read_bytes()

            second = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                self.draft(source_id, "canonical_memory_v3", "Version 3"),
            )

            self.assertEqual(2, second.returncode)
            self.assertIn("already superseded", second.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_superseded_predecessor_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            self.assertEqual(
                0,
                self.supersede(
                    root,
                    memory_dir,
                    run_id,
                    original["key"],
                    original["content_hash"],
                    self.draft(source_id, "canonical_memory_v2", "Version 2"),
                ).returncode,
            )
            predecessor = self.load(memory_dir)["records"][0]
            before = (memory_dir / "memory.json").read_bytes()
            path = self.write_draft(
                root,
                self.draft(source_id, original["key"], "Changed history"),
            )

            result = run_cli(
                "update-record",
                "--dir",
                str(memory_dir),
                "--run-id",
                run_id,
                "--key",
                original["key"],
                "--expect-hash",
                predecessor["content_hash"],
                "--file",
                str(path),
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("is immutable", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_linear_supersession_chain_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            second_run = self.start_run(root, memory_dir, source_id)
            self.assertEqual(
                0,
                self.supersede(
                    root,
                    memory_dir,
                    second_run,
                    original["key"],
                    original["content_hash"],
                    self.draft(source_id, "canonical_memory_v2", "Version 2"),
                ).returncode,
            )
            self.finish_run(root, memory_dir, second_run)
            second = self.load(memory_dir)["records"][-1]
            third_run = self.start_run(root, memory_dir, source_id)

            result = self.supersede(
                root,
                memory_dir,
                third_run,
                second["key"],
                second["content_hash"],
                self.draft(source_id, "canonical_memory_v3", "Version 3"),
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            records = self.load(memory_dir)["records"]
            self.assertEqual(
                ["superseded", "superseded", "active"],
                [record["status"] for record in records],
            )

    def test_invalid_replacement_and_managed_relation_are_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            run_id = self.start_run(root, memory_dir, source_id)
            before = (memory_dir / "memory.json").read_bytes()
            draft = self.draft(source_id, "canonical_memory_v2", "Version 2")
            draft["relations"] = [
                {"type": "supersedes", "target_id": original["id"]}
            ]

            managed = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                draft,
            )
            self.assertEqual(2, managed.returncode)
            self.assertIn("relation is managed", managed.stdout.decode())

            draft = self.draft(source_id, "canonical_memory_v2", "Version 2")
            draft["payload"] = {"decision": "Incomplete."}
            invalid = self.supersede(
                root,
                memory_dir,
                run_id,
                original["key"],
                original["content_hash"],
                draft,
            )
            self.assertEqual(2, invalid.returncode)
            self.assertIn("no changes written", invalid.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_supersede_requires_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            original = self.add_initial(root, memory_dir, source_id)
            completed_run = self.load(memory_dir)["runs"][-1]["id"]

            result = self.supersede(
                root,
                memory_dir,
                completed_run,
                original["key"],
                original["content_hash"],
                self.draft(source_id, "canonical_memory_v2", "Version 2"),
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("is not running", result.stdout.decode())


if __name__ == "__main__":
    unittest.main()
