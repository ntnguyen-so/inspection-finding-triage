"""Synthetic runner controls only; no held-out sources, Git or provider dispatch."""
import asyncio
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from eval import run_knowledge_completion as completion
from eval.knowledge_attempts import AttemptLedger
from eval.knowledge_eval import ROOT, Suite
from eval.knowledge_query_inputs import author_registry
from eval.run_knowledge import EvidenceWriter
from triage_knowledge.source import validate_proposal
from triage_knowledge.source_store import SourceKnowledgeStore


def synthetic_suite():
    ids = [f"dev{i}" for i in range(4)] + [f"eval{i}" for i in range(4)] + ["original_domain"]
    raw = b"Copper widget rules stay uncertain.\nSilver widget rules remain separate.\n"
    records, references = [], []
    for sid in ids:
        partition = "shared_smoke" if sid == "original_domain" else "development" if sid.startswith("dev") else "evaluation"
        records.append({
            "source_id": sid, "partition": partition, "path": sid + ".txt",
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
        references.append({
            "source_id": sid, "atoms": [], "aliases": [],
            "queries": [] if sid == "original_domain" else [
                {"id": sid + "." + kind, "kind": kind,
                 "subject_types": ["Copper widget"] if kind == "scoped" else
                                  ["Silver widget"] if kind == "qualifier" else ["Unknown widget"],
                 "required_atoms": ["EVALUATOR_ONLY_SENTINEL"]}
                for kind in ("scoped", "qualifier", "unknown")
            ],
        })
    slots = [sid + ".primary" for sid in ids] + [
        sid + ".repeat" + str(number) for sid in ("eval0", "eval1") for number in (1, 2)
    ]
    return Suite({
        "version": "synthetic-runner-control", "grader_version": "synthetic-control",
        "sources": records, "slot_ids": slots, "repeat_source_ids": ["eval0", "eval1"],
        "reference": "unused-reference.json", "reference_sha256": "a" * 64,
        "exposure": "Synthetic test data only",
        "experiment": {"maximum_application_attempts": 26, "retry_allowed": sorted(completion.RECOVERABLE)},
        "efficiency_case_ids": [f"eval{i}.{kind}" for i in range(4) for kind in ("scoped", "qualifier")],
        "thresholds": {"each_scoped_irrelevant_byte_reduction": 0.2},
    }, {"sources": references}, {sid: raw for sid in ids})


def raw_proposal():
    return {"groups": [
        {"group_id": "copper", "unit_ids": ["u0001"], "scopes": ["Copper widget"],
         "aliases": [], "evidence": [{"unit_id": "u0001", "quote": "Copper widget"}],
         "required_with": []},
        {"group_id": "silver", "unit_ids": ["u0002"], "scopes": ["Silver widget"],
         "aliases": [], "evidence": [{"unit_id": "u0002", "quote": "Silver widget"}],
         "required_with": []},
    ]}


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "eval" / "results" / "knowledge" / "extraction" / ("runner-control-" + uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        self.suite = synthetic_suite()
        fixture = author_registry(
            {sid: raw for sid, raw in self.suite.sources.items() if sid != "original_domain"},
            ({"case_id": key, "subject_types": query["subject_types"]}
             for key, query in self.suite.queries.items()),
        )
        raw = completion.existing._encoded(fixture)
        path = self.root / "registry.json"
        path.write_bytes(raw)
        self.suite.manifest.update(
            query_registry=str(path.relative_to(ROOT)), query_registry_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def build(self, identity=None):
        return completion.build_plan(self.suite, identity or {"code_sha256": "synthetic"})

    def test_plan_pins_same_slots_source_only_requests_and_new_profile(self):
        requests, _, freeze, ledger = self.build()
        self.assertEqual(len(requests), 13)
        self.assertEqual(set(requests), set(self.suite.manifest["slot_ids"]))
        self.assertEqual(list(requests)[:5], [f"dev{i}.primary" for i in range(4)] + ["original_domain.primary"])
        self.assertEqual(freeze["maximum_application_attempts"], 26)
        self.assertEqual(freeze["maximum_attempts_per_slot"], 2)
        self.assertEqual(set(ledger["development_slots"]), set(requests))
        self.assertIn("NOT a partition", freeze["driver_stop_policy"])
        self.assertFalse(freeze["integration_strategy"]["selected"])
        for request in requests.values():
            self.assertEqual((request.model, request.reasoning_effort, request.timeout_seconds),
                             ("gpt-6-luna", "medium", 120))
            self.assertNotIn("EVALUATOR_ONLY_SENTINEL", json.dumps(completion.request_record(request)))
            self.assertEqual(set(json.loads(request.user)), {"source_id", "units"})
        self.assertEqual(self.build()[2:], (freeze, ledger))

    def test_fixed_ledger_rejects_changed_code_prompt_or_source_identity(self):
        _, _, freeze, plan = self.build()
        path = self.root / "control.experimental-ledger.json"
        AttemptLedger(path, plan)
        original = path.read_bytes()
        variants = [self.build({"code_sha256": "changed"})[3]]
        altered = deepcopy(plan)
        altered["slots"][altered["schedule"][0]] = "b" * 64
        variants.append(altered)
        with patch("triage_knowledge.source.SYSTEM", "Different source-only extraction instructions"):
            variants.append(self.build()[3])
        for variant in variants:
            with self.assertRaisesRegex(ValueError, "changed"):
                AttemptLedger(path, variant)
            self.assertEqual(path.read_bytes(), original)
        self.assertNotEqual(freeze["code_identity"], {"code_sha256": "changed"})

    def test_evidence_directory_and_each_file_are_write_once(self):
        writer = EvidenceWriter(self.root / "evidence")
        writer.write("raw.json", raw_proposal())
        before = (writer.root / "raw.json").read_bytes()
        with self.assertRaises(FileExistsError):
            writer.write("raw.json", {"repaired": True})
        with self.assertRaises(FileExistsError):
            EvidenceWriter(writer.root)
        self.assertEqual((writer.root / "raw.json").read_bytes(), before)
        with self.assertRaises(ValueError):
            writer.write("..\\escape.json", {})

    def test_default_and_plan_only_never_create_provider_or_ledger(self):
        _, _, freeze, plan = self.build()
        with (
            patch("llm_inference.CopilotProvider") as provider,
            patch.object(completion, "AttemptLedger") as ledger,
            patch.object(completion, "load_suite", return_value=self.suite),
            patch.object(completion, "code_identity", return_value={"code_sha256": "synthetic"}),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(completion.main(["--output", str(self.root / "not-created")]), 2)
            self.assertEqual(completion.main(["--plan-only"]), 2)
            self.assertFalse((self.root / "not-created").exists())
            provider.assert_not_called()
            ledger.assert_not_called()

    def test_inference_requires_an_earlier_saved_plan(self):
        with (
            patch("llm_inference.CopilotProvider") as provider,
            patch.object(completion, "AttemptLedger") as ledger,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(completion.main([
                "--output", str(self.root / "not-created"), "--allow-inference",
            ]), 1)
            provider.assert_not_called()
            ledger.assert_not_called()
            self.assertFalse((self.root / "not-created").exists())

    def test_changed_reviewed_plan_rejects_before_ledger_baseline_or_provider(self):
        _, _, freeze, ledger_plan = completion.build_plan(self.suite, completion.code_identity())
        approved = completion.plan_record(freeze, ledger_plan)
        changed = deepcopy(approved)
        changed["freeze"]["profile"]["reasoning_effort"] = "low"
        wrong_type = deepcopy(approved)
        wrong_type["dispatch"] = 0
        with (
            patch("llm_inference.CopilotProvider") as provider,
            patch.object(completion, "AttemptLedger") as ledger,
            patch.object(completion.existing, "run_offline") as baseline,
        ):
            for index, rejected in enumerate((changed, wrong_type)):
                writer = EvidenceWriter(self.root / f"changed-plan-{index}")
                with self.assertRaisesRegex(ValueError, "Reviewed freeze plan differs"):
                    asyncio.run(completion.run_completion(
                        self.suite, writer, allow_inference=True, approved_plan=rejected,
                    ))
                self.assertEqual(list(writer.root.iterdir()), [])
            provider.assert_not_called()
            ledger.assert_not_called()
            baseline.assert_not_called()

    def test_guard_rejects_mutated_request_before_provider_call(self):
        requests, _, freeze, _ = self.build()
        writer = EvidenceWriter(self.root / "guard")
        provider = SimpleNamespace(generate=None)
        guarded = completion.CapturedProvider(provider, requests, freeze, writer)
        first = next(iter(requests.values()))
        changed = replace(first, reasoning_effort="low")
        from llm_inference import InferenceError
        with patch.object(completion, "verify_freeze"):
            with self.assertRaises(InferenceError):
                asyncio.run(guarded.generate(changed))
        self.assertEqual(list(writer.root.iterdir()), [])

    def baseline(self):
        fixture = completion.load_registry_fixture(self.suite)
        return {
            "source_assessments": [{"assessment": {"status": "pass"}} for _ in range(9)],
            "query_count": 24, "query_assessments": {"negative": {"status": "fail"}},
            "status": "failed_component_checks",
            "query_registry_fixture": {key: fixture[key] for key in ("path", "sha256", "registry_sha256")},
            "partitions": {part: {"review_status": "synthetic_software_fixture"}
                           for part in ("development", "evaluation")},
        }

    def run_mocked(self, *, semantic_pass=True, selector=None, recover_first=False,
                   recover_each=False, revalidation_fails=False):
        calls = []
        seen_requests = set()

        class Provider:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return False

            async def generate(self, request):
                calls.append(request)
                first_for_slot = id(request) not in seen_requests
                seen_requests.add(id(request))
                if recover_first and len(calls) == 1 or recover_each and first_for_slot:
                    from llm_inference import InferenceError
                    raise InferenceError("timeout", "Synthetic recoverable error")
                proposal = raw_proposal()
                return SimpleNamespace(
                    text=json.dumps(proposal), parsed=proposal,
                    receipt={"dispatched": True, "adapter_attempts": 1, "synthetic_control": True},
                )

        writer = EvidenceWriter(self.root / "run")
        relative_ledger = self.root.relative_to(ROOT) / "completion.experimental-ledger.json"
        grade_calls = []

        def extraction_grade(*_):
            grade_calls.append(True)
            return {"status": "pass" if semantic_pass and not (revalidation_fails and len(grade_calls) > 13) else "fail"}

        with ExitStack() as stack:
            stack.enter_context(patch.object(completion, "LEDGER", relative_ledger))
            stack.enter_context(patch.object(completion, "verify_freeze"))
            stack.enter_context(patch.object(completion.existing, "run_offline", return_value=self.baseline()))
            stack.enter_context(patch("llm_inference.CopilotProvider", Provider))
            stack.enter_context(patch("eval.run_knowledge.assess_extraction", side_effect=extraction_grade))
            stack.enter_context(patch.object(completion, "assess_repeats", return_value={"status": "pass"}))
            if selector is not None:
                stack.enter_context(patch.object(completion, "selector_diagnostic", selector))
            stack.enter_context(patch.object(completion, "assess_retrieval", return_value={
                "status": "pass", "recall": 1.0, "broadening_ok": True,
                "irrelevant_baseline_bytes": 100, "irrelevant_returned_bytes": 50,
                "irrelevant_byte_reduction": 0.5,
            }))
            _, _, freeze, ledger_plan = completion.build_plan(self.suite, completion.code_identity())
            approved = completion.plan_record(freeze, ledger_plan)
            result = asyncio.run(completion.run_completion(
                self.suite, writer, allow_inference=True, approved_plan=approved,
            ))
        return result, writer, calls, ROOT / relative_ledger

    def test_semantic_failure_stops_all_later_slots_without_selector_or_retry(self):
        from unittest.mock import Mock
        selector = Mock(side_effect=AssertionError("Selector must not run after hard failure"))
        result, writer, calls, ledger = self.run_mocked(semantic_pass=False, selector=selector)
        self.assertEqual(len(calls), 1)
        selector.assert_not_called()
        self.assertEqual(result["exit_code"], 1)
        self.assertEqual(result["checks"]["hard_extraction"]["status"], "fail")
        self.assertEqual(result["checks"]["retrieval"]["status"], "unexecuted")
        history = json.loads(ledger.read_text("utf-8"))["attempts"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["outcome"]["error_class"], "proposal_validation")
        raw = json.loads((writer.root / "C1" / "dev0.primary.json").read_text("utf-8"))
        self.assertEqual(raw["raw_proposal"], raw_proposal())
        self.assertFalse(raw["accepted"])
        self.assertEqual(len(list((writer.root / "calls").glob("response-*.json"))), 1)

    def test_primary_defensive_revalidation_failure_prevents_selector(self):
        from unittest.mock import Mock
        selector = Mock(side_effect=AssertionError("No selector after changed validation"))
        result, _, calls, _ = self.run_mocked(selector=selector, revalidation_fails=True)
        self.assertEqual(len(calls), 13)
        self.assertEqual(result["checks"]["primary_revalidation"]["status"], "fail")
        self.assertEqual(result["exit_code"], 1)
        selector.assert_not_called()

    def test_all_thirteen_slots_can_spend_exactly_twenty_six_allowlisted_attempts(self):
        result, _, calls, path = self.run_mocked(recover_each=True)
        self.assertEqual(len(calls), 26)
        self.assertEqual(result["checks"]["attempts"]["application_attempts"], 26)
        self.assertEqual(result["checks"]["attempts"]["recovery_attempts"], 13)
        self.assertEqual(result["checks"]["hard_extraction"]["status"], "pass")
        self.assertFalse(result["C1_qualified"])
        data = json.loads(path.read_text("utf-8"))
        ledger = AttemptLedger(path, data["plan"])
        before = path.read_bytes()
        slot = data["plan"]["schedule"][0]
        with self.assertRaises(ValueError):
            ledger.reserve(slot, data["plan"]["slots"][slot])
        self.assertEqual(path.read_bytes(), before)

    def test_all_slots_and_raw_selector_captures_preserve_simulated_grading_without_qualification(self):
        result, writer, calls, ledger = self.run_mocked(recover_first=True)
        self.assertEqual(len(calls), 14)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["programmatic_status"], "pass")
        self.assertEqual(result["checks"]["attempts"]["first_attempt_failures"], 1)
        self.assertEqual(result["checks"]["attempts"]["recovery_attempts"], 1)
        self.assertEqual(len(list((writer.root / "queries").glob("*.json"))), 24)
        self.assertEqual(len(list((writer.root / "actual-requests").glob("*.json"))), 14)
        self.assertFalse(result["C1_qualified"])
        self.assertFalse(result["integration_strategy"]["selected"])
        self.assertEqual(result["human_effort"], "unexecuted")
        self.assertIsNone(result["usd_cost"])
        freeze = json.loads((writer.root / "freeze.json").read_text("utf-8"))
        freeze_hash = completion.canonical_hash(freeze)
        profile = {
            "experiment_id": completion.PROFILE["version"] + "-" + freeze_hash,
            "profile_version": completion.PROFILE["version"], "freeze_sha256": freeze_hash,
            "qualification": "unqualified_software_fixture",
        }
        documents = {sid: completion.existing.document_for(self.suite, sid) for sid in self.suite.sources}
        for partition in ("development", "evaluation"):
            store = SourceKnowledgeStore(writer.root / "software-fixture-stores" / partition,
                                         experimental_profile=profile)
            candidate, _ = store.load_draft()
            self.assertEqual(set(candidate["sources"]), self.suite.members(partition))
            self.assertTrue(all(i["review_state"] == "reviewed" for i in candidate["items"].values()))
            for sid in candidate["sources"]:
                expected = validate_proposal(documents[sid], raw_proposal())
                revisions = [item["revision"] for item in candidate["items"].values()
                             if item["revision"]["source_id"] == sid]
                for group in expected.groups:
                    revision = next(row for row in revisions if row["spans"] == group["spans"])
                    for key in ("source_id", "source_sha256", "spans", "text", "scopes", "aliases", "evidence"):
                        self.assertEqual(revision[key], group[key])
        fixture = completion.load_registry_fixture(self.suite)
        for path in (writer.root / "queries").glob("*.json"):
            row = json.loads(path.read_text("utf-8"))
            for key in ("query_context", "provider_payload", "result", "local_evidence"):
                self.assertNotIn("EVALUATOR_ONLY_SENTINEL", json.dumps(row[key]))
            self.assertEqual(row["query_context"],
                             completion.existing.query_rows(
                                 self.suite.queries[row["case_id"]]["subject_types"],
                                 shared_registry_rows=fixture["fixture"]["registry"],
                             ))
            self.assertEqual(row["query_registry_fixture"], freeze["query_registry_fixture"])
            self.assertEqual(row["result"]["selection_mode"],
                             "conservative_expansion" if row["case_id"].endswith(".unknown") else "scoped")
        original = ledger.read_bytes()
        with (
            patch.object(completion, "LEDGER", ledger.relative_to(ROOT)),
            patch.object(completion, "verify_freeze"),
            patch("llm_inference.CopilotProvider") as provider,
        ):
            with self.assertRaisesRegex(ValueError, "already spent"):
                asyncio.run(completion.run_completion(
                    self.suite, EvidenceWriter(self.root / "resumed"), allow_inference=True,
                    approved_plan=json.loads((writer.root / "approved-plan.json").read_text("utf-8")),
                ))
            provider.assert_not_called()
        self.assertEqual(ledger.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
