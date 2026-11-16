"""Software-only review declarations; no domain or human qualification evidence."""
import csv
import io
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

from triage_knowledge.contracts import KnowledgeError, TableSource, canonical_bytes, sha256
from triage_knowledge.source import SourceDocument, extract_code, validate_proposal
from triage_knowledge.source_store import SourceKnowledgeStore
from triage_knowledge.retrieval import (
    FINDING_FIELDS, REGISTRY_FIELDS, binding_from_tables, get_triage_knowledge, strategy_binding,
)


NOW = "2026-07-01T00:00:00Z"
LATER = "2026-08-01T00:00:00Z"
REVIEWER = "software-only-test-declaration"


def document(raw=b"# General\nAlways preserve exceptions.\n", sid="test-source"):
    return SourceDocument.from_bytes(raw, name="Synthetic software test", source_id=sid)


def unit_evidence_proposal(doc):
    proposal = extract_code(doc).proposal
    for group in proposal["groups"]:
        group["evidence"] = [{"unit_id": ev["unit_id"]} for ev in group["evidence"]]
    return {"contract_version": 2, **proposal}


def table(rows, fields, kind, sid):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=sorted(fields), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return TableSource.from_bytes(output.getvalue().encode("utf-8"), source_id=sid, kind=kind)


def inputs(types=("Pumps", "Fans"), descriptions=None):
    descriptions = descriptions or ["observed condition"] * len(types)
    findings, registry = [], []
    for number, (equipment_type, description) in enumerate(zip(types, descriptions), 1):
        equipment_id = f"E-{number}"
        findings.append(dict(finding_id=f"F-{number}", reported_date="2026-06-01",
                             equipment_id=equipment_id, equipment_type=equipment_type,
                             inspection_type="Routine", inspection_method="Visual",
                             finding_description=description, reported_by="Test",
                             reporter_role="Software test"))
        registry.append(dict(equipment_id=equipment_id, equipment_type=equipment_type,
                             service_description="Synthetic", criticality_score="2",
                             reliability_score="8", safety_critical_element="No",
                             redundancy="None", engineer_comment="Authorized comment"))
    return findings, registry


