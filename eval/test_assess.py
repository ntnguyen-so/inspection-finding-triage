"""Software-fixture tests of the evaluator, not observations of a triage system."""

import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from assess import assess, calibrate, contract_errors, main, read_json, review_template
from validate import ROOT, profile_sources


class OutputAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / "docs" / "candidate-pack" / "candidate-pack"
        findings, _, _ = profile_sources(source)
        cls.findings = findings
        cls.expected = {"F-1005": findings["F-1005"]}
        cls.probes = read_json(ROOT / "eval" / "probes.json")
        cls.version = cls.probes["reference_version"]
        cls.card = next(
            json.loads(line) for line in
            (ROOT / "eval" / "development.jsonl").read_text(encoding="utf-8").splitlines()
            if json.loads(line)["finding_id"] == "F-1005"
        )
        cls.ticket = json.loads(
            (source / "reference" / "example_ticket.json").read_text(encoding="utf-8")
        )

    def setUp(self):
        self.payload = {
            "generated_at": "2026-06-22T12:00:00+00:00",
            "tickets_generated": 1,
            "tickets": [copy.deepcopy(self.ticket)],
        }
        self.cards = [copy.deepcopy(self.card)]

    def evaluate(self, review=None):
        return assess(
            self.payload, self.expected, self.cards, "development", self.version, "fixture-hash", review,
        )

    def complete_review(self):
        review = review_template(self.cards, "development", self.version, "fixture-hash")
        review["reviewer"] = {"kind": "ai_only", "independent_of_generation": False}
        for item in review["items"]:
            item.update(
                verdict="pass",
                reason="Synthetic reviewer judgment for protocol testing only.",
                evidence=[{"field": "summary", "quote": self.ticket["summary"]}],
            )
        return review

    def test_valid_contract_is_not_a_semantic_pass(self):
        report = self.evaluate()
        self.assertEqual(report["contract"]["status"], "pass")
        self.assertEqual(report["overall"], "needs_review")
        self.assertEqual(len(report["semantic"]["pending"]), 3)
        self.assertEqual(report["review_template"]["output_sha256"], "fixture-hash")

    def test_score_type_bounds_rationale_and_text_mutations_are_rejected(self):
        mutations = (
            (lambda ticket: ticket["urgency"].update(score=True), "integer 1-10"),
            (lambda ticket: ticket["urgency"].update(score=1.5), "integer 1-10"),
            (lambda ticket: ticket["urgency"].update(score=11), "integer 1-10"),
            (lambda ticket: ticket["urgency"].update(score=0), "integer 1-10"),
            (lambda ticket: ticket["urgency"].update(rationale=" "), "rationale"),
            (lambda ticket: ticket.update(summary="x" * 301), "summary"),
            (lambda ticket: ticket.update(recommended_action=""), "recommended_action"),
            (lambda ticket: ticket.update(review_reason=None), "review_reason"),
            (lambda ticket: ticket.update(review_required="true"), "boolean required"),
            (lambda ticket: ticket.update(equipment_id="PSV-1310"), "mapping mismatch"),
            (lambda ticket: ticket.update(ticket_id="TKT-5"), "TKT-####"),
            (lambda ticket: ticket.pop("summary"), "missing/extra"),
            (lambda ticket: ticket.update(hidden_state="not allowed"), "missing/extra"),
        )
        for mutate, message in mutations:
            with self.subTest(message=message):
                payload = copy.deepcopy(self.payload)
                mutate(payload["tickets"][0])
                self.assertTrue(any(message in error for error in contract_errors(payload, self.expected)))

    def test_coverage_duplicates_count_and_wrapper_mutations_are_rejected(self):
        mutations = (
            lambda payload: payload.update(tickets=[]),
            lambda payload: payload["tickets"].append(copy.deepcopy(payload["tickets"][0])),
            lambda payload: payload.update(tickets_generated=True),
            lambda payload: payload.update(generated_at="2026-06-22T12:00:00"),
            lambda payload: payload.update(extra="not allowed"),
            lambda payload: payload["tickets"][0].update(finding_id="F-1002"),
            lambda payload: payload["tickets"][0].update(urgency={"score": 9}),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                payload = copy.deepcopy(self.payload)
                mutate(payload)
                self.assertTrue(contract_errors(payload, self.expected))

    def test_duplicate_ticket_ids_fail_even_with_distinct_findings(self):
        payload = copy.deepcopy(self.payload)
        second = copy.deepcopy(payload["tickets"][0])
        second["finding_id"] = "F-9999"
        payload["tickets"].append(second)
        payload["tickets_generated"] = 2
        expected = {**self.expected, "F-9999": {"equipment_id": second["equipment_id"]}}
        self.assertTrue(any("duplicate ticket ID" in error
                            for error in contract_errors(payload, expected)))

    def test_missing_review_and_explicit_failure_cannot_pass(self):
        review = self.complete_review()
        review["items"].pop()
        self.assertEqual(self.evaluate(review)["overall"], "needs_review")
        review = self.complete_review()
        review["items"][0]["verdict"] = "fail"
        report = self.evaluate(review)
        self.assertEqual(report["overall"], "fail")
        self.assertEqual(len(report["semantic"]["failed"]), 1)

    def test_stale_review_fabricated_quote_duplicates_and_empty_evidence_fail(self):
        mutations = (
            lambda review: review.update(output_sha256="different-output"),
            lambda review: review.update(reference_version="old"),
            lambda review: review.update(partition="test"),
            lambda review: review["items"].append(copy.deepcopy(review["items"][0])),
            lambda review: review["items"][0].update(evidence=[]),
            lambda review: review["items"][0].update(reason=""),
            lambda review: review["items"][0].update(expectations={}),
            lambda review: review["reviewer"].update(kind=[]),
            lambda review: review["items"][0].update(verdict=[]),
            lambda review: review["items"][0].update(
                evidence=[{"field": "summary", "quote": "This was never in the output."}]
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                review = self.complete_review()
                mutate(review)
                with self.assertRaises(ValueError):
                    self.evaluate(review)

    def test_complete_review_is_only_a_provisional_output_pass(self):
        report = self.evaluate(self.complete_review())
        self.assertEqual(report["overall"], "provisional_pass")
        self.assertEqual(report["semantic"]["reviewer"]["kind"], "ai_only")
        self.assertEqual(report["review_provenance"]["kind"], "ai_only")
        self.assertIn("not_full", report["scope"])
        self.assertEqual(report["system_scenario_results"], "not_provided_not_implied_by_this_report")

    def test_strict_json_rejects_malformed_duplicate_keys_and_nonfinite_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "software-fixture.json"
            for raw in ('{bad', '{"score":1,"score":2}', '{"score":NaN}', '{"score":Infinity}'):
                with self.subTest(raw=raw):
                    path.write_text(raw, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_json(path)

    def test_cli_exit_codes_distinguish_pending_fail_and_provisional_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "software-fixture.json"
            reviews = Path(directory) / "software-review.json"
            output.write_text(json.dumps(self.payload), encoding="utf-8")
            fingerprint = hashlib.sha256(output.read_bytes()).hexdigest()
            args = ["--partition", "development", "--tickets", str(output)]
            reference = (self.version, self.expected, self.cards)
            with patch("assess.load_references", return_value=reference), redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 2)
                review = self.complete_review()
                review["output_sha256"] = fingerprint
                reviews.write_text(json.dumps(review), encoding="utf-8")
                self.assertEqual(main(args + ["--reviews", str(reviews)]), 0)
                review["items"][0]["verdict"] = "fail"
                reviews.write_text(json.dumps(review), encoding="utf-8")
                self.assertEqual(main(args + ["--reviews", str(reviews)]), 1)

    def calibration_review(self):
        return {
            "reference_version": self.version,
            "reviewer": {"kind": "ai_only", "independent_of_generation": False},
            "judgments": [
                {
                    "probe_id": case["probe_id"],
                    "dimension": "grounding",
                    "verdict": "fail",
                    "reason": "Synthetic test judgment; not an actual reviewer observation.",
                    "evidence": [{
                        "field": "likelihood_of_failure.rationale",
                        "quote": case["ticket"]["likelihood_of_failure"]["rationale"],
                    }],
                }
                for case in self.probes["review_calibration"]["cases"]
            ],
        }

    def test_seeded_semantic_contradictions_are_structurally_valid(self):
        for case in self.probes["review_calibration"]["cases"]:
            with self.subTest(probe=case["probe_id"]):
                payload = {
                    "generated_at": self.payload["generated_at"],
                    "tickets_generated": 1,
                    "tickets": [case["ticket"]],
                }
                expected = {case["finding_id"]: self.findings[case["finding_id"]]}
                self.assertEqual(contract_errors(payload, expected), [])

    def test_calibration_rejects_reviewer_acceptance_of_seeded_false_claim(self):
        review = self.calibration_review()
        report = calibrate(review, self.probes)
        self.assertEqual(report["calibration_status"], "pass")
        self.assertNotIn("overall", report)
        self.assertEqual(report["scope"], "known_fixture_conformance")
        review["judgments"][0]["verdict"] = "pass"
        report = calibrate(review, self.probes)
        self.assertEqual(report["calibration_status"], "fail")
        self.assertEqual(len(report["wrong_fixture_judgments"]), 1)

    def test_calibration_missing_judgment_stays_pending_and_bad_quote_fails(self):
        review = self.calibration_review()
        review["judgments"].pop()
        self.assertEqual(calibrate(review, self.probes)["calibration_status"], "needs_review")
        review["judgments"][0]["evidence"][0]["quote"] = "Absent quote."
        with self.assertRaisesRegex(ValueError, "quote not present"):
            calibrate(review, self.probes)


if __name__ == "__main__":
    unittest.main()
