from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy

from tests.knowledge_support import CUTOFF, DOMAIN, KnowledgeCase, tables
from triage_knowledge.legacy_cli import main
from triage_knowledge import KnowledgeStore

HAS_EDITOR = importlib.util.find_spec("streamlit") is not None


class CliTests(KnowledgeCase):
    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["--store", str(self.store.root), "--domain", str(self.domain), *args])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_cli_validation_failure_is_json_and_nonzero(self):
        status, stdout, stderr = self.invoke("check")
        # This store intentionally pins a different logical locator than the CLI configuration.
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error_class"], "domain_hash")

    def test_cli_init_check_publish_and_context_with_old_output_preserved(self):
        self.store = KnowledgeStore(self.root / "cli-knowledge", self.domain)
        status, output, error = self.invoke("init")
        self.assertEqual((status, error), (0, ""))
        digest = json.loads(output)["candidate_digest"]
        self.assertFalse(json.loads(output)["approved"])
        self.assertEqual(self.invoke("check")[0], 0)
        self.assertEqual(self.invoke("diff")[0], 0)
        status, output, error = self.invoke(
            "publish", "--candidate-digest", digest, "--author", "Test author",
            "--reviewer", "Test reviewer", "--reason", "Synthetic CLI software test only.")
        self.assertEqual((status, error), (0, ""))
        version = json.loads(output)["knowledge_version"]
        finding_source, registry_source = tables()
        findings, registry = self.root / "findings.csv", self.root / "registry.csv"
        findings.write_bytes(finding_source.raw)
        registry.write_bytes(registry_source.raw)
        destination = self.root / "context.json"
        args = ("context", "--release", version, "--findings", str(findings),
                "--registry", str(registry), "--assessment-time", CUTOFF, "--output", str(destination))
        status, output, error = self.invoke(*args)
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(json.loads(output)["provider_sends"], 0)
        old = destination.read_bytes()
        self.assertEqual(self.invoke(*args)[0], 1)
        self.assertEqual(destination.read_bytes(), old)
        self.assertEqual(self.invoke(*args, "--max-context-bytes", "1")[0], 1)
        self.assertEqual(destination.read_bytes(), old)

    def test_headless_import_does_not_import_editor_or_inference(self):
        process = subprocess.run([sys.executable, "-B", "-c",
                                  "import sys; import triage_knowledge; "
                                  "assert 'streamlit' not in sys.modules; "
                                  "assert 'llm_inference' not in sys.modules; "
                                  "assert 'eval' not in sys.modules"], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_cli_upgrade_and_retire_are_digest_checked_and_do_not_publish(self):
        self.store = KnowledgeStore(self.root / "cli-knowledge", self.domain)
        self.assertEqual(self.invoke("init")[0], 0)
        candidate, digest = self.store.load_draft()
        legacy = deepcopy(candidate)
        legacy["schema_version"] = 1
        for entry in legacy["guidance"].values():
            del entry["lifecycle"]
        digest = self.store.save_draft(legacy, expected_digest=digest)
        self.assertEqual(self.invoke("upgrade", "--expected-digest", "0" * 64)[0], 1)
        status, output, error = self.invoke("upgrade", "--expected-digest", digest)
        self.assertEqual((status, error), (0, ""))
        digest = json.loads(output)["candidate_digest"]
        status, output, error = self.invoke(
            "retire", "--guidance-id", "psv-assessment", "--reason", "Withdraw obsolete instructions.",
            "--expected-digest", digest)
        self.assertEqual((status, error), (0, ""))
        self.assertFalse(json.loads(output)["approved"])
        self.assertEqual(self.store.load_draft()[0]["guidance"]["psv-assessment"]["lifecycle"]["status"], "retired")
        status, output, error = self.invoke("check", "--assessment-time", CUTOFF)
        self.assertEqual((status, error), (0, ""))
        result = json.loads(output)
        self.assertEqual(result["effective_guidance_ids"], [])
        self.assertEqual(result["excluded_guidance"], {"psv-assessment": "retired"})
        self.assertNotIn("active_guidance_ids", result)
        self.assertFalse((self.store.root / "releases").exists())


@unittest.skipUnless(HAS_EDITOR, "Install the declared editor extra to exercise Streamlit.")
class EditorTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.domain = self.root / "domain.md"
        self.domain.write_bytes(DOMAIN)
        self.store = KnowledgeStore(self.root / "knowledge", self.domain)
        editor = Path(__file__).resolve().parents[1] / "triage_knowledge" / "legacy_editor.py"
        self.app = AppTest.from_file(str(editor), default_timeout=15).run()
        self.app.sidebar.text_input[0].set_value(str(self.store.root))
        self.app.sidebar.text_input[1].set_value(str(self.domain))
        self.app.run()
        self.button("Create initial draft").click().run()
        self.assertEqual(len(self.app.exception), 0)

    def button(self, label):
        return next(value for value in self.app.button if value.label == label)

    def text_area(self, label):
        return next(value for value in self.app.text_area if value.label == label)

    def test_psv_form_diff_review_publish_and_explicit_fork(self):
        self.assertTrue(self.button("Publish reviewed release").disabled)
        revised = "Use documented functional-test evidence and retain uncertainty about unsupported claims."
        self.text_area("Assessment guidance").set_value(revised)
        self.button("Validate and save guidance").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertFalse((self.store.root / "releases").exists())
        self.assertEqual(self.store.load_draft()[0]["guidance"]["psv-assessment"]["guidance"], revised)
        next(x for x in self.app.text_input if x.label == "Declared author").set_value("Test author")
        next(x for x in self.app.text_input if x.label == "Declared reviewer").set_value("Test reviewer")
        self.text_area("Review rationale").set_value("UI software test, not an engineering approval.")
        next(x for x in self.app.checkbox if x.label.startswith("I reviewed")).check()
        self.app.run()
        self.assertFalse(self.button("Publish reviewed release").disabled)
        self.button("Publish reviewed release").click().run()
        self.assertEqual(len(self.app.exception), 0)
        paths = list((self.store.root / "releases").glob("*.json"))
        self.assertEqual(len(paths), 1)
        snapshot = self.store.resolve_knowledge(paths[0].stem)
        self.assertEqual(snapshot.candidate["guidance"]["psv-assessment"]["guidance"], revised)
        self.text_area("Assessment guidance").set_value("Unsaved widget text that must not enter the fork.")
        self.button("Start next draft from this release").click().run()
        self.assertEqual(self.store.load_draft()[0]["base_release_id"], snapshot.knowledge_version)
        self.assertEqual(self.text_area("Assessment guidance").value, revised)

    def test_invalid_draft_has_explicit_archive_recovery(self):
        self.store.draft_path.write_bytes(b'{"broken":')
        self.app.sidebar.button[0].click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(self.button("Archive invalid draft and reset").disabled)
        next(x for x in self.app.checkbox if x.label.startswith("Archive the invalid")).check().run()
        self.button("Archive invalid draft and reset").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(list((self.store.root / "drafts" / "archive").glob("*.json"))), 1)
        self.assertTrue(self.button("Publish reviewed release").disabled)

    def test_invalid_guidance_stays_unpublished(self):
        original = self.store.draft_path.read_bytes()
        next(x for x in self.app.text_input if x.label == "Declared author").set_value("Test author")
        next(x for x in self.app.text_input if x.label == "Declared reviewer").set_value("Test reviewer")
        self.text_area("Review rationale").set_value("Software test only.")
        next(x for x in self.app.checkbox if x.label.startswith("I reviewed")).check().run()
        self.assertFalse(self.button("Publish reviewed release").disabled)
        next(x for x in self.app.text_input if x.label == "Title").set_value(" ")
        self.button("Validate and save guidance").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("schema:" in x.value for x in self.app.error))
        self.assertEqual(original, self.store.draft_path.read_bytes())
        self.assertTrue(self.button("Publish reviewed release").disabled)
        self.assertFalse((self.store.root / "releases").exists())

    def test_stale_tab_does_not_overwrite_newer_draft(self):
        candidate, digest = self.store.load_draft()
        candidate["guidance"]["psv-assessment"]["change_reason"] = "A separately saved edit."
        self.store.save_draft(candidate, expected_digest=digest)
        expected = self.store.draft_path.read_bytes()
        self.text_area("Assessment guidance").set_value("Unsaved work from the stale tab.")
        self.button("Validate and save guidance").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("stale_draft:" in x.value for x in self.app.error))
        self.assertEqual(expected, self.store.draft_path.read_bytes())
        self.assertEqual(self.text_area("Assessment guidance").value, "Unsaved work from the stale tab.")

    def test_engineer_can_schedule_retire_and_restore_guidance_without_editing_json(self):
        until = next(x for x in self.app.text_input if x.label.startswith("Effective until"))
        until.set_value(CUTOFF)
        self.button("Validate and save guidance").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("expired" in value.value for value in self.app.json))
        next(x for x in self.app.checkbox if x.label.startswith("Retire guidance")).check()
        self.text_area("Retirement reason (clear when restoring active guidance)").set_value("Engineer withdrawal.")
        self.button("Validate and save guidance").click().run()
        entry = self.store.load_draft()[0]["guidance"]["psv-assessment"]
        self.assertEqual(entry["lifecycle"]["status"], "retired")
        self.assertTrue(any("retired" in value.value for value in self.app.json))
        next(x for x in self.app.checkbox if x.label.startswith("Retire guidance")).uncheck()
        self.text_area("Retirement reason (clear when restoring active guidance)").set_value("")
        next(x for x in self.app.text_input if x.label.startswith("Effective until")).set_value("")
        self.button("Validate and save guidance").click().run()
        self.assertEqual(self.store.load_draft()[0]["guidance"]["psv-assessment"]["lifecycle"]["status"], "active")
        self.assertEqual(len(self.app.exception), 0)
        self.assertFalse((self.store.root / "releases").exists())

    def test_legacy_editor_upgrade_is_explicit_and_preserves_guidance(self):
        candidate, digest = self.store.load_draft()
        candidate["schema_version"] = 1
        for entry in candidate["guidance"].values():
            del entry["lifecycle"]
        self.store.save_draft(candidate, expected_digest=digest)
        self.app.sidebar.button[0].click().run()
        self.assertFalse(any(value.label == "Publish reviewed release" for value in self.app.button))
        self.button("Upgrade saved draft and reload (discard unsaved edits)").click().run()
        saved, _ = self.store.load_draft()
        self.assertEqual(saved["schema_version"], 2)
        self.assertEqual(saved["guidance"]["psv-assessment"]["guidance"],
                         candidate["guidance"]["psv-assessment"]["guidance"])
        self.assertEqual(len(self.app.exception), 0)
