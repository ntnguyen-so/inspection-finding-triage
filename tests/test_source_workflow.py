from __future__ import annotations

import asyncio
import contextlib
import csv
from copy import deepcopy
from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from llm_inference import InferenceError
from llm_inference.contracts import canonical, strict_json
from tests.triage_support import (
    Artifacts, CUTOFF, FakeProvider, assessment, native_response, source_files, write_csv,
)
from triage.__main__ import main
from triage.assessment_policy import ASSESSMENT_POLICY_SHA256, assessment_policy
from triage.contracts import TriageError, digest
from triage.inputs import EQUIPMENT_FIELDS, FINDING_FIELDS, read_inputs
from triage.policy import CAPACITY_COMPARISON_ACTIVITY, SAME_DAY_ATTENTION_ACTIVITY
from triage.source_context import IsolatedProbeContext, NativeContext, activation_candidate
from triage.workflow import run_workflow
from triage_knowledge.contracts import KnowledgeError, canonical_bytes
from triage_knowledge.source import SourceDocument, extract_code
from triage_knowledge.source_context import SourceContext, build_source_context, validate_source_context
from triage_knowledge.source_store import SourceKnowledgeStore


class SourceWorkflowTests(Artifacts, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.inputs = source_files(self.root)
        self.store = SourceKnowledgeStore(self.root / "source-first")
        document = SourceDocument.from_bytes(
            b"# Synthetic condition guidance\nJustify scores from observed evidence.\n",
            name="Synthetic handoff fixture", source_id="fixture")
        self.store.create_draft([extract_code(document)])
        self.publish()
        self.output = self.root / "tickets.json"

    def publish(self):
        candidate, current = self.store.load_draft()
        for item_id, item in candidate["items"].items():
            if item["review_state"] == "pending":
                current = self.store.review_item(
                    item_id, expected_digest=current, reviewer="Synthetic software fixture",
                    reason="Not actual human or domain approval")
        self.version = self.store.publish(
            expected_digest=current, author="Software fixture", reviewer="Software fixture",
            reason="Mechanical integration only", reviewed_at=CUTOFF)
        self.activation = activation_candidate(self.store, self.version)
        self.activation["review"] = {
            "reviewer": "Synthetic software fixture", "reason": "Not genuine content approval",
            "reviewed_at": CUTOFF, "source_policy_compatible": True,
        }

    def source(self):
        return NativeContext(self.store.root, self.activation)

    def probe_source(self):
        policy = assessment_policy()
        policy["isolated_experiment"] = {
            "experiment_id": "software-probe", "policy_version": "fixture-A",
            "text": "SOFTWARE DIAGNOSTIC MARKER, not engineering guidance.",
        }
        return IsolatedProbeContext(self.store.root, self.activation, {
            "contract": "triage-isolated-probe-v1", "experiment_id": "software-probe",
            "input_kind": "evaluation_input", "findings_sha256": self.inputs.findings_hash,
            "registry_sha256": self.inputs.registry_hash, "assessment_policy": policy,
            "assessment_policy_sha256": digest(canonical_bytes(policy)),
        })

    def config(self, **kwargs):
        return replace(super().config(**kwargs), knowledge_version=self.version)

    def prepare(self, source=None, inputs=None):
        return (source or self.source()).prepare(inputs or self.inputs, self.version, CUTOFF, 128_000)

    def run_one(self, provider, name="run", *, source=None, inputs=None):
        return asyncio.run(run_workflow(
            inputs or self.inputs, source or self.source(), lambda: provider, self.config(),
            self.output, self.root / name))

    def test_native_handoff_separates_policy_and_exact_active_text_from_local_evidence(self):
        provider = FakeProvider()
        result = self.run_one(provider)
        self.assertTrue(result["published_output"])
        actual = strict_json(provider.requests[0].user)["context"]
        self.assertEqual(3, actual["contract_version"])
        self.assertEqual(assessment_policy(), actual["assessment_policy"])
        self.assertEqual("Partner availability is not verified.",
                         actual["payload"]["registry"]["PMP-8001"]["engineer_comment"])
        self.assertIn("Justify scores from observed evidence.", provider.requests[0].user)
        self.assertNotIn("Not genuine content approval", provider.requests[0].user)
        self.assertNotIn("source_manifest", actual)
        self.assertNotIn("rubric", actual["payload"]["knowledge"])
        record = strict_json((self.root / "run" / "run.json").read_text())
        self.assertEqual("native_source_first_bundle_3", record["context_provenance"])
        self.assertEqual(ASSESSMENT_POLICY_SHA256,
                         record["knowledge_handoff"]["activation"]["assessment_policy_sha256"])
        self.assertEqual(digest(self.inputs.findings_raw), self.inputs.findings_hash)

    def test_native_request_exposes_target_history_without_invented_state(self):
        self.inputs = source_files(self.root, count=2)
        provider = FakeProvider([assessment(), assessment("F-8002")])
        self.run_one(provider)
        message = strict_json(provider.requests[0].user)
        self.assertIn("do not transfer a vibration directive", provider.requests[0].system)
        self.assertIn("at-rest, running", provider.requests[0].system)
        self.assertIn("successful retry", provider.requests[0].system)
        self.assertIn("unknown acceptance criteria", provider.requests[0].system)
        self.assertIn("different failure mode", provider.requests[0].system)
        self.assertIn("linked partner's observed impairment", provider.requests[0].system)
        self.assertIn("recorded-deviation status", provider.requests[0].system)
        self.assertIn("confirmed or suspected protection_impaired", provider.requests[0].system)
        self.assertIn("facts.protection_impaired.verification_activity",
                      provider.requests[0].system)
        self.assertIn("poor lubrication", provider.requests[0].system)
        self.assertIn("confirmed out of service", provider.requests[0].system)
        self.assertIn("not currently providing a protective function",
                      provider.requests[0].system)
        self.assertIn("naming only the equipment class", provider.requests[0].system)
        self.assertIn("sound pressure boundary", provider.requests[0].system)
        self.assertIn("explicitly unknown duration", provider.requests[0].system)
        self.assertIn("protected function or consequence path",
                      provider.requests[0].system)
        self.assertIn("source evidence confirms an independent control",
                      provider.requests[0].system)
        self.assertIn("valid in-date certification", provider.requests[0].system)
        self.assertIn("physical or operational deterioration", provider.requests[0].system)
        self.assertIn("observed evidence raises doubt", provider.requests[0].system)
        self.assertIn("unresolved repair, restoration", provider.requests[0].system)
        self.assertIn("existing maintenance-backlog status",
                      provider.requests[0].system)
        self.assertIn("target finding backlog status", provider.requests[0].system)
        self.assertIn("backlog status alone does not lower urgency",
                      provider.requests[0].system)
        self.assertIn("SCE status, redundancy status", provider.requests[0].system)
        self.assertIn("do not infer unstated", provider.requests[0].system)
        self.assertIn("operational, interruption or personnel consequence",
                      provider.requests[0].system)
        self.assertIn("should fit 280 characters", provider.requests[0].system)
        self.assertIn("as fixed", provider.requests[0].system)
        self.assertIn("never paraphrase a fixed activity", provider.requests[0].system)
        self.assertEqual(
            [CAPACITY_COMPARISON_ACTIVITY, SAME_DAY_ATTENTION_ACTIVITY],
            message["possible_policy_activities"],
        )
        history = message["target_query_facts"]["history"]
        self.assertEqual(["F-8001", "F-8002"], [
            item["finding_id"] for item in history["equipment_timeline"]])
        self.assertEqual("F-8002", next(iter(history["related_findings"])))
        self.assertIn("not repair completion", history["limitations"][0])
        self.assertNotIn("score", canonical(history))

    def test_native_timing_is_resolved_routed_and_retained_without_score_repair(self):
        rows = list(self.inputs.data["registry"].values())
        rows[0]["engineer_comment"] = "Specialist attention is required today."
        write_csv(self.root / "registry.csv", EQUIPMENT_FIELDS, rows)
        self.inputs = read_inputs(self.root / "findings.csv", self.root / "registry.csv")

        def response(request, foreign=False):
            message = strict_json(request.user)
            index = message["context"]["source_index"]
            address = ("equipment:PMP-8001:engineer_comment" if not foreign else
                       next(key for key in index if key.startswith("knowledge:")))
            trigger = "finding:F-8001:finding_description"
            attention = [{"reason": "The target has an unconditional same-day instruction.",
                          "directive_evidence": [{"source_ref": address, "quote": index[address].split("\n")[0]}],
                          "trigger_evidence": [{"source_ref": trigger, "quote": index[trigger]}]}]
            return native_response(assessment(), message["citation_catalog"], attention)

        self.run_one(FakeProvider([response]), "timing")
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual((2, 3, 9), (ticket["likelihood_of_failure"]["score"],
                                    ticket["impact_of_failure"]["score"], ticket["urgency"]["score"]))
        self.assertIn(SAME_DAY_ATTENTION_ACTIVITY, ticket["recommended_action"])
        self.assertTrue(ticket["review_required"])
        record = strict_json((self.root / "timing" / "run.json").read_text())
        self.assertIn("citation_catalog_sha256", record["attempts"][0])
        self.assertEqual("Specialist attention is required today.",
                         record["attempts"][0]["same_day_attention"][0]["directive_evidence"][0]["quote"])
        old = self.output.read_bytes()
        with self.assertRaises(TriageError) as caught:
            self.run_one(FakeProvider([lambda request: response(request, True)] * 2), "foreign-timing")
        self.assertEqual("assessment_evidence", caught.exception.code)
        self.assertEqual(old, self.output.read_bytes())
        failed = strict_json((self.root / "foreign-timing" / "run.json").read_text())
        self.assertIn("projected_assessment", failed["attempts"][0])
        self.assertFalse(failed["published_output"])

    def test_pending_activation_or_changed_pins_stop_before_provider_and_preserve_old_output(self):
        self.output.write_bytes(b"old successful output\r\n")
        original = deepcopy(self.activation)
        mutations = [
            lambda a: a.update(review=None),
            lambda a: a.update(knowledge_version="sha256-" + "0" * 64),
            lambda a: a.update(retrieval_index_sha256="0" * 64),
            lambda a: a.update(assessment_policy_sha256="0" * 64),
            lambda a: a.update(execution_policy_sha256="0" * 64),
            lambda a: a["strategy"].update(parameters_sha256="0" * 64),
            lambda a: a["review"].update(source_policy_compatible=False),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(case=number):
                self.activation = deepcopy(original)
                mutate(self.activation)
                provider = FakeProvider()
                with self.assertRaises(TriageError):
                    self.run_one(provider, f"invalid-{number}")
                self.assertFalse(provider.requests)
                self.assertEqual(b"old successful output\r\n", self.output.read_bytes())

    def test_same_context_is_reused_after_knowledge_edit_and_recoverable_response(self):
        def mutate_after_pin(request):
            _, current = self.store.load_draft()
            self.store.set_lifecycle(
                next(iter(self.store.load_draft()[0]["items"])), status="retired",
                reason="Synthetic concurrent draft edit", expected_digest=current)
            return "invalid JSON"
        provider = FakeProvider([mutate_after_pin, assessment()])
        with patch("triage.source_context.build_source_context", wraps=build_source_context) as builder, \
                patch("triage.source_context.validate_source_context", wraps=validate_source_context) as consumer:
            self.run_one(provider)
        self.assertEqual(1, builder.call_count)
        self.assertEqual(1, consumer.call_count)
        self.assertEqual(strict_json(provider.requests[0].user)["context"],
                         strict_json(provider.requests[1].user)["context"])

    def test_release_is_resolved_once_and_not_reopened_by_builder(self):
        original = SourceKnowledgeStore.resolve_release
        calls = []
        def resolve(store, version):
            calls.append(version)
            return original(store, version)
        with patch.object(SourceKnowledgeStore, "resolve_release", resolve):
            self.prepare()
        self.assertEqual([self.version], calls)

    def test_release_resolution_retains_terminal_knowledge_diagnostics(self):
        for number, code in enumerate(("unsupported_contract", "invalid_dependency")):
            provider = FakeProvider()
            with self.subTest(code=code):
                with patch.object(SourceKnowledgeStore, "resolve_release",
                                  side_effect=KnowledgeError(code, "Synthetic release failure")):
                    with self.assertRaises(TriageError) as caught:
                        self.run_one(provider, f"release-error-{number}")
                self.assertEqual(code, caught.exception.code)
                self.assertEqual(0, caught.exception.attempts)
                self.assertFalse(provider.requests)
                self.assertFalse(self.output.exists())
        with patch.object(SourceKnowledgeStore, "resolve_release", side_effect=FileNotFoundError):
            with self.assertRaises(TriageError) as caught:
                self.prepare()
        self.assertEqual("unknown_or_invalid_release", caught.exception.code)

    def test_missing_partner_survives_native_contract_without_model_uncertainty(self):
        self.inputs = source_files(self.root, sce=True, redundancy="N+1 (PMP-8999)")
        provider = FakeProvider()
        self.run_one(provider)
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertTrue(ticket["review_required"])
        self.assertEqual(7, ticket["urgency"]["score"])
        self.assertEqual(2, ticket["likelihood_of_failure"]["score"])
        self.assertIn("Verify availability and capability of PMP-8999.", ticket["recommended_action"])
        self.assertNotIn("gaps", strict_json(provider.requests[0].user)["context"])
        report = strict_json((self.root / "run" / "run.json").read_text())
        self.assertEqual("PMP-8999", report["context_gaps"][0]["partner_equipment_id"])

    def test_row_order_changes_only_raw_input_evidence_not_semantic_context(self):
        self.inputs = source_files(self.root, count=2)
        first, _, first_snapshot = self.prepare()
        write_csv(self.root / "findings.csv", FINDING_FIELDS,
                  list(reversed(list(self.inputs.data["findings"].values()))))
        reordered = read_inputs(self.root / "findings.csv", self.root / "registry.csv")
        second, _, second_snapshot = self.prepare(inputs=reordered)
        self.assertEqual(first, second)
        self.assertNotEqual(first_snapshot["native_evidence"]["source_manifest"],
                            second_snapshot["native_evidence"]["source_manifest"])

    def test_inconsistent_rows_and_independent_raw_bytes_reject_before_build(self):
        data = self.inputs.data
        data["findings"]["F-8001"]["finding_description"] = "Undeclared rewritten description."
        invalid = replace(self.inputs, encoded=canonical(data))
        with self.assertRaises(TriageError) as caught:
            self.prepare(inputs=invalid)
        self.assertEqual("input_binding_mismatch", caught.exception.code)
        with self.assertRaises(TriageError):
            self.prepare(inputs=replace(self.inputs, findings_raw=b"not original CSV"))

    def test_native_contract_mutations_reject_even_when_context_hash_is_recomputed(self):
        def corrupt(change):
            def build(*args, **kwargs):
                actual = build_source_context(*args, **kwargs)
                bundle, evidence = actual.to_dict(), actual.evidence()
                change(bundle, evidence)
                body = {key: value for key, value in bundle.items() if key != "context_hash"}
                bundle["context_hash"] = digest(canonical_bytes(body))
                evidence["context_hash"] = bundle["context_hash"]
                return SourceContext(canonical_bytes(bundle), canonical_bytes(evidence))
            return build
        mutations = [
            lambda b, e: b.update(contract_version="triage-export-v0"),
            lambda b, e: b["payload"]["registry"]["PMP-8001"].update(engineer_comment="Foreign comment."),
            lambda b, e: b["source_index"].update(foreign="Evaluator marker"),
            lambda b, e: b["assessment_policy"].update(version="unapproved"),
            lambda b, e: b.update(finding_ids=["F-8999"]),
            lambda b, e: b.update(knowledge_result_hash="0" * 64),
            lambda b, e: b["payload"]["knowledge"].clear(),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(case=number):
                with patch("triage.source_context.build_source_context", side_effect=corrupt(mutate)):
                    with self.assertRaises(TriageError):
                        self.prepare()

    def test_module_consumer_rebuilds_evidence_instead_of_trusting_packet_owned_metadata(self):
        def corrupt_evidence(*args, **kwargs):
            actual = build_source_context(*args, **kwargs)
            evidence = actual.evidence()
            evidence["source_manifest"][0].update(kind="evaluation_input", sha256="0" * 64)
            evidence["retrieval"].update(status="unavailable", content_sha256="0" * 64)
            return SourceContext(actual.encoded, canonical_bytes(evidence))
        with patch("triage.source_context.build_source_context", side_effect=corrupt_evidence):
            _, _, pinned = self.prepare()
        rebuilt = pinned["native_evidence"]
        self.assertEqual("finding_input", rebuilt["source_manifest"][0]["kind"])
        self.assertEqual(self.inputs.findings_hash, rebuilt["source_manifest"][0]["sha256"])
        self.assertEqual("ok", rebuilt["retrieval"]["status"])
        self.assertEqual("module_owned_independent_rebuild_from_trusted_inputs_and_pins",
                         pinned["consumer_validation"])

    def test_rehashed_omission_of_active_knowledge_is_rejected_before_provider_start(self):
        extra = SourceDocument.from_bytes(
            b"# Required companion\nDo not drop a source qualifier.\n",
            name="Synthetic qualifier fixture", source_id="companion")
        _, current = self.store.load_draft()
        self.store.add_source(extract_code(extra), expected_digest=current)
        self.publish()
        def omit(*args, **kwargs):
            actual = build_source_context(*args, **kwargs)
            bundle = actual.to_dict()
            address = next(iter(bundle["payload"]["knowledge"]))
            del bundle["payload"]["knowledge"][address]
            del bundle["source_index"][address]
            bundle["context_hash"] = digest(canonical_bytes({
                key: value for key, value in bundle.items() if key != "context_hash"}))
            return SourceContext(canonical_bytes(bundle), actual.evidence_bytes)
        provider = FakeProvider()
        self.output.write_bytes(b"old")
        with patch("triage.source_context.build_source_context", side_effect=omit):
            with self.assertRaises(TriageError) as caught:
                self.run_one(provider)
        self.assertEqual("context_contract", caught.exception.code)
        self.assertEqual(0, caught.exception.attempts)
        self.assertFalse(provider.requests)
        self.assertEqual(b"old", self.output.read_bytes())

    def test_empty_active_view_is_terminal_and_old_pin_is_still_immutable(self):
        old_version, old_activation = self.version, deepcopy(self.activation)
        candidate, current = self.store.load_draft()
        for item_id in candidate["items"]:
            current = self.store.set_lifecycle(
                item_id, status="retired", reason="Synthetic withdrawal", expected_digest=current)
        self.publish()
        provider = FakeProvider()
        self.output.write_bytes(b"old")
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("knowledge_gap", caught.exception.code)
        self.assertFalse(provider.requests)
        self.assertEqual(b"old", self.output.read_bytes())
        self.version, self.activation = old_version, old_activation
        self.run_one(FakeProvider(), "old-pin")

    def test_retired_future_expired_and_archived_source_text_do_not_reach_provider(self):
        documents = [SourceDocument.from_bytes(
            f"# {sid}\n{marker}\n".encode(), name="Synthetic exclusion fixture", source_id=sid)
            for sid, marker in (("current", "CURRENT ACTIVE TEXT"),
                                ("withdrawn", "WITHDRAWN SECRET MARKER"),
                                ("future", "FUTURE SECRET MARKER"), ("expired", "EXPIRED SECRET MARKER"))]
        self.store = SourceKnowledgeStore(self.root / "lifecycle-store")
        current = self.store.create_draft([extract_code(doc) for doc in documents])
        candidate, _ = self.store.load_draft()
        for item_id, item in candidate["items"].items():
            sid = item["revision"]["source_id"]
            changes = {"withdrawn": {"status": "retired"},
                       "future": {"effective_from": "2027-01-01T00:00:00+00:00"},
                       "expired": {"effective_until": CUTOFF}}.get(sid)
            if changes:
                current = self.store.set_lifecycle(
                    item_id, reason="Synthetic exclusion audit", expected_digest=current, **changes)
        self.publish()
        provider = FakeProvider()
        self.run_one(provider)
        text = provider.requests[0].user
        self.assertIn("CURRENT ACTIVE TEXT", text)
        for marker in ("WITHDRAWN SECRET MARKER", "FUTURE SECRET MARKER", "EXPIRED SECRET MARKER"):
            self.assertNotIn(marker, text)

    def test_byte_limit_and_unsupported_probe_fail_without_dispatch(self):
        provider = FakeProvider()
        with self.assertRaises(TriageError):
            asyncio.run(run_workflow(
                self.inputs, self.source(), lambda: provider, self.config(max_context_bytes=1),
                self.output, self.root / "small"))
        with self.assertRaises(TriageError) as caught:
            asyncio.run(run_workflow(
                self.inputs, self.source(), lambda: provider, self.config(),
                self.output, self.root / "probe", purpose="isolated_probe", overlay_ref={}))
        self.assertEqual("context_overlay", caught.exception.code)
        self.assertFalse(provider.requests)

    def test_explicit_native_probe_keeps_diagnostic_policy_outside_source_knowledge(self):
        self.output = self.root / "probe.experimental.json"
        provider = FakeProvider(["malformed", assessment()])
        asyncio.run(run_workflow(
            self.inputs, self.probe_source(), lambda: provider, self.config(),
            self.output, self.root / "explicit-probe", purpose="isolated_probe"))
        first = strict_json(provider.requests[0].user)["context"]
        self.assertEqual("isolated_probe", first["input_purpose"])
        self.assertIn("SOFTWARE DIAGNOSTIC MARKER",
                      first["assessment_policy"]["isolated_experiment"]["text"])
        self.assertNotIn("SOFTWARE DIAGNOSTIC MARKER", str(first["payload"]["knowledge"]))
        self.assertEqual(first, strict_json(provider.requests[1].user)["context"])
        local = strict_json((self.root / "explicit-probe" / "run.json").read_text())
        self.assertEqual("evaluation_input",
                         local["knowledge_handoff"]["native_evidence"]["source_manifest"][0]["kind"])

    def test_probe_variant_cannot_enter_normal_workflow_or_publish_final_named_output(self):
        for number, (purpose, output) in enumerate((
                ("normal", self.root / "probe.experimental.json"),
                ("isolated_probe", self.root / "tickets.json"))):
            output.write_bytes(b"previous")
            provider = FakeProvider()
            with self.assertRaises(TriageError) as caught:
                asyncio.run(run_workflow(
                    self.inputs, self.probe_source(), lambda: provider, self.config(),
                    output, self.root / f"forbidden-probe-{number}", purpose=purpose))
            self.assertEqual("context_overlay", caught.exception.code)
            self.assertFalse(provider.requests)
            self.assertEqual(b"previous", output.read_bytes())

    def test_replaced_knowledge_stays_excluded_after_successor_expiry(self):
        documents = [SourceDocument.from_bytes(
            f"# {sid}\n{marker}\n".encode(), name="Replacement software fixture", source_id=sid)
            for sid, marker in (("older", "OLD REPLACED MARKER"),
                                ("newer", "CURRENT REPLACEMENT MARKER"),
                                ("shared", "SHARED ACTIVE GUIDANCE"))]
        self.store = SourceKnowledgeStore(self.root / "replacement-store")
        current = self.store.create_draft([extract_code(doc) for doc in documents])
        candidate, _ = self.store.load_draft()
        by_source = {item["revision"]["source_id"]: identifier
                     for identifier, item in candidate["items"].items()}
        self.store.replace_item(
            by_source["older"], by_source["newer"], effective_from="2025-12-01T00:00:00+00:00",
            reason="Synthetic reviewed replacement", expected_digest=current)
        self.publish()
        provider = FakeProvider()
        self.run_one(provider, "replacement")
        self.assertIn("CURRENT REPLACEMENT MARKER", provider.requests[0].user)
        self.assertNotIn("OLD REPLACED MARKER", provider.requests[0].user)
        _, current = self.store.load_draft()
        self.store.set_lifecycle(
            by_source["newer"], effective_until=CUTOFF, reason="Synthetic expiry",
            expected_digest=current)
        self.publish()
        provider = FakeProvider()
        self.run_one(provider, "expired-replacement")
        self.assertIn("SHARED ACTIVE GUIDANCE", provider.requests[0].user)
        self.assertNotIn("CURRENT REPLACEMENT MARKER", provider.requests[0].user)
        self.assertNotIn("OLD REPLACED MARKER", provider.requests[0].user)

    def test_native_structural_recovery_and_genuine_inability_do_not_invent_scores(self):
        provider = FakeProvider([{}, assessment()])
        self.run_one(provider, "recovered")
        self.assertEqual(2, len(provider.requests))
        record = strict_json((self.root / "recovered" / "run.json").read_text())
        self.assertEqual(["failed", "validated"], [a["status"] for a in record["attempts"]])
        previous = self.output.read_bytes()
        unable = assessment()
        unable.update(status="unassessable", inability_reason="Missing support for required scores.",
                      summary=None, recommended_action=None, likelihood_of_failure=None,
                      impact_of_failure=None, facts=None)
        provider = FakeProvider([unable])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, "inability")
        self.assertEqual("unassessable", caught.exception.code)
        self.assertEqual(1, caught.exception.attempts)
        self.assertEqual(previous, self.output.read_bytes())

    def test_native_cli_permanent_failure_preserves_absent_or_old_output_and_json_diagnostics(self):
        activation_path, config_path = self.root / "activation.json", self.root / "config.json"
        activation_path.write_text(json.dumps(self.activation))
        config_path.write_text(json.dumps(asdict(self.config())))
        for number, old in enumerate((None, b"previous successful output\r\n")):
            if old is not None:
                self.output.write_bytes(old)
            provider = FakeProvider(["malformed", "malformed"])
            with self.subTest(previous=old is not None):
                with patch("triage.__main__.AzureOpenAIProvider", return_value=provider):
                    with contextlib.redirect_stderr(io.StringIO()) as stderr:
                        with contextlib.redirect_stdout(io.StringIO()) as stdout:
                            code = main([
                                "--findings", str(self.root / "findings.csv"),
                                "--registry", str(self.root / "registry.csv"),
                                "--knowledge-store", str(self.store.root),
                                "--activation", str(activation_path), "--config", str(config_path),
                                "--output", str(self.output),
                                "--evidence", str(self.root / f"cli-failure-{number}"),
                                "--allow-inference",
                            ])
                self.assertEqual(1, code)
                self.assertEqual("", stdout.getvalue())
                diagnostic = json.loads(stderr.getvalue())
                self.assertEqual("malformed_json", diagnostic["error_class"])
                self.assertEqual("F-8001", diagnostic["finding_id"])
                self.assertEqual(2, diagnostic["attempts"])
                self.assertFalse(diagnostic["published_output"])
                self.assertEqual(old, self.output.read_bytes() if self.output.exists() else None)

    def test_cli_native_command_generates_drafts_without_any_export(self):
        activation_path, config_path = self.root / "activation.json", self.root / "config.json"
        activation_path.write_text(json.dumps(self.activation))
        config_path.write_text(json.dumps(asdict(self.config(
            azure_max_completion_tokens=8192, reasoning_effort="low", azure_api="responses"))))
        provider = FakeProvider()
        with patch("triage.__main__.AzureOpenAIProvider", return_value=provider) as factory:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = main([
                    "--findings", str(self.root / "findings.csv"),
                    "--registry", str(self.root / "registry.csv"),
                    "--knowledge-store", str(self.store.root), "--activation", str(activation_path),
                    "--config", str(config_path), "--output", str(self.output),
                    "--evidence", str(self.root / "cli-run"), "--allow-inference",
                ])
        self.assertEqual(0, code)
        factory.assert_called_once_with(native_json_schema=True, max_completion_tokens=8192, api="responses")
        self.assertEqual(digest(self.output.read_bytes()), json.loads(stdout.getvalue())["output_sha256"])
        self.assertEqual(1, len(provider.requests))
        self.assertEqual("low", provider.requests[0].reasoning_effort)
        message = json.loads(provider.requests[0].user)
        self.assertEqual(message["context"]["payload"]["findings"][message["target_finding_id"]],
                         message["target_query_facts"]["finding"])
        self.assertEqual(message["context"]["payload"]["registry"][message["primary_equipment_id"]],
                         message["target_query_facts"]["equipment"])

    def test_supplied_domain_and_development_rows_reach_prepared_request_without_test_descriptions(self):
        root = Path(__file__).resolve().parents[1]
        supplied = root / "docs" / "candidate-pack" / "candidate-pack"
        domain = (supplied / "reference" / "domain_knowledge.md").read_bytes()
        split = strict_json((root / "eval" / "spec" / "split.json").read_text())
        self.assertEqual(digest(domain), split["sources_sha256"]["reference\\domain_knowledge.md"])
        with (supplied / "data" / "inspection_findings.csv").open(newline="", encoding="utf-8-sig") as stream:
            original = list(csv.DictReader(stream))
        selected = [row for row in original if row["finding_id"] in split["partitions"]["development"]]
        write_csv(self.root / "findings.csv", FINDING_FIELDS, selected)
        (self.root / "registry.csv").write_bytes((supplied / "data" / "equipment_registry.csv").read_bytes())
        self.inputs = read_inputs(self.root / "findings.csv", self.root / "registry.csv")
        self.store = SourceKnowledgeStore(self.root / "supplied-domain-fixture")
        document = SourceDocument.from_bytes(domain, name="Unchanged supplied domain", source_id="domain")
        self.store.create_draft([extract_code(document)])
        self.publish()
        provider = FakeProvider([InferenceError("refusal", "Synthetic stop after request capture")])
        config = replace(self.config(max_context_bytes=128_000),
                         assessment_time="2026-07-01T00:00:00+00:00")
        with self.assertRaises(TriageError) as caught:
            asyncio.run(run_workflow(self.inputs, self.source(), lambda: provider, config,
                                     self.output, self.root / "supplied-run"))
        self.assertEqual("refusal", caught.exception.code)
        actual = strict_json(provider.requests[0].user)["context"]
        self.assertEqual(sorted(split["partitions"]["development"]), actual["finding_ids"])
        for row in original:
            if row["finding_id"] in split["partitions"]["test"]:
                self.assertNotIn(json.dumps(row["finding_description"], ensure_ascii=True)[1:-1],
                                 provider.requests[0].user)
        for identifier in ("FW-8101", "FW-8102", "PSV-3420"):
            self.assertEqual(self.inputs.data["registry"][identifier]["engineer_comment"],
                             actual["payload"]["registry"][identifier]["engineer_comment"])
        evidence = strict_json((self.root / "supplied-run" / "run.json").read_text())
        entries = evidence["knowledge_handoff"]["native_evidence"]["retrieval"]["entries"]
        intervals = []
        for entry in entries.values():
            self.assertEqual(digest(domain), entry["source_sha256"])
            spans = entry["spans"]
            self.assertEqual(entry["text"],
                             "".join(domain[s["start"]:s["end"]].decode("utf-8") for s in spans))
            intervals.extend((s["start"], s["end"]) for s in spans)
        position = 0
        for start, end in sorted(intervals):
            self.assertEqual(position, start)
            position = end
        self.assertEqual(len(domain), position)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
