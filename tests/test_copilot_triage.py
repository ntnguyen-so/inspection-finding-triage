from __future__ import annotations

import asyncio
import contextlib
from copy import deepcopy
from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from llm_inference import InferenceError, InferenceResponse
from llm_inference.contracts import canonical, strict_json
from triage.__main__ import main
from triage.contracts import TriageError, digest
from triage.workflow import RunConfig, reserve_attempt, run_workflow
from tests.triage_support import Artifacts, FakeProvider, FixtureContext, assessment, source_files


def configuration():
    return {"provider": "github-copilot", "capabilities": {
        "tools": False, "adapter_retries": 0, "internal_http_retries": "unknown",
    }}


def copilot_receipt(request):
    system, user, _ = request.prepared()
    return {
        **configuration(), "dispatched": True, "adapter_attempts": 1,
        "inference_calls_observed": 1, "session_deleted": True,
        "observed_model": request.model, "requested_model": request.model,
        "boundary_violation": None, "http_attempts": None, "usd_cost": None,
        "tool_counts_observed": [0],
        "message_audit": [
            {"kind": "system.message", "matches_sdk_input": True, "content_sha256": digest(system.encode())},
            {"kind": "user.message", "matches_sdk_input": True, "content_sha256": digest(user.encode())},
        ],
    }


class FakeCopilot(FakeProvider):
    def __init__(self, responses=None):
        super().__init__(responses, configuration=configuration())
        self.catalog = [{
            "id": "synthetic-deployment", "provider": {"kind": "copilot"},
            "policy": {"state": "enabled"}, "supportedReasoningEfforts": ["low"],
            "billing": {"multiplier": 1},
        }]

    def models(self):
        return deepcopy(self.catalog)

    async def generate(self, request):
        response = await super().generate(request)
        if response.receipt.get("provider") == "github-copilot":
            return response
        return InferenceResponse(response.text, response.parsed, copilot_receipt(request))


