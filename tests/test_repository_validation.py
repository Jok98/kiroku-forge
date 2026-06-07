from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "kiroku.py"
sys.path.insert(0, str(ROOT / "scripts"))

from kiroku_core.validation import validate_repository_sources  # noqa: E402


def git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=False,
    )


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


class RepositoryValidationTests(unittest.TestCase):
    def repository(self, root: Path) -> tuple[str, bytes]:
        self.assertEqual(0, git(root, "init", "-q").returncode)
        self.assertEqual(
            0,
            git(root, "config", "user.email", "tests@example.invalid").returncode,
        )
        self.assertEqual(
            0,
            git(root, "config", "user.name", "Kiroku Tests").returncode,
        )
        evidence = root / "docs" / "evidence.txt"
        evidence.parent.mkdir(parents=True)
        content = b"durable repository evidence\n"
        evidence.write_bytes(content)
        self.assertEqual(0, git(root, "add", "docs/evidence.txt").returncode)
        self.assertEqual(
            0,
            git(root, "commit", "-q", "-m", "add evidence").returncode,
        )
        revision = git(root, "rev-parse", "HEAD").stdout.decode().strip()
        return revision, content

    def source(self, revision: str, content: bytes) -> dict:
        return {
            "sources": [
                {
                    "id": "src_repository_evidence",
                    "kind": "repository_file",
                    "title": "Repository evidence",
                    "uri": "docs/evidence.txt",
                    "revision": revision,
                    "integrity": "verified",
                    "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
                    "captured_at": "2026-06-07T00:00:00Z",
                    "metadata": {},
                }
            ]
        }

    def test_repository_source_matches_committed_blob(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision, content = self.repository(root)

            result = validate_repository_sources(
                self.source(revision, content),
                root,
            )

            self.assertEqual([], result.errors)

    def test_unknown_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, content = self.repository(root)
            memory = self.source("0" * 40, content)

            result = validate_repository_sources(memory, root)

            self.assertTrue(
                any("revision does not resolve" in error for error in result.errors)
            )

    def test_file_missing_at_revision_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision, content = self.repository(root)
            memory = self.source(revision, content)
            memory["sources"][0]["uri"] = "docs/missing.txt"

            result = validate_repository_sources(memory, root)

            self.assertTrue(
                any("repository file not found" in error for error in result.errors)
            )

    def test_committed_blob_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision, content = self.repository(root)
            memory = self.source(revision, content)
            memory["sources"][0]["content_hash"] = "sha256:" + "0" * 64

            result = validate_repository_sources(memory, root)

            self.assertTrue(
                any("content_hash mismatch" in error for error in result.errors)
            )

    def test_cli_infers_repository_from_memory_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision, _ = self.repository(root)
            memory_dir = root / "kiroku"
            init = run_cli(
                "init",
                "--dir",
                str(memory_dir),
                "--name",
                "Repository Validation",
                "--domain",
                "testing",
                "--goal",
                "Verify repository evidence.",
                cwd=root,
            )
            self.assertEqual(0, init.returncode, init.stdout.decode())
            add_source = run_cli(
                "add-source",
                "--dir",
                str(memory_dir),
                "--kind",
                "repository_file",
                "--title",
                "Repository evidence",
                "--file",
                "docs/evidence.txt",
                "--revision",
                revision,
                cwd=root,
            )
            self.assertEqual(
                0,
                add_source.returncode,
                add_source.stdout.decode(),
            )

            result = run_cli(
                "validate",
                "--dir",
                str(memory_dir),
                "--check-repository",
                cwd=root,
            )

            self.assertEqual(0, result.returncode, result.stdout.decode())
            self.assertIn("Validation OK", result.stdout.decode())

    def test_repo_requires_repository_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            memory_dir = root / "kiroku"
            init = run_cli(
                "init",
                "--dir",
                str(memory_dir),
                "--name",
                "Repository Validation",
                "--domain",
                "testing",
                "--goal",
                "Verify repository evidence.",
                cwd=root,
            )
            self.assertEqual(0, init.returncode)

            result = run_cli(
                "validate",
                "--dir",
                str(memory_dir),
                "--repo",
                str(root),
                cwd=root,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn(
                "--repo requires --check-repository",
                result.stdout.decode(),
            )


if __name__ == "__main__":
    unittest.main()
