"""Known perfect/adversarial grader controls, NOT knowledge-module observations."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import unittest
from unittest.mock import patch

from eval.knowledge_eval import (
    Suite, assess_attempts, assess_boundary_case, assess_effort,
    assess_extraction, assess_observations, assess_repeats, assess_retrieval,
    atom_span, calibrate_semantic_review, canonical_query_hash, case_expectation,
    interval_bytes, load_suite, overlap_bytes, union_intervals,
)


def full_span(suite, sid):
    return {"source_id": sid, "start": 0, "end": len(suite.sources[sid])}


def proposal(suite, sid):
    """Independently assembled positive control from evaluator-only annotations."""
    data = suite.sources[sid]
    source = next(s for s in suite.reference["sources"] if s["source_id"] == sid)
    atoms = {a["id"]: a for a in source["atoms"]}
    cuts = sorted({0, len(data)} | {a[key] for a in atoms.values() for key in ("start", "end")})
    groups = [
        {"spans": [{"source_id": sid, "start": start, "end": end}], "text": data[start:end].decode("utf-8")}
        for start, end in zip(cuts, cuts[1:])
    ]
    return {
        "source_id": sid, "source_sha256": hashlib.sha256(data).hexdigest(),
        "status": "accepted", "groups": groups,
        "metadata": {
            "scopes": [
                {"value": scope, "spans": [atom_span(sid, atom)], "evidence": [full_span(suite, sid)]}
                for atom in atoms.values() for scope in atom["scopes"]
            ],
            "aliases": [
                {"value": a["value"], "target": a["target"], "evidence": [full_span(suite, sid)]}
                for a in source["aliases"]
            ],
            "links": [
                {"from": [atom_span(sid, atom)], "to": [atom_span(sid, atoms[other])],
                 "evidence": [full_span(suite, sid)]}
                for atom in atoms.values() for other in atom["requires"]
            ],
        },
    }


def retrieval(suite, spans, mode="scoped"):
    entries = []
    for span in spans:
        sid, start, end = span["source_id"], span["start"], span["end"]
        entries.append({
            "spans": [span], "text": suite.sources[sid][start:end].decode("utf-8"),
            "source_sha256": hashlib.sha256(suite.sources[sid]).hexdigest(),
        })
    return {"status": "ok", "selection_mode": mode, "entries": entries}


def perfect_retrieval(suite, case_id):
    expected = case_expectation(suite, case_id)
    if expected["query"]["kind"] == "unknown":
        return retrieval(suite, [full_span(suite, sid) for sid in expected["sources"]], "conservative_expansion")
    return retrieval(suite, [atom_span(suite.atoms[key]["source_id"], suite.atoms[key]) for key in expected["required"]])


def human_control_records(suite, c0_count=8, c1_count=0):
    """Disclosed synthetic declarations; no human activity is claimed."""
    records, hashes = [], {}
    for index, schedule in enumerate(suite.manifest["review_schedule"]):
        sid = schedule["source_id"]
        atom = next(a["id"] for a in suite.atoms.values() if a["source_id"] == sid)
        hashes[sid] = {"C0": "d" * 64, "C1": "e" * 64}
        for strategy, total in (("C0", c0_count), ("C1", c1_count)):
            count = total // 4 + (index < total % 4)
            operations = [
                {"kind": "scope_add", "atoms": [atom], "value": f"self-test correction {number}"}
                for number in range(count)
            ]
            records.append({
                "source_id": sid, "strategy": strategy,
                "reviewer_id": f"self-test-{schedule[strategy]}", "reviewer_slot": schedule[strategy],
                "order": schedule["order"], "kind": "human", "blinded": True,
                "answer_sheet_exposed": False, "unblinded": False,
                "recognizability": "Synthetic grader control; no actual humans.",
                "candidate_sha256": hashes[sid][strategy], "operations": operations + deepcopy(operations),
            })
    return records, hashes


class GroupGraphControlTests(unittest.TestCase):
    """Inline grader controls only; no frozen corpus or production extraction."""

    def control(self, *, preamble=False, whole=False, scopes=True, required=True):
        raw = b"PFX\nALPHA---MID\nBETA----" if preamble else b"ALPHA---BETA----"
        a_start, a_end, b_start = (4, 12, 16) if preamble else (0, 8, 8)
        atoms = [
            {"id": "a", "start": a_start, "end": a_end, "scopes": ["ALPHA"] if scopes else [],
             "requires": ["b"] if required else [], "roles": ["rule"]},
            {"id": "b", "start": b_start, "end": len(raw), "scopes": ["BETA"] if scopes else [],
             "requires": ["a"] if required else [], "roles": ["exception"]},
        ]
        if whole:
            atoms = [{"id": "whole", "start": 0, "end": len(raw), "scopes": [], "requires": [], "roles": ["global"]}]
        suite = Suite(
            {"sources": [{"source_id": "control", "partition": "evaluation"}],
             "efficiency_case_ids": [], "thresholds": {"each_scoped_irrelevant_byte_reduction": 0.2}},
            {"sources": [{
                "source_id": "control", "atoms": atoms, "aliases": [],
                "queries": [{"id": "control.scoped", "kind": "scoped", "subject_types": ["ALPHA"]}],
            }]},
            {"control": raw},
        )
        return suite, proposal(suite, "control")

    @staticmethod
    def span(start, end):
        return {"source_id": "control", "start": start, "end": end}

    def repartition(self, suite, value, cuts):
        raw = suite.sources["control"]
        value["groups"] = [
            {"spans": [self.span(start, end)], "text": raw[start:end].decode("utf-8")}
            for start, end in zip(cuts, cuts[1:])
        ]

    def link(self, suite, value, left, right, evidence_spans=None):
        value["metadata"]["links"].append({
            "from": [self.span(*left)], "to": [self.span(*right)],
            "evidence": evidence_spans or [full_span(suite, "control")],
        })

    def scope(self, suite, value, label, start, end):
        value["metadata"]["scopes"].append({
            "value": label, "spans": [self.span(start, end)],
            "evidence": [full_span(suite, "control")],
        })

    def test_atomless_multihop_nodes_connect_whole_atoms_across_actual_groups(self):
        suite, value = self.control(preamble=True)
        self.repartition(suite, value, [0, 4, 8, 12, 16, 24])
        value["metadata"]["links"] = []
        # A is split across two groups. Preamble and MID have no reference atoms.
        for left, right in [((0, 1), (12, 13)), ((12, 13), (4, 5)),
                            ((12, 13), (8, 9)), ((12, 13), (16, 17))]:
            self.link(suite, value, left, right)
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["context"]["recall"], 1)
        self.assertEqual(result["group_graph"]["component_count"], 1)
        self.assertEqual(result["group_graph"]["components"][0]["source_bytes"], {"control": 24})
        self.assertEqual(result["group_graph"]["components"][0]["whole_atom_ids"], ["a", "b"])
        value["groups"].reverse()
        value["metadata"]["links"].reverse()
        reordered = assess_extraction(suite, value)
        self.assertEqual(reordered["metrics"], result["metrics"])
        self.assertEqual(reordered["group_graph"], result["group_graph"])

    def test_whole_source_atom_does_not_require_atom_bearing_link_endpoints(self):
        suite, value = self.control(preamble=True, whole=True)
        self.repartition(suite, value, [0, 4, 8, 12, 16, 24])
        for target in (4, 8, 12, 16):
            self.link(suite, value, (0, 1), (target, target + 1))
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["group_graph"]["components"][0]["whole_atom_ids"], ["whole"])
        self.assertEqual(result["metrics"]["context"]["expected"], 0)
        self.assertIsNone(result["metrics"]["context"]["precision"])

    def test_single_byte_endpoint_does_not_promote_a_fragment_to_a_whole_atom(self):
        suite, value = self.control()
        self.repartition(suite, value, [0, 4, 8, 16])
        # B is scoped and complete. A has a disconnected second half.
        value["metadata"]["scopes"] = [value["metadata"]["scopes"][1]]
        value["metadata"]["links"] = []
        self.link(suite, value, (0, 1), (8, 9))
        result = assess_extraction(suite, value)
        self.assertEqual(result["fidelity"], "pass")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["metrics"]["context"]["recall"], 0)
        self.assertIn("a", result["group_graph"]["atoms_not_whole_in_one_component"])
        self.assertEqual(result["critical_errors"]["detached_scoped_context_pairs"], [("a", "b")])
        # Connecting the actual remaining group supplies the missing whole bytes.
        self.link(suite, value, (4, 5), (0, 1))
        self.assertEqual(assess_extraction(suite, value)["status"], "pass")

    def test_single_byte_endpoint_can_bind_a_whole_actual_group_not_just_that_byte(self):
        suite, value = self.control()
        value["metadata"]["links"] = []
        self.link(suite, value, (0, 1), (8, 9))
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["group_graph"]["components"][0]["source_bytes"]["control"], 16)

    def test_evidence_and_shared_atom_or_source_never_create_graph_edges(self):
        suite, value = self.control(preamble=True)
        self.repartition(suite, value, [0, 4, 12, 16, 24])
        value["metadata"]["links"] = []
        # Evidence cites everything, but the declared edge reaches only preamble/A.
        self.link(suite, value, (0, 1), (4, 5))
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["group_graph"]["component_count"], 3)
        self.assertEqual(result["metrics"]["context"]["observed"], 0)
        suite, value = self.control(scopes=False)
        self.repartition(suite, value, [0, 4, 8, 16])
        value["metadata"]["links"] = []
        result = assess_extraction(suite, value)
        self.assertEqual(result["group_graph"]["component_count"], 3)
        self.assertIn("a", result["group_graph"]["atoms_not_whole_in_one_component"])
        self.assertEqual(result["metrics"]["context"]["observed"], 0)
        self.assertEqual(result["status"], "pass", "Both general remains repair-only, not an invented edge")
        self.assertEqual(result["repair_counts"]["context_add"], 1)

    def test_connected_correct_partial_scope_is_repair_not_an_unsupported_claim(self):
        suite, value = self.control(scopes=False, required=False)
        suite.reference["sources"][0]["atoms"][0]["scopes"] = ["ALPHA"]
        self.repartition(suite, value, [0, 4, 8, 16])
        self.scope(suite, value, "ALPHA", 0, 4)
        self.link(suite, value, (0, 1), (4, 5))
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass", result)
        self.assertFalse(result["accepted_wrong_critical"])
        self.assertEqual(result["repair_counts"]["scope_add"], 1)
        self.assertEqual(result["metrics"]["scope"]["recall"], 0)
        self.assertEqual(result["incomplete_scope_byte_facts"][0]["claimed_bytes"], 4)
        self.assertEqual(result["critical_errors"]["unsupported_scope_facts"], [])
        self.assertEqual(result["critical_errors"]["disconnected_scoped_atoms"], [])

    def test_unsupported_partial_scope_on_general_atom_is_critical_despite_co_return(self):
        suite, value = self.control(scopes=False, required=False)
        self.scope(suite, value, "ALPHA", 0, 1)
        self.link(suite, value, (0, 1), (8, 9))
        result = assess_extraction(suite, value)
        self.assertEqual(result["fidelity"], "pass")
        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["accepted_wrong_critical"])
        self.assertEqual(result["critical_errors"]["unsupported_scope_facts"], [("a", "alpha")])
        self.assertEqual(result["incomplete_scope_byte_facts"][0]["claimed_bytes"], 1)

    def test_disconnected_restrictively_scoped_atom_is_critical_even_with_full_scope_bytes(self):
        suite, value = self.control(scopes=False, required=False)
        suite.reference["sources"][0]["atoms"][0]["scopes"] = ["ALPHA"]
        self.repartition(suite, value, [0, 4, 8, 16])
        self.scope(suite, value, "ALPHA", 0, 8)
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["critical_errors"]["unsupported_scope_facts"], [])
        self.assertEqual(result["critical_errors"]["disconnected_scoped_atoms"], ["a"])
        self.assertEqual(result["metrics"]["scope"]["recall"], 0)

    def test_full_scope_union_across_connected_groups_is_credited_without_inventing_labels(self):
        suite, value = self.control(scopes=False, required=False)
        suite.reference["sources"][0]["atoms"][0]["scopes"] = ["ALPHA"]
        self.repartition(suite, value, [0, 4, 8, 16])
        self.scope(suite, value, "ALPHA", 0, 4)
        self.scope(suite, value, "ALPHA", 4, 8)
        self.link(suite, value, (0, 1), (4, 5))
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["scope"]["recall"], 1)
        self.assertEqual(result["repair_counts"]["scope_add"], 0)
        value["metadata"]["scopes"] = []
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["metrics"]["scope"]["observed"], 0)
        self.assertEqual(result["repair_counts"]["scope_add"], 1)

    def test_nonempty_partial_scope_label_set_remains_critical(self):
        suite, value = self.control(required=False)
        suite.reference["sources"][0]["atoms"][0]["scopes"].append("BETA")
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "fail")
        self.assertIn("a", result["critical_errors"]["nonempty_incomplete_scope_atoms"])
        self.assertEqual(result["critical_errors"]["unsupported_scope_facts"], [])

    def test_overclosure_is_counted_not_mislabeled_as_engineering_entailment(self):
        suite, value = self.control(required=False)
        self.link(suite, value, (0, 1), (8, 9))
        result = assess_extraction(suite, value)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["group_graph"]["overclosure_pair_count"], 1)
        self.assertEqual(result["metrics"]["context"]["observed"], 1)
        self.assertIsNone(result["metrics"]["context"]["recall"])
        self.assertEqual(result["metrics"]["context"]["precision"], 0)

    def test_bad_source_hash_unknown_source_empty_and_out_of_range_endpoints_fail(self):
        for mutation in ("hash", "source", "empty", "range"):
            suite, value = self.control()
            if mutation == "hash":
                value["source_sha256"] = "0" * 64
            elif mutation == "source":
                suite.sources["other"] = suite.sources["control"]
                value["metadata"]["links"][0]["from"][0]["source_id"] = "other"
            elif mutation == "empty":
                value["metadata"]["links"][0]["from"] = []
            else:
                value["metadata"]["links"][0]["from"][0]["end"] = 17
            with self.subTest(mutation=mutation):
                self.assertEqual(assess_extraction(suite, value)["status"], "fail")

    def test_graph_does_not_relax_unsupported_scope_alias_or_exact_text_controls(self):
        suite, original = self.control()
        for mutation in ("scope", "alias", "text", "duplicate_group", "gap"):
            value = deepcopy(original)
            if mutation == "scope":
                value["metadata"]["scopes"][0]["value"] = "BETA"
            elif mutation == "alias":
                value["metadata"]["aliases"].append({
                    "value": "ALPHA", "target": "BETA", "evidence": [full_span(suite, "control")],
                })
            elif mutation == "text":
                value["groups"][0]["text"] += "invented"
            elif mutation == "duplicate_group":
                value["groups"].append(deepcopy(value["groups"][0]))
            else:
                value["groups"].pop(0)
            with self.subTest(mutation=mutation):
                self.assertEqual(assess_extraction(suite, value)["status"], "fail")

    def test_fragment_duplicates_and_byte_gaps_still_cannot_satisfy_retrieval(self):
        suite, _ = self.control()
        fragments = [self.span(0, 4), self.span(0, 4), self.span(8, 16)]
        result = assess_retrieval(suite, "control.scoped", retrieval(suite, fragments))
        self.assertEqual(result["status"], "fail")
        self.assertLess(result["recall"], 1)
        fragments.append(self.span(5, 8))
        self.assertEqual(assess_retrieval(suite, "control.scoped", retrieval(suite, fragments))["status"], "fail")
        fragments.append(self.span(4, 5))
        self.assertEqual(assess_retrieval(suite, "control.scoped", retrieval(suite, fragments))["status"], "pass")

    def test_missing_negation_reversed_direction_and_unresolved_remain_nonpasses(self):
        raw = b"Do not fold. Higher reserve means lower drift.\n"
        suite = Suite({}, {"sources": [{
            "source_id": "control", "aliases": [], "queries": [],
            "atoms": [{"id": "rule", "start": 0, "end": len(raw), "scopes": [], "requires": []}],
        }]}, {"control": raw})
        original = proposal(suite, "control")
        for old, new in (("not ", ""), ("lower drift", "higher drift")):
            value = deepcopy(original)
            value["groups"][0]["text"] = value["groups"][0]["text"].replace(old, new)
            self.assertEqual(assess_extraction(suite, value)["fidelity"], "fail")
        suite.reference["sources"][0]["atoms"][0]["judgment"] = "needs_review"
        result = assess_extraction(suite, original)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["atom_count"], 1)
        self.assertEqual(result["unresolved_atom_count"], 1)

    def test_generic_runtime_ids_adapter_spans_and_independent_atom_graph_agree(self):
        from triage_knowledge.source import SourceDocument, validate_proposal
        from eval.run_knowledge import adapt_extraction

        pieces = [
            b"Preamble for a paper puzzle.\n",
            b"ALPHA: Do not fold the first panel.\n",
            b"ALPHA: Keep the second panel flat.\n",
            b"Bridge heading only.\n",
            b"BETA: Unless the card is blue, hold the exception.\n",
        ]
        raw = b"".join(pieces)
        document = SourceDocument.from_bytes(raw, name="Inline adapter control", source_id="real-control")
        names = ["arbitrary-root", "first-fragment", "second-fragment", "bridge-only", "exception"]
        targets = {0: [3], 3: [1, 2, 4]}
        submitted = {"groups": [
            {
                "group_id": name, "unit_ids": [f"u{index + 1:04d}"],
                "scopes": ["ALPHA"] if index in (1, 2) else ["BETA"] if index == 4 else [],
                "aliases": [], "required_with": [names[i] for i in targets.get(index, [])],
                "evidence": [
                    {"unit_id": f"u{i + 1:04d}", "quote": pieces[i].decode("utf-8")}
                    for i in [index] + targets.get(index, [])
                ],
            } for index, name in enumerate(names)
        ]}
        normalized = adapt_extraction(validate_proposal(document, submitted))
        # Reference offsets come from independently authored byte pieces, not runtime units.
        a_start, a_end, b_start = len(pieces[0]), sum(map(len, pieces[:3])), sum(map(len, pieces[:4]))
        suite = Suite({}, {"sources": [{
            "source_id": "real-control", "aliases": [], "queries": [],
            "atoms": [
                {"id": "rule", "start": a_start, "end": a_end, "scopes": ["ALPHA"], "requires": ["exception"]},
                {"id": "exception", "start": b_start, "end": len(raw), "scopes": ["BETA"], "requires": ["rule"]},
            ],
        }]}, {"real-control": raw})
        result = assess_extraction(suite, normalized)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["metrics"]["scope"]["recall"], 1)
        self.assertEqual(result["metrics"]["context"]["recall"], 1)
        self.assertEqual(result["group_graph"]["component_count"], 1)
        self.assertEqual(result["group_graph"]["components"][0]["source_bytes"], {"real-control": len(raw)})
        self.assertNotIn("first-fragment", str(normalized))
        for index, group in enumerate(normalized["groups"]):
            self.assertEqual(group["spans"], [{
                "source_id": "real-control", "start": sum(map(len, pieces[:index])),
                "end": sum(map(len, pieces[:index + 1])),
            }])


class KnowledgeGraderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = load_suite()

    def test_frozen_inventory_perfect_controls_are_not_system_acceptance(self):
        self.assertEqual(len(self.suite.queries), 24)
        self.assertEqual(len(self.suite.manifest["efficiency_case_ids"]), 8)
        self.assertEqual(len(self.suite.manifest["unknown_case_ids"]), 4)
        for sid in self.suite.sources:
            with self.subTest(source=sid):
                result = assess_extraction(self.suite, proposal(self.suite, sid))
                self.assertEqual(result["status"], "pass", result)
        for case_id in self.suite.queries:
            with self.subTest(case=case_id):
                result = assess_retrieval(self.suite, case_id, perfect_retrieval(self.suite, case_id))
                self.assertEqual(result["status"], "pass", result)
        report = assess_observations(self.suite, {})
        self.assertEqual(report["overall"], "pending")
        self.assertEqual(report["C1_qualification"], "unqualified")
        self.assertEqual(report["human_effort"]["status"], "needs_review")

    def test_missing_negation_and_reversed_direction_fail_exact_materialization(self):
        for old, new in (("Do not open", "Do open"), ("lower flicker", "higher flicker")):
            value = proposal(self.suite, "eval_prism")
            group = next(g for g in value["groups"] if old in g["text"])
            group["text"] = group["text"].replace(old, new)
            report = assess_extraction(self.suite, value)
            self.assertEqual(report["status"], "fail")
            self.assertEqual(report["fidelity"], "fail")
            self.assertFalse(report["accepted_wrong_critical"], "invalid outputs are not accepted-wrong semantics")

    def test_detached_exception_semantic_error_despite_complete_source_partition(self):
        value = proposal(self.suite, "eval_prism")
        value["metadata"]["links"] = []
        report = assess_extraction(self.suite, value)
        self.assertEqual(report["fidelity"], "pass")
        self.assertEqual(report["semantic"], "fail")
        self.assertTrue(report["accepted_wrong_critical"])
        self.assertLess(report["metrics"]["context"]["recall"], 1)

    def test_unsupported_alias_relation_is_not_just_literal_presence(self):
        value = proposal(self.suite, "eval_prism")
        # Both literals are in the source; their claimed equivalence is false.
        value["metadata"]["aliases"][0]["target"] = "Copper Wheels"
        report = assess_extraction(self.suite, value)
        self.assertEqual(report["fidelity"], "pass")
        self.assertTrue(report["accepted_wrong_critical"])
        self.assertEqual(report["semantic"], "fail")
        value["metadata"]["aliases"][0]["value"] = "invented synonym"
        self.assertEqual(assess_extraction(self.suite, value)["status"], "fail")

    def test_empty_scope_omission_is_repair_not_unsupported_restriction(self):
        value = proposal(self.suite, "eval_prism")
        value["metadata"]["scopes"].pop(0)
        report = assess_extraction(self.suite, value)
        self.assertEqual(report["semantic"], "pass")
        self.assertFalse(report["accepted_wrong_critical"])
        self.assertTrue(report["repair_required"])
        self.assertEqual(report["repair_counts"]["scope_add"], 1)
        value["metadata"]["scopes"][0]["value"] = "Copper Wheels"
        report = assess_extraction(self.suite, value)
        self.assertEqual(report["semantic"], "fail")
        self.assertTrue(report["accepted_wrong_critical"])

    def test_empty_metadata_and_both_general_context_are_safe_repair_diagnostics(self):
        value = proposal(self.suite, "eval_prism")
        value["metadata"] = {"scopes": [], "aliases": [], "links": []}
        report = assess_extraction(self.suite, value)
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["accepted_wrong_critical"])
        self.assertEqual(report["repair_counts"], {"scope_add": 5, "alias_add": 2, "context_add": 3})
        self.assertIsNone(report["metrics"]["scope"]["precision"])
        self.assertEqual(report["metrics"]["scope"]["recall"], 0)
        # A scoped endpoint can now be lost independently of its unlinked exception.
        original = proposal(self.suite, "eval_prism")
        value["metadata"]["scopes"] = original["metadata"]["scopes"][:1]
        self.assertTrue(assess_extraction(self.suite, value)["accepted_wrong_critical"])

    def test_nonempty_partial_scope_is_critical_even_without_unsupported_assignment(self):
        reference = deepcopy(self.suite.reference)
        source = next(s for s in reference["sources"] if s["source_id"] == "eval_prism")
        source["atoms"][0]["scopes"].append("Copper Wheels")
        suite = replace(self.suite, reference=reference)
        report = assess_extraction(suite, proposal(self.suite, "eval_prism"))
        self.assertEqual(report["metrics"]["scope"]["unsupported"], [])
        self.assertIn("open", report["critical_errors"]["nonempty_incomplete_scope_atoms"])
        self.assertEqual(report["status"], "fail")

    def test_omitted_alias_is_diagnostic_and_casefold_does_not_rewrite_evidence(self):
        value = proposal(self.suite, "eval_prism")
        value["metadata"]["aliases"].pop()
        report = assess_extraction(self.suite, value)
        self.assertEqual(report["semantic"], "pass")
        self.assertEqual(report["repair_counts"]["alias_add"], 1)
        reference = deepcopy(self.suite.reference)
        source = next(s for s in reference["sources"] if s["source_id"] == "eval_prism")
        for atom in source["atoms"]:
            atom["scopes"] = [s.upper() for s in atom["scopes"]]
        for alias in source["aliases"]:
            alias["value"] = alias["value"].upper()
            alias["target"] = alias["target"].upper()
        suite = replace(self.suite, reference=reference)
        self.assertEqual(assess_extraction(suite, proposal(self.suite, "eval_prism"))["status"], "pass")
        value = proposal(self.suite, "eval_prism")
        value["metadata"]["scopes"][0]["value"] = "PRISM-GATES"
        # It compares equal semantically but is not a literal in the cited source.
        self.assertEqual(assess_extraction(self.suite, value)["status"], "fail")

    def test_empty_inventory_precision_and_recall_are_undefined_not_perfect(self):
        report = assess_extraction(self.suite, proposal(self.suite, "original_domain"))
        self.assertEqual(report["status"], "pass")
        for metric in report["metrics"].values():
            self.assertEqual(metric["expected"], 0)
            self.assertEqual(metric["observed"], 0)
            self.assertIsNone(metric["precision"])
            self.assertIsNone(metric["recall"])

    def test_unresolved_alias_retained_in_metrics_and_query_totals(self):
        reference = deepcopy(self.suite.reference)
        source = next(s for s in reference["sources"] if s["source_id"] == "eval_prism")
        source["aliases"][0]["judgment"] = "needs_review"
        suite = replace(self.suite, reference=reference)
        report = assess_extraction(suite, proposal(suite, "eval_prism"))
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["metrics"]["alias"]["expected"], 2)
        self.assertEqual(report["unresolved_alias_count"], 1)
        for case_id in ("eval_prism.scoped", "eval_prism.unknown"):
            result = assess_retrieval(suite, case_id, perfect_retrieval(suite, case_id))
            self.assertEqual(result["status"], "needs_review")
            self.assertEqual(result["recall"], 1)

    def test_extraction_partition_must_account_for_bytes_exactly_once(self):
        for mutation in ("duplicate", "omit", "invent", "bad_hash", "bad_span", "boolean_offset"):
            value = proposal(self.suite, "eval_prism")
            if mutation == "duplicate":
                value["groups"].append(deepcopy(value["groups"][0]))
            elif mutation == "omit":
                value["groups"].pop(0)
            elif mutation == "invent":
                value["groups"][0]["text"] += "invention"
            elif mutation == "bad_hash":
                value["source_sha256"] = "0" * 64
            elif mutation == "bad_span":
                value["groups"][0]["spans"][0]["end"] = 100000
            else:
                value["groups"][0]["spans"][0]["start"] = False
            with self.subTest(mutation=mutation):
                self.assertEqual(assess_extraction(self.suite, value)["status"], "fail")

    def test_equivalent_partitions_and_context_closures(self):
        fine = proposal(self.suite, "eval_prism")
        coarse = deepcopy(fine)
        data = self.suite.sources["eval_prism"]
        # Co-location safely carries qualification, without one mandatory partition.
        coarse["groups"] = [{"spans": [full_span(self.suite, "eval_prism")], "text": data.decode("utf-8")}]
        coarse["metadata"]["links"] = []
        self.assertEqual(assess_extraction(self.suite, coarse)["status"], "pass")
        fine["groups"].reverse()
        fine["metadata"]["scopes"].reverse()
        self.assertEqual(assess_extraction(self.suite, fine)["status"], "pass")
        # Direct vs transitive context links have the same closure.
        linked = proposal(self.suite, "eval_prism")
        linked["metadata"]["links"] = linked["metadata"]["links"][:2]
        self.assertEqual(assess_extraction(self.suite, linked)["status"], "pass")

    def test_fragments_and_duplicates_do_not_fake_whole_atom_coverage(self):
        case_id = "eval_prism.scoped"
        value = perfect_retrieval(self.suite, case_id)
        index = next(i for i, e in enumerate(value["entries"]) if e["spans"][0] == {"source_id": "eval_prism", "start": 164, "end": 224})
        original = value["entries"].pop(index)["spans"][0]
        fragment = dict(original, end=194)
        value["entries"].extend(retrieval(self.suite, [fragment, fragment])["entries"])
        report = assess_retrieval(self.suite, case_id, value)
        self.assertEqual(report["status"], "fail")
        self.assertLess(report["recall"], 1)
        remainder = dict(original, start=194)
        value["entries"].extend(retrieval(self.suite, [remainder])["entries"])
        report = assess_retrieval(self.suite, case_id, value)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["recall"], 1)

    def test_missing_qualifier_removes_rule_credit(self):
        value = perfect_retrieval(self.suite, "eval_prism.scoped")
        value["entries"] = [e for e in value["entries"] if e["spans"][0] != {"source_id": "eval_prism", "start": 312, "end": 395}]
        result = assess_retrieval(self.suite, "eval_prism.scoped", value)
        self.assertIn("eval_prism:open", result["missing_required_atoms"])
        self.assertIn("eval_prism:permission", result["missing_required_atoms"])

    def test_union_arithmetic_worked_independently(self):
        self.assertEqual(union_intervals([(5, 9), (0, 3), (2, 5), (0, 3)]), [(0, 9)])
        self.assertEqual(interval_bytes([(0, 3), (2, 5), (8, 10)]), 7)
        self.assertEqual(overlap_bytes([(0, 5), (8, 10)], [(3, 9), (3, 9)]), 3)
        data = b"abcdefghijklmnop"
        atoms = [
            {"id": "target", "start": 0, "end": 4, "scopes": ["Target"], "requires": []},
            {"id": "permitted", "start": 4, "end": 6, "scopes": ["Other"], "requires": []},
            {"id": "irrelevant1", "start": 6, "end": 10, "scopes": ["Other"], "requires": []},
            {"id": "irrelevant2", "start": 8, "end": 14, "scopes": ["Other"], "requires": []},
            {"id": "general", "start": 14, "end": 16, "scopes": [], "requires": []},
        ]
        reference = {"sources": [
            {"source_id": "s", "atoms": atoms, "aliases": [], "queries": [
                {"id": "s.scoped", "kind": "scoped", "subject_types": ["Target"], "permitted_context": ["s:permitted"]}]},
            {"source_id": "original_domain", "atoms": [{"id": "whole", "start": 0, "end": 1, "scopes": [], "requires": []}], "aliases": [], "queries": []},
        ]}
        suite = Suite(
            {"sources": [{"source_id": "s", "partition": "evaluation"}, {"source_id": "original_domain", "partition": "shared_smoke"}],
             "efficiency_case_ids": ["s.scoped"], "thresholds": {"each_scoped_irrelevant_byte_reduction": 0.2}},
            reference, {"s": data, "original_domain": b"g"},
        )
        spans = [
            {"source_id": sid, "start": a, "end": b}
            for sid, a, b in [("s", 0, 4), ("s", 14, 16), ("original_domain", 0, 1), ("s", 6, 8), ("s", 6, 8)]
        ]
        report = assess_retrieval(suite, "s.scoped", retrieval(suite, spans))
        self.assertEqual(report["recall"], 1)
        self.assertEqual(report["irrelevant_baseline_bytes"], 8)
        self.assertEqual(report["irrelevant_returned_bytes"], 2)
        self.assertEqual(report["irrelevant_byte_reduction"], 0.75)
        self.assertEqual(report["provider_text_bytes"], 11)
        self.assertEqual(report["selected_source_union_bytes"], 9)

    def test_all_active_is_not_useful_and_each_eight_case_gate_is_independent(self):
        for case_id in self.suite.manifest["efficiency_case_ids"]:
            expected = case_expectation(self.suite, case_id)
            value = retrieval(self.suite, [full_span(self.suite, sid) for sid in expected["sources"]], "conservative_expansion")
            report = assess_retrieval(self.suite, case_id, value)
            self.assertEqual(report["recall"], 1)
            self.assertEqual(report["irrelevant_byte_reduction"], 0)
            self.assertFalse(report["usefulness_pass"])
            self.assertEqual(report["status"], "fail")

    def test_unknown_scope_requires_full_broadening_or_explicit_inability(self):
        for case_id in self.suite.manifest["unknown_case_ids"]:
            self.assertEqual(assess_retrieval(self.suite, case_id, perfect_retrieval(self.suite, case_id))["status"], "pass")
            unavailable = {"status": "unavailable", "error_code": "knowledge_gap", "entries": []}
            self.assertEqual(assess_retrieval(self.suite, case_id, unavailable)["status"], "pass")
            unavailable["entries"] = [{"text": "partial"}]
            self.assertEqual(assess_retrieval(self.suite, case_id, unavailable)["status"], "fail")
            self.assertEqual(assess_retrieval(self.suite, case_id, retrieval(self.suite, []))["status"], "fail")

    def test_partition_and_source_identity_are_not_text_matching(self):
        value = perfect_retrieval(self.suite, "eval_prism.scoped")
        value["entries"].extend(retrieval(self.suite, [full_span(self.suite, "dev_atlas")])["entries"])
        self.assertEqual(assess_retrieval(self.suite, "eval_prism.scoped", value)["status"], "fail")
        value = perfect_retrieval(self.suite, "eval_prism.scoped")
        value["entries"][0]["source_sha256"] = "0" * 64
        self.assertEqual(assess_retrieval(self.suite, "eval_prism.scoped", value)["status"], "fail")

    def test_unresolved_stays_in_denominator_and_does_not_pass(self):
        reference = deepcopy(self.suite.reference)
        source = next(s for s in reference["sources"] if s["source_id"] == "eval_prism")
        source["atoms"][0]["judgment"] = "needs_review"
        suite = replace(self.suite, reference=reference)
        report = assess_retrieval(suite, "eval_prism.scoped", perfect_retrieval(suite, "eval_prism.scoped"))
        original = assess_retrieval(self.suite, "eval_prism.scoped", perfect_retrieval(self.suite, "eval_prism.scoped"))
        self.assertEqual(report["required_atom_count"], original["required_atom_count"])
        self.assertEqual(report["recall"], 1)
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(assess_extraction(suite, proposal(suite, "eval_prism"))["status"], "needs_review")

    def test_byte_mutation_hash_drift_and_exact_utf8_bom_crlf_layout(self):
        original = self.suite.sources["eval_prism"]
        changed = dict(self.suite.sources, eval_prism=b"!" + original[1:])
        suite = replace(self.suite, sources=changed)
        self.assertEqual(assess_extraction(suite, proposal(self.suite, "eval_prism"))["status"], "fail")
        data = "\ufeffPreamble ✔\r\n# Heading\r\n- nested\r\n  - child\r\n```\r\n# fenced\r\nScope: Fake\r\n```\r\n".encode("utf-8")
        suite = Suite({}, {"sources": [{"source_id": "layout", "atoms": [], "aliases": [], "queries": []}]}, {"layout": data})
        value = {
            "source_id": "layout", "source_sha256": hashlib.sha256(data).hexdigest(), "status": "accepted",
            "groups": [{"spans": [full_span(suite, "layout")], "text": data.decode("utf-8")}],
            "metadata": {"scopes": [], "aliases": [], "links": []},
        }
        self.assertEqual(assess_extraction(suite, value)["status"], "pass")
        value["groups"][0]["text"] = value["groups"][0]["text"].replace("\r\n", "\n")
        self.assertEqual(assess_extraction(suite, value)["status"], "fail")
        value["groups"][0]["spans"][0]["start"] = 1  # inside the UTF-8 BOM
        self.assertEqual(assess_extraction(suite, value)["status"], "fail")

    def test_query_identity_is_row_order_invariant_not_content_invariant(self):
        findings = [{"finding_id": "S-2", "equipment_id": "E-2"}, {"finding_id": "S-1", "equipment_id": "E-1"}]
        registry = [{"equipment_id": "E-1", "engineer_comment": "first"}, {"equipment_id": "E-2", "engineer_comment": "second"}]
        self.assertEqual(canonical_query_hash(findings, registry), canonical_query_hash(findings[::-1], registry[::-1]))
        changed = deepcopy(registry)
        changed[0]["engineer_comment"] += "!"
        self.assertNotEqual(canonical_query_hash(findings, registry), canonical_query_hash(findings, changed))
        with self.assertRaises(ValueError):
            canonical_query_hash(findings + findings, registry)

    def test_reference_hash_and_source_hash_are_verified_without_writes(self):
        from pathlib import Path
        original = Path.read_bytes

        def altered(path):
            data = original(path)
            return b"!" + data[1:] if path.name == "eval_prism.md" else data

        with patch.object(Path, "read_bytes", altered):
            with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                load_suite()

    def test_all_six_semantic_reviewer_controls_including_supported_unresolved(self):
        controls = self.suite.reference["semantic_controls"]
        judgments = [{"id": c["id"], "verdict": c["expected"], "reason": "Disclosed self-test judgment."} for c in controls]
        self.assertEqual(calibrate_semantic_review(self.suite, judgments)["status"], "pass")
        for index in range(len(judgments)):
            changed = deepcopy(judgments)
            changed[index]["verdict"] = "pass" if changed[index]["verdict"] != "pass" else "fail"
            self.assertEqual(calibrate_semantic_review(self.suite, changed)["status"], "fail")
        self.assertEqual(calibrate_semantic_review(self.suite, judgments[:-1])["status"], "fail")

    def test_lifecycle_and_adversarial_controls_are_separate_denominators(self):
        self.assertEqual(len(self.suite.queries), 24)
        for case in self.suite.reference["boundary_cases"]:
            marker = f"synthetic-only:{case['id']}"
            value = {"marker": marker, "result_text": "", "index_text": "", "provider_text": ""}
            if case["kind"] == "failure":
                value.update(status="unavailable", error_code=case["code"], entries=[], exit_code=1,
                             before_sha256="a" * 64, after_sha256="a" * 64)
            elif case["expected"] == "included":
                value.update(result_text=marker, index_text=marker, provider_text=marker)
            report = assess_boundary_case(self.suite, case["id"], value)
            self.assertEqual(report["status"], "pass", report)
            self.assertEqual(report["denominator"], "boundary_only")
            if case["kind"] == "failure":
                value["after_sha256"] = "b" * 64
            elif case["expected"] == "included":
                value["provider_text"] = ""
            else:
                value["provider_text"] = marker
            self.assertEqual(assess_boundary_case(self.suite, case["id"], value)["status"], "fail")

    def test_repeats_require_all_three_correct_outputs_and_report_drift(self):
        primaries = [proposal(self.suite, sid) for sid in self.suite.manifest["repeat_source_ids"]]
        repeats = [
            {"slot_id": f"{sid}.repeat{repeat}", "proposal": proposal(self.suite, sid)}
            for sid in self.suite.manifest["repeat_source_ids"] for repeat in (1, 2)
        ]
        self.assertEqual(assess_repeats(self.suite, primaries, [])["status"], "needs_review")
        self.assertEqual(assess_repeats(self.suite, primaries, repeats)["status"], "pass")
        repeats[0]["proposal"]["metadata"]["scopes"][0]["value"] = "Lemon Cubes"
        self.assertEqual(assess_repeats(self.suite, primaries, repeats)["status"], "fail")

    def test_attempt_budget_has_no_semantic_retry_or_hidden_accounting_pass(self):
        def attempt(slot, number=1, status="accepted", error=None):
            sid = slot.rsplit(".", 1)[0]
            return {
                "slot_id": slot, "attempt": number, "status": status, "error_code": error,
                "source_sha256": hashlib.sha256(self.suite.sources[sid]).hexdigest(),
                "prompt_sha256": "a" * 64, "schema_sha256": "b" * 64, "settings_sha256": "c" * 64,
                "model": "self-test-not-a-deployment", "provider": "copilot",
            }
        records = [attempt(slot) for slot in self.suite.manifest["slot_ids"]]
        report = assess_attempts(self.suite, records)
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual(report["strict_accounting"], "not_established")
        self.assertIsNone(report["hidden_http_attempts"])
        self.assertIsNone(report["usd_cost"])
        first = records[0]["slot_id"]
        records[0] = attempt(first, status="structural_error", error="malformed_json")
        records.append(attempt(first, 2))
        self.assertEqual(assess_attempts(self.suite, records)["status"], "pass")
        records[0] = attempt(first, status="semantic_error", error="missing_negation")
        self.assertEqual(assess_attempts(self.suite, records)["status"], "fail")
        records[0] = attempt(first, status="interrupted")
        self.assertEqual(assess_attempts(self.suite, records)["status"], "fail")
        self.assertEqual(assess_attempts(self.suite, records * 2)["status"], "fail")

    def test_effort_normalizes_atom_facts_and_requires_crossed_blinded_humans(self):
        records, hashes = human_control_records(self.suite)
        report = assess_effort(self.suite, records, candidate_hashes=hashes)
        self.assertEqual(report["counts"], {"C0": 8, "C1": 0})
        self.assertEqual(report["status"], "pass", report)
        changed = deepcopy(records)
        changed[1]["operations"] = [{"kind": "group_change", "atoms": ["open"], "value": "necessary split"}] * 5
        report = assess_effort(self.suite, changed, candidate_hashes=hashes)
        self.assertEqual(report["counts"]["C1"], 1, "duplicate edit events count once")
        for mutation in ("same_reviewer", "ai", "unblinded", "missing"):
            changed = deepcopy(records)
            if mutation == "same_reviewer":
                changed[1]["reviewer_id"] = changed[0]["reviewer_id"]
            elif mutation == "ai":
                changed[0]["kind"] = "AI"
            elif mutation == "unblinded":
                changed[0]["unblinded"] = True
            else:
                changed.pop()
            self.assertNotEqual(assess_effort(self.suite, changed, candidate_hashes=hashes)["status"], "pass")
        self.assertEqual(assess_effort(self.suite, records)["status"], "needs_review")
        records[0]["candidate_sha256"] = "0" * 64
        self.assertNotEqual(assess_effort(self.suite, records, candidate_hashes=hashes)["status"], "pass")

    def test_effort_relative_absolute_and_baseline_thresholds_all_required(self):
        # Threshold arithmetic is independent of UI behavior or model self-reports.
        for c0, c1, expected in [(8, 4, True), (8, 5, False), (20, 16, False), (7, 0, False)]:
            records, hashes = human_control_records(self.suite, c0, c1)
            observed = assess_effort(self.suite, records, candidate_hashes=hashes)
            self.assertEqual(observed["benefit_demonstrated"], expected, observed)


if __name__ == "__main__":
    unittest.main()
