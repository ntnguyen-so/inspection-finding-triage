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
    SCHEMA, citation_catalog, project_native_assessment, request_schema, validate_assessment,
    validate_same_day_attention,
)
from triage.contracts import TriageError, digest
from triage.inputs import ExportedContext, FINDING_FIELDS, read_inputs, validate_context
from triage.policy import (
    CAPACITY_COMPARISON_ACTIVITY, SAME_DAY_ATTENTION_ACTIVITY, base_urgency, derive_policy,
)
from triage.workflow import compose_action, run_workflow, validate_output
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
            self.assertEqual(valid, validator.is_valid(changed))
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


class ActionCompositionTests(unittest.TestCase):
    def test_overflow_feedback_budgets_all_checks_not_only_core(self):
        from triage.workflow import action_overflow_message
        composition = compose_action("A" * 46, [f"{number} " + "B" * 42 for number in range(8)])
        original = deepcopy(composition)
        message = action_overflow_message(composition)
        self.assertIn("8 appended checks", message)
        self.assertIn("30 characters per check", message)
        self.assertIn("not just the core", message)
        self.assertIn("Preserve all required steps", message)
        self.assertEqual(original, composition)
        self.assertLessEqual(len(message), 500)

    def test_exact_activities_are_composed_without_rewriting_core_or_duplicate_spans(self):
        core = "Repair the seal; Verify capability."
        result = compose_action(core, ["Verify capability.", "Record the test.", "Record the test."])
        self.assertEqual(core, result["model_core"])
        self.assertEqual(["Record the test."], result["appended_activities"])
        self.assertEqual(core + " Record the test.", result["composed"])
        self.assertEqual("Inspect.", compose_action("Inspect.", [])["composed"])

    def test_paraphrases_do_not_suppress_exact_obligations(self):
        result = compose_action("Verify capability; record the test.", ["Verify capability.", "Record the test."])
        self.assertEqual("Verify capability; record the test. Verify capability. Record the test.",
                         result["composed"])


class PolicyTests(unittest.TestCase):
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
                    values["recorded_deviation"].update(state=deviation,
                                                       verification_activity="Check deviation log.")
                    result = self.derive(values)
                    ids = [r["rule_id"] for r in result["rules"]]
                    self.assertEqual("O-PROTECTION" in ids,
                                     impaired == "confirmed_true" and deviation == "confirmed_false")
                    expected = 9 if impaired == "confirmed_true" and deviation == "confirmed_false" else (
                        7 if impaired == "confirmed_true" and deviation in {"unknown", "suspected"} else 1)
                    self.assertEqual(expected, result["final"])

    def test_precautions_capacity_and_restoration(self):
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
            self.assertEqual(1 if restored == "confirmed_true" else 9, self.derive(values)["final"])

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
                    self.assertIn(CAPACITY_COMPARISON_ACTIVITY, result["verification_activities"])
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
        self.assertTrue(result["review_required"])
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
        self.assertEqual({"O-PROTECTION", "O-EVACUATION", "P-FAILED-TEST", "R-SCE"},
                         {x["rule_id"] for x in result["rules"]})
        self.assertEqual(before, values)

    def test_materiality_applicability_and_missing_partner(self):
        self.assertFalse(self.derive(facts())["review_required"])
        self.assertEqual(1, self.derive(facts(), sce=True)["final"])
        for safety in (True, False):
            uncertainty = {"material": True, "safety": safety, "reason": "Unknown state affects decision.",
                           "sources_checked": [REFERENCE], "verification_activity": "Verify state."}
            result = self.derive(facts(), uncertainties=[uncertainty])
            self.assertEqual(7 if safety else 1, result["final"])
            self.assertEqual(["Verify state."], result["verification_activities"])
        gap = {"kind": "tagged_partner_not_in_registry", "partner_equipment_id": "PMP-8999",
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        self.assertEqual(7, self.derive(facts(), sce=True, gaps=[gap])["final"])
        self.assertTrue(self.derive(facts(), gaps=[gap])["review_required"])
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
        values["unlogged_impairment_discovered"]["state"] = "confirmed_true"
        values["protection_restored"]["state"] = "confirmed_false"
        self.assertEqual(9, self.derive(values)["final"])

    def test_non_sce_safety_uncertainty_still_receives_floor(self):
        gap = {"kind": "tagged_partner_not_in_registry", "partner_equipment_id": "PMP-8999",
               "source_refs": ["equipment:PMP-8001:redundancy"]}
        uncertainty = {"material": True, "safety": True, "reason": "Safety consequence on non-SCE.",
                       "sources_checked": [REFERENCE], "verification_activity": "Verify capability."}
        result = self.derive(facts(), sce=False, gaps=[gap], uncertainties=[uncertainty])
        self.assertEqual(7, result["final"])
        self.assertTrue(result["review_required"])


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
        self.assertEqual("ready_to_publish", record["run_status"])
        self.assertFalse(record["published_output"])
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
        value["recommended_action"] = "Verify availability and capability of PMP-8999."
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
        self.assertEqual("Inspect the surface. Verify availability and capability of PMP-8999.", action)

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
        self.assertIn("Shorten core action", strict_json(provider.requests[1].user)["validation_message"])
        ticket = strict_json(self.output.read_text())["tickets"][0]
        self.assertEqual("Inspect the surface. Verify partner capability.", ticket["recommended_action"])

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
        self.assertTrue(ticket["review_required"])

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
