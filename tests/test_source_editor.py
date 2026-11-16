import importlib.util
from pathlib import Path
import tempfile
import unittest

from triage_knowledge.source_store import SourceKnowledgeStore
from triage_knowledge.retrieval import binding_from_tables, get_triage_knowledge, strategy_binding
from tests.knowledge_support import CUTOFF, tables


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Install the existing editor extra")
class SourceEditorTests(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.domain = root / "domain.md"
        self.original = b"# User notes\nKeep uncertainty explicit.\n"
        self.domain.write_bytes(self.original)
        self.store = SourceKnowledgeStore(root / "source-first")
        self.app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "triage_knowledge" / "editor.py"),
            default_timeout=20).run()
        self.assertEqual(len(self.app.exception), 0)
        self.app.sidebar.text_input[0].set_value(str(self.store.root))
        self.app.sidebar.text_input[1].set_value(str(self.domain))
        self.app.run()
        self.button("Import initial domain").click().run()
        self.assertEqual(len(self.app.exception), 0)

    def button(self, label):
        return next(value for value in self.app.button if value.label == label)

    def text_area(self, label):
        return next(value for value in self.app.text_area if value.label == label)

    def test_source_edit_creates_new_lineage_without_mutating_original(self):
        before, digest = self.store.load_draft()
        self.assertNotIn("rubric", before)
        self.text_area("Revised source text").set_value("User amended condition.\n")
        next(value for value in self.app.text_input if value.label == "Edit reason").set_value(
            "Synthetic source-lineage test")
        self.button("Preview source edit diff").click().run()
        self.assertEqual(self.store.load_draft()[1], digest)
        self.assertTrue(any("+User amended condition." in value.value for value in self.app.code))
        self.button("Save as new user revision").click().run()
        self.assertEqual(len(self.app.exception), 0)
        after, next_digest = self.store.load_draft()
        self.assertNotEqual(digest, next_digest)
        self.assertEqual(self.domain.read_bytes(), self.original)
        self.assertEqual(self.store.source_document("domain").raw, self.original)
        self.assertTrue(any("User amended condition." in item["revision"]["text"]
                            for item in after["items"].values()))
        self.assertTrue(self.button("Publish exact reviewed candidate").disabled)

    def test_invalid_review_is_visible_and_pending_candidate_stays_unchanged(self):
        _, before = self.store.load_draft()
        self.button("Record item review").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertGreater(len(self.app.error), 0)
        self.assertEqual(self.store.load_draft()[1], before)

    def test_invalid_utf8_source_is_visible_without_replacing_saved_draft(self):
        _, digest = self.store.load_draft()
        self.domain.write_bytes(b"\xff")
        self.button("Import initial domain").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("UTF-8" in error.value for error in self.app.error))
        self.assertEqual(self.store.load_draft()[1], digest)

    def test_review_publish_and_retire_require_new_approval_and_preserve_old_pin(self):
        def text_input(label):
            return next(value for value in self.app.text_input if value.label == label)

        def publish():
            text_input("Reviewer").set_value("Software fixture only")
            self.text_area("Review justification").set_value("Mechanical UI regression, not human acceptance.")
            self.button("Record item review").click().run()
            text_input("Author").set_value("Software test")
            self.app.checkbox[0].check().run()
            self.button("Publish exact reviewed candidate").click().run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual([value.value for value in self.app.error], [])
            return next(value.value for value in self.app.code if value.value.startswith("sha256-"))

        initial = publish()
        next(value for value in self.app.sidebar.text_input
             if value.label == "Reviewed release to open for editing").set_value(initial)
        next(value for value in self.app.sidebar.button
             if value.label == "Open release as editable draft").click().run()
        self.assertEqual([value.value for value in self.app.error], [])
        self.assertEqual(self.store.load_draft()[0]["items"],
                         self.store.resolve_release(initial)["candidate"]["items"])
        next(value for value in self.app.selectbox if value.label == "Desired lifecycle").set_value("retired")
        text_input("Lifecycle or rejection reason").set_value("Explicit software-fixture withdrawal.")
        self.button("Save lifecycle for review").click().run()
        candidate, _ = self.store.load_draft()
        self.assertTrue(all(item["review_state"] == "pending" for item in candidate["items"].values()))
        self.assertTrue(self.button("Publish exact reviewed candidate").disabled)
        withdrawn = publish()
        self.assertNotEqual(initial, withdrawn)
        findings, registry = tables()
        query = {"findings": {row["finding_id"]: row for row in findings.rows},
                 "registry": {row["equipment_id"]: row for row in registry.rows}}

        def retrieve(version):
            return get_triage_knowledge(
                self.store, query, knowledge_version=version, assessment_time=CUTOFF,
                expected_strategy=strategy_binding(),
                allowed_input_binding=binding_from_tables(findings, registry), max_bytes=64000)

        self.assertIn(self.original.decode(), retrieve(initial).provider_payload().values())
        retired_result = retrieve(withdrawn)
        self.assertEqual(retired_result.to_dict()["error_code"], "knowledge_gap")
        self.assertEqual(retired_result.provider_payload(), {})


if __name__ == "__main__":
    unittest.main()
