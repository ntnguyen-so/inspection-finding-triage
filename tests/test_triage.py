from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import AsyncMock, patch

from jsonschema import Draft202012Validator
from llm_inference import InferenceError, InferenceResponse
from llm_inference.contracts import canonical, strict_json
from triage.assessment import (
    SCHEMA, assessment_schema, citation_catalog, project_native_assessment,
    request_schema, validate_assessment, validate_same_day_attention,
)
from triage.contracts import TriageError, digest
from triage.inputs import ExportedContext, FINDING_FIELDS, read_inputs, validate_context
from triage.prompt import DEFAULT_ASSESSMENT_PROMPT_VERSION, assessment_prompt
from triage.policy import (
    CAPACITY_COMPARISON_ACTIVITY, CONTROL_ALIGNMENT_ACTIVITY, FAILED_TEST_RETEST_ACTIVITY,
    IMPAIRMENT_RECORD_ACTIVITY, RESTORATION_CLOSURE_ACTIVITY, SAME_DAY_ATTENTION_ACTIVITY,
    base_urgency, derive_policy, gap_verification_activity,
)
from triage.projection import project_related_context
from triage.workflow import (
    action_retry_budget, compose_action, run_workflow, validate_output,
)
from tests.triage_support import (
    Artifacts, CUTOFF, FixtureContext, FakeProvider, QUOTE, REFERENCE, assessment,
    facts, native_response, receipt, source_files, write_csv,
)


class RequestSchemaTests(unittest.TestCase):
    def test_native_joint_fact_score_and_exact_source_pairs_without_score_repair(self):
        context = {"contract_version": 3, "source_index": {
            REFERENCE: QUOTE, "other": "Other source text.\nFollowing exact line."}}
        validator = Draft202012Validator(request_schema(context, "F-8001", "PMP-8001"))
        original = assessment(likelihood=9)
        original["facts"]["required_function_failed"].update(
            state="confirmed_true", evidence=[{"source_ref": REFERENCE, "quote": QUOTE}])
        catalog = citation_catalog(context["source_index"])
        draft = native_response(original, catalog)
        self.assertTrue(validator.is_valid(draft))
        projected, attention = project_native_assessment(canonical(draft), context["source_index"])
        self.assertEqual(original, strict_json(projected))
        self.assertEqual([], attention)
        for value, state in ((10, "confirmed_true"), (7, "suspected")):
            supported = deepcopy(draft)
            supported["assessment"]["likelihood_of_failure"]["score"] = value
            supported["assessment"]["likelihood_of_failure"]["required_function_failed"]["state"] = state
            self.assertTrue(validator.is_valid(supported))
        for field in ("score", "selector"):
            invalid = deepcopy(draft)
            if field == "score":
                invalid["assessment"]["likelihood_of_failure"]["score"] = 7
            else:
                invalid["assessment"]["likelihood_of_failure"]["evidence"][0] = "unknown"
            self.assertFalse(validator.is_valid(invalid))
        with self.assertRaises(TriageError):
            project_native_assessment(canonical(original), context["source_index"])
        duplicate = deepcopy(draft)
        duplicate["assessment"]["facts"]["required_function_failed"] = original["facts"]["required_function_failed"]
        with self.assertRaises(TriageError):
            project_native_assessment(canonical(duplicate), context["source_index"])
        line_citation = deepcopy(draft)
        key = next(key for key, value in catalog.items() if value["quote"] == "Following exact line.")
        line_citation["assessment"]["likelihood_of_failure"]["evidence"][0] = key
        self.assertTrue(validator.is_valid(line_citation))
        line_citation["assessment"]["likelihood_of_failure"]["evidence"][0] = {
            "source_ref": "other", "quote": context["source_index"]["other"]}
        self.assertFalse(validator.is_valid(line_citation))

    def test_native_unassessable_projection_does_not_create_scores(self):
        index = {REFERENCE: QUOTE}
        draft = assessment()
        draft.update(status="unassessable", inability_reason="Required scores cannot be justified.")
        for key in ("summary", "recommended_action", "likelihood_of_failure", "impact_of_failure", "facts"):
            draft[key] = None
        wire = native_response(draft, citation_catalog(index))
        validator = Draft202012Validator(request_schema(
            {"contract_version": 3, "source_index": index}, "F-8001", "PMP-8001"))
        self.assertTrue(validator.is_valid(wire))
        projected, attention = project_native_assessment(canonical(wire), index)
        self.assertEqual(draft, strict_json(projected))
        self.assertEqual([], attention)
        mixed = native_response(assessment(), citation_catalog(index))
        mixed["assessment"]["facts"] = None
        self.assertFalse(validator.is_valid(mixed))
        wire["assessment"]["likelihood_of_failure"] = {"score": 5}
        self.assertFalse(validator.is_valid(wire))
        with self.assertRaises(TriageError) as caught:
            validate_assessment(projected, {"finding_id": "F-8001", "equipment_id": "PMP-8001"}, {})
        self.assertEqual("unassessable", caught.exception.code)

    def test_native_catalog_preserves_literal_lines_identity_and_snapshot_binding(self):
        index = {REFERENCE: QUOTE, "other": "  Literal line.  \n\n" + QUOTE}
        catalog = citation_catalog(index)
        self.assertEqual(3, len(catalog))
        self.assertIn({"source_ref": "other", "quote": "  Literal line.  "}, catalog.values())
        self.assertEqual(2, sum(value["quote"] == QUOTE for value in catalog.values()))
        wire = native_response(assessment(), catalog)
        for changed in ({**index, "other": "Changed."}, {**index, "a": "Added."}):
            with self.assertRaisesRegex(TriageError, "catalog differs"):
                project_native_assessment(canonical(wire), changed)
        wire["assessment"]["impact_of_failure"]["evidence"] = ["unknown"]
        with self.assertRaisesRegex(TriageError, "Unknown or invalid"):
            project_native_assessment(canonical(wire), index)

    def test_same_day_directive_and_trigger_require_exact_own_target_sources(self):
        finding = {"finding_id": "F-8001", "equipment_id": "PMP-8001"}
        own = "equipment:PMP-8001:engineer_comment"
        index = {REFERENCE: QUOTE, own: "Attend today.", "knowledge:legend": "9-10 today.",
                 "equipment:PMP-8999:engineer_comment": "Attend today."}
        item = {"reason": "The target requires attention today.",
                "directive_evidence": [{"source_ref": own, "quote": "Attend today."}],
                "trigger_evidence": [{"source_ref": REFERENCE, "quote": QUOTE}]}
        self.assertEqual([item], validate_same_day_attention([item], finding, index))
        schema = request_schema({"contract_version": 3, "source_index": index}, "F-8001", "PMP-8001")
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(native_response(assessment(), citation_catalog(index), [item])))
        for name in ("directive_evidence", "trigger_evidence"):
            for address in ("knowledge:legend", "equipment:PMP-8999:engineer_comment"):
                invalid = deepcopy(item)
                invalid[name] = [{"source_ref": address, "quote": index[address]}]
                self.assertFalse(validator.is_valid(
                    native_response(assessment(), citation_catalog(index), [invalid])))
                with self.assertRaises(TriageError):
                    validate_same_day_attention([invalid], finding, index)
            for citations in ([], [{"source_ref": own, "quote": "Invented timing."}]):
                invalid = deepcopy(item)
                invalid[name] = citations
                with self.assertRaises(TriageError):
                    validate_same_day_attention([invalid], finding, index)

    def test_native_constraints_bind_known_addresses_and_identity_without_mutating_base(self):
        original = deepcopy(SCHEMA)
        schema = request_schema({"source_index": {REFERENCE: QUOTE}}, "F-8001", "PMP-8001")
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(assessment()))
        for field, value in (("finding_id", "F-9999"), ("equipment_id", "PMP-9999")):
            changed = assessment()
            changed[field] = value
            self.assertFalse(validator.is_valid(changed))
        for location in ("citation", "checked"):
            changed = assessment()
            if location == "citation":
                changed["likelihood_of_failure"]["evidence"][0]["source_ref"] = "finding:F-8001"
            else:
                changed["facts"]["required_function_failed"]["sources_checked"] = ["finding:F-8001"]
            self.assertFalse(validator.is_valid(changed))
        self.assertEqual(original, SCHEMA)

    def test_native_schema_orders_evidence_before_planning_text_without_opening_objects(self):
        schema = request_schema(
            {"contract_version": 3, "source_index": {REFERENCE: QUOTE}},
            "F-8001", "PMP-8001",
        )
        self.assertEqual(
            ["same_day_attention", "assessment", "citation_catalog_sha256"],
            list(schema["properties"]),
        )
        assessed = schema["properties"]["assessment"]["anyOf"][0]
        names = list(assessed["properties"])
        self.assertLess(names.index("likelihood_of_failure"), names.index("summary"))
        self.assertLess(names.index("impact_of_failure"), names.index("summary"))
        self.assertLess(names.index("facts"), names.index("summary"))
        self.assertLess(names.index("uncertainties"), names.index("summary"))
        self.assertLess(names.index("summary"), names.index("recommended_action"))
        for branch in schema["properties"]["assessment"]["anyOf"]:
            self.assertFalse(branch["additionalProperties"])
            self.assertEqual(set(branch["properties"]), set(branch["required"]))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]), set(schema["required"]))

    def test_v4_native_schema_replaces_free_text_action_with_closed_plan(self):
        from triage.prompt import PLANNED_ASSESSMENT_CONTRACT
        schema = request_schema(
            {"contract_version": 3, "source_index": {REFERENCE: QUOTE}},
            "F-8001", "PMP-8001", PLANNED_ASSESSMENT_CONTRACT,
        )
        assessed = schema["properties"]["assessment"]["anyOf"][0]
        self.assertIn("plan", assessed["properties"])
        self.assertNotIn("recommended_action", assessed["properties"])
        plan = assessed["properties"]["plan"]
        self.assertFalse(plan["additionalProperties"])
        self.assertEqual(
            {"diagnose", "disposition", "correction", "acceptance"},
            set(plan["required"]),
        )

    def test_native_fact_branches_preserve_applicability_state_contract(self):
        schema = request_schema({"source_index": {REFERENCE: QUOTE}}, "F-8001", "PMP-8001")
        validator = Draft202012Validator(schema)
        for applicability, state, valid in (
            ("not_applicable", "unknown", True), ("not_applicable", "confirmed_false", False),
            ("uncertain", "suspected", True), ("uncertain", "confirmed_true", False),
            ("applicable", "confirmed_false", True),
        ):
            changed = assessment()
            changed["facts"]["evacuation_unavailable"].update(applicability=applicability, state=state)
            if applicability == "uncertain":
                changed["facts"]["evacuation_unavailable"]["verification_activity"] = (
                    "Verify applicability.")
            self.assertEqual(valid, validator.is_valid(changed))
        uncertain = assessment()
        uncertain["facts"]["protection_test_failed"].update(
            applicability="uncertain", state="unknown", verification_activity=None)
        self.assertFalse(validator.is_valid(uncertain))
        uncertain["facts"]["protection_test_failed"]["verification_activity"] = (
            "Verify test applicability.")
        self.assertTrue(validator.is_valid(uncertain))
        from llm_inference.azure import native_schema
        Draft202012Validator.check_schema(native_schema(schema)["json_schema"]["schema"])

    def test_independent_validator_distinguishes_unknown_address_from_bad_quote(self):
        proposed = assessment()
        proposed["likelihood_of_failure"]["evidence"][0]["source_ref"] = "finding:F-8001"
        with self.assertRaisesRegex(TriageError, "outside context.source_index"):
            validate_assessment(canonical(proposed), {
                "finding_id": "F-8001", "equipment_id": "PMP-8001"}, {REFERENCE: QUOTE})

    def test_one_correction_reports_both_score_contradiction_and_bad_citation(self):
        proposed = assessment(likelihood=7)
        proposed["facts"]["required_function_failed"].update(
            state="confirmed_true", evidence=[{"source_ref": REFERENCE, "quote": QUOTE}])
        proposed["likelihood_of_failure"]["evidence"][0]["quote"] = "Invented quotation"
        with self.assertRaises(TriageError) as caught:
            validate_assessment(canonical(proposed), {
                "finding_id": "F-8001", "equipment_id": "PMP-8001"}, {REFERENCE: QUOTE})
        self.assertEqual("assessment_contradiction", caught.exception.code)
        feedback = str(caught.exception)[:500]
        self.assertIn("requires likelihood>=9", feedback)
        self.assertIn("Invented quotation", feedback)
        self.assertIn(REFERENCE, feedback)


