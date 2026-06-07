from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kiroku_core.io import record_hash  # noqa: E402
from kiroku_core.viewer import (  # noqa: E402
    InvalidMemoryError,
    create_viewer_server,
)


SCHEMA = ROOT / "schemas" / "memory-v2.schema.json"
ASSETS = ROOT / "assets" / "viewer"
FIXTURE = ROOT / "tests" / "fixtures" / "valid-memory.json"
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser")


class ViewerServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.memory_dir = Path(self.temporary.name) / "kiroku"
        self.memory_dir.mkdir()
        self.memory_path = self.memory_dir / "memory.json"
        memory = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for record in memory["records"]:
            record["content_hash"] = record_hash(record)
        self.memory_path.write_text(
            json.dumps(memory, indent=2) + "\n",
            encoding="utf-8",
        )
        self.server = create_viewer_server(
            self.memory_dir,
            SCHEMA,
            ASSETS,
            port=0,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
    ) -> tuple[int, dict[str, str], bytes]:
        request = Request(self.base_url + path, method=method)
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, dict(response.headers), response.read()
        except HTTPError as exc:
            try:
                return exc.code, dict(exc.headers), exc.read()
            finally:
                exc.close()

    def json_request(
        self,
        path: str,
        *,
        method: str = "GET",
    ) -> tuple[int, dict[str, str], dict]:
        status, headers, body = self.request(path, method=method)
        return status, headers, json.loads(body)

    def browser_dom(self, path: str) -> str:
        if CHROMIUM is None:
            self.skipTest("Chromium is not available")
        profile = tempfile.mkdtemp(
            prefix="chromium-profile-",
            dir=self.temporary.name,
        )
        result = subprocess.run(
            [
                CHROMIUM,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-sync",
                "--metrics-recording-only",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={profile}",
                "--virtual-time-budget=3000",
                "--dump-dom",
                self.base_url + path,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
        self.assertEqual(0, result.returncode, result.stderr[-2000:])
        self.assertNotIn(
            "violates the following Content Security Policy",
            result.stderr,
        )
        return result.stdout

    def test_server_binds_only_to_ipv4_loopback(self) -> None:
        self.assertEqual("127.0.0.1", self.server.server_address[0])

    def test_meta_returns_validated_project_summary_and_counts(self) -> None:
        status, headers, payload = self.json_request("/api/v1/meta")

        self.assertEqual(200, status)
        self.assertEqual("no-store", headers["Cache-Control"])
        self.assertEqual("1", payload["api_version"])
        self.assertEqual("2.0.0", payload["schema_version"])
        self.assertTrue(payload["memory_hash"].startswith("sha256:"))
        self.assertEqual("Example Project", payload["data"]["project"]["name"])
        self.assertEqual(3, payload["data"]["counts"]["records"])
        self.assertEqual(50, payload["data"]["page_limits"]["default"])

    def test_records_share_query_semantics_and_paginate(self) -> None:
        status, _, payload = self.json_request(
            "/api/v1/records?type=decision&search=canonical&limit=1"
        )

        self.assertEqual(200, status)
        self.assertEqual(1, payload["page"]["total"])
        self.assertEqual(1, payload["page"]["returned"])
        self.assertEqual("decision_canonical_json", payload["data"][0]["key"])
        self.assertNotIn("content_hash", payload["data"][0])

    def test_record_detail_resolves_sources_and_incoming_relations(self) -> None:
        status, _, payload = self.json_request(
            "/api/v1/records/rec_decision_canonical_json"
        )

        self.assertEqual(200, status)
        data = payload["data"]
        self.assertIn("content_hash", data["record"])
        self.assertEqual("src_user_message", data["evidence_sources"][0]["id"])
        self.assertEqual(
            "rec_task_add_validation",
            data["incoming_relations"][0]["source_id"],
        )

    def test_source_and_run_details_include_reverse_record_ids(self) -> None:
        source_status, _, source = self.json_request(
            "/api/v1/sources/src_user_message"
        )
        run_status, _, run = self.json_request(
            "/api/v1/runs/run_initial_extract"
        )

        self.assertEqual(200, source_status)
        self.assertEqual(200, run_status)
        self.assertEqual(2, len(source["data"]["record_ids"]))
        self.assertEqual(3, len(run["data"]["record_ids"]))

    def test_unknown_duplicate_and_out_of_range_query_is_rejected(self) -> None:
        paths = (
            "/api/v1/records?unknown=x",
            "/api/v1/records?type=fact&type=decision",
            "/api/v1/records?limit=201",
        )

        for path in paths:
            with self.subTest(path=path):
                status, _, payload = self.json_request(path)
                self.assertEqual(400, status)
                self.assertEqual("invalid_query", payload["error"]["code"])

    def test_missing_resource_and_asset_traversal_are_not_found(self) -> None:
        for path in (
            "/api/v1/records/rec_missing",
            "/assets/%2e%2e/%2e%2e/SKILL.md",
        ):
            with self.subTest(path=path):
                status, _, payload = self.json_request(path)
                self.assertEqual(404, status)
                self.assertEqual("not_found", payload["error"]["code"])

    def test_mutating_methods_are_rejected_as_read_only(self) -> None:
        for method in ("POST", "TRACE"):
            with self.subTest(method=method):
                status, headers, payload = self.json_request(
                    "/api/v1/records",
                    method=method,
                )

                self.assertEqual(405, status)
                self.assertEqual("GET, HEAD", headers["Allow"])
                self.assertEqual("read_only", payload["error"]["code"])

    def test_head_returns_headers_without_a_body(self) -> None:
        status, headers, body = self.request("/api/v1/meta", method="HEAD")

        self.assertEqual(200, status)
        self.assertGreater(int(headers["Content-Length"]), 0)
        self.assertEqual(b"", body)

    def test_assets_and_browser_deep_links_are_confined_to_skill_assets(self) -> None:
        index_status, index_headers, index = self.request("/records/rec_example")
        css_status, _, css = self.request("/assets/app.css")

        self.assertEqual(200, index_status)
        self.assertIn("text/html", index_headers["Content-Type"])
        self.assertIn(b"Kiroku Viewer", index)
        self.assertEqual(200, css_status)
        self.assertIn(b"color-scheme", css)

    def test_all_browser_routes_return_spa_shell(self) -> None:
        routes = [
            "/",
            "/records",
            "/records/rec_example",
            "/sources",
            "/sources/src_example",
            "/runs",
            "/runs/run_example",
        ]
        for route in routes:
            with self.subTest(route=route):
                status, headers, body = self.request(route)
                self.assertEqual(200, status)
                self.assertIn("text/html", headers["Content-Type"])
                self.assertIn(b"<script src=\"/assets/app.js\"></script>", body)
                self.assertIn(b"<nav id=\"top-nav\"", body)

    def test_js_and_css_assets_are_served(self) -> None:
        js_status, js_headers, js_body = self.request("/assets/app.js")
        css_status, css_headers, css_body = self.request("/assets/app.css")

        self.assertEqual(200, js_status)
        self.assertIn("javascript", js_headers.get("Content-Type", "").lower())
        self.assertIn(b'"use strict"', js_body)

        self.assertEqual(200, css_status)
        self.assertIn("css", css_headers.get("Content-Type", "").lower())
        self.assertIn(b"color-scheme", css_body)

    def test_spa_shell_contains_no_memory_data_inline(self) -> None:
        status, headers, body = self.request("/")
        self.assertEqual(200, status)

        body_str = body.decode("utf-8")
        self.assertNotIn("canonical_json", body_str)
        self.assertNotIn("Example Project", body_str)
        self.assertNotIn("memory.json", body_str)

    def test_spa_uses_safe_dom_rendering_without_inline_styles(self) -> None:
        status, _, body = self.request("/assets/app.js")
        self.assertEqual(200, status)

        script = body.decode("utf-8")
        self.assertNotIn(".innerHTML", script)
        self.assertNotIn("style:", script)
        self.assertIn("k.slice(2).toLowerCase()", script)

    def test_csp_header_on_html_responses(self) -> None:
        status, headers, _ = self.request("/")
        self.assertEqual(200, status)
        self.assertIn("Content-Security-Policy", headers)
        csp = headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("style-src 'self'", csp)
        self.assertNotIn("'unsafe-inline'", csp)

    @unittest.skipUnless(CHROMIUM, "Chromium is not available")
    def test_browser_executes_explorer_filters_and_deep_links(self) -> None:
        explorer = self.browser_dom(
            "/records?tag=architecture"
            "&verification_status=verified"
            "&sort=title"
            "&sort_dir=desc"
        )

        self.assertIn("Canonical JSON memory", explorer)
        self.assertNotIn("error-banner", explorer)
        self.assertIn('name="verification_status"', explorer)
        self.assertIn('value="verified" selected', explorer)
        self.assertIn('name="sort_dir"', explorer)
        self.assertIn('value="desc" selected', explorer)
        self.assertIn("<h2", explorer)
        self.assertIn("Record Status Legend</h2>", explorer)
        self.assertEqual(7, explorer.count('class="status-legend-item"'))
        self.assertIn(
            "Status describes the lifecycle of a record, not how strongly "
            "it is verified.",
            explorer,
        )
        self.assertIn(
            "Replaced by a newer record and retained only as history.",
            explorer,
        )
        self.assertIn(
            "Planned work finished and supported by completion evidence.",
            explorer,
        )

        grouped = self.browser_dom("/records?sort=type&sort_dir=asc")
        self.assertEqual(3, grouped.count('class="record-type-group"'))
        self.assertIn(
            '<h2 id="record-type-decision">Decision</h2>',
            grouped,
        )
        self.assertIn(
            '<h2 id="record-type-risk">Risk</h2>',
            grouped,
        )
        self.assertIn(
            '<h2 id="record-type-task">Task</h2>',
            grouped,
        )
        self.assertIn('aria-label="Decision records"', grouped)
        self.assertIn("1 record on this page", grouped)
        self.assertLess(
            grouped.index('id="record-type-decision"'),
            grouped.index('id="record-type-risk"'),
        )
        self.assertLess(
            grouped.index('id="record-type-risk"'),
            grouped.index('id="record-type-task"'),
        )

        related = self.browser_dom(
            "/records?key=task_add_validation"
            "&relation_target=rec_decision_canonical_json"
            "&relation_type=implements"
        )
        self.assertIn("Add semantic validation", related)
        self.assertNotIn("Canonical JSON memory</a>", related)
        self.assertIn('name="key"', related)
        self.assertIn('name="relation_target"', related)
        self.assertIn('name="relation_type"', related)
        self.assertIn('value="implements" selected', related)

        record = self.browser_dom(
            "/records/rec_decision_canonical_json"
        )
        self.assertIn("<h1>Canonical JSON memory</h1>", record)
        self.assertIn("Locator:", record)
        self.assertIn("message_id=message-1", record)
        self.assertIn("Observed:", record)

        source = self.browser_dom("/sources/src_user_message")
        self.assertIn("<h1>Initial project decision</h1>", source)

        run = self.browser_dom("/runs/run_initial_extract")
        self.assertIn("<h1>Run Detail</h1>", run)
        self.assertIn("run_initial_extract", run)

    def test_requests_do_not_modify_selected_memory_directory(self) -> None:
        before = {
            path.relative_to(self.memory_dir): (
                path.read_bytes(),
                path.stat().st_mtime_ns,
            )
            for path in self.memory_dir.rglob("*")
            if path.is_file()
        }

        self.json_request("/api/v1/meta")
        self.json_request("/api/v1/records?search=memory")
        self.json_request("/api/v1/sources")
        self.json_request("/api/v1/runs")

        after = {
            path.relative_to(self.memory_dir): (
                path.read_bytes(),
                path.stat().st_mtime_ns,
            )
            for path in self.memory_dir.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_invalid_memory_after_start_returns_diagnostics(self) -> None:
        memory = json.loads(self.memory_path.read_text(encoding="utf-8"))
        memory["records"][0]["title"] = ""
        memory["records"][0]["content_hash"] = record_hash(memory["records"][0])
        self.memory_path.write_text(json.dumps(memory), encoding="utf-8")

        status, _, payload = self.json_request("/api/v1/meta")

        self.assertEqual(422, status)
        self.assertEqual("invalid_memory", payload["error"]["code"])
        self.assertTrue(payload["error"]["details"])

    def test_valid_external_change_is_reloaded_without_restart(self) -> None:
        _, _, initial = self.json_request("/api/v1/meta")
        memory = json.loads(self.memory_path.read_text(encoding="utf-8"))
        memory["project"]["name"] = "Renamed Project"
        self.memory_path.write_text(json.dumps(memory), encoding="utf-8")

        status, _, updated = self.json_request("/api/v1/meta")

        self.assertEqual(200, status)
        self.assertEqual("Renamed Project", updated["data"]["project"]["name"])
        self.assertNotEqual(initial["memory_hash"], updated["memory_hash"])


class ViewerStartupTests(unittest.TestCase):
    def test_invalid_memory_prevents_server_startup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory_dir = Path(directory)
            memory = json.loads(FIXTURE.read_text(encoding="utf-8"))
            memory["records"][0]["title"] = ""
            (memory_dir / "memory.json").write_text(
                json.dumps(memory),
                encoding="utf-8",
            )

            with self.assertRaises(InvalidMemoryError):
                create_viewer_server(
                    memory_dir,
                    SCHEMA,
                    ASSETS,
                    port=0,
                )


if __name__ == "__main__":
    unittest.main()
