from __future__ import annotations

from copy import deepcopy
import unittest

from triage.contracts import TriageError
from triage.planning import compose_plan, validate_plan
from triage.policy import IMPAIRMENT_RECORD_ACTIVITY, RESTORATION_CLOSURE_ACTIVITY
from tests.triage_support import facts


def plan() -> dict:
    return {
        "diagnose": ["Check fault source."],
        "disposition": {"authority": "Integrity engineer", "decision": "approve repair basis"},
        "correction": {"text": "If confirmed, repair defect", "conditional": True},
        "acceptance": {
            "kind": "functional_test", "test": "Test restored function",
            "criterion": "approved limits",
            "witnessed": True, "independent_reference": True,
        },
    }


def decision() -> dict:
    return {
        "verification_activities": [
            "Verify fixed control.", "Check fault source.", RESTORATION_CLOSURE_ACTIVITY,
        ],
        "fixed_verification_activities": [
            "Verify fixed control.", RESTORATION_CLOSURE_ACTIVITY,
        ],
    }


def checks(value: str = "Check fault source.") -> list[dict]:
    return [{"verification_activity": value}]


class PlanningContractTests(unittest.TestCase):
    def test_code_composes_fixed_phase_order_and_one_witnessed_closure(self):
        proposed = plan()
        assessed_facts = facts()
        assessed_facts["protection_impaired"].update(
            applicability="applicable", state="suspected")
        validate_plan(proposed, decision(), assessed_facts, checks())
        result = compose_plan(proposed, decision())
        action = result["composed"]
        self.assertLess(action.index("Verify fixed"), action.index("Check fault"))
        self.assertLess(action.index("Check fault"), action.index("If confirmed"))
        self.assertLess(action.index("If confirmed"), action.index("Witness"))
        self.assertIn("Integrity engineer: If confirmed, repair defect.", action)
        self.assertEqual(1, action.count("Witness; close"))

    def test_model_owned_capacity_wording_is_preserved(self):
        proposed = plan()
        alias = "verify capacity against POB"
        proposed["diagnose"] = [alias]
        proposed["correction"]["conditional"] = False
        changed = {
            "verification_activities": [alias],
            "fixed_verification_activities": [],
        }
        assessed_facts = facts()
        assessed_facts["capacity_below_pob"]["verification_activity"] = alias
        validate_plan(proposed, changed, assessed_facts, [])
        result = compose_plan(proposed, changed)
        self.assertEqual([], result["projected_fixed_prework"])
        self.assertEqual([alias], result["projected_diagnose"])
        self.assertEqual(1, result["composed"].count(alias))

    def test_deviation_alias_projects_once(self):
        proposed = plan()
        proposed["diagnose"] = []
        proposed["correction"]["conditional"] = False
        alias = "verify deviation status"
        changed = {
            "verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
            "fixed_verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
            "covered_verification_activities": [alias],
        }
        assessed_facts = facts()
        assessed_facts["recorded_deviation"]["verification_activity"] = alias
        proposed["diagnose"] = [alias]
        validate_plan(proposed, changed, assessed_facts, [])
        result = compose_plan(proposed, changed)
        self.assertEqual(["Reconcile impairment record."],
                         result["projected_fixed_prework"])
        self.assertNotIn(alias, result["projected_diagnose"])

    def test_acceptance_cannot_repeat_policy_prework(self):
        proposed = plan()
        proposed["acceptance"]["test"] = IMPAIRMENT_RECORD_ACTIVITY
        changed = {
            "verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
            "fixed_verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
        }
        with self.assertRaisesRegex(TriageError, "policy pre-work"):
            validate_plan(proposed, changed, facts(), checks())

    def test_acceptance_cannot_repeat_covered_policy_alias(self):
        proposed = plan()
        proposed["acceptance"]["test"] = "verify deviation status"
        changed = {
            "verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
            "fixed_verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
            "covered_verification_activities": ["verify deviation status"],
        }
        with self.assertRaisesRegex(TriageError, "policy pre-work"):
            validate_plan(proposed, changed, facts(), checks())

    def test_multi_discipline_authority_wording_is_preserved(self):
        proposed = plan()
        proposed["disposition"]["authority"] = "Maintenance and integrity engineers"
        result = compose_plan(proposed, decision())
        self.assertIn(
            "Maintenance and integrity engineers: If confirmed",
            result["composed"],
        )

    def test_exact_membership_rejects_missing_paraphrased_and_extra_checks(self):
        for diagnose in ([], ["Check the fault source."],
                         ["Check fault source.", "Inspect unrelated item."]):
            with self.subTest(diagnose=diagnose):
                proposed = plan()
                proposed["diagnose"] = diagnose
                with self.assertRaises(TriageError):
                    validate_plan(proposed, decision(), facts(), checks())

    def test_impairment_requires_witness_and_independent_reference(self):
        assessed_facts = facts()
        assessed_facts["required_function_failed"].update(
            applicability="applicable", state="confirmed_true")
        for field in ("witnessed", "independent_reference"):
            proposed = plan()
            proposed["acceptance"][field] = False
            with self.subTest(field=field), self.assertRaises(TriageError):
                validate_plan(proposed, decision(), assessed_facts, checks())

    def test_conditional_correction_requires_diagnosis(self):
        proposed = plan()
        proposed["diagnose"] = []
        changed = decision()
        changed["verification_activities"].remove("Check fault source.")
        with self.assertRaisesRegex(TriageError, "requires diagnosis"):
            validate_plan(proposed, changed, facts(), [])

    def test_structure_does_not_depend_on_action_keywords(self):
        proposed = plan()
        proposed["diagnose"] = ["zzz"]
        proposed["disposition"] = {"authority": "zzz", "decision": "zzz"}
        proposed["correction"] = {"text": "zzz", "conditional": False}
        proposed["acceptance"] = {
            "kind": "inspection", "test": "yyy", "criterion": None,
            "witnessed": False, "independent_reference": False,
        }
        changed = {"verification_activities": ["zzz"], "fixed_verification_activities": []}
        validate_plan(proposed, changed, facts(), checks("zzz"))
        result = compose_plan(proposed, changed)
        self.assertEqual(
            ["diagnose", "disposition", "correction", "acceptance"],
            [key for key, present in (
                ("diagnose", bool(result["diagnose"])),
                ("disposition", result["disposition"] is not None),
                ("correction", result["has_correction"]),
                ("acceptance", result["has_acceptance"]),
            ) if present],
        )

    def test_all_authored_fact_and_uncertainty_checks_are_covered_exactly_once(self):
        assessed_facts = facts()
        assessed_facts["capacity_below_pob"]["verification_activity"] = "Check capacity."
        uncertainties = [{"verification_activity": "Check exposure."}]
        changed = {
            "verification_activities": [],
            "fixed_verification_activities": [],
        }
        proposed = plan()
        proposed["diagnose"] = ["Check capacity."]
        proposed["acceptance"]["test"] = "Check exposure."
        validate_plan(proposed, changed, assessed_facts, uncertainties)
        proposed["acceptance"]["test"] = "Check capacity."
        with self.assertRaises(TriageError):
            validate_plan(proposed, changed, assessed_facts, uncertainties)

    def test_confirmed_failure_cannot_close_without_functional_correction_path(self):
        assessed_facts = facts()
        assessed_facts["required_function_failed"].update(
            applicability="applicable", state="confirmed_true")
        for field in ("disposition", "correction"):
            proposed = plan()
            proposed[field] = None
            with self.subTest(field=field), self.assertRaises(TriageError):
                validate_plan(proposed, decision(), assessed_facts, checks())
        proposed = plan()
        proposed["acceptance"]["kind"] = "inspection"
        with self.assertRaisesRegex(TriageError, "functional acceptance"):
            validate_plan(proposed, decision(), assessed_facts, checks())

    def test_exact_policy_literal_remains_model_owned_without_provenance(self):
        assessed_facts = facts()
        assessed_facts["recorded_deviation"]["verification_activity"] = (
            IMPAIRMENT_RECORD_ACTIVITY)
        changed = {
            "verification_activities": [IMPAIRMENT_RECORD_ACTIVITY],
            "fixed_verification_activities": [],
        }
        proposed = plan()
        proposed["diagnose"] = [IMPAIRMENT_RECORD_ACTIVITY]
        proposed["correction"]["conditional"] = False
        validate_plan(proposed, changed, assessed_facts, [])
        result = compose_plan(proposed, changed)
        action = result["composed"]
        self.assertEqual([], result["projected_fixed_prework"])
        self.assertEqual([IMPAIRMENT_RECORD_ACTIVITY], result["projected_diagnose"])
        self.assertEqual(1, action.count(IMPAIRMENT_RECORD_ACTIVITY))
        self.assertLess(action.index(IMPAIRMENT_RECORD_ACTIVITY),
                        action.index("If confirmed"))

    def test_uncertain_suspected_impairment_requires_closure_path(self):
        assessed_facts = facts()
        assessed_facts["protection_impaired"].update(
            applicability="uncertain", state="suspected")
        for field in ("disposition", "correction", "acceptance"):
            proposed = plan()
            proposed[field] = None
            with self.subTest(field=field), self.assertRaises(TriageError):
                validate_plan(proposed, decision(), assessed_facts, checks())

    def test_f1002_like_three_check_plan_fits_without_dropping_phases(self):
        proposed = {
            "diagnose": [
                "Trace leak; gas test",
                "Test as-found relief and seat",
                "Check deviation record",
            ],
            "disposition": {
                "authority": "Integrity engineer",
                "decision": "Decide controls/repair",
            },
            "correction": {
                "text": "If passing, repair PSV as approved",
                "conditional": True,
            },
            "acceptance": {
                "kind": "functional_test",
                "test": "Test relief and seat tightness",
                "criterion": None,
                "witnessed": True,
                "independent_reference": True,
            },
        }
        authored = checks("Trace leak; gas test") + checks(
            "Test as-found relief and seat") + checks("Check deviation record")
        assessed_facts = facts()
        assessed_facts["protection_impaired"].update(
            applicability="applicable", state="suspected")
        changed = {
            "verification_activities": [item["verification_activity"] for item in authored],
            "fixed_verification_activities": [],
        }
        validate_plan(proposed, changed, assessed_facts, authored)
        action = compose_plan(proposed, changed)["composed"]
        self.assertLessEqual(len(action), 300)
        self.assertNotIn("If confirmed, If passing", action)
        self.assertIn("Witness; close.", action)

    def test_schema_caps_fit_three_phase_checks_and_witnessed_closure(self):
        diagnose = ["A" * 25, "B" * 25, "C" * 25]
        proposed = {
            "diagnose": diagnose,
            "disposition": {"authority": "D" * 24, "decision": "E" * 80},
            "correction": {"text": "If " + "F" * 27, "conditional": True},
            "acceptance": {
                "kind": "functional_test", "test": "G" * 35,
                "criterion": "H" * 20, "witnessed": True,
                "independent_reference": True,
            },
        }
        assessed_facts = facts()
        assessed_facts["required_function_failed"].update(
            applicability="applicable", state="confirmed_true")
        authored = [*map(lambda value: {"verification_activity": value}, diagnose)]
        changed = {
            "verification_activities": diagnose,
            "fixed_verification_activities": [],
        }
        validate_plan(proposed, changed, assessed_facts, authored)
        self.assertLessEqual(len(compose_plan(proposed, changed)["composed"]), 300)

    def test_grounded_requirement_must_appear_in_declared_phase(self):
        proposed = plan()
        proposed["planning_requirements"] = [{
            "activity": "Inspect diaphragm and discharge path",
            "phase": "diagnose",
            "reason": "Low discharge pressure has more than one credible source.",
            "evidence": [{"source_ref": "finding:F-1", "quote": "low discharge pressure"}],
        }]
        with self.assertRaisesRegex(TriageError, "grounded planning requirement"):
            validate_plan(proposed, decision(), facts(), checks())
        proposed["diagnose"] = ["Inspect diaphragm and discharge path"]
        changed = {
            "verification_activities": ["Inspect diaphragm and discharge path"],
            "fixed_verification_activities": [],
        }
        validate_plan(
            proposed, changed, facts(),
            checks("Inspect diaphragm and discharge path"),
        )
        self.assertEqual("plan-v2", compose_plan(proposed, changed)["contract"])


if __name__ == "__main__":
    unittest.main()
