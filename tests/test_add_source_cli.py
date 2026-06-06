from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kiroku.py"


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


class AddSourceCliTests(unittest.TestCase):
    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Source Test",
            "--domain",
            "testing",
            "--goal",
            "Verify source acquisition",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stderr.decode())
        return memory_dir

    def load(self, memory_dir: Path) -> dict:
        return json.loads((memory_dir / "memory.json").read_text(encoding="utf-8"))

    def test_add_file_source_with_hash_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_file = root / "notes.txt"
            source_file.write_text("durable evidence\n", encoding="utf-8")

            result = run_cli(
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "document",
                "--title",
                "Planning notes",
                "--file",
                "notes.txt",
                "--revision",
                "v1",
                "--metadata",
                'language="en"',
                cwd=root,
            )

            self.assertEqual(0, result.returncode, result.stderr.decode())
            source = self.load(memory_dir)["sources"][0]
            expected = hashlib.sha256(source_file.read_bytes()).hexdigest()
            self.assertEqual(f"sha256:{expected}", source["content_hash"])
            self.assertEqual("verified", source["integrity"])
            self.assertEqual("notes.txt", source["uri"])
            self.assertEqual("en", source["metadata"]["language"])
            self.assertEqual(source_file.stat().st_size, source["metadata"]["size_bytes"])

    def test_duplicate_source_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_file = root / "notes.txt"
            source_file.write_text("same content", encoding="utf-8")
            command = (
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "document",
                "--title",
                "Notes",
                "--file",
                "notes.txt",
            )

            first = run_cli(*command, cwd=root)
            second = run_cli(*command, cwd=root)

            self.assertEqual(0, first.returncode)
            self.assertEqual(0, second.returncode)
            self.assertIn("[SAME]", second.stdout.decode())
            self.assertEqual(1, len(self.load(memory_dir)["sources"]))

    def test_changed_content_requires_new_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_file = root / "notes.txt"
            source_file.write_text("first", encoding="utf-8")
            command = (
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "document",
                "--title",
                "Notes",
                "--file",
                "notes.txt",
            )
            self.assertEqual(0, run_cli(*command, cwd=root).returncode)
            source_file.write_text("second", encoding="utf-8")

            result = run_cli(*command, cwd=root)

            self.assertEqual(2, result.returncode)
            self.assertIn("different content", result.stdout.decode())
            self.assertEqual(1, len(self.load(memory_dir)["sources"]))

    def test_uri_only_source_has_unavailable_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)

            result = run_cli(
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "url",
                "--title",
                "External reference",
                "--uri",
                "https://example.test/reference",
                cwd=root,
            )

            self.assertEqual(0, result.returncode)
            source = self.load(memory_dir)["sources"][0]
            self.assertEqual("unavailable", source["integrity"])
            self.assertIsNone(source["content_hash"])

    def test_stdin_source_is_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)

            result = run_cli(
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "command_output",
                "--title",
                "Validation output",
                "--uri",
                "command://validate",
                "--stdin",
                cwd=root,
                stdin=b"Validation OK\n",
            )

            self.assertEqual(0, result.returncode)
            source = self.load(memory_dir)["sources"][0]
            expected = hashlib.sha256(b"Validation OK\n").hexdigest()
            self.assertEqual(f"sha256:{expected}", source["content_hash"])

    def test_uri_is_required_without_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)

            result = run_cli(
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "user_input",
                "--title",
                "Missing URI",
                "--text",
                "content",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("--uri is required", result.stdout.decode())
            self.assertEqual([], self.load(memory_dir)["sources"])


if __name__ == "__main__":
    unittest.main()
