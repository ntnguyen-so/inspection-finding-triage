from __future__ import annotations

import unittest

from triage.projection import PROJECTION_VERSION, project_ticket_text


class ProjectionTests(unittest.TestCase):
    def test_projection_preserves_every_rule_and_binding_override(self):
        decision = {
            "policy_version": "triage-policy-v12", "base": 5, "final": 9,
            "review_required": True,
            "rules": [
                {"rule_id": "O-PROTECTION", "kind": "confirmed_override", "floor": 9,
                 "reason": "Confirmed impairment.", "sources": ["source:a"], "activity": None},
                {"rule_id": "R-SCE", "kind": "review", "floor": 1,
                 "reason": "SCE review.", "sources": [], "activity": None},
            ],
        }
        projected = project_ticket_text(decision, 4, 6)
        self.assertEqual(PROJECTION_VERSION, projected["projection_version"])
        self.assertIn("O-PROTECTION[confirmed_override,U9]", projected["urgency_rationale"])
        self.assertIn("R-SCE[review]", projected["urgency_rationale"])
        self.assertNotIn("R-SCE[review,U1]", projected["urgency_rationale"])
        self.assertIn("Basis: Confirmed impairment.", projected["urgency_rationale"])
        self.assertIn("O-PROTECTION: confirmed unrecorded", projected["review_reason"])

    def test_nonbinding_confirmed_override_still_has_plain_language_basis(self):
        decision = {
            "policy_version": "triage-policy-v12", "base": 9, "final": 9,
            "review_required": True,
            "rules": [{
                "rule_id": "O-PROTECTION", "kind": "confirmed_override", "floor": 9,
                "reason": "Confirmed impairment without deviation.",
                "sources": ["source:a"], "activity": None,
            }],
        }
        projected = project_ticket_text(decision, 9, 9)
        self.assertIn("Basis: Confirmed impairment without deviation.",
                      projected["urgency_rationale"])

    def test_projection_is_deterministic_and_nonempty_for_review(self):
        decision = {
            "policy_version": "triage-policy-v12", "base": 4, "final": 4,
            "review_required": True,
            "rules": [{"rule_id": "R-SCE", "kind": "review", "floor": 1,
                       "reason": "SCE review.", "sources": [], "activity": None}],
        }
        first = project_ticket_text(decision, 3, 4)
        self.assertEqual(first, project_ticket_text(decision, 3, 4))
        self.assertTrue(first["review_reason"])
        self.assertIn("R-SCE: SCE draft requires", first["review_reason"])

    def test_review_projection_names_trigger_specific_check(self):
        decision = {
            "policy_version": "triage-policy-v12", "base": 5, "final": 7,
            "review_required": True,
            "rules": [{
                "rule_id": "P-SAFETY-UNKNOWN", "kind": "precautionary_policy", "floor": 7,
                "reason": "Current exposure is unresolved.", "sources": ["source:a"],
                "activity": "Verify occupied-area exposure.",
            }],
        }
        projected = project_ticket_text(decision, 4, 5)
        self.assertIn("Basis: Current exposure is unresolved.",
                      projected["urgency_rationale"])
        self.assertIn("checks: Verify occupied-area exposure.",
                      projected["review_reason"])
        self.assertIn("Why: Current exposure is unresolved.",
                      projected["review_reason"])


if __name__ == "__main__":
    unittest.main()
