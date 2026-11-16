from __future__ import annotations

import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from triage_knowledge import (
    SourceDocument, SourceKnowledgeStore, TableSource, binding_from_tables,
    build_source_context, extract_code, get_triage_knowledge, strategy_binding,
    validate_source_context,
)
from triage_knowledge.contracts import KnowledgeError, canonical_bytes, sha256
from triage_knowledge.retrieval import InputBinding


CUTOFF = "2026-07-01T00:00:00+00:00"
GOLDEN_STRATEGY = {"strategy": "fixed-normal-wire-identity", "parameters": {}}


def table(row: dict, source_id: str, kind: str) -> TableSource:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return TableSource.from_bytes(stream.getvalue().encode(), source_id=source_id, kind=kind)


def rehashed(packet: dict) -> bytes:
    body = {key: value for key, value in packet.items() if key != "context_hash"}
    return canonical_bytes({**body, "context_hash": sha256(canonical_bytes(body))})


class ProbeKnowledgeContextTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(
            prefix=".probe-context-", dir=Path(__file__).resolve().parents[1])
        self.addCleanup(temporary.cleanup)
        self.store = SourceKnowledgeStore(Path(temporary.name) / "software-store")
        document = SourceDocument.from_bytes(
            b"# Software fixture\nKeep uncertainty explicit.\n",
            name="Synthetic binding test", source_id="fixture")
        current = self.store.create_draft([extract_code(document)])
        candidate, _ = self.store.load_draft()
        for item_id in candidate["items"]:
            current = self.store.review_item(
                item_id, expected_digest=current, reviewer="Software fixture",
                reason="Mechanical test only, not human content approval")
        self.version = self.store.publish(
            expected_digest=current, author="Software fixture", reviewer="Software fixture",
            reason="Mechanical test only", reviewed_at=CUTOFF)
        self.findings = table({
            "finding_id": "F-9001", "reported_date": "2026-06-22",
            "equipment_id": "EQ-9001", "equipment_type": "Bench device",
            "inspection_type": "Function Test", "inspection_method": "Synthetic observation",
            "finding_description": "Synthetic isolated observation; function is not verified.",
            "reported_by": "Software fixture", "reporter_role": "Test author",
        }, "findings", "finding_input")
        self.registry = table({
            "equipment_id": "EQ-9001", "equipment_type": "Bench device",
            "service_description": "Isolated software fixture", "criticality_score": "4",
            "reliability_score": "7", "safety_critical_element": "No", "redundancy": "None",
            "engineer_comment": "Not installed plant.",
        }, "registry", "registry_input")
        self.policy = {"version": "fixture-policy-v1", "instructions": "Preserve uncertainty."}

    def options(self):
        return {
            "knowledge_version": self.version, "assessment_time": CUTOFF,
            "expected_strategy": strategy_binding(), "max_bytes": 64_000,
        }

    def build(self, **overrides):
        return build_source_context(
            self.store, self.findings, self.registry, assessment_policy=self.policy,
            **{**self.options(), **overrides})

    def validate(self, bundle, **overrides):
        return validate_source_context(
            bundle, self.findings, self.registry, self.store,
            expected_assessment_policy=self.policy, **{**self.options(), **overrides})

    def retrieve(self, binding, **overrides):
        return get_triage_knowledge(
            self.store,
            {"findings": {row["finding_id"]: row for row in self.findings.rows},
             "registry": {row["equipment_id"]: row for row in self.registry.rows}},
            allowed_input_binding=binding, **{**self.options(), **overrides})

    def test_normal_wire_matches_history_contract_golden_with_fixed_code_identity(self):
        # Executable strategy fingerprints intentionally change with source edits.
        with patch("triage_knowledge.retrieval.strategy_binding", return_value=GOLDEN_STRATEGY):
            bundle = self.build(expected_strategy=GOLDEN_STRATEGY)
            self.assertEqual("bdd0bd3d370d2e6e01a63078e8f603e160c0173c1fb4a6beee52f919c47ac47e",
                             sha256(bundle.encoded))
            self.assertEqual("2ce5c8033e160b1257c13947b5b8e6335eebf6977f42f2487ab699d603385e08",
                             sha256(bundle.evidence_bytes))
            self.assertNotIn("input_purpose", bundle.to_dict())
            self.assertNotIn("input_purpose", bundle.evidence())
            self.assertEqual(bundle, self.validate(bundle, expected_strategy=GOLDEN_STRATEGY))

    def test_explicit_probe_builds_and_independently_validates_both_finding_kinds(self):
        for kind in ("evaluation_input", "finding_input"):
            with self.subTest(kind=kind):
                self.findings = table(self.findings.rows[0], "findings", kind)
                bundle = self.build(input_purpose="isolated_probe")
                validated = self.validate(bundle, expected_input_purpose="isolated_probe")
                self.assertEqual(bundle, validated)
                packet, evidence = bundle.to_dict(), bundle.evidence()
                self.assertEqual("isolated_probe", packet["input_purpose"])
                self.assertEqual("isolated_probe", evidence["input_purpose"])
                self.assertEqual("isolated_probe", evidence["retrieval"]["input_purpose"])
                self.assertEqual(kind, evidence["source_manifest"][0]["kind"])
                self.assertEqual(self.policy, packet["assessment_policy"])
                self.assertEqual(["# Software fixture\nKeep uncertainty explicit.\n"],
                                 list(packet["payload"]["knowledge"].values()))
                self.assertEqual(bundle.encoded, rehashed(packet))

    def test_default_paths_reject_evaluation_tables_and_probe_contexts(self):
        self.findings = table(self.findings.rows[0], "findings", "evaluation_input")
        for action in (lambda: binding_from_tables(self.findings, self.registry), self.build):
            with self.assertRaises(KnowledgeError) as caught:
                action()
            self.assertEqual("input_binding_mismatch", caught.exception.code)
        for kind in ("evaluation_input", "finding_input"):
            self.findings = table(self.findings.rows[0], "findings", kind)
            bundle = self.build(input_purpose="isolated_probe")
            with self.subTest(kind=kind), self.assertRaises(KnowledgeError):
                self.validate(bundle)

    def test_rehashed_missing_or_wrong_purpose_and_policy_fail_validation(self):
        self.findings = table(self.findings.rows[0], "findings", "evaluation_input")
        bundle = self.build(input_purpose="isolated_probe")
        for change in ("missing", "normal", "unknown", "policy"):
            packet = bundle.to_dict()
            if change == "missing":
                del packet["input_purpose"]
            elif change == "policy":
                packet["assessment_policy"]["instructions"] = "Undeclared replacement."
            else:
                packet["input_purpose"] = change
            with self.subTest(change=change), self.assertRaises(KnowledgeError):
                self.validate(rehashed(packet), expected_input_purpose="isolated_probe")
        normal = self.build_with_ordinary_findings()
        packet = normal.to_dict()
        packet["input_purpose"] = "normal"
        with self.assertRaises(KnowledgeError):
            self.validate(rehashed(packet))

    def build_with_ordinary_findings(self):
        self.findings = table(self.findings.rows[0], "findings", "finding_input")
        return self.build()

    def test_lower_level_retrieval_requires_matching_trusted_purpose(self):
        for kind in ("evaluation_input", "finding_input"):
            self.findings = table(self.findings.rows[0], "findings", kind)
            binding = binding_from_tables(
                self.findings, self.registry, input_purpose="isolated_probe")
            with self.subTest(kind=kind):
                self.assertEqual("input_binding_mismatch", self.retrieve(binding).error_code)
                result = self.retrieve(binding, input_purpose="isolated_probe")
                self.assertEqual("ok", result.status)
                self.assertEqual("isolated_probe", result.to_dict()["input_purpose"])
                self.assertEqual("isolated_probe", result.evidence["input_purpose"])
        ordinary = binding_from_tables(self.findings, self.registry)
        self.assertEqual("input_binding_mismatch",
                         self.retrieve(ordinary, input_purpose="isolated_probe").error_code)

    def test_forged_binding_cannot_hide_evaluation_manifest_or_change_declared_purpose(self):
        self.findings = table(self.findings.rows[0], "findings", "evaluation_input")
        original = binding_from_tables(
            self.findings, self.registry, input_purpose="isolated_probe")
        for change in ("missing", "normal", "registry", "manifest", "rows", "extra"):
            value = original.to_dict()
            if change == "missing":
                del value["input_purpose"]
            elif change == "normal":
                value["input_purpose"] = "normal"
            elif change == "registry":
                value["manifest"][1]["kind"] = "evaluation_input"
            elif change == "manifest":
                value["manifest"] = []
            elif change == "rows":
                value["findings"]["F-9001"]["finding_description"] = "Undeclared replacement."
            else:
                value["unexpected"] = True
            forged = InputBinding(canonical_bytes(value))
            for purpose in ("normal", "isolated_probe"):
                with self.subTest(change=change, purpose=purpose):
                    result = self.retrieve(forged, input_purpose=purpose)
                    self.assertEqual("input_binding_mismatch", result.error_code)
                    self.assertEqual({}, result.provider_payload())

    def test_invalid_purpose_and_registry_kind_fail_closed(self):
        for purpose in ("evaluation", None, True, {}):
            with self.subTest(purpose=purpose):
                with self.assertRaises(KnowledgeError):
                    self.build(input_purpose=purpose)
                ordinary = binding_from_tables(self.findings, self.registry)
                self.assertEqual("input_binding_mismatch",
                                 self.retrieve(ordinary, input_purpose=purpose).error_code)
        self.registry = table(self.registry.rows[0], "registry", "evaluation_input")
        with self.assertRaises(KnowledgeError):
            self.build(input_purpose="isolated_probe")
