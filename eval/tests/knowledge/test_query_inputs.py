"""Fixture-authoring and unchanged-selector controls, never model-quality evidence."""
from copy import deepcopy
import hashlib
import json
import shutil
from types import SimpleNamespace
import unittest
from uuid import uuid4

from eval.knowledge.evaluate import ROOT
from eval.knowledge.query_inputs import author_registry, load_registry_fixture
from eval.knowledge.run import ASSESSMENT_TIME, query_binding, query_rows
from triage_knowledge.retrieval import get_triage_knowledge, strategy_binding
from triage_knowledge.source import SourceDocument, extract_code, validate_proposal
from triage_knowledge.source_store import SourceKnowledgeStore


class RegistryFixtureTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "eval" / "results" / "knowledge" / "extraction" / ("registry-control-" + uuid4().hex)
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)

    def test_literal_authoring_preserves_provenance_ignores_fences_and_needs_no_heading(self):
        raw = (
            b"\xef\xbb\xbfScope: Copper widget\r\nEquipment: Silver widget\r\n"
            b"Aliases: Not an inventory declaration\r\n"
            b"```text\r\nScope: PretendScopes\r\n~~~\r\nEquipment: Still fenced\r\n```\r\n"
            b"Inline Scope: Not a field\r\nScope: \t\r\nScope: Copper widget\r\n"
        )
        inputs = [
            {"case_id": "known", "subject_types": ["Copper alias"], "expected_atoms": object()},
            {"case_id": "unknown", "subject_types": ["Unknown widget"]},
            {"case_id": "missing", "subject_types": []},
        ]
        fixture = author_registry({"synthetic": raw}, inputs)
        labels = {row["equipment_type"] for row in fixture["inventory"]}
        self.assertEqual(labels, {
            "Copper widget", "Silver widget", "Copper alias", "Unknown widget",
            "Unrecognized synthetic subject",
        })
        self.assertEqual(fixture, author_registry({"synthetic": raw}, reversed(inputs)))
        self.assertEqual(fixture, author_registry(
            {"synthetic": raw}, [{"case_id": q["case_id"], "subject_types": q["subject_types"]} for q in inputs],
        ))
        for item in fixture["inventory"]:
            for evidence in item["provenance"]:
                if evidence["kind"] == "source_declaration":
                    self.assertEqual(evidence["source_sha256"], hashlib.sha256(raw).hexdigest())
                    self.assertEqual(raw[evidence["start"]:evidence["end"]].decode("utf-8"), evidence["quote"])
        copper = next(row for row in fixture["inventory"] if row["equipment_type"] == "Copper widget")
        self.assertEqual(len(copper["provenance"]), 2)
        self.assertNotIn("expected_labels_used", fixture)
        self.assertFalse(fixture["expected_answer_sheet_used"])
        self.assertTrue(fixture["source_scope_labels_used"])
        self.assertFalse(fixture["inventory_independent_of_sources"])
        self.assertFalse(fixture["candidate_outputs_used"])
        with self.assertRaisesRegex(ValueError, "original domain"):
            author_registry({"original_domain": raw}, inputs)

    def test_loading_verifies_fixed_hash_and_authoring_without_dynamically_extending(self):
        sources = {f"source{i}": b"Scope: Copper widget\n" for i in range(8)}
        queries = {f"query{i}": {"subject_types": ["Copper widget"]} for i in range(24)}
        fixture = author_registry(sources, ({"case_id": key, **value} for key, value in queries.items()))
        path = self.root / "registry.json"
        raw = json.dumps(fixture).encode("utf-8")
        path.write_bytes(raw)
        manifest = {
            "version": "knowledge-extraction-reference-v1.4",
            "query_registry": str(path.relative_to(ROOT)), "query_registry_sha256": hashlib.sha256(raw).hexdigest(),
            "sources": [
                {"source_id": sid, "partition": "development" if i < 4 else "evaluation",
                 "sha256": hashlib.sha256(source).hexdigest()}
                for i, (sid, source) in enumerate(sources.items())
            ],
        }
        suite = SimpleNamespace(manifest=manifest, sources=sources, queries=queries)
        loaded = load_registry_fixture(suite)
        self.assertEqual(loaded["fixture"], fixture)
        original = path.read_bytes()
        sources["unregistered_control"] = b"Scope: Fracture\n"
        self.assertEqual(load_registry_fixture(suite)["fixture"], fixture)
        self.assertEqual(path.read_bytes(), original)
        altered = deepcopy(fixture)
        altered["inventory"][0]["provenance"][0]["quote"] = "Invented"
        changed = json.dumps(altered).encode("utf-8")
        path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            load_registry_fixture(suite)
        manifest["query_registry_sha256"] = hashlib.sha256(changed).hexdigest()
        with self.assertRaisesRegex(ValueError, "provenance"):
            load_registry_fixture(suite)

    def _extraction(self, other="Silver widget", *, c0=False):
        raw = f"# Copper\nScope: Copper widget\n# Other\nScope: {other}\n".encode("utf-8")
        document = SourceDocument.from_bytes(raw, name="Synthetic control", source_id="control")
        if c0:
            return extract_code(document)
        return validate_proposal(document, {"groups": [
            {"group_id": name, "unit_ids": [f"u{offset:04d}", f"u{offset + 1:04d}"],
             "scopes": [label], "aliases": [], "required_with": [],
             "evidence": [{"unit_id": f"u{offset + 1:04d}", "quote": f"Scope: {label}"}]}
            for name, label, offset in (("copper", "Copper widget", 1), ("other", other, 3))
        ]})

    def _retrieve(self, extraction, rows, subject, name):
        store = SourceKnowledgeStore(
            self.root / name, experimental_profile={"experiment_id": "registry-software-control"},
        )
        digest = store.create_draft([extraction])
        candidate, _ = store.load_draft()
        disclosure = "SOFTWARE ONLY control, NOT human or engineering approval"
        for item_id in sorted(candidate["items"]):
            digest = store.review_item(item_id, expected_digest=digest, reviewer=disclosure, reason=disclosure)
        release = store.publish(expected_digest=digest, author=disclosure, reviewer=disclosure,
                                reason=disclosure, reviewed_at=ASSESSMENT_TIME)
        query = query_rows([subject], shared_registry_rows=rows)
        result = get_triage_knowledge(
            store, query, knowledge_version=release, assessment_time=ASSESSMENT_TIME,
            expected_strategy=strategy_binding(), allowed_input_binding=query_binding(query), max_bytes=64000,
        )
        self.assertEqual(result.to_dict()["status"], "ok")
        return result

    def test_one_fixed_registry_enables_declared_types_but_preserves_unknown_and_fracture_guards(self):
        base = self._extraction()
        fixture = author_registry(
            {"inventory_source": base.document.raw},
            [{"case_id": "known", "subject_types": ["Copper widget"]},
             {"case_id": "unknown", "subject_types": ["Unknown widget"]}],
        )
        rows = fixture["registry"]
        before = deepcopy(rows)
        query = query_rows(["Copper widget"], shared_registry_rows=rows)
        self.assertEqual(len(query["findings"]), 1)
        self.assertEqual(query["registry"], rows)
        finding = next(iter(query["findings"].values()))
        self.assertEqual(rows[finding["equipment_id"]]["equipment_type"], "Copper widget")
        known = self._retrieve(base, rows, "Copper widget", "known")
        self.assertEqual(known.to_dict()["selection_mode"], "scoped")
        unknown = self._retrieve(base, rows, "Unknown widget", "unknown")
        self.assertEqual(unknown.to_dict()["selection_mode"], "conservative_expansion")
        fracture = self._retrieve(self._extraction("Fracture"), rows, "Copper widget", "fracture")
        self.assertEqual(fracture.to_dict()["selection_mode"], "conservative_expansion")
        equipment = self._retrieve(self._extraction("Pump"), rows, "Copper widget", "unregistered-equipment")
        self.assertEqual(equipment.to_dict()["selection_mode"], "conservative_expansion")
        self.assertNotIn("Fracture", {row["equipment_type"] for row in rows.values()})
        self.assertNotIn("Pump", {row["equipment_type"] for row in rows.values()})
        c0 = self._retrieve(self._extraction(c0=True), rows, "Copper widget", "c0")
        self.assertEqual(c0.to_dict()["selection_mode"], "conservative_expansion")
        self.assertEqual(c0.evidence["expansion_reason"], "conservative_source_context")
        self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
