from __future__ import annotations

import csv
import io
from pathlib import Path
import tempfile
import unittest

from triage_knowledge.contracts import KnowledgeError, TableSource
from triage_knowledge.source import SourceDocument, extract_code
from triage_knowledge.source_store import SourceKnowledgeStore
from triage_knowledge.retrieval import strategy_binding
from triage_knowledge.source_context import build_source_context


def table(row: dict, source_id: str, kind: str) -> TableSource:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return TableSource.from_bytes(stream.getvalue().encode(), source_id=source_id, kind=kind)


class SourceContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = SourceKnowledgeStore(Path(self.temporary.name) / "source-first")
        document = SourceDocument.from_bytes(
            b"# Shared guidance\nKeep uncertainty explicit.\n\n"
            b"## Rotor rule\nScope: Rotor-A\nUse the source condition, not an invented score.\n",
            name="Synthetic software fixture", source_id="fixture")
        digest = self.store.create_draft([extract_code(document)])
        candidate, _ = self.store.load_draft()
        for item_id in candidate["items"]:
            digest = self.store.review_item(item_id, reviewer="Software fixture only",
                                            reason="Not actual human acceptance", expected_digest=digest)
        self.version = self.store.publish(
            expected_digest=digest, author="Software fixture", reviewer="Software fixture only",
            reason="Mechanical handoff test, not production release",
            reviewed_at="2026-07-01T00:00:00+00:00")
        self.findings = table({
            "finding_id": "F-9001", "reported_date": "2026-06-01", "equipment_id": "EQ-9001",
            "equipment_type": "Rotor-A", "inspection_type": "Routine Operator Round",
            "inspection_method": "Visual", "finding_description": "Synthetic condition record.",
            "reported_by": "Test author", "reporter_role": "Test engineer",
        }, "findings", "finding_input")
        self.registry = table({
            "equipment_id": "EQ-9001", "equipment_type": "Rotor-A",
            "service_description": "Synthetic item", "criticality_score": "5",
            "reliability_score": "5", "safety_critical_element": "No", "redundancy": "None",
            "engineer_comment": "Independent comment delivery marker.",
        }, "registry", "registry_input")

    def build(self, **overrides):
        options = {"knowledge_version": self.version, "assessment_time": "2026-07-01T00:00:00+00:00",
                   "expected_strategy": strategy_binding(),
                   "assessment_policy": {"version": "fixture-policy-v1",
                                         "instructions": "Workflow-owned synthetic policy."},
                   "max_bytes": 64_000}
        options.update(overrides)
        return build_source_context(self.store, self.findings, self.registry, **options)

    def test_exact_provider_context_excludes_editorial_and_legacy_rubric(self):
        bundle = self.build()
        context = bundle.to_dict()
        self.assertEqual(context["contract_version"], 2)
        self.assertEqual(context["payload"]["registry"]["EQ-9001"]["engineer_comment"],
                         "Independent comment delivery marker.")
        self.assertEqual(context["source_index"]["equipment:EQ-9001:engineer_comment"],
                         "Independent comment delivery marker.")
        self.assertEqual(context["assessment_policy"]["version"], "fixture-policy-v1")
        self.assertNotIn("rubric", context["payload"]["knowledge"])
        self.assertNotIn("Software fixture only", bundle.encoded.decode())
        self.assertNotIn("source_manifest", context)
        self.assertEqual(bundle.evidence()["source_manifest"][0]["sha256"], self.findings.raw_sha256)

    def test_full_request_size_and_missing_workflow_policy_fail(self):
        complete = self.build()
        with self.assertRaises(KnowledgeError) as raised:
            self.build(max_bytes=len(complete.encoded) - 1)
        self.assertEqual(raised.exception.code, "context_limit")
        with self.assertRaises(KnowledgeError):
            self.build(assessment_policy={})

    def test_blank_source_preambles_survive_context_materialization(self):
        for number, prefix in enumerate((b"\n", b"\r\n")):
            with self.subTest(prefix=prefix):
                document = SourceDocument.from_bytes(
                    prefix + b"# Additional condition\nKeep the original qualifier.\n",
                    name="Whitespace software fixture", source_id=f"blank-{number}")
                _, digest = self.store.load_draft()
                digest = self.store.add_source(extract_code(document), expected_digest=digest)
                candidate, _ = self.store.load_draft()
                for item_id, item in candidate["items"].items():
                    if item["review_state"] == "pending":
                        digest = self.store.review_item(
                            item_id, reviewer="Software fixture only",
                            reason="Whitespace context regression", expected_digest=digest)
                self.version = self.store.publish(
                    expected_digest=digest, author="Software fixture", reviewer="Software fixture only",
                    reason="Mechanical whitespace test only", reviewed_at="2026-07-01T00:00:00+00:00")
                context = self.build().to_dict()
                self.assertIn(prefix.decode("utf-8"), context["payload"]["knowledge"].values())
                for address, text in context["payload"]["knowledge"].items():
                    self.assertEqual(context["source_index"][address], text)
                self.assertEqual(self.build().encoded, self.build().encoded)


if __name__ == "__main__":
    unittest.main()