class SourceTests(unittest.TestCase):
    def test_v2_unit_evidence_preserves_raw_proposal_and_materializes_exact_quotes(self):
        doc = document(("\ufeff# Main\r\nScope: Pumps\r\nAliases: Pump units\r\n"
                        "Keep qualifier \u2713.\r\n# Qualification\r\nCheck the condition.\r\n").encode())
        proposal = unit_evidence_proposal(doc)
        proposal["groups"][0]["unit_ids"].reverse()
        original = canonical_bytes(proposal)
        extraction = validate_proposal(doc, proposal)
        self.assertEqual(extraction._proposal_bytes, original)
        self.assertEqual(canonical_bytes(proposal), original)
        self.assertEqual(extraction.proposal, proposal)
        units = {unit["unit_id"]: unit for unit in doc.units}
        for raw, group in zip(proposal["groups"], extraction.groups):
            self.assertEqual(group["scopes"], raw["scopes"])
            self.assertEqual(group["aliases"], raw["aliases"])
            self.assertEqual(group["required_with"], raw["required_with"])
            self.assertEqual(group["evidence"], [
                {**entry, "quote": units[entry["unit_id"]]["text"]} for entry in raw["evidence"]])
            self.assertEqual(group["text"].encode(), b"".join(
                doc.raw[span["start"]:span["end"]] for span in group["spans"]))
        self.assertEqual("".join(group["text"] for group in extraction.groups).encode(), doc.raw)

    def test_v2_rejects_bad_versions_evidence_and_unit_partitions_without_repair(self):
        doc = document(b"# Main\nScope: Pumps\n# Other\nCondition.\n")
        for change, code in (
            ("bool_version", "unsupported_contract"), ("old_version", "unsupported_contract"),
            ("text_version", "unsupported_contract"), ("missing_version", "schema"),
            ("unknown_evidence", "evidence"), ("empty_evidence_id", "evidence"),
            ("nonstring_evidence_id", "evidence"), ("object_evidence_id", "evidence"),
            ("extra_quote", "schema"),
            ("duplicate_evidence", "evidence"),
            ("duplicate_unit", "unit_partition"), ("omitted_unit", "unit_partition"),
            ("unknown_unit", "unit_reference"),
        ):
            proposal = unit_evidence_proposal(doc)
            group = proposal["groups"][0]
            if change.endswith("_version"):
                if change == "missing_version":
                    del proposal["contract_version"]
                else:
                    proposal["contract_version"] = {
                        "bool_version": True, "old_version": 1, "text_version": "2"}[change]
            elif change in ("unknown_evidence", "empty_evidence_id",
                            "nonstring_evidence_id", "object_evidence_id"):
                group["evidence"][0]["unit_id"] = {
                    "unknown_evidence": "u9999", "empty_evidence_id": "",
                    "nonstring_evidence_id": [], "object_evidence_id": {}}[change]
            elif change == "extra_quote":
                group["evidence"][0]["quote"] = doc.units[1]["text"]
            elif change == "duplicate_evidence":
                group["evidence"].append(dict(group["evidence"][0]))
            elif change == "duplicate_unit":
                proposal["groups"][1]["unit_ids"].append(group["unit_ids"][0])
            elif change == "omitted_unit":
                proposal["groups"][1]["unit_ids"].pop()
            else:
                proposal["groups"][1]["unit_ids"][0] = "u9999"
            original = canonical_bytes(proposal)
            with self.subTest(change=change), self.assertRaises(KnowledgeError) as raised:
                validate_proposal(doc, proposal)
            self.assertEqual(raised.exception.code, code)
            self.assertEqual(canonical_bytes(proposal), original)

    def test_v2_metadata_still_requires_owned_case_sensitive_whole_word_literal(self):
        doc = document(b"# Main\nScope: Pumps\n# Foreign\nScope: Fans\n")
        for field in ("scopes", "aliases"):
            for label, unit_id in (("Pump", "u0002"), ("pumps", "u0002"),
                                   ("ump", "u0002"), ("Fans", "u0004")):
                proposal = unit_evidence_proposal(doc)
                evidence_ids = ["u0002", "u0004"] if field == "aliases" else [unit_id]
                proposal["groups"][0].update({
                    field: [label], "evidence": [{"unit_id": key} for key in evidence_ids]})
                with self.subTest(field=field, label=label), self.assertRaises(KnowledgeError) as raised:
                    validate_proposal(doc, proposal)
                self.assertEqual(raised.exception.code, "metadata_evidence")
        doc = document(b"# Main\nPumps and Pump units share this label evidence.\n")
        proposal = unit_evidence_proposal(doc)
        proposal["groups"][0].update(
            scopes=["Pumps"], aliases=["Pump units"], evidence=[{"unit_id": "u0002"}])
        self.assertEqual(validate_proposal(doc, proposal).groups[0]["evidence"], [
            {"unit_id": "u0002", "quote": doc.units[1]["text"]}])

    def test_v2_context_evidence_still_requires_both_endpoint_groups(self):
        doc = document(b"# Main\nMain rule\n# Exception\nException\n")
        for citations in ([], ["u0002"], ["u0004"]):
            proposal = unit_evidence_proposal(doc)
            proposal["groups"][0]["evidence"] = [{"unit_id": unit_id} for unit_id in citations]
            with self.subTest(citations=citations), self.assertRaises(KnowledgeError) as raised:
                validate_proposal(doc, proposal)
            self.assertEqual(raised.exception.code, "context_evidence")
        proposal = unit_evidence_proposal(doc)
        proposal["groups"][0]["evidence"] = [{"unit_id": "u0002"}, {"unit_id": "u0004"}]
        extraction = validate_proposal(doc, proposal)
        self.assertEqual(extraction.groups[0]["evidence"], [
            {"unit_id": "u0002", "quote": "Main rule\n"},
            {"unit_id": "u0004", "quote": "Exception\n"}])

    def test_legacy_v1_inexact_quote_is_rejected_not_reconstructed(self):
        doc = document(b"# Main\nScope: Pumps\n")
        proposal = extract_code(doc).proposal
        proposal["groups"][0]["evidence"][0]["quote"] = "scope: pumps"
        with self.assertRaises(KnowledgeError) as raised:
            validate_proposal(doc, proposal)
        self.assertEqual(raised.exception.code, "evidence")
        self.assertEqual(proposal["groups"][0]["evidence"][0]["quote"], "scope: pumps")

    def test_exact_byte_units_and_safe_copies(self):
        raw = b"\xef\xbb\xbfPreamble\r\n# Heading\r\nScope: Pumps\r\nTail \xe2\x9c\x93"
        doc = document(raw)
        extraction = extract_code(doc)
        self.assertEqual(raw, b"".join(u["text"].encode("utf-8") for u in doc.units))
        self.assertEqual(raw, "".join(g["text"] for g in extraction.groups).encode("utf-8"))
        self.assertEqual(doc.units[0]["unit_id"], "u0001")
        self.assertEqual(doc.units[-1]["end"], len(raw))
        extraction.groups[0]["text"] = "bad"
        extraction.proposal["groups"].clear()
        doc.units[0]["text"] = "bad"
        self.assertEqual(extraction.groups[0]["text"], "\ufeffPreamble\r\n")

    def test_reject_unsupported_sources(self):
        for raw in (b"", b"\xff", b"x" * 100001):
            with self.subTest(raw=raw[:2]), self.assertRaises(ValueError):
                document(raw)

    def test_heading_and_label_grammar_is_fence_aware(self):
        raw = (b"Preamble\n# Main\nEquipment: Pump-types\nAliases: Pumps; pump-types\n"
               b"```text\n# Not a heading\nScope: Wrong\n```\n## Next\nProse Scope: Nope\n")
        groups = extract_code(document(raw)).groups
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[1]["scopes"], ["Pump-types"])
        self.assertEqual(groups[1]["aliases"], ["Pumps", "pump-types"])
        self.assertEqual(groups[2]["scopes"], [])

    def test_unheaded_late_scope_never_restricts_preamble(self):
        raw = b"Earlier rules concern several types.\n\nOTHER EQUIPMENT\nScope: Fans\nLater rule.\n"
        extraction = extract_code(document(raw))
        self.assertEqual(len(extraction.groups), 1)
        self.assertEqual(extraction.groups[0]["scopes"], [])
        self.assertEqual(extraction.groups[0]["text"].encode(), raw)
        with_heading = extract_code(document(b"General preamble.\nScope: Fans\n# Scoped\nScope: Pumps\nRule.\n"))
        self.assertEqual([g["scopes"] for g in with_heading.groups], [[], ["Pumps"]])

    def test_alias_semicolon_grammar_preserves_literal_commas(self):
        extraction = extract_code(document(
            b"# Equipment\nScope: Counters\nAliases: azure counters; sky parts; round, flat counters\n"))
        self.assertEqual(extraction.groups[0]["aliases"],
                         ["azure counters", "sky parts", "round, flat counters"])

    def test_cross_heading_qualifiers_get_source_star_without_invented_text(self):
        raw = (b"# Main\nScope: Pumps\nApply the rule only if qualified below.\n"
               b"# Qualifier\nThe earlier rule excludes a marked specimen.\n"
               b"# Uncertainty\nThe condition may be unresolved.\n")
        extraction = extract_code(document(raw))
        groups = extraction.groups
        self.assertEqual(groups[0]["required_with"], ["g0002", "g0003"])
        self.assertTrue(all(not g["required_with"] for g in groups[1:]))
        cited = {e["unit_id"] for e in groups[0]["evidence"]}
        self.assertTrue(all(cited.intersection(g["unit_ids"]) for g in groups))
        self.assertEqual("".join(g["text"] for g in groups).encode(), raw)
        self.assertEqual(extraction.proposal, extract_code(document(raw)).proposal)

    def test_whitespace_preamble_can_be_coupled_without_fabricated_quote(self):
        extraction = extract_code(document(b"\r\n# Rule\r\nScope: Pumps\r\nRule.\r\n"))
        self.assertEqual(extraction.groups[0]["required_with"], ["g0002"])
        self.assertIn({"unit_id": "u0001", "quote": "\r\n"},
                      extraction.groups[0]["evidence"])

    def test_duplicate_omitted_invented_and_extra_fields_rejected(self):
        doc = document(b"# One\nText\n# Two\nOther\n")
        base = extract_code(doc).proposal
        mutations = []
        p = extract_code(doc).proposal
        p["groups"][1]["unit_ids"].append("u0001")
        mutations.append(p)
        p = extract_code(doc).proposal
        p["groups"][0]["unit_ids"].pop()
        mutations.append(p)
        p = extract_code(doc).proposal
        p["groups"][0]["unit_ids"][0] = "u9999"
        mutations.append(p)
        p = extract_code(doc).proposal
        p["groups"][0]["text"] = "Invented"
        mutations.append(p)
        p = extract_code(doc).proposal
        p["groups"][0]["scopes"] = ["Invented"]
        mutations.append(p)
        p = extract_code(doc).proposal
        p["groups"][1]["group_id"] = base["groups"][0]["group_id"]
        mutations.append(p)
        for proposal in mutations:
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                validate_proposal(doc, proposal)

    def test_metadata_requires_case_literal_and_word_endpoints(self):
        doc = document(b"# Main\nScope: Pumps\n")
        for label in ("Pump", "pumps", "ump"):
            proposal = extract_code(doc).proposal
            proposal["groups"][0]["scopes"] = [label]
            with self.subTest(label=label), self.assertRaises(ValueError):
                validate_proposal(doc, proposal)

    def test_metadata_quote_cannot_hide_actual_source_endpoints(self):
        doc = document(b"# Main\nMegaPumps\n")
        proposal = extract_code(doc).proposal
        proposal["groups"][0].update(scopes=["Pumps"], evidence=[
            {"unit_id": "u0002", "quote": "Pumps"}])
        with self.assertRaises(KnowledgeError):
            validate_proposal(doc, proposal)

    def test_materializes_unsorted_units_in_byte_order(self):
        doc = document()
        p = extract_code(doc).proposal
        p["groups"][0]["unit_ids"].reverse()
        self.assertEqual(validate_proposal(doc, p).groups[0]["text"], doc.raw.decode())

    def test_context_evidence_requires_both_endpoints(self):
        doc = document(b"# Main\nMain rule\n# Exception\nException\n")
        p = extract_code(doc).proposal
        p["groups"][0]["required_with"] = ["g0002"]
        p["groups"][0]["evidence"] = []
        with self.assertRaises(ValueError):
            validate_proposal(doc, p)
        p["groups"][0]["evidence"] = [{"unit_id": "u0002", "quote": "Main rule"},
                                      {"unit_id": "u0004", "quote": "Exception"}]
        self.assertEqual(validate_proposal(doc, p).groups[0]["required_with"], ["g0002"])

    def test_headless_imports_do_not_load_inference_ui_or_evaluator(self):
        code = ("import sys; import triage_knowledge.source, triage_knowledge.source_store, "
                "triage_knowledge.retrieval; "
                "assert not any(k.split('.')[0] in {'llm_inference','streamlit','eval'} "
                "for k in sys.modules)")
        subprocess.run([sys.executable, "-B", "-c", code], check=True, capture_output=True)

    def test_extraction_request_uses_fixed_schema_and_system(self):
        from triage_knowledge.source import extraction_request, SCHEMA, SYSTEM
        a = extraction_request(document(), model="test-model")
        b = extraction_request(document(b"Other source"), model="test-model")
        self.assertEqual(a.system, b.system)
        self.assertEqual(a.system, SYSTEM)
        self.assertEqual(a.response_schema, SCHEMA)
        self.assertEqual(a.response_schema, b.response_schema)
        self.assertEqual(a.reasoning_effort, "low")
        a.prepared()


