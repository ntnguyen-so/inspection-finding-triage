from __future__ import annotations

import asyncio
from copy import deepcopy

from tests.knowledge_support import CUTOFF, KnowledgeCase, equipment, tables
from tests.triage_support import FakeProvider
from triage.contracts import TriageError
from triage.inputs import read_inputs, validate_context
from triage.workflow import RunConfig, run_workflow
from triage_knowledge import EvaluationOverlay, build_context
from triage_knowledge.contracts import canonical_bytes, sha256
from triage_knowledge.workflow_export import WorkflowExport


class WorkflowHandoffTests(KnowledgeCase):
    def seam(self, *, missing_partner=False, probe=False):
        snapshot = self.publish()
        selected, registry = tables(
            registry=[equipment(redundancy="N+1 (PMP-8002)" if missing_partner else "None")],
            input_kind="evaluation_input" if probe else "finding_input")
        findings_path, registry_path = self.root / "findings.csv", self.root / "registry.csv"
        findings_path.write_bytes(selected.raw)
        registry_path.write_bytes(registry.raw)
        inputs = read_inputs(findings_path, registry_path)
        overlay = None
        if probe:
            raw = canonical_bytes({"scope": "Synthetic pump mechanism", "dimension": "likelihood",
                                   "guidance": "Use this explicitly isolated synthetic convention."})
            overlay = EvaluationOverlay("probe-policy", raw, sha256(raw))
        bundle = build_context(selected, registry, snapshot, CUTOFF,
                               purpose="evaluation_probe" if probe else "normal", overlay_ref=overlay)
        return inputs, snapshot, bundle, WorkflowExport.from_bundle(
            snapshot, bundle, selected, registry, CUTOFF,
            purpose="evaluation_probe" if probe else "normal", overlay_ref=overlay)

    def test_real_module_export_passes_current_consumer_checks(self):
        inputs, snapshot, original, source = self.seam(missing_partner=True)
        bundle, text, pinned = validate_context(
            source, inputs, snapshot.knowledge_version, CUTOFF, 262_144)
        self.assertEqual(bundle["contract_version"], "triage-export-v0")
        self.assertEqual(bundle["gaps"], original.to_dict()["gaps"])
        self.assertEqual(pinned["knowledge_version"], snapshot.knowledge_version)
        self.assertIn("Partner availability is not verified.", text)
        self.assertIn("Likelihood concerns function", text)
        self.assertEqual(source.read_export(), source.read_export())

    def test_valid_isolated_control_and_mismatched_hash_rejection(self):
        inputs, snapshot, _, source = self.seam(probe=True)
        _, _, pinned = validate_context(
            source, inputs, snapshot.knowledge_version, CUTOFF, 262_144,
            purpose="isolated_probe", overlay_ref=source.overlay_ref)
        self.assertEqual(pinned["knowledge_version"], snapshot.knowledge_version)
        wrong = {**source.overlay_ref, "sha256": "0" * 64}
        with self.assertRaises(TriageError):
            validate_context(source, inputs, snapshot.knowledge_version, CUTOFF, 262_144,
                             purpose="isolated_probe", overlay_ref=wrong)
        with self.assertRaises(TriageError):
            validate_context(source, inputs, snapshot.knowledge_version, CUTOFF, 262_144)

    def test_offline_request_delivery_and_context_failure_preserves_old_output(self):
        inputs, snapshot, _, source = self.seam()
        provider = FakeProvider()
        output = self.root / "draft-tickets.json"
        config = RunConfig(model="synthetic-deployment", knowledge_version=snapshot.knowledge_version,
                           assessment_time=CUTOFF, phase_attempt_budget=2,
                           attempt_ledger=str(self.root / "attempt-ledger.json"), max_context_bytes=262_144)
        report = asyncio.run(run_workflow(inputs, source, lambda: provider, config, output,
                                         self.root / "first-evidence"))
        self.assertTrue(report["published_output"])
        self.assertEqual(len(provider.requests), 1)
        self.assertIn("Partner availability is not verified.", provider.requests[0].user)
        self.assertIn("Likelihood concerns function", provider.requests[0].user)
        previous = output.read_bytes()
        config = RunConfig(model="synthetic-deployment", knowledge_version=snapshot.knowledge_version,
                           assessment_time=CUTOFF, phase_attempt_budget=2,
                           attempt_ledger=str(self.root / "attempt-ledger.json"), max_context_bytes=1)
        no_calls = FakeProvider()
        with self.assertRaises(TriageError):
            asyncio.run(run_workflow(inputs, source, lambda: no_calls, config, output,
                                     self.root / "failed-evidence"))
        self.assertEqual(no_calls.requests, [])
        self.assertEqual(output.read_bytes(), previous)

    def test_superseded_guidance_is_not_sent_to_fake_provider(self):
        candidate = deepcopy(self.candidate)
        retired_text = "Superseded prototype instruction that must not enter assessment context."
        candidate["guidance"]["psv-assessment"]["guidance"] = retired_text
        replacement = deepcopy(candidate["guidance"]["psv-assessment"])
        replacement["guidance"] = "Use current source-grounded evidence guidance."
        replacement["supersedes"] = ["psv-assessment"]
        candidate["guidance"]["current-assessment"] = replacement
        self.digest = self.store.save_draft(candidate, expected_digest=self.digest)
        inputs, snapshot, original, source = self.seam()
        self.assertIn(retired_text, snapshot.release_bytes.decode())
        self.assertNotIn(retired_text, original.encoded.decode())
        provider = FakeProvider()
        config = RunConfig(model="synthetic-deployment", knowledge_version=snapshot.knowledge_version,
                           assessment_time=CUTOFF, phase_attempt_budget=2,
                           attempt_ledger=str(self.root / "attempt-ledger.json"), max_context_bytes=262_144)
        asyncio.run(run_workflow(inputs, source, lambda: provider, config,
                                 self.root / "draft-tickets.json", self.root / "evidence"))
        self.assertNotIn(retired_text, provider.requests[0].user)
        self.assertIn(replacement["guidance"], provider.requests[0].user)

    def test_retired_expired_future_and_maintenance_text_never_reach_provider(self):
        candidate = deepcopy(self.candidate)
        markers = []
        for name, changes in (
            ("withdrawn-fixture-only", {"status": "retired", "retirement_reason": "Withdrawal audit only."}),
            ("future-fixture-only", {"effective_from": "2027-01-01T00:00:00Z"}),
            ("expired-fixture-only", {"effective_until": CUTOFF}),
        ):
            entry = deepcopy(candidate["guidance"]["psv-assessment"])
            marker = f"Excluded instruction for {name} must not reach assessment."
            entry.update(title=f"Excluded title for {name}", guidance=marker)
            entry["lifecycle"].update(changes)
            candidate["guidance"][name] = entry
            markers.extend([name, entry["title"], marker])
        maintenance = "Maintenance-only explanation must not reach assessment."
        candidate["guidance"]["psv-assessment"]["change_reason"] = maintenance
        markers.extend([maintenance, "Withdrawal audit only."])
        self.digest = self.store.save_draft(candidate, expected_digest=self.digest)
        inputs, snapshot, native, source = self.seam()
        provider = FakeProvider()
        config = RunConfig(model="synthetic-deployment", knowledge_version=snapshot.knowledge_version,
                           assessment_time=CUTOFF, phase_attempt_budget=2,
                           attempt_ledger=str(self.root / "attempt-ledger.json"), max_context_bytes=262_144)
        asyncio.run(run_workflow(inputs, source, lambda: provider, config,
                                 self.root / "draft-tickets.json", self.root / "evidence"))
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, snapshot.release_bytes.decode())
                self.assertNotIn(marker, native.encoded.decode())
                self.assertNotIn(marker, source.encoded.decode())
                self.assertNotIn(marker, provider.requests[0].user)
                self.assertNotIn(marker, provider.requests[0].system)
        self.assertIn(candidate["guidance"]["psv-assessment"]["guidance"], provider.requests[0].user)
