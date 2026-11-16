"""Synthetic-only package integration checks; never read the candidate finding CSV."""
from contextlib import redirect_stderr, redirect_stdout
import csv
import io
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from eval import run_knowledge_package as runner
from triage_knowledge.contracts import KnowledgeError, canonical_bytes, sha256, strict_json
from triage_knowledge.source_context import build_source_context


class KnowledgePackageTests(unittest.TestCase):
    def setUp(self):
        token = uuid4().hex
        self.inputs = runner.ROOT / ".artifacts" / "knowledge-package-tests" / token
        self.output = runner.RESULTS / ("software-test-" + token)
        self.inputs.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.inputs)
        self.addCleanup(lambda: shutil.rmtree(self.output, ignore_errors=True))
        self.paths = {name: self.inputs / name for name in ("domain", "findings", "registry", "split")}
        self.paths["domain"].write_bytes(b"".join(
            f"# Guidance {number}\nPreserve source condition {number} and uncertainty.\n\n".encode()
            for number in range(8)))
        self.frows, self.rrows = [], []
        for number in range(1, 4):
            fid, eid = f"F-{9000 + number}", f"EQ-{9000 + number}"
            self.frows.append({
                "finding_id": fid, "reported_date": "2026-06-01", "equipment_id": eid,
                "equipment_type": "Synthetic rotor", "inspection_type": "Routine Operator Round",
                "inspection_method": "Visual", "finding_description": f"Synthetic condition {number}.",
                "reported_by": "Software author", "reporter_role": "Software test",
            })
            self.rrows.append({
                "equipment_id": eid, "equipment_type": "Synthetic rotor",
                "service_description": "Synthetic service", "criticality_score": "5",
                "reliability_score": "5", "safety_critical_element": "No", "redundancy": "None",
                "engineer_comment": f"Independent synthetic comment {number}.",
            })
        for name, rows in (("findings", self.frows), ("registry", self.rrows)):
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            self.paths[name].write_bytes(stream.getvalue().encode())
        self.paths["split"].write_bytes(canonical_bytes({
            "sources_sha256": {key: sha256(self.paths[name].read_bytes())
                               for name, key in runner.SOURCE_KEYS.items()},
            "partitions": {"development": ["F-9001", "F-9002"], "test": ["F-9003"]}}))
        pin = patch.object(runner, "EXPECTED_SPLIT_SHA256", sha256(self.paths["split"].read_bytes()))
        pin.start()
        self.addCleanup(pin.stop)
        self.time = "2026-07-01T00:00:00+00:00"
        self.counts = {"all": 3, "development": 2, "test": 1}
        self.plan = runner.make_plan(self.paths, self.time, self.counts)

    def test_synthetic_end_to_end_preserves_fields_hashes_and_lifecycle(self):
        report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "pass", report.get("failure"))
        self.assertEqual(set(report["goals"].values()), {"pass"})
        self.assertEqual(len(report["cases"]), 6)
        self.assertEqual(report["final_input_sha256"], self.plan["input_sha256"])
        self.assertNotEqual(report["row_order"]["baseline"], report["row_order"]["reversed"])
        context = strict_json((self.output / "all-context.json").read_bytes())
        self.assertEqual(context["payload"]["findings"],
                         {row["finding_id"]: row for row in self.frows})
        self.assertEqual(context["payload"]["registry"],
                         {row["equipment_id"]: row for row in self.rrows})
        dev = strict_json((self.output / "development-context.json").read_bytes())
        self.assertEqual(dev["finding_ids"], ["F-9001", "F-9002"])
        self.assertEqual(len(report["lifecycle"]["excluded_items"]), 4)
        self.assertEqual(len(report["lifecycle"]["baseline_target_items"]), 6)
        lifecycle = strict_json((self.output / "lifecycle-context.json").read_bytes())
        self.assertNotIn(report["lifecycle"]["old_edited_address"], lifecycle["source_index"])
        self.assertEqual(report["runtime"]["core_module_files"]["source"],
                         str((runner.ROOT / "triage_knowledge" / "source.py").resolve()))
        self.assertIn("revision", report["git"])
        self.assertIn("dirty", report["git"])
        self.assertEqual(report["human_review"], "not established")
        self.assertEqual(report["system_acceptance"], "not established")
        diagnostics = {case["case"]: case["error_code"] for case in report["diagnostics"]}
        self.assertEqual(diagnostics["pending_publish"], "pending_review")
        for name in ("rehashed_knowledge", "rehashed_comment", "rehashed_policy", "rehashed_index",
                     "inactive_reinsert"):
            self.assertIn(diagnostics[name], ("context_contract", "assessment_policy"))
        self.assertEqual(diagnostics["unavailable_release"], "unknown_or_invalid_release")
        self.assertEqual(diagnostics["unavailable_strategy"], "strategy_binding_mismatch")
        self.assertEqual(diagnostics["unavailable_overflow"], "result_too_large")
        with self.assertRaises(FileExistsError):
            runner.run_package(self.output, self.paths, self.plan)

    def test_harness_reports_consumer_that_accepts_rehashed_mutation(self):
        original = runner.validate_source_context

        def faulty(bundle, findings, registry, store, **options):
            if type(bundle) is bytes:
                options["assessment_policy"] = options.pop("expected_assessment_policy")
                return build_source_context(store, findings, registry, **options)
            return original(bundle, findings, registry, store, **options)

        with patch.object(runner, "validate_source_context", side_effect=faulty):
            report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failure"]["error_class"], "missing_rejection")
        self.assertEqual(report["failure"]["stage"], "faults")
        self.assertNotEqual(report["goals"]["tamper_rejection"], "pass")
        self.assertEqual(strict_json((self.output / "report.json").read_bytes())["status"], "failed")

    def test_genuinely_unavailable_release_retains_failure_without_context(self):
        with patch.object(runner, "_review_publish", return_value="sha256-" + "0" * 64):
            report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failure"]["error_class"], "unknown_or_invalid_release")
        self.assertFalse((self.output / "all-context.json").exists())
        self.assertTrue((self.output / "report.json").exists())

    def test_wrong_rejection_diagnostic_is_a_harness_failure(self):
        original = runner.validate_source_context

        def wrong_diagnostic(bundle, *args, **kwargs):
            if type(bundle) is bytes:
                raise KnowledgeError("invalid_query", "Deliberately wrong software-fixture diagnostic.")
            return original(bundle, *args, **kwargs)

        with patch.object(runner, "validate_source_context", side_effect=wrong_diagnostic):
            report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failure"]["error_class"], "unexpected_diagnostic")
        self.assertEqual(report["failure"]["field"], "invalid_query")
        self.assertNotEqual(report["goals"]["tamper_rejection"], "pass")

    def test_missing_new_edited_revision_fails_positive_lifecycle_check(self):
        report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "pass", report.get("failure"))
        store = runner.SourceKnowledgeStore(self.output / "software-store")
        candidate = store.resolve_release(report["lifecycle"]["release"])["candidate"]
        edited = report["lifecycle"]["edited_item"]
        revision = candidate["items"][edited]
        address = f"knowledge:{edited}@{revision['revision_id']}:text"
        packet = strict_json((self.output / "lifecycle-context.json").read_bytes())
        del packet["payload"]["knowledge"][address]
        del packet["source_index"][address]
        with self.assertRaises(KnowledgeError) as raised:
            runner._assert_revision_projection(
                packet, candidate, {edited: revision["revision"]["text"]}, store, self.time)
        self.assertEqual(raised.exception.code, "missing_lifecycle_target")

    def test_identical_active_text_does_not_resurrect_retired_item(self):
        duplicate = b"# Shared guidance\nIdentical active source wording.\n\n"
        self.paths["domain"].write_bytes(duplicate * 8)
        split = strict_json(self.paths["split"].read_bytes())
        split["sources_sha256"][runner.SOURCE_KEYS["domain"]] = sha256(duplicate * 8)
        self.paths["split"].write_bytes(canonical_bytes(split))
        with patch.object(runner, "EXPECTED_SPLIT_SHA256", sha256(self.paths["split"].read_bytes())):
            plan = runner.make_plan(self.paths, self.time, self.counts)
            report = runner.run_package(self.output, self.paths, plan)
        self.assertEqual(report["status"], "pass", report.get("failure"))
        packet = strict_json((self.output / "lifecycle-context.json").read_bytes())
        self.assertTrue(any(duplicate.decode() in text
                            for text in packet["payload"]["knowledge"].values()))
        for item_id in report["lifecycle"]["excluded_items"]:
            self.assertFalse(any(key.startswith(f"knowledge:{item_id}@")
                                 for key in packet["source_index"]))

    def test_row_order_semantic_change_is_a_failure_not_an_autofix(self):
        original = runner._table

        def wrong_table(rows, source):
            if source.kind == "registry_input" and rows[0]["equipment_id"] == "EQ-9003":
                rows = [{**row, "engineer_comment": "Unexpected change."} for row in rows]
            return original(rows, source)

        with patch.object(runner, "_table", side_effect=wrong_table):
            report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failure"]["error_class"], "semantic_instability")
        self.assertNotEqual(report["goals"]["row_order_and_repeat"], "pass")

    def test_input_change_after_freeze_is_retained_and_never_accepted(self):
        self.paths["domain"].write_bytes(self.paths["domain"].read_bytes() + b"\n")
        report = runner.run_package(self.output, self.paths, self.plan)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failure"]["error_class"], "original_integrity")
        self.assertEqual(report["goals"]["freeze_unchanged"], "failed")
        self.assertFalse((self.output / "all-context.json").exists())
        self.assertTrue((self.output / "plan.json").exists())
        self.assertTrue((self.output / "report.json").exists())

    def test_source_tampering_before_new_plan_cannot_be_frozen_as_original(self):
        for name in runner.SOURCE_KEYS:
            path = self.paths[name]
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.subTest(source=name), self.assertRaises(KnowledgeError) as raised:
                runner.make_plan(self.paths, self.time, self.counts)
            self.assertEqual(raised.exception.code, "original_integrity")
            path.write_bytes(original)
        forged = strict_json(self.paths["split"].read_bytes())
        forged["sources_sha256"][runner.SOURCE_KEYS["domain"]] = "0" * 64
        self.paths["split"].write_bytes(canonical_bytes(forged))
        with self.assertRaises(KnowledgeError) as raised:
            runner.make_plan(self.paths, self.time, self.counts)
        self.assertEqual(raised.exception.code, "split_integrity")

    def test_cli_plan_only_is_nonexecuting_and_execution_requires_freeze(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (patch.object(runner, "SOURCE_PATHS", self.paths),
              patch.object(runner, "run_package") as execute,
              redirect_stdout(stdout), redirect_stderr(stderr)):
            self.assertEqual(runner.main(["--output", str(self.output),
                                         "--assessment-time", self.time, "--plan-only"]), 0)
            execute.assert_not_called()
        self.assertTrue((self.output / "plan.json").exists())
        self.assertFalse((self.output / "report.json").exists())
        with (patch.object(runner, "SOURCE_PATHS", self.paths),
              redirect_stdout(stdout), redirect_stderr(stderr)):
            self.assertEqual(runner.main(["--output", str(self.output),
                                         "--assessment-time", self.time]), 1)
        self.assertIn("freeze_required", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