class StoreHarness(unittest.TestCase):
    def setUp(self):
        self.root = Path(".artifacts") / ("source-core-test-" + uuid.uuid4().hex)
        self.store = SourceKnowledgeStore(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def create(self, raw=b"# General\nAlways preserve exceptions.\n", *, keep_source_context=False):
        self.digest = self.store.create_draft([extract_code(document(raw))])
        if not keep_source_context and self.store.load_draft()[0]["context_links"]:
            # Independent lifecycle fixtures explicitly remove baseline over-closure.
            self.digest = self.store.set_context_links([], expected_digest=self.digest)
        items = self.store.load_draft()[0]["items"]
        return sorted(items, key=lambda i: items[i]["revision"]["spans"][0]["start"])

    def review_all(self):
        for item_id, item in self.store.load_draft()[0]["items"].items():
            if item["review_state"] != "rejected":
                self.digest = self.store.review_item(item_id, reviewer=REVIEWER,
                                                    reason="Software fixture only",
                                                    expected_digest=self.digest)

    def publish(self):
        return self.store.publish(expected_digest=self.digest, author=REVIEWER,
                                  reviewer=REVIEWER, reason="Software fixture only", reviewed_at=NOW)

    def links(self, ids):
        candidate, _ = self.store.load_draft()
        links = []
        for first, second in zip(ids, ids[1:] + ids[:1]):
            evidence = []
            addresses = []
            for item_id in (first, second):
                item = candidate["items"][item_id]
                rev = item["revision"]
                addresses.append(item_id + "@" + item["revision_id"])
                span = rev["spans"][0]
                raw = self.store._source(rev["source_sha256"])
                evidence.append({"item_id": item_id, "revision_id": item["revision_id"],
                                 **span, "quote": raw[span["start"]:span["end"]].decode()})
            links.append({"from": addresses[0], "to": addresses[1], "evidence": evidence})
        return links


class StoreTests(StoreHarness):
    def test_rejected_item_requires_explicit_restore_before_every_amendment(self):
        first, second = self.create(b"# First\nFirst rule.\n# Second\nSecond rule.\n")
        self.digest = self.store.reject_item(first, reason="Software intake rejection",
                                             expected_digest=self.digest)
        before = self.store.draft_path.read_bytes()
        mutations = (
            lambda: self.store.edit_item(first, "Attempted implicit restoration",
                                         reason="Software test", expected_digest=self.digest),
            lambda: self.store.set_lifecycle(first, reason="Software test", expected_digest=self.digest),
            lambda: self.store.update_metadata(first, scopes=[], aliases=[], evidence=[],
                                               expected_digest=self.digest),
            lambda: self.store.replace_item(first, second, effective_from=NOW,
                                            reason="Software test", expected_digest=self.digest),
            lambda: self.store.replace_item(second, first, effective_from=NOW,
                                            reason="Software test", expected_digest=self.digest),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(KnowledgeError) as caught:
                mutation()
            self.assertEqual(caught.exception.code, "rejected_item")
            self.assertEqual(self.store.draft_path.read_bytes(), before)
            self.assertEqual(self.store.item_record(first)["decision_reason"], "Software intake rejection")
        self.digest = self.store.restore_item(first, reason="Explicit software restoration",
                                              expected_digest=self.digest)
        self.digest = self.store.edit_item(first, "Permitted after explicit restoration",
                                          reason="Software test", expected_digest=self.digest)
        self.assertEqual(self.store.item_record(first)["review_state"], "pending")
        self.review_all()
        self.publish()

    def test_replacement_cancellation_cannot_implicitly_restore_rejected_predecessor(self):
        first, second = self.create(b"# First\nFirst rule.\n# Second\nSecond rule.\n")
        self.digest = self.store.replace_item(first, second, effective_from=NOW,
                                              reason="Software replacement", expected_digest=self.digest)
        self.digest = self.store.reject_item(first, reason="Software intake rejection",
                                             expected_digest=self.digest)
        before = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError) as caught:
            self.store.cancel_replacement(first, reason="Attempted implicit restoration",
                                           expected_digest=self.digest)
        self.assertEqual(caught.exception.code, "rejected_item")
        self.assertEqual(self.store.draft_path.read_bytes(), before)

    def test_published_text_amendment_cannot_be_rejected_as_new_intake(self):
        item_id, = self.create()
        self.review_all()
        release_id = self.publish()
        pinned = self.store.resolve_release(release_id)
        self.digest = self.store.edit_item(item_id, "Changed published text",
                                          reason="Software amendment", expected_digest=self.digest)
        self.store = SourceKnowledgeStore(self.root)
        before = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError) as caught:
            self.store.reject_item(item_id, reason="Invalid intake rejection",
                                   expected_digest=self.digest)
        self.assertEqual(caught.exception.code, "published_item")
        self.assertEqual(self.store.draft_path.read_bytes(), before)
        self.assertEqual(self.store.item_record(item_id)["review_state"], "pending")
        self.assertEqual(self.store.resolve_release(release_id), pinned)
        with self.assertRaises(KnowledgeError):
            self.publish()
        self.digest = self.store.set_lifecycle(item_id, status="retired",
                                              reason="Explicit software withdrawal",
                                              expected_digest=self.digest)
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertFalse(self.store.eligible(candidate, item_id, NOW))

    def test_published_metadata_amendment_cannot_be_rejected_as_new_intake(self):
        item_id, = self.create(b"# Scoped\nScope: Pumps\nRule.\n")
        self.review_all()
        release_id = self.publish()
        prior_revision = self.store.item_record(item_id)["revision_id"]
        self.digest = self.store.update_metadata(item_id, scopes=[], aliases=[], evidence=[],
                                                 expected_digest=self.digest)
        self.assertNotEqual(self.store.item_record(item_id)["revision_id"], prior_revision)
        self.store = SourceKnowledgeStore(self.root)
        before = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError) as caught:
            self.store.reject_item(item_id, reason="Invalid metadata rejection",
                                   expected_digest=self.digest)
        self.assertEqual(caught.exception.code, "published_item")
        self.assertEqual(self.store.draft_path.read_bytes(), before)
        self.assertTrue(self.store.resolve_release(release_id))

    def test_unpublished_text_and_metadata_amendments_remain_rejectable_intake(self):
        first, second = self.create(b"# First\nScope: Pumps\nFirst rule.\n"
                                    b"# Second\nScope: Fans\nSecond rule.\n")
        self.review_all()
        self.digest = self.store.edit_item(first, "Unpublished edited text",
                                          reason="Software amendment", expected_digest=self.digest)
        self.digest = self.store.update_metadata(second, scopes=[], aliases=[], evidence=[],
                                                 expected_digest=self.digest)
        for item_id in (first, second):
            self.digest = self.store.reject_item(item_id, reason="Rejected before first publication",
                                                 expected_digest=self.digest)
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertTrue(all(item["review_state"] == "rejected"
                            for item in candidate["items"].values()))

    def test_windows_transient_replace_denial_retries_without_partial_draft(self):
        item_id, = self.create()
        import os
        real_replace, attempts = os.replace, []
        def delayed_replace(source, target):
            attempts.append(True)
            if len(attempts) == 1:
                raise PermissionError("Synthetic Windows sharing violation")
            return real_replace(source, target)
        with patch("triage_knowledge.source_store.os.replace", side_effect=delayed_replace):
            self.digest = self.store.review_item(item_id, reviewer=REVIEWER, reason="Software test",
                                                 expected_digest=self.digest)
        self.assertEqual(len(attempts), 2)
        self.assertEqual(self.store.item_record(item_id)["review_state"], "reviewed")
        self.assertFalse((self.root / ".draft-writing.json").exists())

    def test_add_source_preserves_existing_candidate_and_source_document(self):
        item_id, = self.create()
        self.review_all()
        before = self.store.item_record(item_id)
        additional = document(b"# Amendment\r\nExplicit user addition.\r\n", "addition-source")
        self.digest = self.store.add_source(extract_code(additional), expected_digest=self.digest)
        self.assertEqual(self.store.item_record(item_id), before)
        self.assertEqual(self.store.source_document("addition-source").raw, additional.raw)
        self.assertEqual(self.store.source_document("addition-source").units, additional.units)
        with self.assertRaises(KnowledgeError):
            self.publish()
        self.review_all()
        self.assertEqual(len(self.store.resolve_release(self.publish())["candidate"]["items"]), 2)

    def test_fork_release_reinstates_exact_pinned_candidate_not_hot_reload(self):
        item_id, = self.create()
        self.review_all()
        original_release = self.publish()
        original, _ = self.store.load_draft()
        self.digest = self.store.edit_item(item_id, "Later draft", reason="Software change",
                                          expected_digest=self.digest)
        with self.assertRaises(KnowledgeError):
            self.store.fork_release(original_release, expected_digest="stale")
        self.digest = self.store.fork_release(original_release, expected_digest=self.digest)
        self.assertEqual(self.store.load_draft()[0], original)
        self.assertEqual(self.publish(), original_release)

    def test_unqualified_c1_requires_explicit_experiment_and_never_activates_by_default(self):
        doc = document()
        c1 = validate_proposal(doc, extract_code(doc).proposal)
        with self.assertRaises(KnowledgeError):
            self.store.create_draft([c1])
        self.assertFalse(self.store.draft_path.exists())
        self.store = SourceKnowledgeStore(self.root, experimental_profile={
            "experiment_id": "software-only-unqualified"})
        self.digest = self.store.create_draft([c1])
        self.review_all()
        release_id = self.publish()
        self.assertTrue(self.store.resolve_release(release_id))
        with self.assertRaises(KnowledgeError):
            SourceKnowledgeStore(self.root).resolve_release(release_id)

    def test_v2_code_expanded_evidence_round_trips_existing_store_and_retrieval(self):
        doc = document(b"# Main\nScope: Pumps\nPreserve the condition.\n"
                       b"# Qualification\nCheck the qualification.\n")
        extraction = validate_proposal(doc, unit_evidence_proposal(doc))
        self.store = SourceKnowledgeStore(self.root, experimental_profile={
            "experiment_id": "software-only-v2-unit-evidence"})
        self.digest = self.store.create_draft([extraction])
        self.review_all()
        release_id = self.publish()
        candidate = self.store.resolve_release(release_id)["candidate"]
        units = {unit["unit_id"]: unit["text"] for unit in doc.units}
        self.assertEqual(candidate["schema_version"], 3)
        for item in candidate["items"].values():
            self.assertTrue(all(entry["quote"] == units[entry["unit_id"]]
                                for entry in item["revision"]["evidence"]))
        frows, rrows = inputs(("Pumps",))
        findings = table(frows, FINDING_FIELDS, "finding_input", "findings")
        registry = table(rrows, REGISTRY_FIELDS, "registry_input", "registry")
        result = get_triage_knowledge(
            self.store, {"findings": {row["finding_id"]: row for row in frows},
                         "registry": {row["equipment_id"]: row for row in rrows}},
            knowledge_version=release_id, assessment_time=NOW, expected_strategy=strategy_binding(),
            allowed_input_binding=binding_from_tables(findings, registry), max_bytes=64000)
        self.assertEqual(result.status, "ok", result.error_code)
        self.assertEqual(set(result.provider_payload().values()),
                         {group["text"] for group in extraction.groups})

    def test_metadata_edit_changes_revision_and_invalidates_review(self):
        item_id, = self.create(b"# Main\nScope: Pumps\nAliases: Rotors\nRule\n")
        self.review_all()
        before = self.store.item_record(item_id)
        self.digest = self.store.update_metadata(
            item_id, scopes=["Pumps"], aliases=[], evidence=before["evidence"],
            expected_digest=self.digest)
        after = self.store.item_record(item_id)
        self.assertNotEqual(before["revision_id"], after["revision_id"])
        self.assertEqual(after["review_state"], "pending")
        self.assertEqual(after["source_sha256"], before["source_sha256"])
        self.assertEqual(after["text"], before["text"])

    def test_replacement_expiry_has_no_ancestor_resurrection_and_cancel_needs_review(self):
        first, second = self.create(b"# Predecessor\nOld\n# Successor\nNew\n")
        self.digest = self.store.set_lifecycle(second, effective_until=LATER,
                                              reason="Software expiry", expected_digest=self.digest)
        self.digest = self.store.replace_item(first, second, effective_from=NOW,
                                              reason="Software replacement", expected_digest=self.digest)
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertFalse(self.store.eligible(candidate, first, LATER))
        self.assertFalse(self.store.eligible(candidate, second, LATER))
        self.digest = self.store.cancel_replacement(first, reason="Explicit software cancellation",
                                                    expected_digest=self.digest)
        self.assertEqual(self.store.item_record(first)["review_state"], "pending")
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertTrue(self.store.eligible(candidate, first, LATER))

    def test_replacement_cycle_and_rejected_successor_block_publication(self):
        first, second = self.create(b"# Predecessor\nOld\n# Successor\nNew\n")
        self.digest = self.store.replace_item(first, second, effective_from=NOW,
                                              reason="Software replacement", expected_digest=self.digest)
        before = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError):
            self.store.replace_item(second, first, effective_from=NOW,
                                    reason="Invalid cycle fixture", expected_digest=self.digest)
        self.assertEqual(before, self.store.draft_path.read_bytes())
        self.digest = self.store.reject_item(second, reason="Software rejection",
                                             expected_digest=self.digest)
        self.review_all()
        with self.assertRaises(KnowledgeError):
            self.publish()

    def test_blank_line_source_is_not_silently_discarded(self):
        item_id, = self.create(b"\r\n")
        self.assertEqual(self.store.item_record(item_id)["text"], "\r\n")
        self.review_all()
        self.publish()

    def test_pending_and_stale_mutations_do_not_publish_or_overwrite(self):
        item_id, = self.create()
        original = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError):
            self.publish()
        with self.assertRaises(KnowledgeError):
            self.store.set_lifecycle(item_id, reason="test", status="invalid",
                                     expected_digest=self.digest)
        self.assertEqual(self.store.draft_path.read_bytes(), original)
        with self.assertRaises(KnowledgeError):
            self.store.review_item(item_id, reviewer=REVIEWER, reason="test", expected_digest="stale")
        self.assertEqual(self.store.draft_path.read_bytes(), original)
        self.review_all()
        self.assertTrue(self.publish().startswith("sha256-"))

    def test_edit_new_source_ancestry_and_review_invalidation(self):
        item_id, = self.create()
        self.review_all()
        release_id = self.publish()
        original = self.store.load_draft()[0]["items"][item_id]["revision"]
        self.digest = self.store.edit_item(item_id, "New user text \u2713\r\n",
                                          reason="Explicit software amendment", expected_digest=self.digest)
        candidate, _ = self.store.load_draft()
        item = candidate["items"][item_id]
        self.assertEqual(item["review_state"], "pending")
        self.assertNotEqual(item["revision"]["source_id"], original["source_id"])
        self.assertEqual(item["revision"]["text"], "New user text \u2713\r\n")
        self.assertTrue(item["revision"]["ancestry"])
        self.assertTrue(candidate["sources"][item["revision"]["source_id"]]["ancestry"])
        with self.assertRaises(KnowledgeError):
            self.publish()
        self.review_all()
        self.publish()
        pinned = self.store.resolve_release(release_id)["candidate"]["items"][item_id]["revision"]
        self.assertEqual(pinned, original)
        self.digest = self.store.edit_item(item_id, "Second edit", reason="Second software edit",
                                          expected_digest=self.digest)
        self.review_all()
        self.publish()

    def test_rejected_source_spans_require_reason_and_are_retained_locally(self):
        ids = self.create(b"# One\nKeep\n# Two\nReject\n")
        with self.assertRaises(KnowledgeError):
            self.store.reject_item(ids[1], reason="", expected_digest=self.digest)
        self.digest = self.store.reject_item(ids[1], reason="Software rejection fixture",
                                             expected_digest=self.digest)
        self.review_all()
        release = self.store.resolve_release(self.publish())
        self.assertEqual(release["candidate"]["items"][ids[1]]["review_state"], "rejected")

    def test_immutable_revision_and_source_corruption_detected(self):
        item_id, = self.create()
        self.review_all()
        release_id = self.publish()
        candidate, _ = self.store.load_draft()
        rev = candidate["items"][item_id]
        revision_path = self.root / "revisions" / (rev["revision_id"] + ".json")
        original = revision_path.read_bytes()
        revision_path.write_bytes(original + b" ")
        with self.assertRaises(KnowledgeError):
            self.store.resolve_release(release_id)
        revision_path.write_bytes(original)
        source_path = self.root / "sources" / ("sha256-" + rev["revision"]["source_sha256"] + ".bin")
        source_path.write_bytes(b"Changed")
        with self.assertRaises(KnowledgeError):
            self.store.resolve_release(release_id)

    def test_hash_paths_and_duplicate_json_rejected(self):
        self.create()
        for release_id in ("../draft", "sha256-" + "0" * 63, 1):
            with self.assertRaises(ValueError):
                self.store.resolve_release(release_id)
        self.store.draft_path.write_bytes(b'{"schema_version":3,"schema_version":3}')
        with self.assertRaises(KnowledgeError):
            self.store.load_draft()

    def test_lock_and_existing_draft_are_not_overwritten(self):
        self.create()
        original = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError):
            self.store.create_draft([extract_code(document())])
        lock = self.root / ".writer.lock"
        lock.write_bytes(b"test")
        with self.assertRaises(KnowledgeError):
            self.review_all()
        self.assertEqual(self.store.draft_path.read_bytes(), original)

    def test_lifecycle_boundaries_and_retirement(self):
        item_id, = self.create()
        self.digest = self.store.set_lifecycle(item_id, effective_from=NOW, effective_until=LATER,
                                              reason="Software window", expected_digest=self.digest)
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertFalse(self.store.eligible(candidate, item_id, "2026-06-30T23:59:59Z"))
        self.assertTrue(self.store.eligible(candidate, item_id, NOW))
        self.assertFalse(self.store.eligible(candidate, item_id, LATER))
        self.digest = self.store.set_lifecycle(item_id, status="retired", reason="Software withdrawal",
                                              expected_digest=self.digest)
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertFalse(self.store.eligible(candidate, item_id, NOW))

    def test_replacement_does_not_resurrect_after_successor_retirement(self):
        first, second = self.create(b"# Predecessor\nOld\n# Successor\nNew\n")
        self.digest = self.store.replace_item(first, second, effective_from=NOW,
                                              reason="Software replacement", expected_digest=self.digest)
        self.review_all()
        self.digest = self.store.set_lifecycle(second, status="retired",
                                              reason="Software withdrawal", expected_digest=self.digest)
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertTrue(self.store.eligible(candidate, first, "2026-06-30T23:59:59Z"))
        self.assertFalse(self.store.eligible(candidate, first, NOW))
        self.assertFalse(self.store.eligible(candidate, second, NOW))
        self.digest = self.store.restore_item(first, reason="Explicit software restoration",
                                              expected_digest=self.digest)
        with self.assertRaises(KnowledgeError):
            self.publish()
        self.review_all()
        candidate = self.store.resolve_release(self.publish())["candidate"]
        self.assertTrue(self.store.eligible(candidate, first, NOW))

    def test_cyclic_context_edges_and_edited_endpoint_require_explicit_rebinding(self):
        ids = self.create(b"# One\nFirst\n# Two\nSecond\n# Three\nThird\n")
        self.digest = self.store.set_context_links(self.links(ids), expected_digest=self.digest)
        self.review_all()
        release_id = self.publish()
        self.digest = self.store.edit_item(ids[1], "Edited second", reason="Software edit",
                                          expected_digest=self.digest)
        self.review_all()
        with self.assertRaises(KnowledgeError):
            self.publish()
        self.assertEqual(len(self.store.resolve_release(release_id)["candidate"]["context_links"]), 3)
        self.digest = self.store.set_context_links(self.links(ids), expected_digest=self.digest)
        self.review_all()
        self.publish()

    def test_known_incompatible_dependency_windows_block_publication(self):
        ids = self.create(b"# One\nFirst\n# Two\nSecond\n")
        self.digest = self.store.set_lifecycle(ids[0], effective_from=LATER,
                                              reason="Future fixture", expected_digest=self.digest)
        self.digest = self.store.set_context_links(self.links(ids), expected_digest=self.digest)
        self.review_all()
        with self.assertRaises(KnowledgeError):
            self.publish()


