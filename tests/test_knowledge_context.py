from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from tests.knowledge_support import (
    CUTOFF, KnowledgeCase, csv_bytes, equipment, finding, tables,
)
from triage_knowledge import (
    ContextError, EvaluationOverlay, KnowledgeError, TableSource,
    ContextBundle, build_context, canonical_context_bytes, serialize_context, verify_context,
)
from triage_knowledge.contracts import canonical_bytes, sha256


class ContextTests(KnowledgeCase):
    def test_complete_source_delivery_and_exact_index_locations(self):
        snapshot = self.publish()
        selected, registry = tables([finding(), finding("F-8002", "PMP-8002")],
                                    [equipment(), equipment("PMP-8002")])
        original_rows = deepcopy(selected.rows)
        with patch("builtins.open", side_effect=AssertionError("Context must not discover files")):
            bundle = build_context(selected, registry, snapshot, CUTOFF)
        data = bundle.to_dict()
        self.assertEqual(data["finding_ids"], ["F-8001", "F-8002"])
        self.assertEqual(data["payload"]["primary_equipment_by_finding"]["F-8002"], "PMP-8002")
        self.assertEqual(data["payload"]["domain"]["text"], snapshot.domain_bytes.decode())
        self.assertEqual(data["payload"]["registry"]["PMP-8002"]["engineer_comment"],
                         registry.rows[1]["engineer_comment"])
        self.assertEqual(selected.rows, original_rows)
        for address, item in data["source_index"].items():
            value = data
            for part in item["location"]:
                value = value[part]
            self.assertEqual(value, item["text"], address)
        self.assertIn("\u2713", serialize_context(bundle).decode())
        detached = bundle.payload
        detached["findings"].clear()
        self.assertEqual(len(bundle.payload["findings"]), 2)

    def test_row_reordering_changes_only_raw_provenance(self):
        snapshot = self.publish()
        findings = [finding(), finding("F-8002", "PMP-8002")]
        registry = [equipment(redundancy="N+1 (PMP-8002)"), equipment("PMP-8002")]
        first = build_context(*tables(findings, registry), snapshot, CUTOFF)
        second = build_context(*tables(findings[::-1], registry[::-1]), snapshot, CUTOFF)
        self.assertEqual(canonical_context_bytes(first), canonical_context_bytes(second))
        self.assertEqual(first.context_hash, second.context_hash)
        self.assertEqual(first.source_index, second.source_index)
        self.assertNotEqual(first.to_dict()["source_manifest"], second.to_dict()["source_manifest"])
        self.assertNotEqual(serialize_context(first), serialize_context(second))

    def test_missing_partner_is_a_factual_gap_not_a_failure_or_assessment(self):
        bundle = build_context(*tables(registry=[equipment(redundancy="N+1 (PMP-8002)")]),
                               self.publish(), CUTOFF)
        self.assertEqual(bundle.to_dict()["gaps"], [{
            "kind": "tagged_partner_not_in_registry", "subject_equipment_id": "PMP-8001",
            "partner_equipment_id": "PMP-8002", "finding_ids": ["F-8001"],
            "source_refs": ["equipment:PMP-8001:redundancy"],
        }])
        for redundancy in ("None", "Voted 2oo3", "Yes (bypass available)", "N+1 partner unspecified"):
            with self.subTest(redundancy=redundancy):
                value = build_context(*tables(registry=[equipment(redundancy=redundancy)]),
                                      self.store.resolve_knowledge(bundle.to_dict()["knowledge_version"]), CUTOFF)
                self.assertEqual(value.to_dict()["gaps"], [])

    def test_primary_mapping_duplicates_and_cutoff_fail_visibly(self):
        snapshot = self.publish()
        scenarios = [
            (*tables([finding(equipment="PMP-8999")]), CUTOFF),
            (*tables([finding(), finding()]), CUTOFF),
            (*tables(), "2024-01-01T00:00:00+00:00"),
            (*tables(), "2026-01-01"),
        ]
        for selected, registry, cutoff in scenarios:
            with self.subTest(cutoff=cutoff, rows=len(selected.rows)), self.assertRaises(ContextError):
                build_context(selected, registry, snapshot, cutoff)
        self.assertEqual(build_context(*tables(), snapshot, CUTOFF).finding_ids, ("F-8001",))

    def test_csv_shape_and_role_failures(self):
        for raw in (b"a,a\r\nx,y\r\n", b"a,b\r\nx\r\n", b"a,b\r\nx,y,z\r\n", b"a,b\r\n"):
            with self.subTest(raw=raw), self.assertRaises(KnowledgeError):
                TableSource.from_bytes(raw, source_id="findings", kind="finding_input")
        selected, registry = tables()
        for bad in (replace(selected, kind="registry_input"), replace(selected, source_id="domain")):
            with self.subTest(source=bad.source_id), self.assertRaises(ContextError):
                build_context(bad, registry, self.publish_or_resolve(), CUTOFF)

    def publish_or_resolve(self):
        versions = list((self.store.root / "releases").glob("*.json"))
        return (self.store.resolve_knowledge(versions[0].stem) if versions else self.publish())

    def test_pinned_snapshot_and_bundle_survive_new_draft_and_release(self):
        snapshot = self.publish()
        before = build_context(*tables(), snapshot, CUTOFF)
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["guidance"] = "A revised general evidence instruction."
        self.digest = self.store.save_draft(candidate, expected_digest=self.digest)
        newer = self.publish()
        after = build_context(*tables(), snapshot, CUTOFF)
        self.assertEqual(before.encoded, after.encoded)
        self.assertNotEqual(before.context_hash, build_context(*tables(), newer, CUTOFF).context_hash)

    def test_isolated_overlay_valid_control_and_normal_rejections(self):
        snapshot = self.publish()
        raw = canonical_bytes({"scope": "Synthetic pump mechanism", "dimension": "likelihood",
                               "guidance": "Use the declared isolated experiment convention."})
        overlay = EvaluationOverlay("probe-policy", raw, sha256(raw))
        selected, registry = tables(input_kind="evaluation_input")
        probe = build_context(selected, registry, snapshot, CUTOFF,
                              purpose="evaluation_probe", overlay_ref=overlay)
        self.assertEqual(probe.to_dict()["purpose"], "evaluation_probe")
        self.assertEqual(probe.payload["evaluation_overlay"]["sha256"], sha256(raw))
        self.assertIn("overlay:probe-policy:guidance", probe.source_index)
        self.assertIn("evaluation_input", [x["kind"] for x in probe.to_dict()["source_manifest"]])
        for purpose, value, findings in [
            ("normal", overlay, tables()[0]), ("normal", None, selected),
            ("evaluation_probe", None, selected), ("unknown", overlay, selected),
        ]:
            with self.subTest(purpose=purpose, overlay=value), self.assertRaises(ContextError):
                build_context(findings, registry, snapshot, CUTOFF, purpose=purpose, overlay_ref=value)
        with self.assertRaises(KnowledgeError):
            EvaluationOverlay("probe-policy", raw, "0" * 64)
        revised_raw = raw.replace(b"declared isolated", b"revised isolated")
        revised = EvaluationOverlay("probe-policy", revised_raw, sha256(revised_raw))
        changed = build_context(selected, registry, snapshot, CUTOFF,
                                purpose="evaluation_probe", overlay_ref=revised)
        self.assertNotEqual(probe.context_hash, changed.context_hash)
        self.assertEqual(probe.to_dict()["knowledge_version"], changed.to_dict()["knowledge_version"])

    def test_semantic_canonical_projection_has_independent_exact_bytes(self):
        data = {
            "contract_version": 1, "payload": {}, "source_index": {}, "finding_ids": [],
            "knowledge_version": "fixture", "assessment_time": CUTOFF, "gaps": [], "purpose": "normal",
            "source_manifest": [{"source_id": "findings", "kind": "finding_input",
                                 "version": None, "sha256": "0" * 64, "locator": "different.csv"}],
        }
        expected = (
            b'{"assessment_time":"2026-01-01T00:00:00+00:00","contract_version":1,'
            b'"finding_ids":[],"gaps":[],"knowledge_version":"fixture","payload":{},'
            b'"purpose":"normal","source_index":{},"source_manifest":[{"kind":"finding_input",'
            b'"source_id":"findings","version":null}]}'
        )
        self.assertEqual(canonical_context_bytes(data), expected)
        data["source_manifest"][0]["sha256"] = "1" * 64
        self.assertEqual(canonical_context_bytes(data), expected)
        data["contract_version"] = True
        with self.assertRaises(KnowledgeError):
            canonical_context_bytes(data)

    def test_serializer_rejects_disguised_probe_unknown_gap_and_bad_index(self):
        data = build_context(*tables(), self.publish(), CUTOFF).to_dict()
        mutations = [
            lambda x: x["source_manifest"][0].update(kind="evaluation_overlay"),
            lambda x: x["gaps"].append({"kind": "unknown", "subject_equipment_id": "PMP-8001",
                                        "partner_equipment_id": "PMP-8002", "finding_ids": ["F-8001"],
                                        "source_refs": ["equipment:PMP-8001:redundancy"]}),
            lambda x: x["source_index"]["finding:F-8001:finding_description"].update(text="Fabricated."),
        ]
        for mutate in mutations:
            changed = deepcopy(data)
            mutate(changed)
            changed["context_hash"] = sha256(canonical_context_bytes(changed))
            with self.subTest(mutation=mutate), self.assertRaises(KnowledgeError):
                serialize_context(changed)

    def test_missing_partner_gap_cannot_be_removed_or_duplicated_then_rehashed(self):
        data = build_context(*tables(registry=[equipment(redundancy="N+1 (PMP-8002)")]),
                             self.publish(), CUTOFF).to_dict()
        for gaps in ([], data["gaps"] * 2):
            changed = {**data, "gaps": gaps}
            changed["context_hash"] = sha256(canonical_context_bytes(changed))
            with self.subTest(gaps=gaps), self.assertRaises(KnowledgeError):
                serialize_context(changed)

    def test_anchored_verifier_rejects_rehashed_forged_provenance_and_knowledge(self):
        snapshot = self.publish()
        selected, registry = tables()
        bundle = build_context(selected, registry, snapshot, CUTOFF)
        verify_context(bundle, snapshot, selected, registry, CUTOFF)
        mutations = [
            lambda x: x["source_manifest"][0].update(locator="forged-locator"),
            lambda x: x["source_manifest"][1].update(sha256="0" * 64),
            lambda x: x["payload"]["domain"].update(text="Forged source."),
            lambda x: x["payload"]["managed_knowledge"].update(active_guidance_ids=[]),
            lambda x: x["payload"]["managed_knowledge"].update(guidance=[]),
            lambda x: x.update(knowledge_version="sha256-" + "0" * 64),
            lambda x: x.update(source_index={}),
            lambda x: x["payload"]["findings"]["F-8001"].update(expected_urgency="9"),
        ]
        for mutate in mutations:
            data = bundle.to_dict()
            mutate(data)
            data["context_hash"] = sha256(canonical_context_bytes(data))
            forged = ContextBundle(canonical_bytes(data))
            with self.subTest(mutation=mutate), self.assertRaises(KnowledgeError):
                verify_context(forged, snapshot, selected, registry, CUTOFF)

    def test_blank_evidence_and_unexpected_answer_columns_fail_before_context(self):
        snapshot = self.publish()
        for changed in ({**finding(), "finding_description": " "},
                        {**finding(), "expected_urgency": "9"}):
            selected = TableSource.from_bytes(csv_bytes(tuple(changed), [changed]), source_id="findings",
                                               kind="finding_input")
            with self.subTest(fields=list(changed)), self.assertRaises(ContextError):
                build_context(selected, tables()[1], snapshot, CUTOFF)
