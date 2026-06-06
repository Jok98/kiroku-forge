from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kiroku_core.bootstrap import build_bootstrap  # noqa: E402
from kiroku_core.io import record_hash, write_text_if_changed  # noqa: E402
from kiroku_core.rendering import render_views  # noqa: E402


FIXTURE = ROOT / "tests" / "fixtures" / "valid-memory.json"


def fixture() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for record in data["records"]:
        record["content_hash"] = record_hash(record)
    return data


class ProjectionTests(unittest.TestCase):
    def test_each_record_appears_in_exactly_one_primary_view(self) -> None:
        memory = fixture()
        views = render_views(memory)
        primary = {
            name: content
            for name, content in views.items()
            if name not in {"INDEX.md", "sources.md"}
        }
        for record in memory["records"]:
            marker = f"<!-- record:{record['id']} -->"
            count = sum(content.count(marker) for content in primary.values())
            self.assertEqual(1, count, record["id"])

    def test_bootstrap_scope_filter(self) -> None:
        memory = fixture()
        memory["records"][2]["scope"] = ["other"]
        bootstrap = build_bootstrap(memory, scope="example")
        ids = {record["id"] for record in bootstrap["records"]}
        self.assertNotIn("rec_risk_missing_evidence", ids)

    def test_unchanged_projection_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.md"
            self.assertTrue(write_text_if_changed(path, "same\n"))
            first_mtime = path.stat().st_mtime_ns
            time.sleep(0.01)
            self.assertFalse(write_text_if_changed(path, "same\n"))
            self.assertEqual(first_mtime, path.stat().st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
