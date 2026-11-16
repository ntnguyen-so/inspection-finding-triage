from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from llm_inference import InferenceResponse
from tools.probe_knowledge import CONDITIONS, ROOT, prepare, run
from triage_knowledge.contracts import sha256


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "observation"
        self.plan = prepare(self.target, "synthetic-model")

    def test_only_declared_overlay_changes_within_each_input_pair(self):
        split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
        for kind in ("positive", "negative"):
            requests = [json.loads((self.target / f"{kind}-{policy}.request.json").read_text())
                        for policy in ("before", "after")]
            self.assertEqual(requests[0]["system"], requests[1]["system"])
            contexts = []
            for request in requests:
                self.assertIsNone(request["response_schema"])
                self.assertIn("JSON Schema", request["system"])
                message = json.loads(request["user"])
                self.assertNotIn("expected", message)
                context = deepcopy(message["context"])
                expected = {"F-9001"} if kind == "positive" else set(split["partitions"]["development"])
                self.assertEqual(set(context["finding_ids"]), expected)
                self.assertFalse(set(context["finding_ids"]) & set(split["partitions"]["test"]))
                self.assertNotIn("context_hash", context)
                self.assertNotIn("source_manifest", context)
                for mapping in (context["payload"]["knowledge"], context["source_index"]):
                    for key in list(mapping):
                        if key.startswith("probe-policy-"):
                            del mapping[key]
                contexts.append(context)
            self.assertEqual(contexts[0], contexts[1])

    def test_invalid_real_shape_is_retained_and_phase_cannot_repeat(self):
        requests = []

        class FakeProvider:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                pass

            def configuration(self):
                return {"provider": "synthetic-no-network"}

            async def generate(self, request):
                requests.append(request)
                system, user, _ = request.prepared()
                receipt = {
                    "system_sha256": sha256(system.encode()), "user_sha256": sha256(user.encode()),
                    "message_audit": [{"kind": kind, "matches_sdk_input": True}
                                      for kind in ("system.message", "user.message")],
                    "boundary_violation": None,
                }
                return InferenceResponse('{"invalid":"assessment"}', None, receipt)

        ledger = Path(self.temporary.name) / "phase.experimental-ledger.json"
        result = asyncio.run(run(self.target, ledger_path=ledger, factory=FakeProvider))
        self.assertEqual(result["status"], "failed_or_inconclusive")
        self.assertEqual(result["attempt_reservations"], 4)
        self.assertEqual(len(requests), 4)
        for name in CONDITIONS:
            self.assertEqual(result["results"][name]["error_class"], "assessment_schema")
            self.assertEqual((self.target / f"{name}.response.txt").read_text(), '{"invalid":"assessment"}')
        with self.assertRaises(ValueError):
            asyncio.run(run(self.target, ledger_path=ledger, factory=FakeProvider))
        self.assertEqual(len(requests), 4)

    def test_changed_request_is_rejected_before_reserving_or_calling(self):
        path = self.target / "positive-before.request.json"
        path.write_text("{}")
        ledger = Path(self.temporary.name) / "phase.experimental-ledger.json"
        with self.assertRaises(ValueError):
            asyncio.run(run(self.target, ledger_path=ledger))
        self.assertFalse(ledger.exists())
