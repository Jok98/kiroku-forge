from __future__ import annotations

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
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=cwd,
        capture_output=True,
        check=False,
    )


class SourceStatusCliTests(unittest.TestCase):
    def initialize(self, root: Path) -> Path:
        memory_dir = root / "kiroku"
        result = run_cli(
            "init",
            "--dir",
            str(memory_dir),
            "--name",
            "Source Status",
            "--domain",
            "testing",
            "--goal",
            "Detect changed source content.",
            cwd=root,
        )
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return memory_dir

    def add_source(
        self,
        root: Path,
        memory_dir: Path,
        path: str,
        *,
        uri: str | None = None,
        revision: str | None = None,
    ) -> str:
        command = [
            "add-source",
            "--dir",
            str(memory_dir),
            "--kind",
            "document",
            "--title",
            "Tracked source",
            "--file",
            path,
        ]
        if uri is not None:
            command.extend(["--uri", uri])
        if revision is not None:
            command.extend(["--revision", revision])
        result = run_cli(*command, cwd=root)
        self.assertEqual(0, result.returncode, result.stdout.decode())
        return json.loads(
            (memory_dir / "memory.json").read_text(encoding="utf-8")
        )["sources"][-1]["id"]

    def status(
        self,
        root: Path,
        memory_dir: Path,
        *args: str,
    ) -> tuple[subprocess.CompletedProcess[bytes], dict]:
        result = run_cli(
            "source-status",
            "--dir",
            str(memory_dir),
            *args,
            cwd=root,
        )
        output = json.loads(result.stdout) if result.returncode == 0 else {}
        return result, output

    def test_unchanged_file_matches_latest_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            (root / "notes.txt").write_text("same content", encoding="utf-8")
            source_id = self.add_source(root, memory_dir, "notes.txt")

            result, output = self.status(
                root,
                memory_dir,
                "--file",
                "notes.txt",
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(1, output["summary"]["unchanged"])
            self.assertEqual("unchanged", output["sources"][0]["status"])
            self.assertEqual(source_id, output["sources"][0]["source_id"])

    def test_changed_file_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_file = root / "notes.txt"
            source_file.write_text("first", encoding="utf-8")
            self.add_source(root, memory_dir, "notes.txt")
            source_file.write_text("second", encoding="utf-8")

            result, output = self.status(
                root,
                memory_dir,
                "--file",
                "notes.txt",
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(1, output["summary"]["changed"])
            source = output["sources"][0]
            self.assertEqual("changed", source["status"])
            self.assertNotEqual(source["stored_hash"], source["current_hash"])

    def test_unregistered_file_is_new(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            (root / "new.txt").write_text("new content", encoding="utf-8")

            result, output = self.status(
                root,
                memory_dir,
                "--file",
                "new.txt",
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(1, output["summary"]["new"])
            self.assertEqual("new", output["sources"][0]["status"])
            self.assertIsNone(output["sources"][0]["source_id"])

    def test_changed_only_filters_unchanged_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            unchanged = root / "unchanged.txt"
            changed = root / "changed.txt"
            new = root / "new.txt"
            unchanged.write_text("stable", encoding="utf-8")
            changed.write_text("before", encoding="utf-8")
            new.write_text("new", encoding="utf-8")
            self.add_source(root, memory_dir, "unchanged.txt")
            self.add_source(root, memory_dir, "changed.txt")
            changed.write_text("after", encoding="utf-8")

            result, output = self.status(
                root,
                memory_dir,
                "--file",
                "unchanged.txt",
                "--file",
                "changed.txt",
                "--file",
                "new.txt",
                "--changed-only",
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(3, output["summary"]["total"])
            self.assertEqual(2, output["summary"]["actionable"])
            self.assertEqual(2, output["summary"]["returned"])
            self.assertEqual(
                {"changed", "new"},
                {source["status"] for source in output["sources"]},
            )

    def test_explicit_uri_mapping_matches_stored_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_file = root / "local-copy.txt"
            source_file.write_text("mapped content", encoding="utf-8")
            source_id = self.add_source(
                root,
                memory_dir,
                "local-copy.txt",
                uri="docs/source.txt",
            )

            result, output = self.status(
                root,
                memory_dir,
                "--map",
                "docs/source.txt=local-copy.txt",
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual("unchanged", output["sources"][0]["status"])
            self.assertEqual(source_id, output["sources"][0]["source_id"])

    def test_latest_revision_is_used_as_hash_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            source_file = root / "notes.txt"
            source_file.write_text("version one", encoding="utf-8")
            self.add_source(
                root,
                memory_dir,
                "notes.txt",
                revision="v1",
            )
            source_file.write_text("version two", encoding="utf-8")
            latest_id = self.add_source(
                root,
                memory_dir,
                "notes.txt",
                revision="v2",
            )
            source_file.write_text("version one", encoding="utf-8")

            result, output = self.status(
                root,
                memory_dir,
                "--file",
                "notes.txt",
            )

            self.assertEqual(0, result.returncode)
            source = output["sources"][0]
            self.assertEqual("changed", source["status"])
            self.assertEqual(latest_id, source["source_id"])
            self.assertEqual("v2", source["revision"])

    def test_source_status_does_not_modify_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)
            (root / "notes.txt").write_text("content", encoding="utf-8")
            before = (memory_dir / "memory.json").read_bytes()

            result, _ = self.status(
                root,
                memory_dir,
                "--file",
                "notes.txt",
            )

            self.assertEqual(0, result.returncode)
            self.assertEqual(before, (memory_dir / "memory.json").read_bytes())

    def test_missing_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = self.initialize(root)

            result = run_cli(
                "source-status",
                "--dir",
                str(memory_dir),
                "--file",
                "missing.txt",
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("source file not found", result.stdout.decode())


if __name__ == "__main__":
    unittest.main()
