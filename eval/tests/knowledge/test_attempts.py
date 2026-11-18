from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eval.knowledge import attempts
from eval.knowledge.attempts import AttemptLedger, inspect_ledger


class AttemptLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "phase.experimental-ledger.json"
        self.plan = {"phase": "software-test", "slots": {"a": "a" * 64, "b": "b" * 64},
                     "maximum_attempts": 2, "per_slot_attempts": 2,
                     "schedule": ["a", "b"], "development_slots": ["a"],
                     "recoverable_codes": ["transport"]}

    def test_failure_is_spent_and_total_ceiling_survives_reload(self):
        ledger = AttemptLedger(self.path, self.plan)
        ledger.finish(ledger.reserve("a", "a" * 64),
                      {"status": "failed", "error_class": "transport"})
        ledger = AttemptLedger(self.path, self.plan)
        ledger.finish(ledger.reserve("a", "a" * 64),
                      {"status": "failed", "error_class": "transport"})
        with self.assertRaisesRegex(ValueError, "exhausted"):
            ledger.reserve("b", "b" * 64)
        self.assertEqual(ledger.observation()["application_attempts_reserved"], 2)
        self.assertIsNone(ledger.observation()["http_attempts"])

    def test_changed_request_plan_and_success_repeat_are_rejected(self):
        ledger = AttemptLedger(self.path, self.plan)
        with self.assertRaisesRegex(ValueError, "not in"):
            ledger.reserve("a", "b" * 64)
        ledger.finish(ledger.reserve("a", "a" * 64), {"status": "success"})
        with self.assertRaisesRegex(ValueError, "successful"):
            ledger.reserve("a", "a" * 64)
        changed = {**self.plan, "maximum_attempts": 3}
        with self.assertRaisesRegex(ValueError, "changed"):
            AttemptLedger(self.path, changed)

    def test_reserved_send_is_not_automatically_retried_after_crash(self):
        ledger = AttemptLedger(self.path, self.plan)
        ledger.reserve("a", "a" * 64)
        with self.assertRaisesRegex(ValueError, "Interrupted"):
            AttemptLedger(self.path, self.plan).reserve("a", "a" * 64)
        self.assertEqual(ledger.observation()["application_attempts_reserved"], 1)
        self.assertEqual(inspect_ledger(self.path)["attempts"][0]["state"], "reserved")

    def test_schedule_and_recoverability_are_frozen(self):
        ledger = AttemptLedger(self.path, self.plan)
        ledger.finish(ledger.reserve("a", "a" * 64),
                      {"status": "failed", "error_class": "proposal_validation"})
        with self.assertRaisesRegex(ValueError, "not recoverable"):
            ledger.reserve("a", "a" * 64)
        with self.assertRaises(ValueError):
            AttemptLedger(self.path, {**self.plan, "development_slots": []})

    def test_corrupt_duplicate_keys_fail_without_replacing_evidence(self):
        self.path.write_bytes(b'{"plan":{},"plan":{}}')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            AttemptLedger(self.path, self.plan)
        self.assertEqual(self.path.read_bytes(), before)

    def test_transient_windows_replace_denial_is_retried(self):
        ledger = AttemptLedger(self.path, self.plan)
        original = attempts.os.replace
        calls = 0

        def transient(source, destination):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise PermissionError("Synthetic Windows file lock")
            return original(source, destination)

        with (
            patch.object(attempts.os, "replace", side_effect=transient),
            patch.object(attempts.time, "sleep") as sleep,
        ):
            ledger.reserve("a", "a" * 64)
        self.assertEqual(calls, 2)
        sleep.assert_called_once_with(0.01)
        self.assertEqual(ledger.observation()["application_attempts_reserved"], 1)


if __name__ == "__main__":
    unittest.main()
