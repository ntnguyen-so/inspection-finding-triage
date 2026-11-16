"""Adapter software checks; no publication, human review or paid sends occur."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

from eval.knowledge_eval import Suite, canonical_hash, load_suite
from eval.run_knowledge import (
    ROOT, SOFTWARE_REVIEWER, _reviewed_partition, adapt_extraction, adapt_result, build_experiment, code_identity,
    collect_c0, document_for, main, make_validator, query_binding, query_rows,
    run_experiment, run_offline,
)


class MemoryWriter:
    def __init__(self):
        self.root = ROOT / "eval" / "results" / "knowledge" / "extraction" / "software-control-not-written"
        self.values = {}

    def write(self, name, value):
        key = str(name)
        if key in self.values:
            raise AssertionError("Evidence overwrite attempted")
        self.values[key] = deepcopy(value)


class UnreviewedStore:
    instances = []

    def __init__(self, path):
        self.path = Path(path)
        self.members = []
        self.__class__.instances.append(self)

    def create_draft(self, extractions):
        self.members = [e.document.source_id for e in extractions]
        return "a" * 64

    def load_draft(self):
        return {"items": {sid: {"review_state": "pending"} for sid in self.members}}, "a" * 64

    def review_item(self, *args, **kwargs):
        raise AssertionError("Adapter must not manufacture review")

    def publish(self, *args, **kwargs):
        raise AssertionError("Adapter must not publish unreviewed output")


class DiagnosticAdapterTests(unittest.TestCase):
    """Entirely mocked extraction/store/tool; never execute the frozen C0 corpus."""

    def setUp(self):
        source_ids = [f"dev{i}" for i in range(4)] + [f"eval{i}" for i in range(4)] + ["original_domain"]
        manifest_sources, reference_sources = [], []
        for sid in source_ids:
            partition = "shared_smoke" if sid == "original_domain" else "development" if sid.startswith("dev") else "evaluation"
            manifest_sources.append({
                "source_id": sid, "partition": partition, "path": f"{sid}.txt",
                "sha256": hashlib.sha256(b"x").hexdigest(),
            })
            reference_sources.append({
                "source_id": sid, "atoms": [], "aliases": [],
                "queries": [] if sid == "original_domain" else [
                    {"id": f"{sid}.{kind}", "kind": kind, "subject_types": ["Artificial subject"]}
                    for kind in ("scoped", "qualifier", "unknown")
                ],
            })
        self.suite = Suite(
            {"sources": manifest_sources, "version": "software-control", "grader_version": "software-control"},
            {"sources": reference_sources}, {sid: b"x" for sid in source_ids},
        )
        self.extractions = {sid: SimpleNamespace(document=SimpleNamespace(source_id=sid)) for sid in source_ids}
        self.rows = [
            {"source_id": sid, "assessment": {"status": "pass"},
             "observation": {"source_id": sid, "status": "accepted"}}
            for sid in source_ids
        ]
        self.tool_calls = []
        self.stores = []

        owner = self

        class Store:
            def __init__(self, path):
                self.path = Path(path)
                self.reviews = []
                self.publications = []
                owner.stores.append(self)

            def create_draft(self, extractions):
                self.received = list(extractions)
                self.candidate = {
                    "schema_version": 3,
                    "sources": {e.document.source_id: {"source_sha256": hashlib.sha256(b"x").hexdigest()} for e in self.received},
                    "items": {
                        e.document.source_id: {
                            "revision_id": "sha256-" + "a" * 64,
                            "revision": {"source_id": e.document.source_id, "text": "x", "scopes": [], "aliases": []},
                            "review_state": "pending", "review": None,
                        } for e in self.received
                    },
                    "context_links": [], "replacements": [],
                }
                return canonical_hash(self.candidate)

            def load_draft(self):
                return deepcopy(self.candidate), canonical_hash(self.candidate)

            def review_item(self, item_id, *, reviewer, reason, expected_digest):
                owner.assertEqual(expected_digest, canonical_hash(self.candidate))
                self.reviews.append({"item_id": item_id, "reviewer": reviewer, "reason": reason})
                self.candidate["items"][item_id].update(review_state="reviewed", review={"reviewer": reviewer, "reason": reason})
                return canonical_hash(self.candidate)

            def publish(self, **kwargs):
                owner.assertEqual(kwargs["expected_digest"], canonical_hash(self.candidate))
                owner.assertTrue(all(i["review_state"] == "reviewed" for i in self.candidate["items"].values()))
                self.publications.append(kwargs)
                return "sha256-" + canonical_hash(self.candidate)

            def resolve_release(self, release_id):
                return {"candidate": self.candidate}

            def update_metadata(self, *args, **kwargs):
                raise AssertionError("Diagnostic must not repair raw metadata")

            def edit_item(self, *args, **kwargs):
                raise AssertionError("Diagnostic must not edit raw content")

        self.Store = Store

    def run_mocked(self, *, diagnostic, store_type=None):
        def retrieve(store, query, **kwargs):
            self.tool_calls.append((store, deepcopy(query), kwargs))
            entries = {
                f"opaque-{sid}": {
                    "source_id": sid, "source_sha256": hashlib.sha256(b"x").hexdigest(),
                    "spans": [{"start": 0, "end": 1}], "text": "x", "scopes": [], "aliases": [],
                } for sid in store.candidate["sources"]
            }
            return SimpleNamespace(
                to_dict=lambda: {"status": "ok", "selection_mode": "conservative_expansion", "entries": entries},
                provider_payload=lambda: {"knowledge": {address: entry["text"] for address, entry in entries.items()}},
                evidence={"software_control": True},
            )

        runtime = SimpleNamespace(strategy_binding=lambda: {"pinned": "software-control"}, get_triage_knowledge=retrieve)
        real_import = importlib.import_module

        def modules(name):
            if name == "triage_knowledge.source_store":
                return SimpleNamespace(SourceKnowledgeStore=store_type or self.Store)
            if name == "triage_knowledge.retrieval":
                return runtime
            return real_import(name)

        writer = MemoryWriter()
        with (
            patch("eval.run_knowledge.collect_c0", return_value=(deepcopy(self.rows), self.extractions)) as collect,
            patch("eval.run_knowledge.importlib.import_module", side_effect=modules),
            patch("eval.run_knowledge.query_binding", side_effect=lambda q: SimpleNamespace(to_dict=lambda: deepcopy(q))),
            patch("eval.run_knowledge.assess_retrieval", return_value={"status": "pass", "recall": 1.0}) as grade,
            patch("eval.run_knowledge.assess_observations", return_value={"overall": "pending"}),
        ):
            report = run_offline(
                self.suite, writer, identity={"scope": "mocked software test"},
                synthetic_review_diagnostic=diagnostic,
            )
        self.assertEqual(collect.call_count, 1)
        return report, writer, grade

    def test_explicit_diagnostic_publishes_unchanged_raw_inputs_and_grades_twenty_four_outputs(self):
        report, writer, grade = self.run_mocked(diagnostic=True)
        self.assertEqual(len(self.tool_calls), 24)
        self.assertEqual(grade.call_count, 24)
        self.assertEqual(report["query_count"], 24)
        self.assertTrue(report["synthetic_review_diagnostic"])
        self.assertEqual(report["overall"], "pending")
        for flag in ("human_approval_established", "system_qualified", "C1_qualified", "selective_retrieval_qualified"):
            self.assertFalse(report[flag])
        self.assertEqual(report["human_effort"], "unexecuted")
        self.assertEqual(report["strict_qualification"], "unexecuted")
        for store, partition in zip(self.stores, ("development", "evaluation")):
            self.assertEqual(set(store.candidate["sources"]), self.suite.members(partition))
            self.assertEqual(len(store.candidate["sources"]), 5)
            self.assertIn("original_domain", store.candidate["sources"])
            self.assertEqual(len(store.publications), 1)
            self.assertIn("synthetic-review-diagnostic", store.path.parts)
            for extraction in store.received:
                self.assertIs(extraction, self.extractions[extraction.document.source_id])
            self.assertTrue(all(r["reviewer"] == SOFTWARE_REVIEWER for r in store.reviews))
            self.assertEqual(store.publications[0]["reviewer"], SOFTWARE_REVIEWER)
            self.assertTrue(all(item["revision"]["scopes"] == [] for item in store.candidate["items"].values()))
        for key, observed in writer.values.items():
            if key.startswith("queries"):
                self.assertTrue(observed["synthetic_review_only"])
                self.assertTrue(observed["synthetic_review_diagnostic"])
                self.assertEqual(observed["execution"], "observed")
                self.assertFalse(observed["selective_qualification"])
        self.assertEqual(
            {call.args[1] for call in grade.call_args_list},
            set(self.suite.queries),
        )

    def test_default_does_not_publish_or_retrieve_and_still_includes_common_source(self):
        report, _, grade = self.run_mocked(diagnostic=False)
        self.assertEqual(self.tool_calls, [])
        grade.assert_not_called()
        self.assertTrue(all(not store.reviews and not store.publications for store in self.stores))
        self.assertTrue(all(len(store.candidate["sources"]) == 5 for store in self.stores))
        self.assertEqual(report["status"], "pending_review")

    def test_mutated_revision_during_declaration_blocks_publication_and_retrieval(self):
        base = self.Store

        class MutatingStore(base):
            def review_item(self, item_id, **kwargs):
                super().review_item(item_id, **kwargs)
                self.candidate["items"][item_id]["revision"]["text"] = "altered"
                return canonical_hash(self.candidate)

        with self.assertRaisesRegex(ValueError, "changed raw"):
            self.run_mocked(diagnostic=True, store_type=MutatingStore)
        self.assertEqual(self.tool_calls, [])
        self.assertTrue(all(not store.publications for store in self.stores))

    def test_reviewed_release_requires_four_plus_common_and_diagnostic_modes_are_exclusive(self):
        store = self.Store(ROOT / "eval")
        store.create_draft([self.extractions[sid] for sid in self.suite.members("development")])
        record = {"review_kind": "synthetic_software_fixture", "review_disclosure": "Software control only",
                  "store": "eval", "release_id": "sha256-" + "a" * 64}
        with patch("eval.run_knowledge.importlib.import_module", return_value=SimpleNamespace(SourceKnowledgeStore=lambda path: store)):
            self.assertIs(_reviewed_partition(self.suite, "development", record), store)
            del store.candidate["sources"]["original_domain"]
            with self.assertRaisesRegex(ValueError, "mixes partitions"):
                _reviewed_partition(self.suite, "development", record)
        with patch("eval.run_knowledge.collect_c0") as collect:
            with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                run_offline(self.suite, MemoryWriter(), identity={}, reviewed_inputs={}, synthetic_review_diagnostic=True)
            collect.assert_not_called()
        with patch("eval.run_knowledge.EvidenceWriter") as writer, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--synthetic-review-diagnostic", "--copilot-experiment", "--plan-only"]), 1)
            writer.assert_not_called()
        with redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
            main(["--synthetic-review-diagnostic", "--reviewed-inputs", "unused.json"])
        self.assertEqual(error.exception.code, 2)

    def test_cli_diagnostic_remains_nonzero_pending_and_uses_a_distinct_run_directory(self):
        self.suite.manifest["exposure"] = "Mocked software control only"
        writer = MemoryWriter()
        with (
            patch("eval.run_knowledge.load_suite", return_value=self.suite),
            patch("eval.run_knowledge.code_identity", return_value={"software_control": True}),
            patch("eval.run_knowledge.EvidenceWriter", return_value=writer) as writer_type,
            patch("eval.run_knowledge.run_offline", return_value={"status": "pending_review"}) as offline,
            redirect_stdout(io.StringIO()),
        ):
            status = main(["--synthetic-review-diagnostic"])
        self.assertEqual(status, 2)
        self.assertEqual(writer_type.call_args.args[0].name, "source-first-software-review-1")
        self.assertIs(offline.call_args.kwargs["synthetic_review_diagnostic"], True)
        self.assertIsNone(offline.call_args.kwargs["reviewed_inputs"])


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = load_suite()

    def test_actual_c0_gets_only_each_exact_source_not_reference_labels(self):
        raw = (
            b"Artificial paper puzzle preamble.\r\n# Paper\r\nScope: Paper\r\n"
            b"Aliases: sheet\r\nKeep the page folded unless the flag is blue.\r\n"
        )
        suite = Suite(
            {"sources": [{"source_id": "adapter-control", "path": "generic-control.md"}]},
            {"not_for_runtime": "EVALUATOR_ONLY_SENTINEL"},
            {"adapter-control": raw},
        )
        runtime = importlib.import_module("triage_knowledge.source")
        with (
            patch.object(runtime, "extract_code", wraps=runtime.extract_code) as extract,
            patch("eval.run_knowledge.assess_extraction", return_value={"status": "pass", "fidelity": "pass"}) as grade,
        ):
            rows, extractions = collect_c0(suite)
        self.assertEqual(len(extract.call_args_list), 1)
        self.assertEqual(set(extractions), set(suite.sources))
        for call in extract.call_args_list:
            document = call.args[0]
            self.assertEqual(document.raw, suite.sources[document.source_id])
            self.assertNotIn(b"EVALUATOR_ONLY_SENTINEL", document.raw)
        self.assertEqual(grade.call_count, 1)
        self.assertEqual(rows[0]["source_id"], "adapter-control")
        self.assertEqual(rows[0]["assessment"]["status"], "pass", "Disclosed stub judgment, not corpus acceptance")

    def test_source_unit_metadata_translation_does_not_depend_on_group_ids(self):
        runtime = importlib.import_module("triage_knowledge.source")
        document = runtime.SourceDocument.from_bytes(
            b"Scope: Paper\r\nAliases: sheet\r\nDo not fold.\r\n# Qualification\r\nUnless the light is blue.\r\n",
            name="Synthetic adapter control", source_id="adapter-control",
        )
        units = document.units
        raw = {"groups": [
            {"group_id": "arbitrary-left", "unit_ids": [u["unit_id"] for u in units[:3]],
             "scopes": ["Paper"], "aliases": ["sheet"], "required_with": ["unrelated-name"],
             "evidence": [{"unit_id": u["unit_id"], "quote": u["text"]} for u in (units[0], units[1], units[4])]},
            {"group_id": "unrelated-name", "unit_ids": [u["unit_id"] for u in units[3:]],
             "scopes": [], "aliases": [], "required_with": [], "evidence": []},
        ]}
        extraction = runtime.validate_proposal(document, raw)
        adapted = adapt_extraction(extraction)
        self.assertEqual("".join(g["text"] for g in adapted["groups"]), document.raw.decode("utf-8"))
        self.assertEqual(adapted["metadata"]["aliases"][0]["target"], "Paper")
        self.assertEqual(adapted["metadata"]["links"][0]["to"][0]["start"], units[3]["start"])
        self.assertNotIn("arbitrary-left", str(adapted))
        raw["groups"][0]["scopes"] = []
        extraction = runtime.validate_proposal(document, raw)
        with self.assertRaisesRegex(ValueError, "alias target"):
            adapt_extraction(extraction)

    def test_actual_query_binding_contains_only_authorized_synthetic_csv_rows(self):
        query = query_rows(["Prism-Gates"])
        binding = query_binding(query).to_dict()
        self.assertEqual(binding["findings"], query["findings"])
        self.assertEqual(binding["registry"], query["registry"])
        self.assertEqual({row["kind"] for row in binding["manifest"]}, {"finding_input", "registry_input"})
        self.assertNotIn("required_atoms", str(query))
        unknown = query_rows([])
        self.assertEqual(next(iter(unknown["findings"].values()))["equipment_type"], "Unrecognized synthetic subject")

    def test_default_offline_keeps_all_twenty_four_queries_pending_without_review(self):
        UnreviewedStore.instances = []
        real_import = importlib.import_module

        def modules(name):
            if name == "triage_knowledge.source_store":
                return SimpleNamespace(SourceKnowledgeStore=UnreviewedStore)
            return real_import(name)

        writer = MemoryWriter()
        extractions = {
            sid: SimpleNamespace(document=SimpleNamespace(source_id=sid))
            for sid in self.suite.sources
        }
        source_rows = [
            {"source_id": sid, "assessment": {"status": "pass"},
             "observation": {"source_id": sid, "status": "software_stub"}}
            for sid in self.suite.sources
        ]
        with (
            patch("eval.run_knowledge.importlib.import_module", side_effect=modules),
            patch("eval.run_knowledge.collect_c0", return_value=(source_rows, extractions)) as collect,
            patch("eval.run_knowledge.assess_observations", return_value={"scope": "software-control", "overall": "pending"}),
            patch("eval.run_knowledge._runtime_source", side_effect=AssertionError("No frozen-source extraction in this unit test")),
        ):
            report = run_offline(self.suite, writer, identity={"scope": "software-test"})
        collect.assert_called_once()
        self.assertEqual(report["query_count"], 24)
        self.assertTrue(all(row["status"] == "needs_review" for row in report["query_assessments"].values()))
        self.assertEqual(len(UnreviewedStore.instances), 2)
        memberships = [set(store.members) for store in UnreviewedStore.instances]
        self.assertEqual(memberships, [self.suite.members("development"), self.suite.members("evaluation")])
        self.assertEqual(memberships[0] & memberships[1], {"original_domain"})
        self.assertFalse(report["selective_retrieval_qualified"])
        self.assertFalse(report["C1_qualified"])
        self.assertEqual(report["human_effort"], "unexecuted")
        self.assertEqual(report["overall"], "pending")
        for key, value in writer.values.items():
            if key.startswith("queries"):
                self.assertIsNone(value["result"])
                self.assertEqual(value["execution"], "not_run_pending_review")

    def test_result_adapter_preserves_exact_source_bytes_and_rejects_partial_failure(self):
        raw = {
            "status": "ok", "selection_mode": "conservative_expansion",
            "entries": {"opaque-address": {
                "source_id": "s", "source_sha256": "a" * 64,
                "spans": [{"start": 2, "end": 7}], "text": "not\r\n",
                "scopes": [], "aliases": [],
            }},
        }
        result = SimpleNamespace(to_dict=lambda: raw)
        adapted = adapt_result(result)
        self.assertEqual(adapted["selection_mode"], "conservative_expansion")
        self.assertEqual(adapted["entries"][0]["text"], "not\r\n")
        self.assertEqual(adapted["entries"][0]["spans"][0], {"source_id": "s", "start": 2, "end": 7})
        raw["selection_mode"] = "scoped"
        self.assertEqual(adapt_result(result)["selection_mode"], "scoped")
        for invalid in ("conservative_all_active", "unknown", None):
            raw["selection_mode"] = invalid
            with self.subTest(mode=invalid), self.assertRaisesRegex(ValueError, "selection mode"):
                adapt_result(result)
        raw.update(status="unavailable", error_code="knowledge_gap")
        with self.assertRaisesRegex(ValueError, "partial"):
            adapt_result(result)
        raw["entries"] = {}
        self.assertEqual(adapt_result(result), {"status": "unavailable", "error_code": "knowledge_gap", "entries": []})

    def test_experiment_has_thirteen_source_only_requests_and_development_smoke_prefix(self):
        from eval.knowledge_copilot import request_record

        reference = deepcopy(self.suite.reference)
        reference["not_for_provider"] = "EVALUATOR_EXPECTATION_SECRET"
        suite = replace(self.suite, reference=reference)
        identity = {"code": {"code_sha256": "f" * 64}}
        requests, documents, development, freeze = build_experiment(suite, identity)
        self.assertEqual(len(requests), 13)
        self.assertEqual(set(requests), set(suite.manifest["slot_ids"]))
        self.assertEqual(set(list(requests)[:5]), set(development))
        self.assertIn("original_domain.primary", development)
        self.assertTrue(all(slot.startswith("dev_") or slot == "original_domain.primary" for slot in development))
        profiles = {(r.model, r.system, canonical_hash(r.response_schema), r.reasoning_effort, r.timeout_seconds) for r in requests.values()}
        self.assertEqual(len(profiles), 1)
        for slot, request in requests.items():
            self.assertEqual((request.model, request.reasoning_effort, request.timeout_seconds), ("gpt-6-luna", "low", 90))
            self.assertNotIn("EVALUATOR_EXPECTATION_SECRET", request.user)
            self.assertNotIn("expected_scopes", request.user)
            sid = slot.rsplit(".", 1)[0]
            self.assertEqual(documents[sid].raw, suite.sources[sid])
            system, user, validator = request.prepared()
            self.assertTrue(system.startswith(request.system))
            self.assertEqual(user, request.user)
            self.assertEqual(validator.schema, request.response_schema)
            record = request_record(request)
            self.assertEqual(record["prepared_system"], system)
            self.assertEqual(record["prepared_user"], user)
            self.assertEqual(record["configuration"]["response_schema"], validator.schema)
        for sid in suite.manifest["repeat_source_ids"]:
            self.assertEqual(requests[f"{sid}.primary"].user, requests[f"{sid}.repeat1"].user)
            self.assertEqual(requests[f"{sid}.repeat1"].user, requests[f"{sid}.repeat2"].user)
        self.assertEqual(freeze["maximum_application_attempts"], 26)
        self.assertEqual(freeze["identity"], identity)
        self.assertFalse(freeze["C1_qualified"])

    def test_validation_callback_uses_actual_runtime_validation_before_accepting(self):
        runtime = importlib.import_module("triage_knowledge.source")
        raw = b"Artificial callback validation control.\r\n"
        suite = Suite(
            {"sources": [{"source_id": "callback-control", "path": "generic-callback.txt"}]},
            {"sources": [{
                "source_id": "callback-control", "aliases": [], "queries": [],
                "atoms": [{"id": "whole", "start": 0, "end": len(raw), "scopes": [], "requires": []}],
            }]},
            {"callback-control": raw},
        )
        document = document_for(suite, "callback-control")
        extraction = runtime.extract_code(document)
        callback = make_validator(suite, {"callback-control": document})
        with patch.object(runtime, "validate_proposal", wraps=runtime.validate_proposal) as validate:
            result = callback("callback-control.primary", extraction.proposal)
        self.assertEqual(validate.call_count, 1)
        self.assertTrue(result["accepted"])
        bad = deepcopy(extraction.proposal)
        bad["groups"][0]["unit_ids"] = ["u9999"]
        captured = MemoryWriter()
        callback = make_validator(suite, {"callback-control": document}, captured.write)
        with self.assertRaises(ValueError):
            callback("callback-control.primary", bad)
        self.assertFalse(next(iter(captured.values.values()))["accepted"])

    def test_authorization_failure_does_not_start_provider_or_write_evidence(self):
        writer = MemoryWriter()
        with self.assertRaisesRegex(ValueError, "allow-inference"):
            asyncio.run(run_experiment(self.suite, writer, identity={}, allow_inference=False))
        self.assertEqual(writer.values, {})
        with patch("eval.run_knowledge.EvidenceWriter") as writer_type, redirect_stdout(io.StringIO()):
            result = main(["--copilot-experiment"])
        self.assertEqual(result, 1)
        writer_type.assert_not_called()

    def test_code_identity_hash_binds_actual_files_and_revision(self):
        identity = code_identity()
        self.assertEqual(identity["code_sha256"], canonical_hash(identity["files_sha256"]))
        source_key = str(Path("triage_knowledge") / "source.py")
        self.assertEqual(identity["files_sha256"][source_key], hashlib.sha256((ROOT / source_key).read_bytes()).hexdigest())
        self.assertIn(str(Path("eval") / "run_knowledge.py"), identity["files_sha256"])


if __name__ == "__main__":
    unittest.main()
