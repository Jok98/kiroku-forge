"""Exercise context budgets against real temporary Markdown/SQLite hubs."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import memory
from memory_store import DB_NAME, build_index, open_index


TRACK = "atlas"
REQUIRED_PATHS = (
    "START_HERE.md",
    "CONSTRAINTS.md",
    "tracks/atlas/START_HERE.md",
    "tracks/atlas/STATE.md",
    "tracks/atlas/ROADMAP.md",
    "tracks/atlas/WORK.md",
)


class ContextTests(unittest.TestCase):
    def make_hub(self, overrides=None, omitted=()):
        workspace = tempfile.TemporaryDirectory(prefix="kiroku-context-")
        self.addCleanup(workspace.cleanup)
        hub = Path(workspace.name) / "kiroku"
        sources = {
            "START_HERE.md": "# Project handoff\n\n## Next\nContinue the atlas task.\n",
            "CONSTRAINTS.md": "# Shared constraints\n\n## Rules\nKeep Markdown authoritative.\n",
            "tracks/atlas/START_HERE.md": "# Atlas handoff\n\n## Next\nRead the current task owners.\n",
            "tracks/atlas/STATE.md": "# State\n\n## Current\nThe context delivery is in progress.\n",
            "tracks/atlas/ROADMAP.md": (
                "# Roadmap\n\n## M-01: Deliver context\nStatus: in_progress\n"
                "Completion:\nThe complete context fits its declared budget.\n"
            ),
            "tracks/atlas/WORK.md": "# Work\n\n## Current\nVerify serialized responses and recovery.\n",
        }
        sources.update(overrides or {})
        for path in omitted:
            sources.pop(path, None)
        for relative, body in sources.items():
            destination = hub / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body.encode("utf-8"))
        self.assertEqual(build_index(hub)["state"], "ready")
        return hub, sources

    def api_context(self, hub, budget=16000, query=""):
        with closing(open_index(hub)) as connection:
            return memory.context(connection, TRACK, query, budget)

    def cli_context(self, hub, budget=16000, query="", track=TRACK):
        command = [sys.executable, "-B", str(SCRIPTS / "memory.py"), "context",
                   str(hub), "--hub-dir", "--track", track]
        if budget is not None:
            command.extend(["--max-chars", str(budget)])
        if query:
            command.extend(["--query", query])
        return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def assert_envelope(self, output, budget):
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        self.assertTrue(output.endswith("\n"))
        self.assertEqual(output.count("\n"), 1, "JSON must be compact with exactly one trailing LF")
        value = json.loads(output)
        self.assertLessEqual(len(output), budget)
        self.assertEqual(value["used_chars"], len(output))
        self.assertEqual(value["format_version"], 2)
        self.assertEqual(value["budget_unit"], "serialized_json_characters")
        self.assertEqual(memory.serialize_context(value), output)
        return value

    def assert_required_sources(self, result, sources):
        required = [item for item in result["items"] if item["reason"] == "required"]
        self.assertEqual(len(required), 6)
        self.assertEqual({item["id"] for item in required}, set(REQUIRED_PATHS))
        for item in required:
            self.assertEqual(item["body"], sources[item["id"]])

    def snapshot(self, hub):
        return {
            path.relative_to(hub).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in hub.rglob("*") if path.is_file()
        }

    def test_required_documents_are_complete_and_unique_with_default_cli_budget(self):
        hub, sources = self.make_hub()
        response = self.cli_context(hub, budget=None)
        self.assertEqual(response.returncode, 0, response.stderr.decode())
        self.assertEqual(response.stderr, b"")
        result = self.assert_envelope(response.stdout, 16000)
        self.assertEqual(result["state"], "ready")
        self.assert_required_sources(result, sources)
        self.assertEqual(len(result["items"]), 6)
        self.assertEqual(result["omitted_count"], 0)
        self.assertFalse(result["search_limited"])
        self.assertNotIn("query", result)
        self.assertNotIn("edges", result)

    def test_required_chars_is_an_exact_retry_budget_without_partial_sources(self):
        hub, sources = self.make_hub({
            "CONSTRAINTS.md": "# Shared constraints\n\n## Rules\n" + "Verified owner context.\n" * 430,
        })
        too_small = self.api_context(hub, memory.CONTEXT_MIN_CHARS)
        self.assert_envelope(memory.serialize_context(too_small), memory.CONTEXT_MIN_CHARS)
        self.assertEqual(too_small["state"], "budget_exceeded")
        self.assertEqual(too_small["items"], [])
        required = too_small["required_chars"]
        self.assertGreater(required, memory.CONTEXT_MIN_CHARS)
        for budget, state in ((required - 1, "budget_exceeded"), (required, "ready")):
            with self.subTest(budget=budget):
                result = self.api_context(hub, budget)
                serialized = memory.serialize_context(result)
                self.assert_envelope(serialized, budget)
                self.assertEqual(result["state"], state)
                self.assertEqual(result["required_chars"], required)
                if state == "ready":
                    self.assertEqual(len(serialized), required)
                    self.assert_required_sources(result, sources)
                else:
                    self.assertEqual(result["items"], [])
        response = self.cli_context(hub, required)
        self.assertEqual(response.returncode, 0, response.stderr.decode())
        self.assertEqual(len(response.stdout.decode("utf-8")), required)

    def test_unicode_escaping_and_newlines_count_serialized_characters(self):
        special = '# State\r\n\r\n## Current\r\nCittà 日本語 🧭 "quoted" \\path\tvalue\r\nNo final newline'
        hub, sources = self.make_hub({"tracks/atlas/STATE.md": special})
        response = self.cli_context(hub)
        self.assertEqual(response.returncode, 0, response.stderr.decode())
        result = self.assert_envelope(response.stdout, 16000)
        self.assert_required_sources(result, sources)
        serialized = response.stdout.decode("utf-8")
        self.assertGreater(len(response.stdout), len(serialized))
        self.assertIn('\\"quoted\\"', serialized)
        self.assertIn("\\r\\n", serialized)
        self.assertIn("\\t", serialized)
        self.assertGreater(result["required_chars"], sum(map(len, sources.values())))
        exact = self.cli_context(hub, result["required_chars"])
        self.assertEqual(exact.returncode, 0, exact.stderr.decode())
        self.assert_envelope(exact.stdout, result["required_chars"])

    def test_many_omissions_and_long_metadata_stay_within_a_small_budget(self):
        long_path = "notes/" + "long-provenance-" * 10 + "evidence.md"
        evidence = "# Evidence\n\n" + "".join(
            f"## Record {index:03d} {'detailed-heading-' * 12}\n"
            + "retrievaltoken is supported by this recorded source.\n" * 8
            + "\n" for index in range(80)
        )
        hub, _ = self.make_hub({long_path: evidence})
        required = self.api_context(hub)["required_chars"]
        budget = required + 100
        query = "retrievaltoken " * 500
        response = self.cli_context(hub, budget, query)
        self.assertEqual(response.returncode, 0, response.stderr.decode())
        result = self.assert_envelope(response.stdout, budget)
        self.assertEqual(result["state"], "ready")
        self.assertEqual(type(result["omitted_count"]), int)
        self.assertGreater(result["omitted_count"], 0)
        self.assertTrue(result["search_limited"])
        self.assertEqual(len(result["items"]), 6)
        for removed_field in ("query", "omitted", "edges"):
            self.assertNotIn(removed_field, result)

    def test_nested_required_section_seeds_explicit_edges_and_required_paths_are_deduplicated(self):
        handoff = (
            "# Project handoff\n\n## Routing\n\n### Evidence\n"
            "[Design](DESIGN.md#details)\n"
            "[Same design](DESIGN.md#details)\n"
            "[Rules](CONSTRAINTS.md#rules)\n"
            "[Task work](tracks/atlas/WORK.md)\n"
        )
        detail = "## Details\nUse the recorded design to guide the task.\n"
        hub, sources = self.make_hub({
            "START_HERE.md": handoff,
            "tracks/atlas/STATE.md": "# State\n\n## Current\n[Rules](../../CONSTRAINTS.md#rules)\n",
            "DESIGN.md": "# Design\n\n" + detail,
        })
        result = self.api_context(hub)
        self.assert_envelope(memory.serialize_context(result), 16000)
        self.assert_required_sources(result, sources)
        optional = [item for item in result["items"] if item["reason"] != "required"]
        self.assertEqual(len(optional), 1)
        item = optional[0]
        self.assertEqual(item["id"], "DESIGN.md#details")
        self.assertEqual(item["path"], "DESIGN.md")
        self.assertEqual(item["body"], detail)
        self.assertEqual(item["reason"], "related")
        self.assertEqual(set(item["via"]), {"source", "relation", "source_path", "source_line"})
        self.assertEqual(item["via"]["source"], "START_HERE.md#evidence")
        self.assertEqual(item["via"]["relation"], "references")
        source_line = sources[item["via"]["source_path"]].splitlines()[item["via"]["source_line"] - 1]
        self.assertIn("DESIGN.md#details", source_line)
        self.assertEqual((item["start_line"], item["end_line"]), (3, 4))

    def test_search_item_preserves_original_body_and_source_provenance(self):
        detail = '## Findings\r\nauroraneedle has an explicit "source".\r\nUse \\literal paths.\r\n'
        hub, _ = self.make_hub({"NOTES.md": "# Notes\r\n\r\n" + detail})
        result = self.api_context(hub, query="auroraneedle")
        self.assert_envelope(memory.serialize_context(result), 16000)
        optional = [item for item in result["items"] if item["reason"] != "required"]
        self.assertEqual(len(optional), 1)
        item = optional[0]
        self.assertEqual(item["reason"], "search")
        self.assertEqual(item["id"], "NOTES.md#findings")
        self.assertEqual(item["path"], "NOTES.md")
        self.assertEqual(item["body"], detail)
        self.assertEqual((item["start_line"], item["end_line"]), (3, 5))

    def test_context_reads_preserve_all_source_and_index_bytes_and_mtimes(self):
        hub, _ = self.make_hub({"NOTES.md": "# Notes\n\n## Evidence\nreadingneedle belongs to this note.\n"})
        original = self.snapshot(hub)
        self.api_context(hub, query="readingneedle")
        self.api_context(hub, memory.CONTEXT_MIN_CHARS)
        for budget in (16000, memory.CONTEXT_MIN_CHARS):
            response = self.cli_context(hub, budget, "readingneedle")
            self.assert_envelope(response.stdout, budget)
        self.assertEqual(self.snapshot(hub), original)
        self.assertIn(DB_NAME, original)

    def test_missing_index_and_missing_required_owner_return_bounded_errors(self):
        for missing in (DB_NAME, "CONSTRAINTS.md"):
            with self.subTest(missing=missing):
                hub, _ = self.make_hub(omitted=(missing,) if missing.endswith(".md") else ())
                if missing == DB_NAME:
                    (hub / DB_NAME).unlink()
                original = self.snapshot(hub)
                response = self.cli_context(hub, memory.CONTEXT_MIN_CHARS)
                self.assertEqual(response.returncode, 1)
                self.assertEqual(response.stderr, b"")
                result = self.assert_envelope(response.stdout, memory.CONTEXT_MIN_CHARS)
                self.assertEqual(result["state"], "error")
                self.assertTrue(result["error"])
                self.assertEqual(self.snapshot(hub), original)

    def test_unpublished_source_changes_keep_the_bounded_published_context(self):
        hub, sources = self.make_hub()
        changed = hub / "tracks/atlas/STATE.md"
        changed.write_bytes((sources["tracks/atlas/STATE.md"] + "A verified fact changed.\n").encode("utf-8"))
        original = self.snapshot(hub)
        response = self.cli_context(hub)
        self.assertEqual(response.returncode, 0)
        self.assertEqual(response.stderr, b"")
        result = self.assert_envelope(response.stdout, 16000)
        self.assertEqual(result["state"], "ready")
        self.assert_required_sources(result, sources)
        response = self.cli_context(hub, memory.CONTEXT_MIN_CHARS)
        self.assertEqual(response.returncode, 1)
        result = self.assert_envelope(response.stdout, memory.CONTEXT_MIN_CHARS)
        self.assertEqual(result["state"], "budget_exceeded")
        self.assertEqual(result["items"], [])
        self.assertEqual(self.snapshot(hub), original)

    def test_long_operational_error_is_explicitly_truncated_within_budget(self):
        hub, _ = self.make_hub()
        unknown_track = "unknown-" + "x" * 3000
        response = self.cli_context(hub, memory.CONTEXT_MIN_CHARS, track=unknown_track)
        self.assertEqual(response.returncode, 1)
        self.assertEqual(response.stderr, b"")
        result = self.assert_envelope(response.stdout, memory.CONTEXT_MIN_CHARS)
        self.assertEqual(result["state"], "error")
        self.assertTrue(result["error_truncated"])
        self.assertTrue(result["error"])
        self.assertNotIn(unknown_track, response.stdout.decode("utf-8"))

    def test_cli_rejects_budgets_outside_the_supported_range(self):
        self.assertEqual(memory.CONTEXT_MIN_CHARS, 256)
        self.assertEqual(memory.CONTEXT_MAX_CHARS, 1_000_000)
        hub, _ = self.make_hub()
        for budget in (0, memory.CONTEXT_MIN_CHARS - 1, memory.CONTEXT_MAX_CHARS + 1):
            with self.subTest(budget=budget):
                response = self.cli_context(hub, budget)
                self.assertEqual(response.returncode, 2)
                self.assertEqual(response.stdout, b"")
                self.assertEqual(json.loads(response.stderr)["state"], "error")


if __name__ == "__main__":
    unittest.main()
