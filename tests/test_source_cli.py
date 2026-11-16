from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from triage_knowledge.source_cli import main, write_new_json
from triage_knowledge.source_store import SourceKnowledgeStore


class SourceCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store_path = self.root / "source-first"

    def invoke(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(["--store", str(self.store_path), *args])
        return status, out.getvalue(), err.getvalue()

    def test_import_uses_source_bytes_and_stale_review_does_not_publish(self):
        source = self.root / "source.md"
        raw = b"\xef\xbb\xbf# User notes\r\nKeep the original condition.\r\n"
        source.write_bytes(raw)
        status, out, error = self.invoke("import-source", "--source", str(source),
                                         "--name", "Synthetic source", "--source-id", "fixture")
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(json.loads(out)["status"], "pending_review")
        store = SourceKnowledgeStore(self.store_path)
        candidate, digest = store.load_draft()
        self.assertEqual(store.source_document("fixture").raw, raw)
        item = next(iter(candidate["items"]))
        status, out, error = self.invoke(
            "review", "--item", item, "--reviewer", "Software test",
            "--reason", "Stale edit test", "--expected-digest", "0" * 64)
        self.assertEqual((status, out), (1, ""))
        self.assertIn("error_class", json.loads(error))
        self.assertEqual(store.load_draft()[1], digest)
        self.assertEqual(source.read_bytes(), raw)

    def test_old_output_is_unchanged_when_destination_exists(self):
        destination = self.root / "previous.json"
        destination.write_bytes(b"previous output")
        with self.assertRaises(FileExistsError):
            write_new_json(destination, {"replacement": True})
        self.assertEqual(destination.read_bytes(), b"previous output")

    def test_status_distinguishes_pending_draft_releases_and_deployment(self):
        source = self.root / "source.txt"
        source.write_bytes(b"Only user-written knowledge.\n")
        status, out, error = self.invoke("status")
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(json.loads(out)["releases"], [])
        self.assertIsNone(json.loads(out)["candidate_digest"])
        self.invoke("import-source", "--source", str(source), "--name", "User source")
        store = SourceKnowledgeStore(self.store_path)
        candidate, digest = store.load_draft()
        item = next(iter(candidate["items"]))
        digest = store.review_item(item, reviewer="Software fixture",
                                   reason="Storage test only", expected_digest=digest)
        release = store.publish(expected_digest=digest, author="Software fixture",
                                reviewer="Software fixture", reason="Storage test only",
                                reviewed_at="2026-07-01T00:00:00Z")
        status, out, error = self.invoke("status")
        self.assertEqual((status, error), (0, ""))
        record = json.loads(out)
        self.assertEqual(record["releases"][0]["knowledge_version"], release)
        self.assertEqual(record["review_counts"]["reviewed"], 1)
        self.assertFalse(record["legacy_draft_used"])
        self.assertIsNone(record["workflow_pin"])
        release_path = self.store_path / "releases" / (release + ".json")
        release_path.write_bytes(b"{}")
        status, out, error = self.invoke("status")
        self.assertEqual((status, out), (1, ""))
        self.assertIn("error_class", json.loads(error))


if __name__ == "__main__":
    unittest.main()
