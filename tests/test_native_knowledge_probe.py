from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from tests.triage_support import Artifacts
from tools import probe_native_knowledge as probe
from tools.integrate_triage import write_once


class NativeProbeDriverTests(Artifacts, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.prepared = self.root / "plan"
        self.prepared.mkdir()
        self.plan = probe.prepare(self.prepared, "synthetic-not-an-LLM")

    def test_only_explicit_policy_changes_between_actual_native_before_after_packets(self):
        for kind in ("positive", "negative"):
            before, after = [json.loads((self.prepared / f"{kind}-{when}.context.json").read_text())
                             for when in ("before", "after")]
            self.assertEqual("isolated_probe", before["input_purpose"])
            self.assertEqual(before["payload"], after["payload"])
            self.assertEqual(before["source_index"], after["source_index"])
            self.assertNotEqual(before["assessment_policy"], after["assessment_policy"])
            self.assertNotEqual(before["context_hash"], after["context_hash"])
            self.assertNotIn("Testing-only diagnostic convention", str(before["payload"]["knowledge"]))
        self.assertEqual(["F-1016"], self.plan["cases"]["negative-before"]["finding_ids"])
        self.assertEqual(8, self.plan["maximum_sends"])

    def test_exact_positive_controls_do_not_claim_negative_semantic_acceptance(self):
        target = self.root / "observed"
        target.mkdir()
        observed_scores = iter(((6, 3), (8, 3), (2, 4), (2, 4)))
        async def fake_workflow(inputs, context, factory, config, output, evidence, **kwargs):
            self.assertEqual("isolated_probe", kwargs["purpose"])
            self.assertTrue(output.name.endswith(".experimental.json"))
            likelihood, impact = next(observed_scores)
            write_once(output, {"tickets": [{
                "likelihood_of_failure": {"score": likelihood},
                "impact_of_failure": {"score": impact},
            }]})
            return {"published_output": True}
        with patch.object(probe, "run_workflow", side_effect=fake_workflow):
            report = asyncio.run(probe.execute(self.plan, target))
        self.assertTrue(report["positive_policy_response_observed"])
        self.assertEqual(3, report["conditions"]["positive-before"]["observed_impact"])
        self.assertEqual(3, report["conditions"]["positive-after"]["observed_impact"])
        self.assertEqual("pending_calibrated_review", report["negative_semantic_status"])
        self.assertFalse(report["acceptance_eligible"])


if __name__ == "__main__":
    unittest.main()
