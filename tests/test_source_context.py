from __future__ import annotations

import csv
import io
from pathlib import Path
import tempfile
import unittest

from triage_knowledge.contracts import KnowledgeError, TableSource, canonical_bytes, sha256
from triage_knowledge.source import SourceDocument, extract_code
from triage_knowledge.source_store import SourceKnowledgeStore
from triage_knowledge.retrieval import strategy_binding
from triage_knowledge.source_context import (SourceContext, build_source_context,
                                             validate_source_context)


def table(row: dict | list[dict], source_id: str, kind: str) -> TableSource:
    rows = row if isinstance(row, list) else [row]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return TableSource.from_bytes(stream.getvalue().encode(), source_id=source_id, kind=kind)


def rehashed(packet: dict) -> bytes:
    body = {key: value for key, value in packet.items() if key != "context_hash"}
    return canonical_bytes({**body, "context_hash": sha256(canonical_bytes(body))})


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
        self.policy = {"version": "fixture-policy-v1",
                       "instructions": "Workflow-owned synthetic policy."}

    def build(self, **overrides):
        options = {"knowledge_version": self.version, "assessment_time": "2026-07-01T00:00:00+00:00",
                   "expected_strategy": strategy_binding(),
                   "assessment_policy": self.policy,
                   "max_bytes": 64_000}
        options.update(overrides)
        return build_source_context(self.store, self.findings, self.registry, **options)

    def validate(self, bundle, **overrides):
        options = {"knowledge_version": self.version, "assessment_time": "2026-07-01T00:00:00+00:00",
                   "expected_strategy": strategy_binding(),
                   "expected_assessment_policy": self.policy, "max_bytes": 64_000}
        options.update(overrides)
        return validate_source_context(bundle, self.findings, self.registry, self.store, **options)

    def test_consumer_rebuilds_local_evidence_and_accepts_semantic_row_order(self):
        frow, rrow = self.findings.rows[0], self.registry.rows[0]
        self.findings = table([frow, {**frow, "finding_id": "F-9002", "equipment_id": "EQ-9002"}],
                              "findings", "finding_input")
        self.registry = table([rrow, {**rrow, "equipment_id": "EQ-9002"}],
                              "registry", "registry_input")
        original = self.build()
        self.findings = table(list(reversed(self.findings.rows)), "findings", "finding_input")
        self.registry = table(list(reversed(self.registry.rows)), "registry", "registry_input")
        for supplied in (original, original.encoded, b" \n" + original.encoded):
            with self.subTest(kind=type(supplied)):
                validated = self.validate(supplied)
                self.assertEqual(validated.encoded, original.encoded)
                self.assertEqual(validated.evidence(), self.build().evidence())
                self.assertNotEqual(validated.evidence()["source_manifest"],
                                    original.evidence()["source_manifest"])
                snapshot = validated.to_dict()
                snapshot["payload"]["knowledge"].clear()
                self.assertTrue(validated.to_dict()["payload"]["knowledge"])
        forged_local_evidence = SourceContext(original.encoded, b"not trusted evidence")
        self.assertEqual(self.validate(forged_local_evidence).evidence(), self.build().evidence())

    def test_consumer_rejects_rehashed_text_comment_and_result_tampering(self):
        original = self.build()
        address = next(iter(original.to_dict()["payload"]["knowledge"]))
        for change in ("knowledge", "comment", "result_hash", "index"):
            packet = original.to_dict()
            if change == "knowledge":
                packet["payload"]["knowledge"][address] = "Altered source condition."
                packet["source_index"][address] = "Altered source condition."
            elif change == "comment":
                packet["payload"]["registry"]["EQ-9001"]["engineer_comment"] = "Altered comment."
                packet["source_index"]["equipment:EQ-9001:engineer_comment"] = "Altered comment."
            elif change == "result_hash":
                packet["knowledge_result_hash"] = "0" * 64
            else:
                packet["source_index"][address] = "Altered index."
            with self.subTest(change=change), self.assertRaises(KnowledgeError) as raised:
                self.validate(rehashed(packet))
            self.assertEqual(raised.exception.code, "context_contract")
        packet = original.to_dict()
        packet["context_hash"] = "0" * 64
        with self.assertRaises(KnowledgeError) as raised:
            self.validate(canonical_bytes(packet))
        self.assertEqual(raised.exception.code, "context_hash")

    def test_consumer_rejects_missing_extra_identity_fields_types_and_policy(self):
        original = self.build()
        for change in ("missing_root", "extra_root", "missing_field", "extra_field",
                       "missing_id", "extra_id", "ids", "type", "version", "legacy",
                       "policy", "rubric"):
            packet = original.to_dict()
            if change == "missing_root":
                del packet["source_index"]
            elif change == "extra_root":
                packet["rubric"] = {}
            elif change == "missing_field":
                del packet["payload"]["registry"]["EQ-9001"]["engineer_comment"]
            elif change == "extra_field":
                packet["payload"]["findings"]["F-9001"]["unexpected"] = "Not authorized."
            elif change == "missing_id":
                packet["payload"]["findings"].clear()
            elif change == "extra_id":
                packet["payload"]["findings"]["F-9999"] = {
                    **packet["payload"]["findings"]["F-9001"], "finding_id": "F-9999"}
            elif change == "ids":
                packet["finding_ids"] = ["F-9999"]
            elif change == "type":
                packet["payload"]["registry"]["EQ-9001"]["criticality_score"] = 5
            elif change in ("version", "legacy"):
                packet["contract_version"] = True if change == "version" else 0
            elif change == "policy":
                packet["assessment_policy"]["instructions"] = "Untrusted replacement policy."
            else:
                packet["payload"]["knowledge"]["rubric"] = "Injected scoring instructions."
            with self.subTest(change=change), self.assertRaises(KnowledgeError) as raised:
                self.validate(rehashed(packet))
            expected_code = ("schema" if change in ("missing_root", "extra_root") else
                             "unsupported_contract" if change in ("version", "legacy") else
                             "assessment_policy" if change == "policy" else "context_contract")
            self.assertEqual(raised.exception.code, expected_code)

    def test_consumer_checks_independent_pins_store_and_table_bindings(self):
        original = self.build()
        for options, code in (
            ({"knowledge_version": "sha256-" + "0" * 64}, "unknown_or_invalid_release"),
            ({"assessment_time": "2026-07-02T00:00:00+00:00"}, "context_contract"),
            ({"assessment_time": "not-a-time"}, "invalid_query"),
            ({"expected_strategy": {}}, "strategy_binding_mismatch"),
            ({"expected_assessment_policy": {**self.policy, "extra": True}}, "assessment_policy"),
        ):
            with self.subTest(options=options), self.assertRaises(KnowledgeError) as raised:
                self.validate(original, **options)
            self.assertEqual(raised.exception.code, code)
        original_store = self.store
        self.store = SourceKnowledgeStore(Path(self.temporary.name) / "other-store")
        with self.assertRaises(KnowledgeError) as raised:
            self.validate(original)
        self.assertEqual(raised.exception.code, "unknown_or_invalid_release")
        self.store = original_store
        self.registry = table({**self.registry.rows[0], "engineer_comment": "New trusted comment."},
                              "registry", "registry_input")
        with self.assertRaises(KnowledgeError) as raised:
            self.validate(original)
        self.assertEqual(raised.exception.code, "context_contract")
        self.registry = table(self.registry.rows[0], "findings", "registry_input")
        with self.assertRaises(KnowledgeError) as raised:
            self.validate(original)
        self.assertEqual(raised.exception.code, "input_binding_mismatch")

    def test_consumer_bounds_and_strict_wire_format_fail_closed(self):
        original = self.build()
        for raw, code in ((b"\xff", "json_decode"), (b'{"x":1,"x":2}', "json_duplicate"),
                          (b"[]", "schema"), (original.encoded.decode(), "context_contract")):
            with self.subTest(raw=repr(raw)[:35]), self.assertRaises(KnowledgeError) as raised:
                self.validate(raw)
            self.assertEqual(raised.exception.code, code)
        for limit in (False, 0, len(original.encoded) - 1):
            with self.subTest(limit=limit), self.assertRaises(KnowledgeError) as raised:
                self.validate(original, max_bytes=limit)
            self.assertEqual(raised.exception.code, "context_limit")
        self.assertEqual(self.validate(original, max_bytes=len(original.encoded)).encoded,
                         original.encoded)

    def test_consumer_cannot_reinsert_retired_text_into_new_release(self):
        old = self.build()
        candidate, digest = self.store.load_draft()
        retired_id = next(item_id for item_id, item in candidate["items"].items()
                          if "Rotor rule" in item["revision"]["text"])
        digest = self.store.set_context_links(
            [edge for edge in candidate["context_links"]
             if all(edge[key].split("@")[0] != retired_id for key in ("from", "to"))],
            expected_digest=digest)
        digest = self.store.set_lifecycle(
            retired_id, status="retired", reason="Synthetic withdrawal", expected_digest=digest)
        candidate, _ = self.store.load_draft()
        for item_id in candidate["items"]:
            digest = self.store.review_item(
                item_id, reviewer="Software fixture only", reason="Synthetic withdrawal review",
                expected_digest=digest)
        self.version = self.store.publish(
            expected_digest=digest, author="Software fixture", reviewer="Software fixture only",
            reason="Synthetic withdrawal release", reviewed_at="2026-07-01T00:00:00+00:00")
        current = self.build()
        self.assertFalse(any("Rotor rule" in text
                             for text in current.to_dict()["payload"]["knowledge"].values()))
        self.assertEqual(self.validate(current).encoded, current.encoded)
        with self.assertRaises(KnowledgeError):
            self.validate(old)
        packet = current.to_dict()
        for address, text in old.to_dict()["payload"]["knowledge"].items():
            if "Rotor rule" in text:
                packet["payload"]["knowledge"][address] = text
                packet["source_index"][address] = text
        with self.assertRaises(KnowledgeError) as raised:
            self.validate(rehashed(packet))
        self.assertEqual(raised.exception.code, "context_contract")

    def test_exact_provider_context_excludes_editorial_and_legacy_rubric(self):
        bundle = self.build()
        context = bundle.to_dict()
        self.assertEqual(context["contract_version"], 3)
        self.assertEqual(context["payload"]["registry"]["EQ-9001"]["engineer_comment"],
                         "Independent comment delivery marker.")
        self.assertEqual(context["source_index"]["equipment:EQ-9001:engineer_comment"],
                         "Independent comment delivery marker.")
        self.assertEqual(context["assessment_policy"]["version"], "fixture-policy-v1")
        self.assertNotIn("rubric", context["payload"]["knowledge"])
        self.assertNotIn("Software fixture only", bundle.encoded.decode())
        self.assertNotIn("source_manifest", context)
        self.assertEqual(bundle.evidence()["source_manifest"][0]["sha256"], self.findings.raw_sha256)

    def test_history_projection_is_chronological_source_bound_and_noncausal(self):
        frow, rrow = self.findings.rows[0], self.registry.rows[0]
        self.findings = table([
            {**frow, "finding_id": "F-9002", "reported_date": "2026-06-02"},
            {**frow, "finding_id": "F-9001", "reported_date": "2026-06-01"},
            {**frow, "finding_id": "F-9003", "reported_date": "2026-06-03",
             "equipment_id": "EQ-9002", "equipment_type": "Rotor-B"},
        ], "findings", "finding_input")
        self.registry = table([
            {**rrow, "redundancy": "N+1 (EQ-9002)"},
            {**rrow, "equipment_id": "EQ-9002", "equipment_type": "Rotor-B",
             "service_description": "Protection for EQ-9001", "redundancy": "N+1 (EQ-9001)"},
        ], "registry", "registry_input")
        history = self.build().to_dict()["payload"]["history"]
        self.assertEqual("triage-input-history-v1", history["contract"])
        self.assertEqual(["F-9001", "F-9002"], [
            item["finding_id"] for item in history["equipment_timelines"]["EQ-9001"]])
        redundancy = next(item for item in history["case_links"]
                          if item["kind"] == "explicit_redundancy")
        self.assertEqual(["F-9001", "F-9002", "F-9003"], redundancy["finding_ids"])
        self.assertEqual("context_only_not_causation", redundancy["interpretation"])
        reference = next(item for item in history["case_links"]
                         if item["kind"] == "explicit_registry_reference")
        self.assertEqual(["EQ-9002", "EQ-9001"], reference["direction"])
        self.assertEqual(["equipment:EQ-9002:service_description"], reference["source_refs"])

    def test_consumer_rejects_rehashed_history_tampering(self):
        original = self.build()
        packet = original.to_dict()
        packet["payload"]["history"]["limitations"] = ["Invented repair history."]
        with self.assertRaises(KnowledgeError) as raised:
            self.validate(rehashed(packet))
        self.assertEqual("context_contract", raised.exception.code)

    def test_cross_equipment_link_requires_findings_on_both_endpoints(self):
        frow, rrow = self.findings.rows[0], self.registry.rows[0]
        self.findings = table([
            frow,
            {**frow, "finding_id": "F-9002", "reported_date": "2026-06-02"},
        ], "findings", "finding_input")
        self.registry = table([
            {**rrow, "redundancy": "N+1 (EQ-9002)"},
            {**rrow, "equipment_id": "EQ-9002", "equipment_type": "Rotor-B",
             "redundancy": "N+1 (EQ-9001)"},
        ], "registry", "registry_input")
        history = self.build().to_dict()["payload"]["history"]
        self.assertEqual([], history["case_links"])

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
