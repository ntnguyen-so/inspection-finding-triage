from __future__ import annotations

import contextlib
from copy import deepcopy
import io
import json
import subprocess
import unittest
from unittest.mock import patch

from tests.triage_support import Artifacts, receipt as strict_receipt
from tests.test_copilot_triage import copilot_receipt
from tools import integrate_triage as integration
from triage.assessment import request_for
from triage.contracts import TriageError, digest
from triage.inputs import read_inputs
from triage.source_context import NativeContext


class NativeIntegrationDriverTests(Artifacts, unittest.TestCase):
    def test_new_copilot_preparation_defaults_to_fast_model(self):
        target = self.root / "fast-default"
        plan = {"model": integration.DEFAULT_COPILOT_MODEL}
        with patch.object(integration, "prepare", return_value=plan) as prepare, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, integration.main(["--output", str(target)]))
        self.assertEqual(integration.DEFAULT_COPILOT_MODEL, prepare.call_args.args[1])
        self.assertEqual("copilot_experiment", prepare.call_args.kwargs["execution_mode"])

    def test_new_azure_preparation_still_requires_explicit_deployment(self):
        target = self.root / "azure-no-deployment"
        with patch.object(integration, "prepare") as prepare, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(1, integration.main(["--output", str(target), "--provider", "azure"]))
        prepare.assert_not_called()

    def test_http_accounting_preserves_unknown_and_unrecorded_dispatches(self):
        complete = {"receipt": {"http_dispatches_observed": 1, "observed_model": "observed-test"}}
        self.assertEqual(1, integration.dispatch_summary([complete], 1)["http_attempts"])
        self.assertIsNone(integration.dispatch_summary([complete], 2)["http_attempts"])
        self.assertEqual(1, integration.dispatch_summary([complete], 2)["unrecorded_reservations"])
        self.assertIsNone(integration.dispatch_summary([complete, {}], 2)["http_attempts"])

    def setUp(self):
        super().setUp()
        self.prepared = self.root / "prepared"
        self.prepared.mkdir()
        self.plan = integration.prepare(self.prepared, "synthetic-not-an-LLM")
        integration.write_once(self.prepared / "plan.json", self.plan)

    def test_prepared_native_store_contains_unchanged_domain_and_development_only(self):
        inputs = read_inputs(self.prepared / "selected.csv", self.prepared / "registry.csv")
        activation = json.loads((self.prepared / "activation.json").read_text())
        config = self.plan["config"]
        bundle, _, local = NativeContext(self.prepared / "software-store", activation).prepare(
            inputs, config["knowledge_version"], config["assessment_time"], config["max_context_bytes"])
        self.assertEqual(self.plan["finding_ids"], bundle["finding_ids"])
        self.assertEqual(13, len(bundle["finding_ids"]))
        original = (integration.SOURCE / "reference" / "domain_knowledge.md").read_bytes()
        for entry in local["native_evidence"]["retrieval"]["entries"].values():
            self.assertEqual(digest(original), entry["source_sha256"])
            self.assertIn(entry["text"], original.decode("utf-8-sig"))
        self.assertFalse(self.plan["human_content_approval"])
        self.assertFalse(self.plan["acceptance_eligible"])

    def test_input_tampering_or_code_drift_cannot_silently_refresh_prepared_pins(self):
        with patch.object(integration, "hashes", return_value={"changed.py": "0" * 64}):
            with self.assertRaises(TriageError) as caught:
                integration.validate_plan(self.plan)
        self.assertEqual("freeze_changed", caught.exception.code)
        with (self.prepared / "registry.csv").open("ab") as stream:
            stream.write(b"\r\n")
        with self.assertRaises(TriageError) as caught:
            integration.validate_plan(self.plan)
        self.assertEqual("freeze_changed", caught.exception.code)

    def test_used_phase_ledger_cannot_be_reset_by_new_preparation(self):
        ledger = self.root / "native-e2e.experimental-ledger.json"
        ledger.write_bytes(b"retained prior failure accounting")
        other = self.root / "another"
        other.mkdir()
        with self.assertRaises(TriageError) as caught:
            integration.prepare(other, "synthetic-not-an-LLM")
        self.assertEqual("attempt_ledger", caught.exception.code)
        self.assertEqual(b"retained prior failure accounting", ledger.read_bytes())

    def test_explicit_correction_continues_existing_phase_without_refunding_spend(self):
        ledger = self.root / "native-e2e.experimental-ledger.json"
        integration.write_once(ledger, {
            "budget": 52, "execution_mode": "copilot_experiment", "reservations": list(range(12))})
        before = ledger.read_bytes()
        target = self.root / "continued"
        target.mkdir()
        continuation = {"reason": "Owner renewed correction of a diagnosed failure.",
                        "prior_plan_path": str(self.prepared / "plan.json"),
                        "prior_plan_sha256": digest((self.prepared / "plan.json").read_bytes()),
                        "prior_ledger_sha256": digest(before),
                        "prior_reserved_sends": 12}
        plan = integration.prepare(target, "synthetic-not-an-LLM", continuation=continuation)
        self.assertEqual(str(ledger), plan["config"]["attempt_ledger"])
        self.assertEqual(52, plan["phase_send_ceiling"])
        self.assertEqual(continuation, plan["continuation"])
        self.assertEqual(before, ledger.read_bytes())

    def test_one_fixed_config_repeat_uses_original_ledger_and_cannot_be_relaunched(self):
        origin = self.root / "first"
        origin.mkdir()
        integration.write_once(origin / "plan.json", self.plan)
        integration.write_once(origin / "observation.json", {"status": "experimental_e2e_pass"})
        success = {"status": "experimental_e2e_pass"}
        with patch.object(integration, "execute", return_value=success) as execute:
            for number, expected in ((1, 0), (2, 1)):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    code = integration.main([
                        "--repeat-from", str(origin), "--output", str(self.root / f"repeat-{number}"),
                        "--allow-inference"])
                self.assertEqual(expected, code)
        execute.assert_called_once()
        self.assertEqual(deepcopy(self.plan), execute.call_args.args[0])

    def test_post_dispatch_audit_failure_preserves_attempt_accounting(self):
        target = self.root / "audit-failure"
        target.mkdir()
        original_run = subprocess.run
        def fake_cli(command, **kwargs):
            if command[:3] != [integration.sys.executable, "-B", "-m"]:
                return original_run(command, **kwargs)
            (target / "run").mkdir()
            integration.write_once(target / "run" / "run.json", {"application_sends": [{
                "status": "failed", "provider_input": {"system": "Synthetic",
                    "user": json.dumps({"context": {"contract_version": 3, "finding_ids": []}})},
            }]})
            integration.write_once(self.root / "native-e2e.experimental-ledger.json",
                                   {"reservations": ["synthetic-dispatched-send"]})
            return subprocess.CompletedProcess(command, 1, "", "Synthetic CLI failure")
        with patch.object(integration.subprocess, "run", side_effect=fake_cli):
            report = integration.execute(self.plan, target)
        self.assertEqual("experimental_e2e_failed", report["status"])
        self.assertEqual("context_isolation", report["verification_error_class"])
        self.assertEqual(1, report["application_sends"])
        self.assertEqual(1, report["phase_application_send_reservations"])
        self.assertEqual(report, json.loads((target / "observation.json").read_text()))

    def test_successful_cli_capture_and_publication_are_verified_before_repeat_is_enabled(self):
        self.assert_successful_capture()

    def test_strict_cli_capture_requires_matching_retry_free_wire_receipts(self):
        self.prepared = self.root / "strict-plan"
        self.prepared.mkdir()
        self.plan = integration.prepare(self.prepared, "synthetic-not-an-LLM", execution_mode="strict")
        integration.write_once(self.prepared / "plan.json", self.plan)
        self.assert_successful_capture()

    def test_strict_plan_pins_explicit_reasoning_cap_and_timeout(self):
        target = self.root / "reasoning-plan"
        target.mkdir()
        plan = integration.prepare(target, "synthetic-not-an-LLM", execution_mode="strict",
                                   reasoning_effort="medium", max_completion_tokens=16384,
                                   timeout_seconds=180, azure_api="responses",
                                   minimum_request_interval_seconds=90)
        config = json.loads((target / "config.json").read_text())
        self.assertEqual(config, plan["config"])
        self.assertEqual(("medium", 16384, 180), (
            config["reasoning_effort"], config["azure_max_completion_tokens"], config["timeout_seconds"]))
        self.assertEqual(52, plan["phase_send_ceiling"])
        self.assertEqual("responses", config["azure_api"])
        self.assertEqual(90, config["minimum_request_interval_seconds"])

    def assert_successful_capture(self):
        target = self.root / "success"
        target.mkdir()
        inputs = read_inputs(self.prepared / "selected.csv", self.prepared / "registry.csv")
        activation = json.loads((self.prepared / "activation.json").read_text())
        config = self.plan["config"]
        _, text, _ = NativeContext(self.prepared / "software-store", activation).prepare(
            inputs, config["knowledge_version"], config["assessment_time"], config["max_context_bytes"])
        original_run = subprocess.run
        def fake_cli(command, **kwargs):
            if command[:3] != [integration.sys.executable, "-B", "-m"]:
                return original_run(command, **kwargs)
            sends, tickets = [], []
            for identifier, row in inputs.data["findings"].items():
                request = request_for(self.plan["model"], text, identifier, row["equipment_id"], 90, "low", None)
                system, user, _ = request.prepared()
                receipt = copilot_receipt(request)
                if config["execution_mode"] == "strict":
                    receipt = {**strict_receipt(), "system_sha256": digest(system.encode()),
                               "user_sha256": digest(user.encode())}
                sends.append({"finding_id": identifier, "status": "validated",
                              "provider_input": {"system": system, "user": user},
                              "receipt": receipt})
                tickets.append({
                    "ticket_id": "TKT-" + identifier[2:], "finding_id": identifier,
                    "equipment_id": row["equipment_id"], "summary": "Synthetic software fixture.",
                    "recommended_action": "Perform a synthetic inspection.",
                    **{field: {"score": 3, "rationale": "Synthetic, not engineering judgment."}
                       for field in ("likelihood_of_failure", "impact_of_failure", "urgency")},
                    "review_required": False, "review_reason": None,
                })
            (target / "run").mkdir()
            integration.write_once(target / "run" / "run.json",
                                   {"attempts" if config["execution_mode"] == "strict" else "application_sends": sends})
            integration.write_once(integration.Path(config["attempt_ledger"]),
                                   {"reservations": list(range(len(sends)))})
            output = target / "tickets.experimental.json"
            integration.write_once(output, {"generated_at": config["assessment_time"],
                                           "tickets_generated": len(tickets), "tickets": tickets})
            return subprocess.CompletedProcess(command, 0,
                json.dumps({"output_sha256": digest(output.read_bytes())}), "")
        with patch.object(integration.subprocess, "run", side_effect=fake_cli):
            report = integration.execute(self.plan, target)
        self.assertEqual("experimental_e2e_pass", report["status"])
        self.assertTrue(report["actual_native_context_delivery"])
        self.assertEqual(13, report["application_sends"])
        if config["execution_mode"] == "strict":
            self.assertEqual(13, report["http_attempts"])
        self.assertFalse(report["acceptance_eligible"])


if __name__ == "__main__":
    unittest.main()