class PromptArtifactTests(unittest.TestCase):
    def test_assessment_prompt_has_stable_identity_and_exact_request_text(self):
        artifact = assessment_prompt()
        self.assertEqual("assessment-system-v1", DEFAULT_ASSESSMENT_PROMPT_VERSION)
        self.assertEqual("44206b1b43708f90ce7c2900796daeb3716b54fa39e921438739ba1f57b74bb0",
                         artifact.sha256)
        self.assertTrue(artifact.text.startswith("Produce an evidence-grounded draft assessment"))
        self.assertFalse(artifact.text.endswith("\n"))

    def test_v2_prompt_excludes_known_equipment_specific_clauses(self):
        artifact = assessment_prompt("assessment-system-v2")
        for text in ("illegible label", "out of service", "vibration directive",
                     "during-cranking", "mass, height", "failure to start"):
            self.assertNotIn(text, artifact.text)

    def test_v3_prompt_classifies_documentation_and_operational_unknowns_generically(self):
        artifact = assessment_prompt("assessment-system-v3")
        self.assertIn("Documentation-only identity and record verification", artifact.text)
        self.assertIn("credible current safety consequence path", artifact.text)
        self.assertIn(RESTORATION_CLOSURE_ACTIVITY, artifact.text)
        for text in ("PSV-3420", "V-1305", "F-1014", "F-1016"):
            self.assertNotIn(text, artifact.text)

    def test_v4_prompt_uses_typed_plan_contract_without_case_specific_rules(self):
        artifact = assessment_prompt("assessment-system-v4")
        self.assertEqual("native-assessment-v3", artifact.assessment_contract)
        self.assertEqual("triage-assessment-schema-v2", artifact.schema_contract)
        self.assertIn("Return plan-v1 instead of a free-text action", artifact.text)
        self.assertIn("acceptance proves restored function after correction", artifact.text.lower())
        for text in ("PSV-3420", "V-1305", "F-1014", "F-1016"):
            self.assertNotIn(text, artifact.text)

    def test_v5_prompt_grounds_one_failure_basis_and_complete_planning_scope(self):
        artifact = assessment_prompt("assessment-system-v5")
        self.assertEqual("native-assessment-v4", artifact.assessment_contract)
        self.assertEqual("triage-assessment-schema-v3", artifact.schema_contract)
        self.assertIn("Define one shared failure_basis", artifact.text)
        self.assertIn("planning_requirements", artifact.text)
        self.assertIn("exceptional specialist review", artifact.text)
        for text in ("F-1007", "F-1012", "F-1019", "P-3305", "LB-4102"):
            self.assertNotIn(text, artifact.text)

        schema = assessment_schema("native-assessment-v4")
        fact = schema["properties"]["facts"]["anyOf"][0]["properties"][
            "protection_impaired"
        ]
        self.assertEqual(
            64,
            fact["properties"]["verification_activity"]["maxLength"],
        )

    def test_v7_prompt_applies_versioned_test_interpretation(self):
        artifact = assessment_prompt("assessment-system-v7")
        self.assertIn("assessment_policy.test_result_interpretation", artifact.text)
        for text in (
            "F-1017", "FW-8101", "9.2 barg", "11 barg",
            "F-1013", "F-1014", "F-1015", "F-1018",
        ):
            self.assertNotIn(text, artifact.text)

    def test_v8_prompt_requires_visible_related_chronology_without_transfer(self):
        artifact = assessment_prompt("assessment-system-v8")
        base = assessment_prompt("assessment-system-v7")
        self.assertTrue(artifact.text.startswith(base.text + "\n\n"))
        self.assertIn("assessment_policy.test_result_interpretation", artifact.text)
        self.assertIn("A citation used only inside a typed fact is incomplete.", artifact.text)
        self.assertIn("Do not copy its fact state, override, directive or defect", artifact.text)
        for text in ("F-1011", "F-1020", "DEL-8300", "branch valve"):
            self.assertNotIn(text, artifact.text)

    def test_v6_prompt_reserves_exceptional_review_for_prequeue_safety_decisions(self):
        artifact = assessment_prompt("assessment-system-v6")
        self.assertEqual("native-assessment-v4", artifact.assessment_contract)
        self.assertIn("Do not convert missing post-report observations", artifact.text)
        self.assertIn("Non-safety diagnostic uncertainty", artifact.text)
        for text in ("F-1007", "F-1012", "F-1019", "P-3305", "LB-4102"):
            self.assertNotIn(text, artifact.text)

    def test_missing_prompt_fails_explicitly(self):
        assessment_prompt.cache_clear()
        self.addCleanup(assessment_prompt.cache_clear)
        with patch("triage.prompt.files", side_effect=OSError("missing")):
            with self.assertRaisesRegex(TriageError, "Assessment prompt artifact is unavailable"):
                assessment_prompt()


