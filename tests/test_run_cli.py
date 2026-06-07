from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kiroku.py"


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        capture_output=True,
        check=False,
    )


class RunCliTests(unittest.TestCase):
    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Run Test",
            "--domain",
            "testing",
            "--goal",
            "Verify run lifecycle",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return memory_dir

    def load(self, memory_dir: Path) -> dict:
        return json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))

    def add_source(self, root: Path, memory_dir: Path) -> str:
        result = run_cli(
            "add-source",
            "--dir",
            str(memory_dir),
            "--kind",
            "user_input",
            "--title",
            "User request",
            "--uri",
            "conversation://run-test/message-1",
            "--text",
            "Update the memory.",
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
            "--actor-version",
            "1",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return self.load(memory_dir)["runs"][-1]["id"]

    def test_start_run_creates_running_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)

            run_id = self.start_run(root, memory_dir, source_id)

            run = self.load(memory_dir)["runs"][-1]
            self.assertEqual(run_id, run["id"])
            self.assertEqual("running", run["status"])
            self.assertEqual("update", run["operation"])
            self.assertEqual([source_id], run["inputs"])
            self.assertEqual("test-agent", run["actor"]["name"])
            self.assertIsNone(run["completed_at"])
            self.assertIsNone(run["summary"])

    def test_start_run_rejects_unknown_source_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            before = (memory_dir / "memory.json").read_bytes()

            result = run_cli(
                "start-run",
                "--dir",
                str(memory_dir),
                "--operation",
                "review",
                "--input",
                "src_missing",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("unknown input source", result.stdout.decode())
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_only_one_run_can_be_running(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)

            result = run_cli(
                "start-run",
                "--dir",
                str(memory_dir),
                "--operation",
                "review",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn(run_id, result.stdout.decode())
            self.assertEqual(2, len(self.load(memory_dir)["runs"]))

    def test_finish_run_completes_it_with_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)

            result = run_cli(
                "finish-run",
                "--dir",
                str(memory_dir),
                "--run-id",
                run_id,
                "--summary",
                "Updated durable memory.",
                "--warning",
                "One claim remains unverified.",
                cwd=root,
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            run = self.load(memory_dir)["runs"][-1]
            self.assertEqual("completed", run["status"])
            self.assertEqual("Updated durable memory.", run["summary"])
            self.assertEqual(["One claim remains unverified."], run["warnings"])
            self.assertIsNotNone(run["completed_at"])

    def test_finish_run_is_idempotent_for_same_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            command = (
                "finish-run",
                "--dir",
                str(memory_dir),
                "--run-id",
                run_id,
                "--summary",
                "Completed extraction.",
            )

            first = run_cli(*command, cwd=root)
            after_first = (memory_dir / "memory.json").read_bytes()
            second = run_cli(*command, cwd=root)

            self.assertEqual(0, first.returncode)
            self.assertEqual(0, second.returncode)
            self.assertIn("[SAME]", second.stdout.decode())
            self.assertEqual(after_first, (memory_dir / "memory.json").read_bytes())

    def test_completed_run_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)
            self.assertEqual(
                0,
                run_cli(
                    "finish-run",
                    "--dir",
                    str(memory_dir),
                    "--run-id",
                    run_id,
                    "--summary",
                    "Original summary.",
                    cwd=root,
                ).returncode,
            )

            result = run_cli(
                "finish-run",
                "--dir",
                str(memory_dir),
                "--run-id",
                run_id,
                "--summary",
                "Changed summary.",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("immutable", result.stdout.decode())
            self.assertEqual(
                "Original summary.",
                self.load(memory_dir)["runs"][-1]["summary"],
            )

    def test_build_requires_running_run_to_be_finished(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_id = self.add_source(root, memory_dir)
            run_id = self.start_run(root, memory_dir, source_id)

            blocked = run_cli(
                "build",
                "--dir",
                str(memory_dir),
                cwd=root,
            )
            self.assertEqual(2, blocked.returncode)
            self.assertIn(run_id, blocked.stdout.decode())
            self.assertFalse((memory_dir / "agent-bootstrap.json").exists())

            self.assertEqual(
                0,
                run_cli(
                    "finish-run",
                    "--dir",
                    str(memory_dir),
                    "--run-id",
                    run_id,
                    "--summary",
                    "Completed extraction.",
                    cwd=root,
                ).returncode,
            )
            completed = run_cli(
                "build",
                "--dir",
                str(memory_dir),
                cwd=root,
            )
            self.assertEqual(0, completed.returncode, completed.stdout.decode())
            self.assertTrue((memory_dir / "agent-bootstrap.json").exists())


if __name__ == "__main__":
    unittest.main()
