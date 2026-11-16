from pathlib import Path
import json
import tempfile
import unittest

from llm_inference import InferenceError, InferenceRequest, InferenceResponse
from eval.knowledge_copilot import run_requests
from eval.knowledge_eval import ROOT


class Provider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.sends = 0

    async def generate(self, request):
        self.sends += 1
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return InferenceResponse("{}", result, {"http_attempts": None})


class CopilotDriverTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "eval" / "results" / "knowledge" / "extraction")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        request = InferenceRequest(model="test-model", system="Source-only test", user="Source")
        self.requests = {"dev": request, "evaluation": request}

    async def run_probe(self, provider, validate=lambda slot, value: {"accepted": True},
                        allow=True, **limits):
        return await run_requests(
            provider, self.requests, output=self.root / "observations",
            ledger_path=self.root / "phase.experimental-ledger.json", phase="software-test",
            validate_response=validate, development_slots=frozenset({"dev"}),
            allow_inference=allow, **limits)

    async def test_structural_retry_preserves_first_failure(self):
        provider = Provider([InferenceError("malformed_json", "Synthetic"), {}, {}])
        report = await self.run_probe(provider)
        self.assertEqual(provider.sends, 3)
        self.assertEqual(report["accounting"]["application_attempts_reserved"], 3)
        self.assertEqual(report["results"]["dev"]["attempt"], 2)
        self.assertTrue((self.root / "observations" / "attempt-0001.json").exists())
        self.assertEqual(report["accounting"]["attempts"][0]["outcome"]["raw_invalid_output"],
                         "unavailable_from_adapter")
        self.assertFalse(report["c1_qualified"])
        plan = json.loads((self.root / "phase.experimental-ledger.json").read_text("utf-8"))["plan"]
        self.assertEqual((plan["maximum_attempts"], plan["per_slot_attempts"]), (26, 2))

    async def test_optional_total_ceiling_stops_without_spending_another_slot(self):
        provider = Provider([{}, {}])
        report = await self.run_probe(provider, max_application_attempts=1, max_attempts_per_slot=1)
        self.assertEqual(provider.sends, 1)
        self.assertEqual(report["accounting"]["maximum_application_attempts"], 1)
        self.assertEqual(report["results"]["evaluation"], {
            "status": "unexecuted", "reason": "application_budget_exhausted",
        })
        path = self.root / "phase.experimental-ledger.json"
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "plan changed"):
            await self.run_probe(Provider([{}]))
        self.assertEqual(path.read_bytes(), before)

    async def test_optional_per_slot_ceiling_forbids_a_second_recoverable_attempt(self):
        provider = Provider([InferenceError("timeout", "Synthetic"), {}])
        report = await self.run_probe(provider, max_attempts_per_slot=1)
        self.assertEqual(provider.sends, 1)
        self.assertEqual(report["results"]["dev"]["status"], "failed")
        self.assertEqual(report["results"]["evaluation"]["status"], "unexecuted")

    async def test_invalid_or_boolean_ceilings_never_reserve_or_send(self):
        for key, values in (
            ("max_application_attempts", (0, 27, True, 1.0, "1")),
            ("max_attempts_per_slot", (0, 3, True, 1.0, "1")),
        ):
            for value in values:
                provider = Provider([{}])
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "ceilings"):
                    await self.run_probe(provider, **{key: value})
                self.assertEqual(provider.sends, 0)
                self.assertFalse((self.root / "phase.experimental-ledger.json").exists())

    async def test_reference_failure_is_not_retried_and_stops_evaluation(self):
        def invalid(slot, value):
            raise ValueError("Invented source-unit ID")
        provider = Provider([{}])
        report = await self.run_probe(provider, invalid)
        self.assertEqual(provider.sends, 1)
        self.assertEqual(report["results"]["evaluation"]["status"], "unexecuted")

    async def test_missing_authorization_does_not_send_or_create_ledger(self):
        provider = Provider([{}])
        with self.assertRaisesRegex(ValueError, "authorization"):
            await self.run_probe(provider, allow=False)
        self.assertEqual(provider.sends, 0)
        self.assertFalse((self.root / "phase.experimental-ledger.json").exists())

    async def test_negative_validation_is_not_a_success_shaped_fallback(self):
        provider = Provider([{}])
        report = await self.run_probe(provider, lambda slot, value: {"accepted": False})
        self.assertEqual(provider.sends, 1)
        self.assertEqual(report["results"]["dev"]["status"], "failed")

    async def test_mixed_profiles_fail_before_reserving_or_sending(self):
        self.requests["evaluation"] = InferenceRequest(
            model="different-model", system="Source-only test", user="Source")
        provider = Provider([{}])
        with self.assertRaisesRegex(ValueError, "frozen profile"):
            await self.run_probe(provider)
        self.assertEqual(provider.sends, 0)
        self.assertFalse((self.root / "phase.experimental-ledger.json").exists())

    async def test_validator_bug_keeps_paid_response_and_unresolved_reservation(self):
        def broken(slot, value):
            raise KeyError("Synthetic evaluator bug")
        provider = Provider([{}])
        with self.assertRaises(KeyError):
            await self.run_probe(provider, broken)
        self.assertTrue((self.root / "observations" / "response-0001.json").exists())
        self.assertEqual(provider.sends, 1)

    async def test_retry_exhaustion_stops_without_replacing_existing_observations(self):
        provider = Provider([InferenceError("transport", "First"),
                             InferenceError("transport", "Second")])
        report = await self.run_probe(provider)
        self.assertEqual(provider.sends, 2)
        self.assertEqual(report["results"]["evaluation"]["status"], "unexecuted")
        before = (self.root / "observations" / "observation.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already contains"):
            await self.run_probe(Provider([{}]))
        self.assertEqual((self.root / "observations" / "observation.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
