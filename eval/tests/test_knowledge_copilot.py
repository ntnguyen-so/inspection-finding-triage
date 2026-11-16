from pathlib import Path
import tempfile
import unittest

from llm_inference import InferenceError, InferenceRequest, InferenceResponse
from eval.knowledge_copilot import run_requests


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
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        request = InferenceRequest(model="test-model", system="Source-only test", user="Source")
        self.requests = {"dev": request, "evaluation": request}

    async def run_probe(self, provider, validate=lambda slot, value: {"accepted": True},
                        allow=True):
        return await run_requests(
            provider, self.requests, output=self.root / "observations",
            ledger_path=self.root / "phase.experimental-ledger.json", phase="software-test",
            validate_response=validate, development_slots=frozenset({"dev"}),
            allow_inference=allow)

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