class ActionCompositionTests(unittest.TestCase):
    def test_related_fact_context_is_projected_without_transferring_state(self):
        facts = {
            "protection_restored": {
                "applicability": "applicable",
                "state": "unknown",
                "reason": "A later action does not prove restored function.",
                "evidence": [{
                    "source_ref": "finding:F-B:finding_description",
                    "quote": "A control was changed later.",
                }],
            },
            "required_function_failed": {
                "applicability": "applicable",
                "state": "confirmed_true",
                "reason": "The target test failed.",
                "evidence": [{
                    "source_ref": "finding:F-A:finding_description",
                    "quote": "The target test failed.",
                }],
            },
        }
        self.assertEqual(
            " Related-finding context cited by typed facts: "
            "[protection_restored=unknown] Fact reason: "
            "A later action does not prove restored function. "
            "Related quote (F-B finding_description): "
            "\"A control was changed later.\"",
            project_related_context(facts, "F-A"),
        )

    def test_code_owned_activity_is_removed_from_core_and_appended_once(self):
        core = f"Diagnose and correct the fault. {FAILED_TEST_RETEST_ACTIVITY} Record findings."
        result = compose_action(
            core,
            ["Check exposure.", FAILED_TEST_RETEST_ACTIVITY],
            [FAILED_TEST_RETEST_ACTIVITY],
        )
        self.assertEqual(
            "Diagnose and correct the fault. Record findings. Check exposure. "
            "Witness function test; close impairment only after pass.",
            result["composed"],
        )
        self.assertEqual(1, result["composed"].count(FAILED_TEST_RETEST_ACTIVITY))

    def test_f1002_like_many_check_overflow_has_exact_actionable_budget(self):
        from triage.workflow import action_overflow_message
        fixed = [
            CAPACITY_COMPARISON_ACTIVITY,
            SAME_DAY_ATTENTION_ACTIVITY,
        ]
        model = [
            "Check approved impairment and deviation records.",
            "Leak-test the passing PSV and confirm correction.",
            "Verify set-pressure certification and relief readiness.",
        ]
        composition = compose_action(
            "Authorized inspector to assess PSV-1310 passing below set pressure and correct the defect.",
            [*fixed, *model],
            fixed,
        )
        original = deepcopy(composition)
        message, budget = action_overflow_message(composition)
        fixed_chars = sum(len(activity) + 1 for activity in fixed)
        self.assertEqual(fixed_chars, budget["fixed_appended_chars_with_separators"])
        self.assertEqual(3, budget["model_check_count"])
        self.assertEqual(20, budget["safety_margin_chars"])
        self.assertEqual(
            280,
            fixed_chars + budget["model_separator_chars"]
            + budget["core_max_chars"]
            + budget["model_check_count"] * budget["model_check_max_chars"],
        )
        self.assertGreaterEqual(budget["core_max_chars"],
                                len(composition["model_core"]) / 2)
        self.assertIn(f"Proportional core cap {budget['core_max_chars']}", message)
        self.assertIn("uniform model-check cap", message)
        self.assertIn("code-owned and must remain exact", message)
        self.assertIn("preserve every activity", message)
        self.assertEqual(original, composition)
        self.assertLessEqual(len(message), 500)

    def test_retry_budget_arithmetic_is_exact_for_zero_through_eight_model_checks(self):
        fixed = ["Verify fixed policy condition."]
        for count in range(9):
            with self.subTest(count=count):
                model = [f"Verify model condition {number}." for number in range(count)]
                composition = compose_action("Correct the defect.", [*fixed, *model], fixed)
                budget = action_retry_budget(composition)
                self.assertEqual(count, budget["model_check_count"])
                self.assertEqual(count == 0, budget["model_check_max_chars"] == 0)
                if count:
                    self.assertGreater(budget["model_check_max_chars"], 0)
                self.assertEqual(
                    budget["safety_target_chars"],
                    budget["fixed_appended_chars_with_separators"]
                    + budget["model_separator_chars"] + budget["core_max_chars"]
                    + count * budget["model_check_max_chars"],
                )
                self.assertGreaterEqual(
                    budget["hard_limit_chars"] - budget["safety_target_chars"], 20)

    def test_retry_budget_is_stable_when_model_checks_are_reordered(self):
        fixed = ["Verify fixed policy condition."]
        model = [
            "Check short condition.",
            "Verify a substantially longer model-authored condition and purpose.",
            "Retest medium condition after correction.",
        ]
        first = action_retry_budget(compose_action("Repair the release gear.", [*fixed, *model], fixed))
        second = action_retry_budget(compose_action(
            "Repair the release gear.", [*fixed, *reversed(model)], fixed))
        self.assertEqual(first, second)
        self.assertIsInstance(first["model_check_max_chars"], int)

    def test_fixed_and_model_appended_checks_are_separated_without_rewriting(self):
        fixed = ["Obtain source-required attention today."]
        model = ["Verify relief capacity.", "Check deviation record."]
        result = compose_action("Inspect PSV-1310.", [model[0], fixed[0], model[1]], fixed)
        self.assertEqual(fixed, result["fixed_appended_activities"])
        self.assertEqual(model, result["model_appended_activities"])
        self.assertIn(fixed[0], result["composed"])

    def test_model_authored_text_matching_a_fixed_literal_stays_model_owned(self):
        decision = derive_policy(
            2, 3, facts(), [{
                "material": True, "safety": True, "affected_decision": "disposition",
                "reason": "Synthetic model-owned timing check.",
                "verification_activity": SAME_DAY_ATTENTION_ACTIVITY,
                "evidence": [], "sources_checked": [REFERENCE],
            }],
            sce=False, gaps=[], same_day_attention=[],
        )
        self.assertIn(SAME_DAY_ATTENTION_ACTIVITY, decision["verification_activities"])
        self.assertNotIn(SAME_DAY_ATTENTION_ACTIVITY, decision["fixed_verification_activities"])
        result = compose_action(
            "Inspect the condition.", decision["verification_activities"],
            decision["fixed_verification_activities"],
        )
        self.assertEqual([SAME_DAY_ATTENTION_ACTIVITY],
                         result["model_appended_activities"])

    def test_only_exact_duplicate_activities_are_omitted_without_rewriting_source_text(self):
        core = "Repair the seal; Verify capability."
        result = compose_action(core, [
            "Verify capability.", "Record the test.", "  Record   the test.  ", "Record the test."
        ])
        self.assertEqual(core, result["model_core"])
        self.assertEqual(["Record the test.", "  Record   the test.  "],
                         result["appended_activities"])
        self.assertEqual(["Verify capability.", "Record the test.", "  Record   the test.  "],
                         result["required_activities"])
        self.assertEqual(core + " Record the test.   Record   the test.  ", result["composed"])
        self.assertEqual("Inspect.", compose_action("Inspect.", [])["composed"])

    def test_impossible_fixed_only_overflow_fails_visibly(self):
        fixed = ["Verify fixed condition A: " + "A" * 140,
                 "Verify fixed condition B: " + "B" * 140]
        with self.assertRaises(TriageError) as caught:
            action_retry_budget(compose_action("Inspect.", fixed, fixed))
        self.assertEqual("policy_verification_impossible", caught.exception.code)
        self.assertIn("no nonempty action core", str(caught.exception))

    def test_paraphrases_do_not_suppress_exact_obligations(self):
        result = compose_action("Verify capability; record the test.", ["Verify capability.", "Record the test."])
        self.assertEqual("Verify capability; record the test. Verify capability. Record the test.",
                         result["composed"])

    def test_whitespace_variant_completeness_uses_the_same_exact_semantics(self):
        activities = [
            "Inspect release gear.", "Inspect  release gear.",
            "Test release gear.", "Functional Test release gear.",
        ]
        result = compose_action("Overhaul release gear.", activities)
        self.assertEqual(activities, result["appended_activities"])
        self.assertFalse([activity for activity in activities if activity not in result["composed"]])


