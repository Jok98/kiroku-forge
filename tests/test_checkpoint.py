"""Verify published DB reads and batched Markdown checkpoint publication."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import memory
import memory_store
from memory_store import DB_NAME, MemoryIndexError, build_index, index_status, open_index
from memory_writer import write_entry


TRACK = "atlas"
OWNER = "DECISIONS.md"
ENTRY_ID = "DEC-published"
NODE_ID = "entry:" + ENTRY_ID


class CheckpointTests(unittest.TestCase):
    def make_hub(self):
        workspace = tempfile.TemporaryDirectory(prefix="kiroku-checkpoint-")
        self.addCleanup(workspace.cleanup)
        hub = Path(workspace.name) / "kiroku"
        sources = {
            "START_HERE.md": "# Project\n\n## Next\n[Decisions](DECISIONS.md) guide atlas.\n",
            "CONSTRAINTS.md": "# Constraints\n\n## Rules\nKeep canonical Markdown.\n",
            "tracks/atlas/START_HERE.md": "# Atlas\n\n## Next\nResume from the published snapshot.\n",
            "tracks/atlas/STATE.md": "# State\n\n## Current\nPublished state is stable.\n",
            "tracks/atlas/ROADMAP.md": "# Roadmap\n\n## M-01\nStatus: in_progress\nVerify checkpoints.\n",
            "tracks/atlas/WORK.md": "# Work\n\n## Current\nVerify snapshot isolation.\n",
            OWNER: (
                "# Decisions\n\n## Active Decisions\n\n"
                '<!-- kiroku:entry {"version":1,"id":"DEC-published",'
                '"type":"decision","status":"active"} -->\n'
                "### Published decision\n\n"
                "Decision:\nUse publishedneedle as the current fact.\n\n"
                "Rationale:\nKeep the last checkpoint readable.\n\n"
                "Consequences:\n[State](tracks/atlas/STATE.md#current) supplies context.\n\n"
                "<!-- kiroku:end -->\n"
            ),
        }
        for relative, text in sources.items():
            target = hub / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(text.encode("utf-8"))
        self.assertEqual(build_index(hub)["state"], "ready")
        return hub, sources

    def cli(self, hub, command, *arguments, payload=None):
        invocation = [sys.executable, "-B", str(SCRIPTS / "memory.py"),
                      command, str(hub), "--hub-dir", *arguments]
        if payload is not None:
            invocation.extend(["--data", "-"])
        return subprocess.run(
            invocation, input=None if payload is None else json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def value(self, response, exit_code=0):
        self.assertEqual(response.returncode, exit_code, response.stdout.decode("utf-8", errors="replace"))
        self.assertEqual(response.stderr, b"")
        return json.loads(response.stdout)

    def snapshot(self, hub):
        return {path.relative_to(hub).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in hub.rglob("*") if path.is_file()}

    def index_snapshot(self, hub):
        target = hub / DB_NAME
        return target.read_bytes(), target.stat().st_mtime_ns

    def all_cli_reads(self, hub):
        requests = (
            ("search", "publishedneedle", "--track", TRACK),
            ("show", NODE_ID),
            ("related", NODE_ID),
            ("entries", "--type", "decision", "--track", TRACK),
            ("context", "--track", TRACK, "--query", "publishedneedle", "--max-chars", "16000"),
        )
        results = {}
        for command, *arguments in requests:
            response = self.cli(hub, command, *arguments)
            results[command] = self.value(response)
            if command == "context":
                self.assertEqual(results[command]["used_chars"], len(response.stdout.decode("utf-8")))
                self.assertLessEqual(results[command]["used_chars"], 16000)
        return results

    def assert_saved(self, result, changed=True):
        self.assertEqual(result["state"], "saved")
        self.assertIs(result["markdown_saved"], changed)
        self.assertIs(result["checkpoint_required"], True)
        self.assertIs(result["index_updated"], False)
        self.assertIn("checkpoint", result["next_action"].lower())

    def creation_payload(self):
        return {
            "id": "DEC-pending", "type": "decision", "status": "active",
            "title": "Next checkpoint decision",
            "fields": {"Decision": "Introduce pendingneedle at publication.",
                       "Rationale": "Batch the accepted memory changes.",
                       "Consequences": "Keep the old snapshot available until checkpoint."},
            "links": [{"relation": "depends_on", "target": ENTRY_ID}],
        }

    def test_every_read_uses_only_the_database_without_source_or_integrity_scans(self):
        hub, sources = self.make_hub()
        before = self.snapshot(hub)
        statements = []
        original_connect = memory_store._connect_readonly
        original_open = Path.open

        def guarded_open(path, *args, **kwargs):
            if path.suffix == ".md":
                raise AssertionError("A published read opened canonical Markdown")
            return original_open(path, *args, **kwargs)

        def guarded_connect(selected_hub):
            connection = original_connect(selected_hub)

            def authorize(action, first, second, database, origin):
                if action == sqlite3.SQLITE_PRAGMA and first.lower() in {"integrity_check", "quick_check"}:
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            connection.set_authorizer(authorize)
            connection.set_trace_callback(statements.append)
            return connection

        with ExitStack() as guards:
            guards.enter_context(patch.object(memory_store, "_read_sources", side_effect=AssertionError("Source scan")))
            guards.enter_context(patch.object(memory_store, "iter_hub_markdown", side_effect=AssertionError("Markdown traversal")))
            guards.enter_context(patch.object(Path, "open", guarded_open))
            guards.enter_context(patch.object(memory_store, "_connect_readonly", guarded_connect))
            with closing(open_index(hub)) as connection:
                self.assertEqual(memory.search(connection, "publishedneedle", TRACK, 8)[0]["id"], NODE_ID)
                self.assertEqual(memory.show(connection, OWNER)["body"], sources[OWNER])
                self.assertEqual(memory.show(connection, NODE_ID)["fields"]["Decision"],
                                 "Use publishedneedle as the current fact.")
                self.assertTrue(memory.related(connection, NODE_ID, 1, 20)["edges"])
                self.assertEqual(memory.entries(connection, "decision", "active", TRACK, 20, 0)["results"][0]["id"], NODE_ID)
                result = memory.context(connection, TRACK, "publishedneedle", 16000)
                self.assertEqual(result["state"], "ready")
                self.assertEqual(result["used_chars"], len(memory.serialize_context(result)))
        self.assertTrue(statements)
        self.assertFalse(any("integrity_check" in statement.lower() or "quick_check" in statement.lower()
                             for statement in statements))
        self.assertEqual(self.snapshot(hub), before)

    def test_all_cli_reads_survive_missing_or_malformed_canonical_sources(self):
        for source_state in ("missing", "invalid_utf8", "malformed_record"):
            with self.subTest(source_state=source_state):
                hub, sources = self.make_hub()
                expected = self.all_cli_reads(hub)
                index_before = self.index_snapshot(hub)
                if source_state == "missing":
                    destination = hub.parent / "unavailable-sources"
                    for relative in sources:
                        target = destination / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        (hub / relative).rename(target)
                elif source_state == "invalid_utf8":
                    (hub / OWNER).write_bytes(b"\xff\xfe invalid canonical source")
                else:
                    (hub / OWNER).write_text("<!-- kiroku:entry {broken JSON} -->\n", encoding="utf-8")
                before = self.snapshot(hub)
                self.assertEqual(self.all_cli_reads(hub), expected)
                self.assertEqual(self.snapshot(hub), before)
                self.assertEqual(self.index_snapshot(hub), index_before)

    def test_guided_edits_are_batched_until_one_explicit_checkpoint(self):
        hub, _ = self.make_hub()
        original_index = self.index_snapshot(hub)
        expected = self.all_cli_reads(hub)
        changes = (
            ("add", ("--file", OWNER, "--section", "Active Decisions"), self.creation_payload()),
            ("update", ("DEC-pending",), {"fields": {"Rationale": "Revise unpublishedneedle before publication."}}),
            ("update", (ENTRY_ID,), {"fields": {"Decision": "Replace publishedneedle with revisedneedle."}}),
        )
        for command, arguments, payload in changes:
            with self.subTest(command=command, arguments=arguments):
                result = self.value(self.cli(hub, command, *arguments, payload=payload))
                self.assert_saved(result)
                self.assertEqual(self.index_snapshot(hub), original_index)
                self.assertEqual(self.all_cli_reads(hub), expected)
        self.assertEqual(index_status(hub)["state"], "stale")
        markdown_before = {path: value for path, value in self.snapshot(hub).items() if path.endswith(".md")}
        published = self.value(self.cli(hub, "checkpoint"))
        self.assertEqual(published["state"], "ready")
        self.assertIs(published["changed"], True)
        self.assertNotEqual(self.index_snapshot(hub)[0], original_index[0])
        self.assertEqual(index_status(hub)["state"], "ready")
        with closing(open_index(hub)) as connection:
            pending = memory.show(connection, "entry:DEC-pending")
            self.assertEqual(pending["fields"]["Rationale"], "Revise unpublishedneedle before publication.")
            self.assertEqual(memory.show(connection, NODE_ID)["fields"]["Decision"],
                             "Replace publishedneedle with revisedneedle.")
            self.assertEqual(memory.search(connection, "pendingneedle", None, 8)[0]["id"], "entry:DEC-pending")
            self.assertEqual(len(memory.entries(connection, "decision", None, None, 20, 0)["results"]), 2)
            self.assertTrue(any(edge["source"] == "entry:DEC-pending" and edge["target"] == NODE_ID
                                and edge["relation"] == "depends_on"
                                for edge in memory.related(connection, NODE_ID, 1, 20)["edges"]))
        self.assertEqual({path: value for path, value in self.snapshot(hub).items() if path.endswith(".md")}, markdown_before)

    def test_dry_run_and_noop_preserve_files_even_with_pending_changes(self):
        hub, _ = self.make_hub()
        original_index = self.index_snapshot(hub)
        write_entry(hub, "update", {"title": "Pending published decision"}, entry_id=ENTRY_ID)
        self.assertEqual(index_status(hub)["state"], "stale")
        before = self.snapshot(hub)
        preview = self.value(self.cli(hub, "add", "--file", OWNER, "--section", "Active Decisions",
                                      "--dry-run", payload=self.creation_payload()))
        self.assertEqual(preview["state"], "dry_run")
        self.assertIs(preview["markdown_saved"], False)
        self.assertIn("DEC-pending", preview["diff"])
        self.assertEqual(self.snapshot(hub), before)
        noop = self.value(self.cli(hub, "update", ENTRY_ID, payload={"title": "Pending published decision"}))
        self.assert_saved(noop, changed=False)
        self.assertEqual(self.snapshot(hub), before)
        self.assertEqual(self.index_snapshot(hub), original_index)
        self.assertEqual(index_status(hub)["state"], "stale")

    def test_noop_checkpoint_and_build_alias_preserve_the_existing_snapshot(self):
        hub, _ = self.make_hub()
        before = self.snapshot(hub)
        for command in ("checkpoint", "build"):
            result = self.value(self.cli(hub, command))
            self.assertEqual(result["state"], "ready")
            self.assertIs(result["changed"], False)
            self.assertEqual(self.snapshot(hub), before)

    def test_guided_writes_need_no_database_even_when_missing_or_unusable(self):
        for database_state in ("missing", "foreign"):
            with self.subTest(database_state=database_state):
                hub, _ = self.make_hub()
                target = hub / DB_NAME
                if database_state == "missing":
                    target.unlink()
                else:
                    target.write_bytes(b"An unrelated database must remain untouched.")
                original = self.snapshot(hub)
                original_open = Path.open

                def guarded_open(path, *args, **kwargs):
                    if path.name == DB_NAME:
                        raise AssertionError("The Markdown writer opened the database")
                    return original_open(path, *args, **kwargs)

                def guarded_write(operation, payload, **options):
                    with patch.object(sqlite3, "connect", side_effect=AssertionError("The Markdown writer used SQLite")):
                        with patch.object(Path, "open", guarded_open):
                            return write_entry(hub, operation, payload, **options)

                self.assert_saved(guarded_write(
                    "add", self.creation_payload(), source_file=OWNER, section="Active Decisions"))
                self.assert_saved(guarded_write(
                    "update", {"title": "Updated without a database"}, entry_id="DEC-pending"))
                self.assertIn("### Updated without a database", (hub / OWNER).read_text(encoding="utf-8"))
                before_noop = self.snapshot(hub)
                self.assert_saved(guarded_write(
                    "update", {"title": "Updated without a database"}, entry_id="DEC-pending"), changed=False)
                self.assertEqual(self.snapshot(hub), before_noop)
                self.assertEqual(set(before_noop), set(original))
                if database_state == "missing":
                    self.assertFalse(target.exists())
                else:
                    self.assertEqual(self.index_snapshot(hub), original[DB_NAME])

    def test_invalid_guided_edit_preserves_pending_markdown_and_published_database(self):
        hub, _ = self.make_hub()
        original_index = self.index_snapshot(hub)
        write_entry(hub, "update", {"title": "Pending title"}, entry_id=ENTRY_ID)
        before = self.snapshot(hub)
        invalid = self.value(self.cli(hub, "update", ENTRY_ID, payload={"fields": {"Decision": None}}), exit_code=1)
        self.assertEqual(invalid["state"], "error")
        self.assertEqual(self.snapshot(hub), before)
        self.assertEqual(self.index_snapshot(hub), original_index)
        with closing(open_index(hub)) as connection:
            self.assertEqual(memory.show(connection, NODE_ID)["title"], "Published decision")

    def test_failed_checkpoint_replacement_preserves_previous_reads_and_cleans_temporary_files(self):
        hub, _ = self.make_hub()
        expected = self.all_cli_reads(hub)
        original_index = self.index_snapshot(hub)
        write_entry(hub, "update", {"title": "Pending replacement"}, entry_id=ENTRY_ID)
        before = self.snapshot(hub)
        with patch.object(memory_store.os, "replace", side_effect=OSError("Injected publication failure")):
            with self.assertRaisesRegex(MemoryIndexError, "Injected publication failure"):
                build_index(hub)
        self.assertEqual(self.snapshot(hub), before)
        self.assertEqual(self.index_snapshot(hub), original_index)
        self.assertEqual(self.all_cli_reads(hub), expected)
        self.assertEqual(index_status(hub)["state"], "stale")
        self.assertIs(build_index(hub)["changed"], True)
        with closing(open_index(hub)) as connection:
            self.assertEqual(memory.show(connection, NODE_ID)["title"], "Pending replacement")

    def test_invalid_sources_fail_checkpoint_but_preserve_the_published_snapshot(self):
        hub, _ = self.make_hub()
        expected = self.all_cli_reads(hub)
        original_index = self.index_snapshot(hub)
        (hub / OWNER).write_text("<!-- kiroku:entry {invalid} -->\n", encoding="utf-8")
        before = self.snapshot(hub)
        result = self.value(self.cli(hub, "checkpoint"), exit_code=1)
        self.assertEqual(result["state"], "error")
        self.assertEqual(self.snapshot(hub), before)
        self.assertEqual(self.index_snapshot(hub), original_index)
        self.assertEqual(self.all_cli_reads(hub), expected)

    def test_explicit_status_detects_source_drift_without_publishing(self):
        hub, _ = self.make_hub()
        self.assertEqual(self.value(self.cli(hub, "status"))["state"], "ready")
        target = hub / "tracks/atlas/STATE.md"
        target.write_text("# State\n\n## Current\nUnpublished state.\n", encoding="utf-8")
        before = self.snapshot(hub)
        result = self.value(self.cli(hub, "status"), exit_code=1)
        self.assertEqual(result["state"], "stale")
        self.assertEqual(self.snapshot(hub), before)
        with closing(open_index(hub)) as connection:
            self.assertIn("Published state is stable.", memory.show(connection, "tracks/atlas/STATE.md")["body"])

    def test_missing_and_invalid_databases_remain_errors_without_fallback_to_markdown(self):
        for database_state in ("missing", "foreign", "incompatible"):
            with self.subTest(database_state=database_state):
                hub, _ = self.make_hub()
                target = hub / DB_NAME
                if database_state == "missing":
                    target.unlink()
                elif database_state == "foreign":
                    target.write_bytes(b"This is not a Kiroku SQLite database.")
                else:
                    with closing(sqlite3.connect(target)) as connection:
                        connection.execute("PRAGMA user_version=9999")
                        connection.commit()
                before = self.snapshot(hub)
                with self.assertRaises(MemoryIndexError):
                    open_index(hub)
                requests = (("search", "publishedneedle"), ("show", NODE_ID),
                            ("related", NODE_ID), ("entries",),
                            ("context", "--track", TRACK, "--max-chars", "256"))
                for command, *arguments in requests:
                    response = self.cli(hub, command, *arguments)
                    result = self.value(response, exit_code=1)
                    self.assertEqual(result["state"], "error")
                    if command == "context":
                        self.assertEqual(result["used_chars"], len(response.stdout.decode("utf-8")))
                        self.assertLessEqual(result["used_chars"], 256)
                self.assertEqual(self.snapshot(hub), before)


if __name__ == "__main__":
    unittest.main()