class RetrievalTests(StoreHarness):
    def setUp(self):
        super().setUp()
        self.findings, self.registry = inputs()
        self.bind()

    def bind(self):
        self.binding = binding_from_tables(
            table(self.findings, FINDING_FIELDS, "finding_input", "findings"),
            table(self.registry, REGISTRY_FIELDS, "registry_input", "registry"))

    def query(self, release_id, selected=None, **changes):
        query = {"findings": {r["finding_id"]: r for r in (selected or self.findings[:1])},
                 "registry": {r["equipment_id"]: r for r in self.registry}}
        kwargs = dict(knowledge_version=release_id, assessment_time=NOW,
                      expected_strategy=strategy_binding(), allowed_input_binding=self.binding,
                      max_bytes=100000)
        kwargs.update(changes)
        return get_triage_knowledge(self.store, query, **kwargs)

    def test_binding_maps_immutable_and_raw_hashes_retained(self):
        with self.assertRaises(TypeError):
            self.binding.findings["F-1"]["finding_description"] = "bad"
        self.assertEqual(self.binding.manifest[0]["raw_sha256"],
                         table(self.findings, FINDING_FIELDS, "finding_input", "findings").raw_sha256)

    def test_code_source_star_conservatively_returns_cross_heading_context(self):
        self.create(b"# Main\nScope: Pumps\nMain rule.\n"
                    b"# Exception\nScope: Fans\nException to the earlier rule.\n",
                    keep_source_context=True)
        self.review_all()
        release_id = self.publish()
        release = self.store.resolve_release(release_id)
        self.assertEqual(release["candidate"]["context_links"][0]["kind"],
                         "conservative_source_context")
        result = self.query(release_id)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.provider_payload()), 2)
        self.assertEqual(result.to_dict()["selection_mode"], "conservative_expansion")
        self.assertEqual(result.evidence["expansion_reason"], "conservative_source_context")
        self.assertNotIn("expansion_reason", result.to_dict())
        self.assertTrue(result.evidence["conservative_expansion"])
        self.assertEqual(result.evidence["conservative_source_context_edges"], 1)
        self.assertEqual(len(result.evidence["context_added_item_ids"]), 1)
        self.assertNotIn("conservative_source_context", str(result.provider_payload()))

    def test_source_star_never_couples_different_submitted_sources(self):
        self.create(b"# Main\nScope: Pumps\nMain rule.\n"
                    b"# Qualifier\nScope: Fans\nCross-heading qualifier.\n",
                    keep_source_context=True)
        self.digest = self.store.add_source(extract_code(document(
            b"# Other source\nScope: Fans\nUnrelated source rule.\n", "other-source")),
            expected_digest=self.digest)
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.status, "ok")
        texts = "\n".join(result.provider_payload().values())
        self.assertIn("Cross-heading qualifier", texts)
        self.assertNotIn("Unrelated source rule", texts)

    def test_actual_row_mutation_not_just_ids_rejected(self):
        self.create()
        self.review_all()
        release_id = self.publish()
        self.findings[0]["finding_description"] = "Injected"
        result = self.query(release_id)
        self.assertEqual(result.error_code, "input_binding_mismatch")
        self.assertEqual(result.provider_payload(), {})
        self.assertEqual(result.to_dict()["entries"], {})

    def test_registry_mutation_rejected(self):
        self.create()
        self.review_all()
        release_id = self.publish()
        self.registry[1]["engineer_comment"] = "Injected"
        self.assertEqual(self.query(release_id).error_code, "input_binding_mismatch")

    def test_raw_row_order_changes_manifest_not_semantic_result(self):
        self.create()
        self.review_all()
        release_id = self.publish()
        before = self.query(release_id, selected=self.findings)
        self.findings.reverse()
        self.registry.reverse()
        self.bind()
        after = self.query(release_id, selected=self.findings)
        self.assertEqual(before.to_dict(), after.to_dict())
        self.assertNotEqual(before.evidence["authorized_input_manifest_sha256"],
                            after.evidence["authorized_input_manifest_sha256"])

    def test_scope_and_unicode_alias_selection_with_general_and_no_lexical_overinclusion(self):
        self.findings[0]["finding_description"] = "The condition is marked CAF\u00c9 indicator"
        self.findings[0]["equipment_type"] = self.registry[0]["equipment_type"] = "P\u00dcMPS"
        self.bind()
        self.create(("# General\nAlways qualify.\n# Pump\nScope: Rotors\nAliases: P\u00fcmps\n"
                     "Rotoronly.\n# Fan\nScope: Fans\nFanonly.\n"
                     "# Extra\nScope: Fans\nThe condition is Caf\u00e9 indicator.\n").encode())
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.to_dict()["selection_mode"], "scoped")
        texts = "\n".join(result.provider_payload().values())
        self.assertIn("Always qualify", texts)
        self.assertIn("Rotoronly", texts)
        self.assertNotIn("Caf\u00e9", texts)
        self.assertNotIn("Fanonly", texts)
        self.assertEqual(strategy_binding()["parameters"]["lexical"], "disabled")

    def test_unknown_type_and_mechanism_only_scope_expand_conservatively(self):
        self.create(b"# Known\nScope: Pumps\nPump rule.\n# Other\nScope: Fracture\nOther rule.\n")
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.to_dict()["selection_mode"], "conservative_expansion")
        self.assertEqual(len(result.to_dict()["entries"]), 2)

    def test_unknown_subject_type_expands(self):
        self.registry[0]["equipment_type"] = self.findings[0]["equipment_type"] = "Unknown"
        self.bind()
        self.create(b"# Known\nScope: Pumps\nPump rule.\n# Other\nScope: Fans\nFan rule.\n")
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.to_dict()["selection_mode"], "conservative_expansion")
        self.assertEqual(len(result.to_dict()["entries"]), 2)

    def test_overflow_no_partial_entries_or_text(self):
        self.create()
        self.review_all()
        result = self.query(self.publish(), max_bytes=1)
        self.assertEqual(result.error_code, "result_too_large")
        self.assertEqual(result.to_dict()["entries"], {})
        self.assertEqual(result.provider_payload(), {})
        self.assertNotIn("Always preserve", str(result.to_dict()))

    def test_exact_utf8_projection_byte_limit(self):
        self.create("# General\nPreserve the checkmark \u2713.\n".encode())
        self.review_all()
        release_id = self.publish()
        size = len(canonical_bytes(self.query(release_id).provider_payload()))
        self.assertEqual(self.query(release_id, max_bytes=size).status, "ok")
        self.assertEqual(self.query(release_id, max_bytes=size - 1).error_code, "result_too_large")

    def test_expired_successor_returns_gap_never_ancestor_source_text(self):
        first, second = self.create(b"# Old\nAncestor sentinel\n# New\nSuccessor sentinel\n")
        self.digest = self.store.replace_item(first, second, effective_from=NOW,
                                              reason="Software replacement", expected_digest=self.digest)
        self.digest = self.store.set_lifecycle(second, effective_until=LATER,
                                              reason="Software expiry", expected_digest=self.digest)
        self.review_all()
        release_id = self.publish()
        current = self.query(release_id)
        self.assertEqual(current.status, "ok")
        self.assertNotIn("Ancestor sentinel", str(current.provider_payload()))
        expired = self.query(release_id, assessment_time=LATER)
        self.assertEqual(expired.error_code, "knowledge_gap")
        self.assertEqual(expired.provider_payload(), {})

    def test_retired_future_expired_rejected_never_projected(self):
        ids = self.create(b"# Active\nActive sentinel.\n# Retired\nRetired sentinel.\n"
                          b"# Future\nFuture sentinel.\n# Expired\nExpired sentinel.\n"
                          b"# Rejected\nRejected sentinel.\n")
        self.digest = self.store.set_lifecycle(ids[1], status="retired", reason="Test retirement",
                                              expected_digest=self.digest)
        self.digest = self.store.set_lifecycle(ids[2], effective_from=LATER, reason="Test future",
                                              expected_digest=self.digest)
        self.digest = self.store.set_lifecycle(ids[3], effective_until=NOW, reason="Test expiry",
                                              expected_digest=self.digest)
        self.digest = self.store.reject_item(ids[4], reason="Test rejection", expected_digest=self.digest)
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.status, "ok")
        texts = str(result.provider_payload())
        self.assertIn("Active sentinel", texts)
        for word in ("Retired", "Future", "Expired", "Rejected", "Software", "reviewer"):
            self.assertNotIn(word, texts)
        self.assertEqual(len(result.to_dict()["entries"]), 1)

    def test_empty_active_view_is_knowledge_gap(self):
        item_id, = self.create()
        self.digest = self.store.set_lifecycle(item_id, status="retired", reason="Software fixture",
                                              expected_digest=self.digest)
        self.review_all()
        self.assertEqual(self.query(self.publish()).error_code, "knowledge_gap")

    def test_invalid_queries_strategy_and_release_fail_closed(self):
        self.create()
        self.review_all()
        release_id = self.publish()
        self.assertEqual(self.query(release_id, expected_strategy={}).error_code,
                         "strategy_binding_mismatch")
        self.assertEqual(self.query("sha256-" + "0" * 64).error_code, "unknown_or_invalid_release")
        self.assertEqual(self.query(release_id, assessment_time="today").error_code, "invalid_query")
        self.assertEqual(self.query(release_id, max_bytes=True).error_code, "invalid_query")
        self.findings[0]["unexpected"] = "Injected field"
        self.assertEqual(self.query(release_id).error_code, "invalid_query")

    def test_global_inactive_context_fails_even_when_not_relevant(self):
        ids = self.create(b"# Pump\nScope: Pumps\nPump rule.\n"
                          b"# Fan\nScope: Fans\nFan rule.\n"
                          b"# Fan qualifier\nScope: Fans\nQualifier.\n")
        for item_id in ids[1:]:
            self.digest = self.store.set_lifecycle(item_id, effective_from=LATER,
                                                  reason="Future context", expected_digest=self.digest)
        self.digest = self.store.set_context_links(self.links(ids[1:]), expected_digest=self.digest)
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.error_code, "invalid_dependency")
        self.assertEqual(result.provider_payload(), {})

    def test_bidirectional_cyclic_context_closure(self):
        ids = self.create(b"# Pump\nScope: Pumps\nPump rule.\n"
                          b"# Fan\nScope: Fans\nFan rule.\n"
                          b"# Fan qualifier\nScope: Fans\nQualifier.\n")
        self.digest = self.store.set_context_links(self.links(ids), expected_digest=self.digest)
        self.review_all()
        result = self.query(self.publish())
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.to_dict()["entries"]), 3)
        for address, entry in result.to_dict()["entries"].items():
            self.assertTrue(address.startswith("knowledge:item-"))
            self.assertEqual(set(entry), {"source_id", "source_sha256", "spans", "text", "scopes", "aliases"})


if __name__ == "__main__":
    unittest.main()