class PolicyTests(unittest.TestCase):
    def test_policy_reports_all_missing_fact_activities_in_one_retry(self):
        values = facts()
        values["protection_impaired"]["state"] = "suspected"
        values["recorded_deviation"]["state"] = "unknown"
        values["evacuation_unavailable"]["state"] = "confirmed_true"
        values["capacity_below_pob"]["state"] = "unknown"
        with self.assertRaises(TriageError) as caught:
            self.derive(values)
        self.assertEqual("policy_verification", caught.exception.code)
        message = str(caught.exception)
        self.assertNotIn("facts.recorded_deviation.verification_activity", message)
        self.assertIn("facts.capacity_below_pob.verification_activity", message)

    def test_independently_worked_grid_and_monotonicity(self):
        expected = (
            (1, 2, 3, 4, 4, 5, 6, 6, 7, 8),
            (2, 2, 3, 4, 5, 5, 6, 7, 7, 8),
            (2, 3, 3, 4, 5, 6, 6, 7, 8, 8),
            (2, 3, 4, 4, 5, 6, 7, 7, 8, 9),
            (3, 3, 4, 5, 5, 6, 7, 8, 8, 9),
            (3, 4, 4, 5, 6, 6, 7, 8, 9, 9),
            (3, 4, 5, 5, 6, 7, 7, 8, 9, 10),
            (4, 4, 5, 6, 6, 7, 8, 8, 9, 10),
            (4, 5, 5, 6, 7, 7, 8, 9, 9, 10),
            (4, 5, 6, 6, 7, 8, 8, 9, 10, 10),
        )
        for likelihood in range(1, 11):
            for impact in range(1, 11):
                result = base_urgency(likelihood, impact)
                self.assertEqual(expected[likelihood - 1][impact - 1], result)
                self.assertTrue(1 <= result <= 10)
                if likelihood < 10:
                    self.assertLessEqual(result, base_urgency(likelihood + 1, impact))
                if impact < 10:
                    self.assertLessEqual(result, base_urgency(likelihood, impact + 1))
        self.assertEqual((4, 8), (base_urgency(10, 1), base_urgency(1, 10)))

    def test_score_types_and_ranges(self):
        for invalid in (True, False, 1.0, "2", 0, 11, None):
            with self.subTest(invalid=invalid), self.assertRaises(TriageError):
                base_urgency(invalid, 5)

    def derive(self, values, likelihood=1, impact=1, sce=False, uncertainties=None, gaps=None):
        return derive_policy(likelihood, impact, values, uncertainties or [], sce=sce, gaps=gaps or [])

    def test_confirmed_override_state_matrix(self):
        for impaired in ("confirmed_true", "confirmed_false", "suspected", "unknown"):
            for deviation in ("confirmed_true", "confirmed_false", "suspected", "unknown"):
                with self.subTest(impaired=impaired, deviation=deviation):
                    values = facts()
                    values["protection_impaired"]["state"] = impaired
                    if impaired == "suspected":
                        values["protection_impaired"]["verification_activity"] = "Verify protection capability."
                    values["recorded_deviation"].update(state=deviation,
                                                       verification_activity="Check deviation log.")
                    result = self.derive(values)
                    ids = [r["rule_id"] for r in result["rules"]]
                    self.assertEqual("O-PROTECTION" in ids,
                                     impaired == "confirmed_true" and deviation == "confirmed_false")
                    expected = 9 if impaired == "confirmed_true" and deviation == "confirmed_false" else (
                        7 if impaired in {"confirmed_true", "suspected"}
                        and deviation in {"confirmed_false", "unknown", "suspected"}
                        and not (impaired == "confirmed_true" and deviation == "confirmed_false")
                        else 1)
                    self.assertEqual(expected, result["final"])
                    if impaired == "suspected" and deviation in {"unknown", "suspected"}:
                        self.assertIn("Protection impairment suspected", result["review_reason"])
                        self.assertIn(IMPAIRMENT_RECORD_ACTIVITY,
                                      result["verification_activities"])
                        self.assertIn("Check deviation log.",
                                      result["covered_verification_activities"])
                        rule = next(rule for rule in result["rules"]
                                    if rule["reason"].startswith("Protection impairment suspected"))
                        self.assertEqual("precautionary_policy", rule["kind"])
                    if impaired == "suspected" and deviation == "confirmed_false":
                        self.assertIn("no recorded deviation", result["review_reason"])
                        self.assertNotIn("Check deviation log.", result["verification_activities"])
                        self.assertIn("Verify protection capability.",
                                      result["verification_activities"])

    def test_precautions_capacity_and_restoration(self):
        values = facts()
        values["protection_test_failed"]["state"] = "confirmed_true"
        result = self.derive(values)
        self.assertIn(FAILED_TEST_RETEST_ACTIVITY, result["verification_activities"])
        self.assertIn(FAILED_TEST_RETEST_ACTIVITY, result["fixed_verification_activities"])
        self.assertEqual(FAILED_TEST_RETEST_ACTIVITY, result["verification_activities"][-1])

        values["unlogged_impairment_discovered"]["state"] = "confirmed_true"
        values["protection_restored"].update(
            state="unknown", verification_activity=RESTORATION_CLOSURE_ACTIVITY)
        uncertainty = {
            "material": True,
            "safety": False,
            "affected_decision": "disposition",
            "reason": "Restoration remains unverified.",
            "sources_checked": [REFERENCE],
            "verification_activity": RESTORATION_CLOSURE_ACTIVITY,
        }
        result = self.derive(values, uncertainties=[uncertainty])
        self.assertEqual(1, result["verification_activities"].count(RESTORATION_CLOSURE_ACTIVITY))
        self.assertEqual(RESTORATION_CLOSURE_ACTIVITY, result["verification_activities"][-1])

        for capacity in ("confirmed_true", "confirmed_false", "suspected", "unknown"):
            values = facts()
            values["evacuation_unavailable"]["state"] = "confirmed_true"
            values["capacity_below_pob"].update(state=capacity, verification_activity="Check capacity and POB.")
            result = self.derive(values)
            ids = [r["rule_id"] for r in result["rules"]]
            self.assertEqual(1 if capacity == "confirmed_false" else 9, result["final"])
            self.assertEqual("O-EVACUATION" in ids, capacity == "confirmed_true")
            self.assertEqual("P-EVACUATION" in ids, capacity in {"suspected", "unknown"})
        for restored in ("confirmed_true", "confirmed_false", "suspected", "unknown"):
            values = facts()
            values["unlogged_impairment_discovered"]["state"] = "confirmed_true"
            values["protection_restored"].update(state=restored, verification_activity="Verify restoration.")
            result = self.derive(values)
            self.assertEqual(1 if restored == "confirmed_true" else 9, result["final"])
            fixed = result["fixed_verification_activities"]
            if restored == "confirmed_true":
                self.assertEqual([], fixed)
            else:
                self.assertEqual([
                    CONTROL_ALIGNMENT_ACTIVITY,
                    IMPAIRMENT_RECORD_ACTIVITY,
                    RESTORATION_CLOSURE_ACTIVITY,
                ], fixed)

    def test_uncertain_dependents_cannot_bypass_immediate_precautions(self):
        for trigger, dependent, rule in (
            ("evacuation_unavailable", "capacity_below_pob", "P-EVACUATION"),
            ("unlogged_impairment_discovered", "protection_restored", "P-RESTORATION"),
        ):
            for state in ("unknown", "suspected"):
                values = facts()
                values[trigger]["state"] = "confirmed_true"
                values[dependent].update(applicability="uncertain", state=state,
                                         verification_activity="Verify current condition.")
                result = self.derive(values)
                self.assertEqual(9, result["final"])
                self.assertIn(rule, {item["rule_id"] for item in result["rules"]})
                self.assertNotIn("confirmed_override", {item["kind"] for item in result["rules"]})
                self.assertIn("Verify current condition.", result["verification_activities"])
                if trigger == "evacuation_unavailable":
                    self.assertNotIn("Verify current condition.",
                                     result["fixed_verification_activities"])
        self.assertNotIn(CAPACITY_COMPARISON_ACTIVITY, self.derive(facts())["verification_activities"])

    def test_source_directed_attention_floors_urgency_without_altering_scores_or_facts(self):
        citation = {"source_ref": REFERENCE, "quote": QUOTE}
        attention = [{"reason": "Explicit same-day source instruction with observed trigger.",
                      "directive_evidence": [citation], "trigger_evidence": [citation]}]
        values = facts()
        before = deepcopy(values)
        result = derive_policy(1, 1, values, [], sce=False, gaps=[], same_day_attention=attention)
        self.assertEqual((1, 9), (result["base"], result["final"]))
        self.assertEqual("source_directed_attention", result["rules"][0]["kind"])
        self.assertEqual([SAME_DAY_ATTENTION_ACTIVITY], result["verification_activities"])
        self.assertFalse(result["review_required"])
        self.assertEqual(before, values)
        self.assertIn("L=1, I=1", result["rationale"])
        with self.assertRaises(TriageError):
            derive_policy(1, 1, values, [], sce=False, gaps=[], same_day_attention=[{}])

    def test_multiple_rules_do_not_change_scores_or_hide_nonbinding_floor(self):
        values = facts()
        for name in ("protection_impaired", "capacity_below_pob", "protection_test_failed"):
            values[name]["state"] = "confirmed_true"
        values["recorded_deviation"]["state"] = "confirmed_false"
        before = deepcopy(values)
        result = self.derive(values, 10, 10, sce=True)
        self.assertEqual(10, result["final"])
        self.assertEqual({"O-PROTECTION", "O-EVACUATION", "P-FAILED-TEST",
                          "P-SCE-HIGH-IMPACT"},
                         {x["rule_id"] for x in result["rules"]})
        self.assertEqual(before, values)

    def test_materiality_applicability_and_missing_partner(self):
        self.assertFalse(self.derive(facts())["review_required"])
        self.assertEqual(1, self.derive(facts(), sce=True)["final"])
        for safety in (True, False):
            uncertainty = {"material": True, "safety": safety, "reason": "Unknown state affects decision.",
                           "affected_decision": "redundancy" if safety else "likelihood",
                           "sources_checked": [REFERENCE], "verification_activity": "Verify state."}
            result = self.derive(facts(), uncertainties=[uncertainty])
            self.assertEqual(7 if safety else 1, result["final"])
            self.assertEqual(["Verify state."], result["verification_activities"])
        gap = {"kind": "tagged_partner_not_in_registry", "partner_equipment_id": "PMP-8999",
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        self.assertEqual(7, self.derive(facts(), sce=True, gaps=[gap])["final"])
        self.assertFalse(self.derive(facts(), gaps=[gap])["review_required"])
        values = facts()
        values["protection_impaired"].update(applicability="uncertain",
                                            verification_activity="Verify applicability.")
        self.assertEqual(7, self.derive(values)["final"])
        values["protection_impaired"]["state"] = "confirmed_true"
        with self.assertRaises(TriageError):
            self.derive(values)
        values["protection_impaired"].update(applicability="not_applicable", state="confirmed_false")
        with self.assertRaises(TriageError):
            self.derive(values)

    def test_high_impact_sce_gets_week_level_floor(self):
        result = self.derive(facts(), likelihood=1, impact=8, sce=True)
        self.assertEqual((6, 7), (result["base"], result["final"]))
        self.assertIn("P-SCE-HIGH-IMPACT", {rule["rule_id"] for rule in result["rules"]})
        self.assertEqual(6, self.derive(facts(), likelihood=1, impact=8, sce=False)["final"])
        self.assertLess(self.derive(facts(), likelihood=1, impact=7, sce=True)["final"], 7)

    def test_missing_verification_blocks_policy(self):
        values = facts()
        values["evacuation_unavailable"]["state"] = "confirmed_true"
        with self.assertRaisesRegex(TriageError, "verification"):
            self.derive(values)

    def test_triggered_dependent_fact_cannot_be_declared_nonapplicable(self):
        for positive, negative in (
            ("protection_impaired", "recorded_deviation"),
            ("evacuation_unavailable", "capacity_below_pob"),
            ("unlogged_impairment_discovered", "protection_restored"),
        ):
            with self.subTest(positive=positive):
                values = facts()
                values[positive]["state"] = "confirmed_true"
                values[negative]["applicability"] = "not_applicable"
                with self.assertRaises(TriageError) as caught:
                    self.derive(values)
                self.assertEqual("fact_contract", caught.exception.code)
                values[positive]["state"] = "unknown"
                result = self.derive(values)
                self.assertEqual(1, result["final"])
                self.assertFalse(result["review_required"])
        values = facts()
        values["protection_impaired"]["state"] = "suspected"
        values["recorded_deviation"]["applicability"] = "not_applicable"
        with self.assertRaises(TriageError) as caught:
            self.derive(values)
        self.assertEqual("fact_contract", caught.exception.code)
        values = facts()
        values["unlogged_impairment_discovered"]["state"] = "confirmed_true"
        values["protection_restored"]["state"] = "confirmed_false"
        self.assertEqual(9, self.derive(values)["final"])

    def test_non_sce_safety_uncertainty_still_receives_floor(self):
        gap = {"kind": "tagged_partner_not_in_registry", "partner_equipment_id": "PMP-8999",
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        uncertainty = {"material": True, "safety": True, "reason": "Safety consequence on non-SCE.",
                       "affected_decision": "protection",
                       "sources_checked": [REFERENCE], "verification_activity": "Verify capability."}
        result = self.derive(facts(), sce=False, gaps=[gap], uncertainties=[uncertainty])
        self.assertEqual(7, result["final"])
        self.assertTrue(result["review_required"])

    def test_nonbinding_material_safety_uncertainty_still_requires_review(self):
        uncertainty = {
            "material": True,
            "safety": True,
            "affected_decision": "protection",
            "reason": "Exposure detail could refine an already high base score.",
            "sources_checked": [REFERENCE],
            "verification_activity": "Verify exposure.",
        }
        result = self.derive(
            facts(), likelihood=8, impact=7, sce=False, uncertainties=[uncertainty],
        )
        self.assertEqual((8, 8), (result["base"], result["final"]))
        self.assertTrue(result["review_required"])
        self.assertIn("P-SAFETY-UNKNOWN", result["review_reason"])
        self.assertIn("P-SAFETY-UNKNOWN", result["rationale"])

    def test_local_safety_disposition_stays_under_global_approval(self):
        uncertainty = {
            "material": True,
            "safety": True,
            "affected_decision": "disposition",
            "reason": "Local integrity disposition is required.",
            "sources_checked": [REFERENCE],
            "verification_activity": "Verify local integrity condition.",
        }
        result = self.derive(
            facts(), likelihood=7, impact=7, sce=False, uncertainties=[uncertainty],
        )
        self.assertEqual(7, result["final"])
        self.assertFalse(result["review_required"])
        self.assertIn("Verify local integrity condition.", result["verification_activities"])

    def test_deterministic_sce_floor_does_not_create_exceptional_review(self):
        result = self.derive(facts(), likelihood=10, impact=10, sce=True)
        self.assertEqual((10, 10), (result["base"], result["final"]))
        self.assertFalse(result["review_required"])
        self.assertIsNone(result["review_reason"])
        self.assertEqual({"P-SCE-HIGH-IMPACT"},
                         {rule["rule_id"] for rule in result["rules"]})


class BoundaryTests(Artifacts, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.inputs = source_files(self.root)
        self.source = FixtureContext(self.inputs)

    def validate(self):
        return validate_context(self.source, self.inputs, "fixture-v1", CUTOFF, 64000)

    def test_bad_quote_feedback_identifies_exact_field_quote_and_complete_native_address(self):
        address = "knowledge:item-" + "a" * 32 + "@sha256-" + "b" * 64 + ":text"
        for field, source, quote in (
            ("likelihood_of_failure", "First line.\nSecond line.", "First line. Second line."),
            ("impact_of_failure", "Only this item's clause.", "A related item's clause."),
        ):
            with self.subTest(field=field):
                proposed = assessment()
                proposed[field]["evidence"] = [{"source_ref": address, "quote": quote}]
                index = {**self.source.bundle["source_index"], address: source}
                with self.assertRaises(TriageError) as caught:
                    validate_assessment(canonical(proposed), self.inputs.data["findings"]["F-8001"], index)
                self.assertEqual("assessment_evidence", caught.exception.code)
                message = str(caught.exception)
                self.assertIn(f"{field}.evidence[0]", message)
                self.assertIn(address, message)
                self.assertIn(repr(quote), message)
                self.assertLessEqual(len(message), 500)

    def test_input_bytes_preserved_and_primary_mapping_rejected(self):
        original = (self.root / "findings.csv").read_bytes()
        self.assertEqual(digest(original), self.inputs.findings_hash)
        data = self.inputs.data
        data["findings"]["F-8001"]["equipment_id"] = "PMP-8999"
        write_csv(self.root / "findings.csv", FINDING_FIELDS, list(data["findings"].values()))
        with self.assertRaises(TriageError) as caught:
            read_inputs(self.root / "findings.csv", self.root / "registry.csv")
        self.assertEqual("input_mapping", caught.exception.code)

    def test_duplicate_csv_identity_and_invalid_date(self):
        rows = list(self.inputs.data["findings"].values())
        write_csv(self.root / "findings.csv", FINDING_FIELDS, rows + rows)
        with self.assertRaises(TriageError):
            read_inputs(self.root / "findings.csv", self.root / "registry.csv")
        rows[0]["reported_date"] = "2025-02-31"
        write_csv(self.root / "findings.csv", FINDING_FIELDS, rows)
        with self.assertRaises(TriageError):
            read_inputs(self.root / "findings.csv", self.root / "registry.csv")

    def test_context_hash_literal_serialization_and_export(self):
        # Literal wire-format example is independent of the serializer under test.
        from triage.inputs import context_body
        tiny = {key: value for key, value in self.source.bundle.items()
                if key not in {"context_hash", "source_manifest"}}
        self.assertEqual(
            '{"assessment_time": "t", "contract_version": "v", "finding_ids": [], "gaps": [], '
            '"knowledge_version": "k", "payload": {}, "purpose": "normal", "source_index": {}}',
            context_body({**tiny, "assessment_time": "t", "contract_version": "v",
                          "finding_ids": [], "gaps": [], "knowledge_version": "k",
                          "payload": {}, "purpose": "normal", "source_index": {}}),
        )
        path = self.root / "export.json"
        path.write_text(canonical({"snapshot": self.source.snapshot, "bundle": self.source.bundle}))
        exported = ExportedContext(path)
        self.assertEqual(self.validate(), validate_context(exported, self.inputs, "fixture-v1", CUTOFF, 64000))

    def test_context_mutations_fail_closed(self):
        def mutate_manifest(bundle):
            bundle["source_manifest"][0]["kind"] = "evaluation_input"
        mutations = (
            lambda b: b["finding_ids"].append("F-8999"),
            lambda b: b.update(contract_version=99),
            lambda b: b.update(knowledge_version="other"),
            lambda b: b.update(assessment_time="2026-01-02T00:00:00Z"),
            lambda b: b["payload"]["findings"]["F-8001"].update(finding_description="Rewritten source"),
            lambda b: b["payload"]["knowledge"].update(leaked="Unapproved source"),
            lambda b: b["source_index"].update(foreign="Not allowed"),
            lambda b: b.update(context_hash="0" * 64),
            lambda b: b.update(gaps=[{"kind": "unknown"}]),
            lambda b: b["source_manifest"][0].update(sha256="0" * 64),
            lambda b: b["source_manifest"][0].update(kind=[]),
            mutate_manifest,
        )
        original = deepcopy(self.source.bundle)
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                self.source.bundle = deepcopy(original)
                mutate(self.source.bundle)
                with self.assertRaises(TriageError):
                    self.validate()

    def test_knowledge_hash_cutoff_and_context_limit(self):
        with self.assertRaises(TriageError):
            validate_context(self.source, self.inputs, "fixture-v1", CUTOFF, 1)
        with self.assertRaises(TriageError):
            validate_context(self.source, self.inputs, "fixture-v1", "2024-01-01T00:00:00Z", 64000)
        self.source.snapshot["content"]["knowledge:fixture"] = "Unreleased edit"
        with self.assertRaises(TriageError):
            self.validate()

    def test_probe_overlay_cannot_be_used_in_normal_generation(self):
        overlay = {"source_id": "knowledge:overlay", "text": "Synthetic isolated policy.",
                   "sha256": digest(b"Synthetic isolated policy."), "input_kind": "evaluation_input"}
        self.source.bundle.update(purpose="isolated_probe")
        self.source.bundle["payload"]["knowledge"][overlay["source_id"]] = overlay["text"]
        self.source.bundle["source_index"][overlay["source_id"]] = overlay["text"]
        self.source.bundle["source_manifest"][0]["kind"] = "evaluation_input"
        self.source.bundle["source_manifest"].append({
            "source_id": overlay["source_id"], "kind": "evaluation_overlay", "sha256": overlay["sha256"],
        })
        self.source.rehash()
        with self.assertRaises(TriageError):
            self.validate()
        validate_context(self.source, self.inputs, "fixture-v1", CUTOFF, 64000,
                         purpose="isolated_probe", overlay_ref=overlay)
        overlay["sha256"] = "0" * 64
        with self.assertRaises(TriageError):
            validate_context(self.source, self.inputs, "fixture-v1", CUTOFF, 64000,
                             purpose="isolated_probe", overlay_ref=overlay)

    def test_free_text_parentheses_are_not_a_guessed_partner_declaration(self):
        self.inputs = source_files(self.root, redundancy="Inspection note (PMP-8999)")
        self.source = FixtureContext(self.inputs)
        self.validate()

    def test_row_order_changes_raw_hash_not_semantic_hash(self):
        first = source_files(self.root, count=2)
        first_bundle = FixtureContext(first)
        rows = list(first.data["findings"].values())
        write_csv(self.root / "findings.csv", FINDING_FIELDS, list(reversed(rows)))
        second = read_inputs(self.root / "findings.csv", self.root / "registry.csv")
        second_bundle = FixtureContext(second)
        self.assertNotEqual(first.findings_hash, second.findings_hash)
        self.assertEqual(first_bundle.bundle["context_hash"], second_bundle.bundle["context_hash"])

    def test_assessment_rejects_nonlocal_quotes_identity_fraction_and_contradiction(self):
        sample = assessment()
        mutations = (
            lambda a: a.update(finding_id="F-8999"),
            lambda a: a.update(extra="LLM cannot add fields"),
            lambda a: a["likelihood_of_failure"].update(score=2.0),
            lambda a: a["likelihood_of_failure"]["evidence"][0].update(quote="Invented quotation"),
            lambda a: a["likelihood_of_failure"]["evidence"][0].update(source_ref="foreign"),
            lambda a: a["facts"]["required_function_failed"].update(state="confirmed_true",
                evidence=[{"source_ref": REFERENCE, "quote": QUOTE}]),
            lambda a: a["facts"]["recorded_deviation"].update(state="confirmed_false"),
            lambda a: a.update(summary=" " * 2),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                value = deepcopy(sample)
                mutate(value)
                with self.assertRaises(TriageError):
                    validate_assessment(canonical(value), self.inputs.data["findings"]["F-8001"],
                                        self.source.bundle["source_index"])
        for raw in ('{"status": "a", "status": "b"}', '{"x":NaN}', "```json\n{}\n```"):
            with self.assertRaises(TriageError):
                validate_assessment(raw, self.inputs.data["findings"]["F-8001"],
                                    self.source.bundle["source_index"])


class WorkflowTests(Artifacts, unittest.TestCase):
    def test_overflow_repair_that_drops_fixed_activity_fails_without_publication(self):
        first = assessment()
        first["recommended_action"] = "Inspect and correct. " + "x" * 220
        first["facts"]["unlogged_impairment_discovered"].update(
            state="confirmed_true",
            evidence=[{"source_ref": REFERENCE, "quote": QUOTE}],
        )
        first["facts"]["protection_restored"]["verification_activity"] = (
            "Verify restored protection."
        )
        repaired = assessment()
        repaired["recommended_action"] = "Inspect and correct."
        provider = FakeProvider([first, repaired])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("policy_verification", caught.exception.code)
        retry = strict_json(provider.requests[1].user)
        self.assertEqual(
            [
                CONTROL_ALIGNMENT_ACTIVITY,
                IMPAIRMENT_RECORD_ACTIVITY,
                RESTORATION_CLOSURE_ACTIVITY,
            ],
            retry["fixed_appended_verification_activities"],
        )
        self.assertFalse(self.output.exists())
        self.assertEqual(
            "failed",
            strict_json((self.evidence / "run.json").read_text())["run_status"],
        )

    def test_locally_rejected_visible_draft_is_retained_and_sent_as_untrusted_retry_data(self):
        rejected = '{"status":"assessed","incomplete":true}'
        provider = FakeProvider([
            InferenceError("schema_violation", "Local schema rejected visible draft.",
                           receipt(), response_text=rejected), assessment(),
        ])
        self.run_one(provider)
        retry = strict_json(provider.requests[1].user)
        self.assertEqual(rejected, retry["previous_assessment"])
        record = strict_json((self.root / "run" / "run.json").read_text())
        self.assertEqual(rejected, record["attempts"][0]["response"])
        self.assertEqual("failed", record["attempts"][0]["status"])

    def test_explicit_pacing_applies_between_findings_without_spending_another_attempt(self):
        self.inputs = source_files(self.root, count=2)
        self.source = FixtureContext(self.inputs)
        provider = FakeProvider([assessment(), assessment("F-8002")])
        with patch("triage.workflow.time") as clock, patch(
                "triage.workflow.asyncio.sleep", new_callable=AsyncMock) as sleep:
            clock.monotonic.return_value = 100
            self.run_one(provider, config=self.config(minimum_request_interval_seconds=30))
        sleep.assert_awaited_once_with(30)
        self.assertEqual(2, len(provider.requests))

    def test_invalid_pacing_is_rejected(self):
        for value in (True, -1, float("inf"), float("nan"), 301):
            with self.subTest(value=value), self.assertRaises(TriageError):
                self.config(minimum_request_interval_seconds=value).validate()
        for value in (True, 0, -1, 8192.0, 32769):
            with self.subTest(cap=value), self.assertRaises(TriageError):
                self.config(azure_max_completion_tokens=value).validate()
        for value in (None, "auto", True, {}):
            with self.subTest(api=value), self.assertRaises(TriageError):
                self.config(azure_api=value).validate()

    def test_azure_api_mismatch_fails_before_dispatch(self):
        settings = {**receipt(), "provider": "azure-openai", "api": "azure-openai-v1-chat-completions",
                    "max_completion_tokens": 4096}
        provider = FakeProvider(configuration=settings)
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, config=self.config(azure_api="responses"))
        self.assertEqual("provider_capabilities", caught.exception.code)
        self.assertFalse(provider.requests)
        self.assertFalse(self.output.exists())

    def test_azure_receipts_must_match_configured_api_and_actual_messages(self):
        settings = {**receipt(), "provider": "azure-openai", "api": "azure-openai-v1-responses",
                    "max_completion_tokens": 4096}
        for field, wrong in (("api", "azure-openai-v1-chat-completions"), ("user_sha256", "0" * 64)):
            def response(request):
                system, user, _ = request.prepared()
                observed = {**settings, "requested_model": request.model, "wire_message_hashes_match": True,
                            "system_sha256": digest(system.encode()), "user_sha256": digest(user.encode()),
                            field: wrong}
                return InferenceResponse(canonical(assessment()), None, observed)
            provider = FakeProvider([response], configuration=settings)
            with self.subTest(field=field), self.assertRaises(TriageError) as caught:
                self.run_one(provider, config=self.config(azure_api="responses"),
                             evidence=self.root / f"azure-{field}")
            self.assertEqual("unverified_provider_call", caught.exception.code)
            self.assertEqual(1, len(provider.requests))
            self.assertFalse(self.output.exists())

    def setUp(self):
        super().setUp()
        self.inputs = source_files(self.root)
        self.source = FixtureContext(self.inputs)
        self.output = self.root / "tickets.json"
        self.evidence = self.root / "run"

    def run_one(self, provider, *, config=None, evidence=None):
        return asyncio.run(run_workflow(self.inputs, self.source, lambda: provider,
                                       config or self.config(), self.output, evidence or self.evidence))

    def test_complete_batch_publication_and_contract(self):
        self.inputs = source_files(self.root, count=2)
        self.source = FixtureContext(self.inputs)
        provider = FakeProvider([assessment(), assessment("F-8002")])
        result = self.run_one(provider)
        payload = strict_json(self.output.read_text())
        validate_output(payload, self.inputs.data["findings"])
        self.assertEqual(2, payload["tickets_generated"])
        self.assertEqual(digest(self.output.read_bytes()), result["output_sha256"])
        self.assertEqual("not_reviewed", result["semantic_status"])
        self.assertEqual(1, self.source.read_calls)
        record = strict_json((self.evidence / "run.json").read_text())
        self.assertEqual("published", record["run_status"])
        self.assertTrue(record["published_output"])
        publication = strict_json((self.evidence / "publication.json").read_text())
        self.assertEqual("triage-publication-receipt-v1", publication["contract"])
        self.assertEqual(result["output_sha256"], publication["output_sha256"])
        self.assertTrue(publication["verified_after_replace"])
        self.assertEqual(2, len(record["attempts"]))
        self.assertFalse(list(self.root.glob(".triage-*.tmp")))

    def test_one_recovery_and_same_pinned_context(self):
        def edit_after_preflight(request):
            self.source.snapshot["content"]["knowledge:fixture"] = "Edited after snapshot"
            self.source.bundle["payload"]["knowledge"]["knowledge:fixture"] = "Edited after snapshot"
            return "{malformed"
        provider = FakeProvider([edit_after_preflight, assessment()])
        self.run_one(provider)
        contexts = [strict_json(request.user)["context"] for request in provider.requests]
        self.assertEqual(contexts[0], contexts[1])
        self.assertEqual("malformed_json", strict_json(provider.requests[1].user)["validation_error"])
        record = strict_json((self.evidence / "run.json").read_text())
        self.assertEqual(["failed", "validated"], [x["status"] for x in record["attempts"]])

    def test_structural_recovery_is_distinct_from_malformed_json(self):
        provider = FakeProvider([{}, assessment()])
        self.run_one(provider)
        record = strict_json((self.evidence / "run.json").read_text())
        self.assertEqual("assessment_schema", record["attempts"][0]["error_class"])
        self.assertEqual(["failed", "validated"], [x["status"] for x in record["attempts"]])
        payload = strict_json(self.output.read_text())
        validate_output(payload, self.inputs.data["findings"])
        self.assertEqual(1, payload["tickets_generated"])
        self.assertEqual(2, len(provider.requests))

    def test_permanent_failure_preserves_previous_bytes_and_all_attempts(self):
        old = b"old output\r\n"
        self.output.write_bytes(old)
        provider = FakeProvider(["bad", "bad"])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual(2, caught.exception.attempts)
        self.assertEqual("F-8001", caught.exception.finding_id)
        self.assertEqual(old, self.output.read_bytes())
        record = strict_json((self.evidence / "run.json").read_text())
        self.assertEqual(2, len(record["attempts"]))
        self.assertEqual(record["previous_output_sha256"], record["output_after_failure_sha256"])
        self.assertEqual(False, caught.exception.diagnostic()["published_output"])

    def test_batch_not_partially_published(self):
        self.inputs = source_files(self.root, count=2)
        self.source = FixtureContext(self.inputs)
        provider = FakeProvider([assessment(), "bad", "bad"])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("F-8002", caught.exception.finding_id)
        self.assertFalse(self.output.exists())
        self.assertEqual(3, len(provider.requests))

    def test_provider_error_recovery_requires_dispatch_accounting(self):
        provider = FakeProvider([InferenceError("malformed_json", "Synthetic", receipt()), assessment()])
        self.run_one(provider)
        self.assertEqual(2, len(provider.requests))
        provider = FakeProvider([InferenceError("malformed_json", "Unknown internal retries", {})])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, evidence=self.root / "unknown-accounting")
        self.assertEqual("unverified_attempts", caught.exception.code)
        self.assertEqual(1, len(provider.requests))

    def test_unassessable_fails_without_forced_scores(self):
        value = assessment()
        value.update(status="unassessable", inability_reason="Insufficient input to support scores.",
                     summary=None, recommended_action=None, likelihood_of_failure=None,
                     impact_of_failure=None, facts=None)
        provider = FakeProvider([value])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("unassessable", caught.exception.code)
        self.assertEqual(1, len(provider.requests))
        self.assertFalse(self.output.exists())

    def test_fatal_transport_timeout_refusal_and_cleanup_do_not_publish(self):
        for code in ("transport", "timeout", "refusal", "authentication"):
            with self.subTest(code=code):
                provider = FakeProvider([InferenceError(code, "Synthetic failure", receipt())])
                with self.assertRaises(TriageError):
                    self.run_one(provider, evidence=self.root / code)
                self.assertEqual(1, len(provider.requests))
                self.assertFalse(self.output.exists())
        self.output.write_bytes(b"old")
        with self.assertRaises(TriageError) as caught:
            self.run_one(FakeProvider(close_error=True), evidence=self.root / "cleanup")
        self.assertEqual("cleanup", caught.exception.code)
        self.assertEqual(b"old", self.output.read_bytes())

    def test_invalid_provider_capability_and_receipt_fail_closed(self):
        configuration = receipt()
        configuration["http_transport_retries"] = "caller_supplied"
        provider = FakeProvider(configuration=configuration)
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("provider_capabilities", caught.exception.code)
        self.assertFalse(provider.requests)
        invalid_receipt = receipt()
        invalid_receipt["http_dispatches_observed"] = 2
        provider = FakeProvider([InferenceResponse(canonical(assessment()), None, invalid_receipt)])
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, evidence=self.root / "bad-receipt")
        self.assertEqual("unverified_attempts", caught.exception.code)
        self.assertFalse(self.output.exists())

    def test_malformed_provider_object_and_receiptless_fatal_error(self):
        provider = FakeProvider()
        async def broken_response(request):
            provider.requests.append(request)
            return object()
        provider.generate = broken_response
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("provider_contract", caught.exception.code)
        self.assertFalse(self.output.exists())
        with self.assertRaises(TriageError) as caught:
            self.run_one(FakeProvider([InferenceError("authentication", "Synthetic", {})]),
                         evidence=self.root / "no-receipt")
        self.assertEqual("authentication", caught.exception.code)

    def test_actual_timeout_is_terminal_with_reserved_attempt(self):
        provider = FakeProvider()
        async def delayed(request):
            provider.requests.append(request)
            await asyncio.sleep(10)
        provider.generate = delayed
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider, config=self.config(timeout_seconds=0.01))
        self.assertEqual("timeout", caught.exception.code)
        self.assertEqual(1, caught.exception.attempts)
        self.assertFalse(self.output.exists())

    def test_persistent_budget_cannot_reset_by_starting_another_run(self):
        provider = FakeProvider(["bad", "bad"])
        with self.assertRaises(TriageError):
            self.run_one(provider, config=self.config(budget=1))
        self.assertEqual(1, len(provider.requests))
        another = FakeProvider()
        with self.assertRaises(TriageError) as caught:
            self.run_one(another, config=self.config(budget=1), evidence=self.root / "second")
        self.assertEqual("attempt_budget", caught.exception.code)
        self.assertEqual(0, caught.exception.attempts)
        self.assertFalse(another.requests)
        self.assertEqual(1, len(strict_json((self.root / "phase-ledger.json").read_text())["reservations"]))

    def test_missing_partner_cannot_be_suppressed_by_model(self):
        self.inputs = source_files(self.root, sce=True, redundancy="N+1 (PMP-8999)")
        gap = {"kind": "tagged_partner_not_in_registry", "subject_equipment_id": "PMP-8001",
               "partner_equipment_id": "PMP-8999", "finding_ids": ["F-8001"],
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        self.source = FixtureContext(self.inputs, gaps=[gap])
        value = assessment()
        value["recommended_action"] = gap_verification_activity(gap)
        self.run_one(FakeProvider([value]))
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual(7, ticket["urgency"]["score"])
        self.assertTrue(ticket["review_required"])
        self.assertEqual(2, ticket["likelihood_of_failure"]["score"])

    def test_missing_partner_gap_omission_blocks_before_dispatch(self):
        self.inputs = source_files(self.root, redundancy="Duplicated (PMP-8999)")
        self.source = FixtureContext(self.inputs)
        provider = FakeProvider()
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("context_gap", caught.exception.code)
        self.assertFalse(provider.requests)

    def test_code_known_gap_action_overflow_recovers_without_omitting_the_gap(self):
        self.inputs = source_files(self.root, sce=True, redundancy="N+1 (PMP-8999)")
        gap = {"kind": "tagged_partner_not_in_registry", "subject_equipment_id": "PMP-8001",
               "partner_equipment_id": "PMP-8999", "finding_ids": ["F-8001"],
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        self.source = FixtureContext(self.inputs, gaps=[gap])
        value = assessment()
        value["recommended_action"] = "Inspect the surface. " + "x" * 270
        repaired = deepcopy(value)
        repaired["recommended_action"] = "Inspect the surface."
        provider = FakeProvider([value, repaired])
        self.run_one(provider)
        self.assertEqual(2, len(provider.requests))
        action = strict_json(self.output.read_text())["tickets"][0]["recommended_action"]
        self.assertEqual(
            "Inspect the surface. Verify PMP-8999 availability/capability.",
            action,
        )

    def test_required_verification_is_composed_without_a_model_copying_retry(self):
        value = assessment()
        value["uncertainties"] = [{
            "material": True, "safety": True, "affected_decision": "redundancy",
            "reason": "Capability not verified.", "verification_activity": "Verify partner capability.",
            "evidence": [], "sources_checked": [REFERENCE],
        }]
        provider = FakeProvider([value])
        self.run_one(provider)
        self.assertEqual(1, len(provider.requests))
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual(7, ticket["urgency"]["score"])
        self.assertEqual(value["recommended_action"] + " Verify partner capability.", ticket["recommended_action"])
        report = strict_json((self.root / "run" / "run.json").read_text())
        self.assertEqual(["Verify partner capability."],
                         report["attempts"][0]["action_composition"]["appended_activities"])

    def test_unlogged_impairment_appends_ordered_code_owned_restoration_sequence(self):
        value = assessment()
        value["recommended_action"] = (
            "Investigate unauthorized isolation and correct defects under fire-protection authority."
        )
        evidence = [{"source_ref": REFERENCE, "quote": QUOTE}]
        value["facts"]["protection_impaired"].update(state="confirmed_true", evidence=evidence)
        value["facts"]["recorded_deviation"].update(state="confirmed_false", evidence=evidence)
        value["facts"]["unlogged_impairment_discovered"].update(
            state="confirmed_true", evidence=evidence)
        value["facts"]["protection_restored"].update(
            state="unknown",
            verification_activity=RESTORATION_CLOSURE_ACTIVITY,
        )
        provider = FakeProvider([value])
        self.run_one(provider)
        request = strict_json(provider.requests[0].user)
        for activity in (
            CONTROL_ALIGNMENT_ACTIVITY,
            IMPAIRMENT_RECORD_ACTIVITY,
            RESTORATION_CLOSURE_ACTIVITY,
        ):
            self.assertIn(activity, request["possible_policy_activities"])
        action = strict_json(self.output.read_text())["tickets"][0]["recommended_action"]
        positions = [
            action.index(CONTROL_ALIGNMENT_ACTIVITY),
            action.index(IMPAIRMENT_RECORD_ACTIVITY),
            action.index(RESTORATION_CLOSURE_ACTIVITY),
        ]
        self.assertEqual(sorted(positions), positions)
        self.assertLessEqual(len(action), 300)

    def test_unlogged_impairment_overflow_repairs_without_dropping_restoration_sequence(self):
        evidence = [{"source_ref": REFERENCE, "quote": QUOTE}]
        first = assessment()
        first["recommended_action"] = (
            "Investigate the unauthorized protection isolation, inspect all affected components, "
            "correct defects under fire-protection authority, and document the authorized disposition."
        )
        first["facts"]["protection_impaired"].update(state="confirmed_true", evidence=evidence)
        first["facts"]["recorded_deviation"].update(state="confirmed_false", evidence=evidence)
        first["facts"]["unlogged_impairment_discovered"].update(
            state="confirmed_true", evidence=evidence)
        first["facts"]["protection_restored"].update(
            state="unknown",
            verification_activity=RESTORATION_CLOSURE_ACTIVITY,
        )
        checks = (
            "Inspect north-quadrant nozzles.",
            "Trace isolation duration and authority.",
        )
        first["uncertainties"] = [{
            "material": True,
            "safety": True,
            "affected_decision": decision,
            "reason": f"Restoration check {number}.",
            "verification_activity": activity,
            "evidence": [],
            "sources_checked": [REFERENCE],
        } for number, (decision, activity) in enumerate(
            zip(("protection", "disposition"), checks), start=1)]
        repaired = deepcopy(first)
        repaired["recommended_action"] = "Correct the unauthorized isolation under fire-protection authority."
        provider = FakeProvider([first, repaired])
        self.run_one(provider)
        self.assertEqual(2, len(provider.requests))
        retry = strict_json(provider.requests[1].user)
        self.assertEqual([
            CONTROL_ALIGNMENT_ACTIVITY,
            IMPAIRMENT_RECORD_ACTIVITY,
            RESTORATION_CLOSURE_ACTIVITY,
        ], retry["fixed_appended_verification_activities"])
        action = strict_json(self.output.read_text())["tickets"][0]["recommended_action"]
        for activity in (*checks, CONTROL_ALIGNMENT_ACTIVITY, IMPAIRMENT_RECORD_ACTIVITY,
                         RESTORATION_CLOSURE_ACTIVITY):
            self.assertIn(activity, action)
        self.assertLessEqual(len(action), 300)

    def test_whitespace_variant_activities_publish_without_false_missing_failure(self):
        value = assessment()
        value["uncertainties"] = [{
            "material": True, "safety": True, "affected_decision": "disposition",
            "reason": f"Distinct check {number}.", "verification_activity": activity,
            "evidence": [], "sources_checked": [REFERENCE],
        } for number, activity in enumerate(
            ("Inspect release gear.", "Inspect  release gear."), start=1)]
        provider = FakeProvider([value])
        self.run_one(provider)
        self.assertEqual(1, len(provider.requests))
        action = strict_json(self.output.read_text())["tickets"][0]["recommended_action"]
        self.assertIn("Inspect release gear.", action)
        self.assertIn("Inspect  release gear.", action)

    def test_composed_action_overflow_recovers_by_shortening_core_not_dropping_steps(self):
        value = assessment()
        value["recommended_action"] = "Inspect the surface. " + "x" * 270
        value["uncertainties"] = [{
            "material": True, "safety": True, "affected_decision": "redundancy",
            "reason": "Capability not verified.", "verification_activity": "Verify partner capability.",
            "evidence": [], "sources_checked": [REFERENCE],
        }]
        corrected = deepcopy(value)
        corrected["recommended_action"] = "Inspect the surface."
        provider = FakeProvider([value, corrected])
        self.run_one(provider)
        self.assertEqual(2, len(provider.requests))
        feedback = strict_json(provider.requests[1].user)["validation_message"]
        self.assertIn("Retry target <= 280", feedback)
        self.assertIn("uniform model-check cap", feedback)
        self.assertIn("Shorten each model check", feedback)
        self.assertLessEqual(len(feedback), 500)
        retry = strict_json(provider.requests[1].user)
        self.assertEqual(["Verify partner capability."],
                         retry["model_appended_verification_activities"])
        self.assertEqual([], retry["fixed_appended_verification_activities"])
        self.assertEqual(20, retry["retry_action_budget"]["safety_margin_chars"])
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual("Inspect the surface. Verify partner capability.", ticket["recommended_action"])

    def test_f1002_like_fixed_and_multi_check_overflow_repairs_with_exact_budget(self):
        self.inputs = source_files(self.root, sce=True, redundancy="N+1 (PSV-1311)")
        gap = {"kind": "tagged_partner_not_in_registry", "subject_equipment_id": "PMP-8001",
               "partner_equipment_id": "PSV-1311", "finding_ids": ["F-8001"],
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        self.source = FixtureContext(self.inputs, gaps=[gap])
        first = assessment()
        checks = (
            "Verify relief capacity and set-pressure operation.",
            "Check approved impairment and deviation records.",
            "Confirm personnel exposure and overpressure scenario.",
        )
        first["recommended_action"] = "Authorized inspector assess passing PSV and correct defect. " + "x" * 150
        first["uncertainties"] = [{
            "material": True, "safety": True, "affected_decision": decision,
            "reason": f"Required check {number}.", "verification_activity": activity,
            "evidence": [], "sources_checked": [REFERENCE],
        } for number, (decision, activity) in enumerate(zip(
            ("protection", "disposition", "impact"), checks), start=1)]
        repaired = deepcopy(first)
        repaired["recommended_action"] = "Inspect and correct the passing PSV."
        repaired_checks = ("Verify relief capacity.", "Check deviation record.", "Confirm exposure.")
        for uncertainty, activity in zip(repaired["uncertainties"], repaired_checks):
            uncertainty["verification_activity"] = activity
        provider = FakeProvider([first, repaired])
        self.run_one(provider)
        retry = strict_json(provider.requests[1].user)
        fixed = gap_verification_activity({
            "kind": "tagged_partner_not_in_registry",
            "partner_equipment_id": "PSV-1311",
            "source_refs": ["equipment:PSV-1310:redundancy"],
        })
        self.assertEqual([fixed], retry["fixed_appended_verification_activities"])
        self.assertEqual(list(checks), retry["model_appended_verification_activities"])
        budget = retry["retry_action_budget"]
        self.assertEqual(3, budget["model_check_count"])
        self.assertGreaterEqual(budget["core_max_chars"], len(first["recommended_action"]) / 2)
        self.assertEqual(
            280,
            budget["fixed_appended_chars_with_separators"]
            + budget["model_separator_chars"] + budget["core_max_chars"]
            + budget["model_check_count"] * budget["model_check_max_chars"],
        )
        action = strict_json(self.output.read_text())["tickets"][0]["recommended_action"]
        self.assertIn(fixed, action)
        for activity in repaired_checks:
            self.assertIn(activity, action)
        self.assertLessEqual(len(action), 280)

    def test_f1012_like_repair_with_rebalanced_fields_is_not_falsely_rejected(self):
        first = assessment()
        first["recommended_action"] = (
            "Marine and class specialists overhaul release gear, correct defects, and document acceptance. "
            + "x" * 80
        )
        first_checks = (
            "Inspect and test release gear through full travel under the specified proof load, then document results.",
            "Verify class recertification and craft readiness after correction before return to service.",
        )
        first["uncertainties"] = [{
            "material": True, "safety": True, "affected_decision": decision,
            "reason": f"Release-gear check {number}.", "verification_activity": activity,
            "evidence": [], "sources_checked": [REFERENCE],
        } for number, (decision, activity) in enumerate(
            zip(("protection", "disposition"), first_checks), start=1)]
        repaired = deepcopy(first)
        repaired["recommended_action"] = (
            "Marine/class overhaul release gear and correct the defective mechanism before return."
        )
        repaired_checks = (
            "Inspect and proof-load the full release path; record force, travel, smooth operation and acceptance.",
            "Verify class sign-off.",
        )
        for uncertainty, activity in zip(repaired["uncertainties"], repaired_checks):
            uncertainty["verification_activity"] = activity
        provider = FakeProvider([first, repaired])
        self.run_one(provider)
        retry = strict_json(provider.requests[1].user)
        cap = retry["retry_action_budget"]["model_check_max_chars"]
        self.assertGreater(len(repaired_checks[0]), cap)
        action = strict_json(self.output.read_text())["tickets"][0]["recommended_action"]
        self.assertLessEqual(len(action), 280)
        for activity in repaired_checks:
            self.assertIn(activity, action)

    def test_impossible_fixed_gap_fails_before_paid_dispatch(self):
        partner = "X" * 290 + "-8999"
        self.inputs = source_files(self.root, redundancy=f"N+1 ({partner})")
        self.source = FixtureContext(self.inputs, gaps=[{
            "kind": "tagged_partner_not_in_registry",
            "subject_equipment_id": "PMP-8001",
            "partner_equipment_id": partner,
            "finding_ids": ["F-8001"],
            "source_refs": ["equipment:PMP-8001:redundancy"],
        }])
        provider = FakeProvider()
        with self.assertRaises(TriageError) as caught:
            self.run_one(provider)
        self.assertEqual("policy_verification_impossible", caught.exception.code)
        self.assertEqual(0, caught.exception.attempts)
        self.assertFalse(provider.requests)
        self.assertFalse(self.output.exists())

    def test_nonapplicable_dependent_contradiction_can_recover_but_not_suppress_floor(self):
        value = assessment()
        value["facts"]["protection_impaired"].update(
            state="confirmed_true", evidence=[{"source_ref": REFERENCE, "quote": QUOTE}])
        value["facts"]["recorded_deviation"].update(
            applicability="not_applicable", evidence=[{"source_ref": REFERENCE, "quote": QUOTE}])
        repaired = deepcopy(value)
        repaired["facts"]["recorded_deviation"].update(
            applicability="applicable", verification_activity="Check deviation log.")
        repaired["recommended_action"] = "Check deviation log."
        provider = FakeProvider([value, repaired])
        self.run_one(provider)
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual(2, len(provider.requests))
        self.assertEqual(7, ticket["urgency"]["score"])
        self.assertFalse(ticket["review_required"])
        self.assertIn("Reconcile impairment/deviation record", ticket["recommended_action"])

    def test_verification_overflow_fails_visibly_without_truncating_or_publishing(self):
        value = assessment()
        value["uncertainties"] = [{
            "material": True, "safety": True, "affected_decision": "redundancy",
            "reason": "Synthetic long distinct verification requirements.",
            "verification_activity": f"Verify synthetic condition {suffix}: " + suffix * 140,
            "evidence": [], "sources_checked": [REFERENCE],
        } for suffix in ("A", "B")]
        value["recommended_action"] = value["uncertainties"][0]["verification_activity"]
        self.output.write_bytes(b"old")
        with self.assertRaises(TriageError) as caught:
            self.run_one(FakeProvider([value, value]))
        self.assertEqual("policy_verification", caught.exception.code)
        self.assertEqual(2, caught.exception.attempts)
        self.assertEqual(b"old", self.output.read_bytes())

    def test_atomic_replace_failure_preserves_old_output_and_cleans_temp(self):
        self.output.write_bytes(b"old")
        import triage.workflow as module
        actual = module.os.replace

        def replace_except_output(source, target):
            if Path(target) == self.output:
                raise PermissionError("Synthetic publication failure")
            return actual(source, target)

        with patch("triage.workflow.os.replace", side_effect=replace_except_output):
            with self.assertRaises(TriageError):
                self.run_one(FakeProvider())
        self.assertEqual(b"old", self.output.read_bytes())
        self.assertFalse(list(self.root.glob(".triage-*.tmp")))

    def test_receipt_failure_rolls_back_published_output(self):
        import triage.workflow as module
        actual = module.save_json_atomic
        self.output.write_bytes(b"old")

        def fail_publication_receipt(path, value):
            if Path(path).name == "publication.json":
                raise PermissionError("Synthetic receipt failure")
            return actual(path, value)

        with patch("triage.workflow.save_json_atomic", side_effect=fail_publication_receipt):
            with self.assertRaises(TriageError) as caught:
                self.run_one(FakeProvider())
        self.assertEqual(b"old", self.output.read_bytes())
        self.assertFalse(caught.exception.diagnostic()["published_output"])
        record = strict_json((self.evidence / "run.json").read_text())
        self.assertTrue(record["publication_rolled_back"])
        self.assertFalse(record["diagnostic"]["published_output"])

    def test_final_report_failure_rolls_back_output_and_receipt(self):
        import triage.workflow as module
        actual = module.save_json
        failed = False
        self.output.write_bytes(b"old")

        def fail_published_report_once(path, value):
            nonlocal failed
            if value.get("run_status") == "published" and not failed:
                failed = True
                raise PermissionError("Synthetic final report failure")
            return actual(path, value)

        with patch("triage.workflow.save_json", side_effect=fail_published_report_once):
            with self.assertRaises(TriageError) as caught:
                self.run_one(FakeProvider())
        self.assertEqual(b"old", self.output.read_bytes())
        self.assertFalse(caught.exception.diagnostic()["published_output"])
        self.assertFalse((self.evidence / "publication.json").exists())
        record = strict_json((self.evidence / "run.json").read_text())
        self.assertEqual("failed", record["run_status"])
        self.assertTrue(record["publication_rolled_back"])
        self.assertFalse(record["published_output"])
        self.assertNotIn("output_sha256", record)
        self.assertNotIn("publication_receipt", record)

    def test_old_evidence_is_not_reused(self):
        self.evidence.mkdir()
        marker = self.evidence / "keep.txt"
        marker.write_text("unchanged")
        provider = FakeProvider()
        with self.assertRaises(TriageError):
            self.run_one(provider)
        self.assertEqual("unchanged", marker.read_text())
        self.assertFalse(provider.requests)

    def test_final_contract_rejects_mutated_coverage_schema_and_types(self):
        self.run_one(FakeProvider())
        original = strict_json(self.output.read_text())
        mutations = (
            lambda p: p.update(tickets_generated=True),
            lambda p: p["tickets"].append(deepcopy(p["tickets"][0])),
            lambda p: p["tickets"][0].update(ticket_id="TKT-8999"),
            lambda p: p["tickets"][0].update(equipment_id="PMP-8999"),
            lambda p: p["tickets"][0].update(summary="x" * 301),
            lambda p: p["tickets"][0].update(review_required="false"),
            lambda p: p["tickets"][0]["urgency"].update(score=3.0),
            lambda p: p.update(extra=1),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                value = deepcopy(original)
                mutate(value)
                with self.assertRaises(TriageError):
                    validate_output(value, self.inputs.data["findings"])

    def test_cli_json_diagnostic_no_authorized_inference(self):
        command = [sys.executable, "-B", "-m", "triage", "--findings", str(self.root / "findings.csv"),
                   "--registry", str(self.root / "registry.csv"), "--context-export", str(self.root / "context.json"),
                   "--config", str(self.root / "config.json"), "--output", str(self.output),
                   "--evidence", str(self.evidence)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(1, result.returncode)
        diagnostic = json.loads(result.stderr)
        self.assertEqual("inference_not_authorized", diagnostic["error_class"])
        self.assertIsNone(diagnostic["finding_id"])
        self.assertEqual(0, diagnostic["attempts"])
        self.assertFalse(self.output.exists())
        missing = subprocess.run([sys.executable, "-B", "-m", "triage"], capture_output=True,
                                 text=True, check=False)
        self.assertEqual("configuration", json.loads(missing.stderr)["error_class"])

    def test_external_export_raw_hash_is_recorded_not_authenticated(self):
        path = self.root / "context.json"
        path.write_text(canonical(self.source.read_export()), encoding="utf-8")
        self.source = ExportedContext(path)
        self.run_one(FakeProvider())
        report = strict_json((self.evidence / "run.json").read_text())
        self.assertEqual(digest(path.read_bytes()), report["context_export_sha256"])
        self.assertEqual("producer_claim_not_independently_verified", report["knowledge_approval"])

    def test_cli_permanent_failure_with_absent_and_old_output(self):
        export = self.root / "context.json"
        export.write_text(canonical(self.source.read_export()), encoding="utf-8")
        config = self.root / "config.json"
        config.write_text(json.dumps(asdict(self.config(budget=4))), encoding="utf-8")
        script = (
            "import triage.__main__ as cli; "
            "from tests.triage_support import FakeProvider; "
            "cli.AzureOpenAIProvider=lambda **kwargs: FakeProvider(['bad','bad']); "
            "raise SystemExit(cli.main())"
        )
        for old in (None, b"old successful output\r\n"):
            with self.subTest(previous_output=old is not None):
                if old is not None:
                    self.output.write_bytes(old)
                evidence = self.root / ("cli-old" if old else "cli-absent")
                result = subprocess.run([
                    sys.executable, "-B", "-c", script,
                    "--findings", str(self.root / "findings.csv"),
                    "--registry", str(self.root / "registry.csv"), "--context-export", str(export),
                    "--legacy-replay",
                    "--config", str(config), "--output", str(self.output), "--evidence", str(evidence),
                    "--allow-inference",
                ], capture_output=True, text=True, check=False)
                self.assertEqual(1, result.returncode)
                diagnostic = strict_json(result.stderr)
                self.assertEqual("failed", diagnostic["run_status"])
                self.assertEqual("F-8001", diagnostic["finding_id"])
                self.assertEqual("malformed_json", diagnostic["error_class"])
                self.assertEqual(2, diagnostic["attempts"])
                self.assertFalse(diagnostic["published_output"])
                self.assertEqual("", result.stdout)
                report = strict_json((evidence / "run.json").read_text())
                self.assertEqual(2, len(report["attempts"]))
                self.assertEqual(report["previous_output_sha256"], report["output_after_failure_sha256"])
                if old is None:
                    self.assertFalse(self.output.exists())
                else:
                    self.assertEqual(old, self.output.read_bytes())
                (evidence / "stderr.json").write_text(result.stderr, encoding="utf-8")
                (evidence / "process.json").write_text(json.dumps({"exit_code": result.returncode,
                                                                  "provider": "synthetic-no-network"}))

if __name__ == "__main__":
    unittest.main()
