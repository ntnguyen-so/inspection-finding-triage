"""Synthetic-only transport preparation: no provider startup or network dispatch."""
from contextlib import redirect_stderr
import asyncio
import io
import unittest
from unittest.mock import patch

from eval.knowledge import handoff
from eval.knowledge import package
from eval.tests.knowledge import test_package as package_tests
from eval.knowledge.attempts import AttemptLedger, inspect_ledger
from llm_inference import InferenceError
from triage_knowledge.contracts import KnowledgeError, canonical_bytes, sha256, strict_json


class KnowledgeHandoffTests(unittest.TestCase):
    def setUp(self):
        package_tests.KnowledgePackageTests.setUp(self)
        report = package.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "pass", report.get("failure"))
        prior_path = self.inputs / "prior-handoff.experimental-ledger.json"
        ledger = AttemptLedger(prior_path, {
            "phase": "historical-software-fixture", "slots": {"historical": "0" * 64},
            "maximum_attempts": 2, "per_slot_attempts": 2, "schedule": ["historical"],
            "development_slots": ["historical"], "recoverable_codes": ["timeout"]})
        ledger.finish(ledger.reserve("historical", "0" * 64), {"status": "success"})
        self.prior_bytes = prior_path.read_bytes()
        for patcher in (patch.object(package, "SOURCE_PATHS", self.paths),
                        patch.object(handoff, "COUNTS", self.counts),
                        patch.object(handoff, "PRIOR_LEDGER", prior_path),
                        patch.object(handoff, "PRIOR_LEDGER_SHA256", sha256(self.prior_bytes)),
                        patch.object(handoff, "LEDGER",
                                     self.inputs / "handoff-v2.experimental-ledger.json")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_modified_and_rehashed_packet_is_not_authorized_by_its_own_hash(self):
        path = self.output / "development-context.json"
        packet = strict_json(path.read_bytes())
        address = next(iter(packet["payload"]["knowledge"]))
        packet["payload"]["knowledge"][address] += "\nAltered transport source."
        packet["source_index"][address] = packet["payload"]["knowledge"][address]
        body = {key: value for key, value in packet.items() if key != "context_hash"}
        path.write_bytes(canonical_bytes({**body, "context_hash": sha256(canonical_bytes(body))}))
        with self.assertRaises(KnowledgeError) as raised:
            handoff.prepare(self.output)
        self.assertEqual(raised.exception.code, "context_contract")

    def test_exact_development_packet_excludes_test_findings_and_binds_message_audit(self):
        request, plan = handoff.prepare(self.output)
        self.assertEqual(request.user.encode(), (self.output / "development-context.json").read_bytes())
        packet = strict_json(request.user)
        self.assertEqual(set(packet["payload"]["findings"]), {"F-9001", "F-9002"})
        self.assertNotIn("Synthetic condition 3.", request.user)
        self.assertEqual(len(packet["payload"]["registry"]), 3)
        self.assertEqual(plan["maximum_application_attempts"], 1)
        self.assertEqual(plan["maximum_attempts_per_slot"], 1)
        self.assertEqual(plan["prior_ledger"]["application_attempts_reserved"], 1)
        self.assertEqual(plan["cumulative_handoff_ceiling"], 2)
        self.assertEqual(request.model, "gpt-6-luna")
        self.assertIsNone(plan["usd_cost"])
        receipt = {
            "dispatched": True, "adapter_attempts": 1, "inference_calls_observed": 1,
            "observed_model": plan["model"], "boundary_violation": None,
            "system_sha256": plan["system_sha256"], "user_sha256": plan["user_sha256"],
            "tool_counts_observed": [0],
            "message_audit": [
                {"kind": kind, "matches_sdk_input": True, "content_sha256": plan[key]}
                for kind, key in (("system.message", "system_sha256"), ("user.message", "user_sha256"))
            ],
        }
        handoff.verify_receipt(receipt, plan)
        receipt["message_audit"][1]["content_sha256"] = "0" * 64
        with self.assertRaises(KnowledgeError):
            handoff.verify_receipt(receipt, plan)

    def test_nonpassing_tampered_frozen_run_and_amended_lineage_block_dispatch(self):
        report_path, plan_path = self.output / "report.json", self.output / "plan.json"
        original_report, original_plan = report_path.read_bytes(), plan_path.read_bytes()
        for mutation in ("nonpassing", "plan", "lineage"):
            report_path.write_bytes(original_report)
            plan_path.write_bytes(original_plan)
            report = strict_json(original_report)
            if mutation == "nonpassing":
                report["goals"]["lifecycle"] = "failed"
                report_path.write_bytes(canonical_bytes(report))
            elif mutation == "plan":
                frozen = strict_json(original_plan)
                frozen["input_sha256"]["domain"] = "0" * 64
                plan_path.write_bytes(canonical_bytes(frozen))
            else:
                report["baseline_release"] = report["lifecycle"]["edited_release"]
                report_path.write_bytes(canonical_bytes(report))
            probe = self.output / ("probe-" + mutation)
            with (self.subTest(mutation=mutation), redirect_stderr(io.StringIO()),
                  patch.object(handoff, "dispatch") as dispatch):
                self.assertEqual(handoff.main([
                    "--package-run", str(self.output), "--output", str(probe), "--plan-only"]), 1)
                dispatch.assert_not_called()
                diagnostic = strict_json((probe / "report.json").read_bytes())
                self.assertEqual(diagnostic["status"], "failed")
                self.assertIn(diagnostic["error_class"],
                              ("package_acceptance", "package_freeze", "source_lineage"))

    def test_one_prior_reservation_leaves_one_send_and_never_resets_old_ledger(self):
        request, plan = handoff.prepare(self.output)
        calls = []

        class NoNetworkProvider:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def generate(self, sent):
                calls.append(sent)
                raise InferenceError("timeout", "Synthetic timeout, no SDK or network.")

        with patch("llm_inference.CopilotProvider", NoNetworkProvider):
            with self.assertRaises(KnowledgeError) as raised:
                asyncio.run(handoff.dispatch(request, plan, self.output / "probe-one"))
            self.assertEqual(raised.exception.code, "handoff_failed")
            with self.assertRaises(KnowledgeError) as raised:
                asyncio.run(handoff.dispatch(request, plan, self.output / "probe-two"))
            self.assertEqual(raised.exception.code, "handoff_failed")
        exhausted = strict_json((self.output / "probe-two" / "calls" / "observation.json").read_bytes())
        self.assertEqual(exhausted["results"][handoff.SLOT]["reason"], "application_budget_exhausted")
        current = inspect_ledger(handoff.LEDGER)
        self.assertEqual(len(calls), 1)
        self.assertEqual(current["application_attempts_reserved"]
                         + plan["prior_ledger"]["application_attempts_reserved"], 2)
        self.assertEqual(current["maximum_application_attempts"], 1)
        self.assertEqual(handoff.PRIOR_LEDGER.read_bytes(), self.prior_bytes)
        handoff.PRIOR_LEDGER.write_bytes(self.prior_bytes + b"\n")
        with self.assertRaises(KnowledgeError) as raised:
            handoff.prepare(self.output)
        self.assertEqual(raised.exception.code, "prior_ledger_integrity")


if __name__ == "__main__":
    unittest.main()