class CopilotIntegrationTests(Artifacts, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.inputs = source_files(self.root)
        self.context = FixtureContext(self.inputs)
        self.output = self.root / "tickets.experimental.json"
        self.config = replace(self.config(), execution_mode="copilot_experiment",
                              attempt_ledger=str(self.root / "phase.experimental-ledger.json"))

    def run_one(self, provider, name="run", *, config=None, output=None):
        return asyncio.run(run_workflow(self.inputs, self.context, lambda: provider,
                                       config or self.config, output or self.output, self.root / name))

    def test_explicit_copilot_mode_publishes_only_ineligible_experimental_draft(self):
        result = self.run_one(FakeCopilot())
        self.assertEqual("experimental_draft_generated", result["run_status"])
        self.assertFalse(result["acceptance_eligible"])
        self.assertEqual(1, result["application_send_count"])
        report = strict_json((self.root / "run" / "run.json").read_text())
        self.assertNotIn("attempts", report)
        self.assertEqual(1, len(report["application_sends"]))
        self.assertIsNone(report["http_attempts"])
        self.assertEqual("not_established", report["strict_attempt_contract"])

    def test_strict_default_rejects_copilot_without_dispatch(self):
        provider = FakeCopilot()
        config = replace(self.config, execution_mode="strict",
                         attempt_ledger=str(self.root / "strict-ledger.json"))
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, config=config)
        self.assertEqual("provider_capabilities", caught.exception.code)
        self.assertFalse(provider.requests)
        self.assertFalse(self.output.exists())

    def test_final_filename_and_wrong_ledger_rejected_before_provider_start(self):
        old = self.root / "tickets.json"
        old.write_bytes(b"old final output")
        for config, output in (
            (self.config, old),
            (replace(self.config, attempt_ledger=str(self.root / "strict-ledger.json")), self.output),
        ):
            provider = FakeCopilot()
            with self.assertRaises(TriageError):
                self.run_one(provider, config=config, output=output)
            self.assertFalse(provider.requests)
        self.assertEqual(b"old final output", old.read_bytes())

    def test_catalog_guards_reject_disabled_non_copilot_unknown_model_or_effort(self):
        mutations = (
            lambda p: p.catalog[0]["policy"].update(state="disabled"),
            lambda p: p.catalog[0]["provider"].update(kind="byok"),
            lambda p: p.catalog[0].update(id="other"),
            lambda p: p.catalog[0].update(supportedReasoningEfforts=[]),
        )
        for i, mutate in enumerate(mutations):
            provider = FakeCopilot()
            mutate(provider)
            with self.subTest(case=i), self.assertRaises(TriageError):
                self.run_one(provider, name=f"catalog-{i}")
            self.assertFalse(provider.requests)

    def test_receipt_mutation_matrix_stops_without_retry_or_publication(self):
        mutations = (
            lambda r: r.update(adapter_attempts=2),
            lambda r: r.update(inference_calls_observed=2),
            lambda r: r.update(inference_calls_observed=True),
            lambda r: r.update(observed_model="other"),
            lambda r: r.update(requested_model="other"),
            lambda r: r.update(dispatched=False),
            lambda r: r.update(boundary_violation="tool.started"),
            lambda r: r.pop("boundary_violation"),
            lambda r: r.update(session_deleted=False),
            lambda r: r.update(cleanup_errors=[{"operation": "delete"}]),
            lambda r: r.update(runtime_shutdown_error="cleanup"),
            lambda r: r.update(primary_error_class="cleanup"),
            lambda r: r.update(http_attempts=1),
            lambda r: r.update(message_audit=[]),
            lambda r: r["message_audit"].pop(),
            lambda r: r["message_audit"][0].update(matches_sdk_input=False),
            lambda r: r["message_audit"][1].update(content_sha256="0" * 64),
            lambda r: r.update(tool_counts_observed=[]),
            lambda r: r.update(tool_counts_observed=[1]),
        )
        for i, mutate in enumerate(mutations):
            def response(request):
                receipt = copilot_receipt(request)
                mutate(receipt)
                return InferenceResponse(canonical(assessment()), None, receipt)
            provider = FakeCopilot([response])
            with self.subTest(case=i), self.assertRaises(TriageError) as caught:
                self.run_one(provider, name=f"receipt-{i}",
                             config=replace(self.config, phase_attempt_budget=len(mutations)))
            self.assertEqual("unverified_copilot_call", caught.exception.code)
            self.assertEqual(1, len(provider.requests))
            self.assertFalse(self.output.exists())

    def test_recoverable_adapter_error_needs_the_same_complete_audit(self):
        def malformed(request):
            return InferenceError("malformed_json", "Synthetic", copilot_receipt(request))
        provider = FakeCopilot([malformed, assessment()])
        self.run_one(provider)
        self.assertEqual(2, len(provider.requests))
        report = strict_json((self.root / "run" / "run.json").read_text())
        self.assertEqual(["failed", "validated"], [x["status"] for x in report["application_sends"]])
        provider = FakeCopilot([InferenceError("malformed_json", "Missing audit", {})])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, name="missing-audit")
        self.assertEqual("unverified_copilot_call", caught.exception.code)
        self.assertEqual(1, len(provider.requests))

    def test_retry_receives_rejected_draft_and_specific_contract_error_not_answers(self):
        rejected = assessment()
        rejected["facts"]["evacuation_unavailable"].update(
            applicability="not_applicable", state="confirmed_false")
        provider = FakeCopilot([rejected, assessment()])
        self.run_one(provider)
        retry = strict_json(provider.requests[1].user)
        self.assertEqual(canonical(rejected), retry["previous_assessment"])
        self.assertEqual("fact_contract", retry["validation_error"])
        self.assertIn("evacuation_unavailable", retry["validation_message"])
        self.assertIn("not_applicable requires unknown", retry["validation_message"])
        self.assertEqual(strict_json(provider.requests[0].user)["context"], retry["context"])

    def test_phase_ledgers_cannot_cross_modes(self):
        path = self.root / "shared.json"
        reserve_attempt(path, 3, "strict")
        with self.assertRaises(TriageError):
            reserve_attempt(path, 3, "experiment", "copilot_experiment")
        alternate = self.root / "other.json"
        reserve_attempt(alternate, 3, "experiment", "copilot_experiment")
        with self.assertRaises(TriageError):
            reserve_attempt(alternate, 3, "strict")

    def test_outer_deadline_records_unknown_outcome_without_retry(self):
        provider = FakeCopilot([TimeoutError("Synthetic outer timeout")])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("timeout", caught.exception.code)
        self.assertEqual(1, len(provider.requests))
        record = strict_json((self.root / "run" / "run.json").read_text())
        self.assertEqual("failed", record["application_sends"][0]["status"])
        self.assertEqual("unknown", record["application_sends"][0]["dispatch_outcome"])

    def test_cli_selects_only_copilot_and_no_azure_constructor(self):
        export = self.root / "context.json"
        export.write_text(canonical(self.context.read_export()), encoding="utf-8")
        config = self.root / "config.json"
        config.write_text(json.dumps(asdict(self.config)), encoding="utf-8")
        arguments = [
            "--provider", "copilot", "--findings", str(self.root / "findings.csv"),
            "--registry", str(self.root / "registry.csv"), "--context-export", str(export),
            "--legacy-replay",
            "--config", str(config), "--output", str(self.output),
            "--evidence", str(self.root / "run"), "--allow-inference",
        ]
        with patch("triage.__main__.CopilotProvider", return_value=FakeCopilot()), \
                patch("triage.__main__.AzureOpenAIProvider", side_effect=AssertionError("Must not use Azure")), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(0, main(arguments))
        self.assertFalse(strict_json(stdout.getvalue())["acceptance_eligible"])
        strict = replace(self.config, execution_mode="strict")
        config.write_text(json.dumps(asdict(strict)), encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(1, main(arguments))
        self.assertEqual("configuration", strict_json(stderr.getvalue())["error_class"])

    def test_gap_activity_is_disclosed_before_model_assessment(self):
        self.inputs = source_files(self.root, sce=True, redundancy="N+1 (PMP-8999)")
        gap = {"kind": "tagged_partner_not_in_registry", "subject_equipment_id": "PMP-8001",
               "partner_equipment_id": "PMP-8999", "finding_ids": ["F-8001"],
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        self.context = FixtureContext(self.inputs, gaps=[gap])
        def respond(request):
            activities = strict_json(request.user)["required_verification_activities"]
            result = assessment()
            result["recommended_action"] = " ".join(activities)
            return result
        self.run_one(FakeCopilot([respond]))
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual("Verify availability and capability of PMP-8999.", ticket["recommended_action"])
        self.assertEqual(7, ticket["urgency"]["score"])


class CollectorTests(Artifacts, unittest.TestCase):
    def test_repeat_retains_spent_budget_and_original_configuration(self):
        from tools.probe_triage import ROOT, prepare_run, repeat_run
        parent = self.root / "parent"
        parent.mkdir()
        split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
        _, selection = prepare_run(parent, "synthetic-explicit-model", split, 12)
        config = json.loads((parent / "config.json").read_text())
        (parent / "experiment.json").write_text(json.dumps({"selection": selection}), encoding="utf-8")
        (parent / "run").mkdir()
        (parent / "run" / "run.json").write_text(json.dumps({"config": config}), encoding="utf-8")
        ledger = Path(config["attempt_ledger"])
        reserve_attempt(ledger, 12, "prior-1", "copilot_experiment")
        reserve_attempt(ledger, 12, "prior-2", "copilot_experiment")
        command, repeated = repeat_run(parent, self.root / "repeat", "synthetic-explicit-model")
        self.assertEqual(2, repeated["prior_application_send_reservations"])
        self.assertIn(str(parent / "config.json"), command)
        self.assertEqual(2, len(json.loads(ledger.read_text())["reservations"]))
        changed = {**config, "phase_attempt_budget": 13}
        (parent / "config.json").write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaises(TriageError):
            repeat_run(parent, self.root / "repeat", "synthetic-explicit-model")
        (parent / "config.json").write_text(json.dumps(config), encoding="utf-8")
        manifest = {"selection": selection}
        changed_manifest = {"selection": {**selection, "application_send_ceiling": 11}}
        (parent / "experiment.json").write_text(json.dumps(changed_manifest), encoding="utf-8")
        with self.assertRaises(TriageError):
            repeat_run(parent, self.root / "repeat", "synthetic-explicit-model")
        (parent / "experiment.json").write_text(json.dumps(manifest), encoding="utf-8")
        original_ledger = json.loads(ledger.read_text())
        for changed_ledger, error_code in (
            ({**original_ledger, "budget": 11}, "repeat_contract"),
            ({**original_ledger, "reservations": [f"spent-{i}" for i in range(12)]}, "attempt_budget"),
        ):
            ledger.write_text(json.dumps(changed_ledger), encoding="utf-8")
            with self.assertRaises(TriageError) as caught:
                repeat_run(parent, self.root / "repeat", "synthetic-explicit-model")
            self.assertEqual(error_code, caught.exception.code)
        ledger.write_text(json.dumps(original_ledger), encoding="utf-8")
        redirected = {**config, "attempt_ledger": str(self.root / "other.experimental-ledger.json")}
        (parent / "config.json").write_text(json.dumps(redirected), encoding="utf-8")
        (parent / "run" / "run.json").write_text(json.dumps({"config": redirected}), encoding="utf-8")
        with self.assertRaises(TriageError):
            repeat_run(parent, self.root / "repeat", "synthetic-explicit-model")
        (parent / "config.json").write_text(json.dumps(config), encoding="utf-8")
        (parent / "run" / "run.json").write_text(json.dumps({"config": config}), encoding="utf-8")
        with (parent / "selected.csv").open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaises(TriageError):
            repeat_run(parent, self.root / "repeat", "synthetic-explicit-model")

    def test_cli_rejects_invalid_or_replacement_phase_budget_before_preparation(self):
        from tools.probe_triage import main as probe, prepare_run
        for i, controls in enumerate((
            ["--phase-budget", "0"], ["--phase-budget", "13"],
            ["--repeat-from", str(self.root), "--repeat-reason", "Synthetic", "--phase-budget", "12"],
        )):
            target = self.root / f"invalid-budget-{i}"
            with patch("tools.probe_triage.prepare_run", side_effect=AssertionError("Must not prepare")), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(1, probe(["--output", str(target), "--model", "synthetic",
                                           "--allow-inference", *controls]))
            self.assertFalse(target.exists())
        with self.assertRaises(TriageError):
            prepare_run(self.root / "invalid", "synthetic", {}, True)

    def test_real_smoke_preparation_checks_original_sources_without_model_calls(self):
        from tools.probe_triage import ROOT, SMOKE_IDS, prepare_run
        from triage.inputs import ExportedContext, read_inputs, validate_context
        target = self.root / "prepare"
        target.mkdir()
        split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
        with patch("tools.probe_triage.CopilotProvider", side_effect=AssertionError("No generation in preparation")):
            command, selection = prepare_run(target, "synthetic-explicit-model", split)
        config = RunConfig(**strict_json((target / "config.json").read_text()))
        inputs = read_inputs(target / "selected.csv", target / "registry.csv")
        bundle, _, _ = validate_context(ExportedContext(target / "context.json"), inputs,
                                       config.knowledge_version, config.assessment_time,
                                       config.max_context_bytes)
        self.assertEqual(set(SMOKE_IDS), set(bundle["finding_ids"]))
        self.assertEqual(6, selection["application_send_ceiling"])
        self.assertIn("copilot", command)

    def collect(self, name, child):
        from tools.probe_triage import main as probe
        target = self.root / name

        def fake_run(command, **kwargs):
            if command[0] == "synthetic-child":
                return child(target, command)
            return subprocess.CompletedProcess(command, 0, "synthetic-metadata", "")

        with patch("tools.probe_triage.prepare_run", return_value=(["synthetic-child"], {})), \
                patch("tools.probe_triage.subprocess.run", side_effect=fake_run), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = probe(["--output", str(target), "--model", "synthetic", "--allow-inference"])
        return code, strict_json((target / "observation.json").read_text())

    def test_missing_capture_does_not_prove_isolation(self):
        code, result = self.collect("missing", lambda target, command:
                                   subprocess.CompletedProcess(command, 1, "", "failure"))
        self.assertEqual(1, code)
        self.assertEqual("unverified_no_sends_captured", result["test_descriptions_sent"])
        self.assertFalse(result["output_contract_valid"])

    def test_corrupt_capture_retains_failed_observation(self):
        def corrupt(target, command):
            (target / "run").mkdir()
            (target / "run" / "run.json").write_text("{broken", encoding="utf-8")
            return subprocess.CompletedProcess(command, 1, "", "failure")
        code, result = self.collect("corrupt", corrupt)
        self.assertEqual(1, code)
        self.assertEqual("integration_failed", result["status"])
        self.assertEqual("collecting", result["stage"])
        self.assertEqual("JSONDecodeError", result["collector_error"])

    def test_valid_draft_with_wrong_capture_is_not_a_pass(self):
        from types import SimpleNamespace
        def completed(target, command):
            (target / "run").mkdir()
            captured = {"application_sends": [{
                "provider_input": {"system": "synthetic", "user": canonical({
                    "context": {"finding_ids": ["F-8001"]}})},
            }]}
            (target / "run" / "run.json").write_text(canonical(captured), encoding="utf-8")
            (target / "tickets.experimental.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "synthetic-result", "")
        with patch("tools.probe_triage.validate_output"), \
                patch("tools.probe_triage.read_inputs",
                      return_value=SimpleNamespace(data={"findings": {}})):
            code, result = self.collect("wrong-capture", completed)
        self.assertEqual(1, code)
        self.assertEqual("draft_generated_but_evidence_invalid", result["status"])
        self.assertEqual("isolation_failure", result["test_descriptions_sent"])


if __name__ == "__main__":
    unittest.main()
