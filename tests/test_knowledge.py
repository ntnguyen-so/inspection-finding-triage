from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from unittest.mock import patch

from tests.knowledge_support import CUTOFF, DOMAIN, KnowledgeCase
from triage_knowledge import KnowledgeError, KnowledgeStore, active_guidance, candidate_diff
from triage_knowledge.contracts import canonical_bytes, sha256, strict_json
from triage_knowledge.knowledge import domain_sections, validate_snapshot


class StoreTests(KnowledgeCase):
    def test_strict_json_and_canonical_oracle(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1.0}', '{"a":'):
            with self.subTest(raw=raw), self.assertRaises(KnowledgeError):
                strict_json(raw)
        expected = b'{"a":1,"b":2}'
        self.assertEqual(canonical_bytes({"b": 2, "a": 1}), expected)
        self.assertEqual(sha256(expected),
                         "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777")
        self.assertEqual(canonical_bytes({"check": "\u2713"}), b'{"check":"\xe2\x9c\x93"}')

    def test_candidate_schema_and_source_failures_are_explicit(self):
        mutations = [
            lambda x: x.update(schema_version=True),
            lambda x: x.update(extra="not supported"),
            lambda x: x["domain_source"].update(path="other.md"),
            lambda x: x["domain_source"].update(sha256="0" * 64),
            lambda x: x["rubric"]["likelihood"][0].update(minimum=True),
            lambda x: x["rubric"]["impact"][1].update(minimum=4),
            lambda x: x["rubric"]["impact"][-1].update(maximum=9),
            lambda x: x["rubric"].update(confirmed_required_function_failure_band=[1, 10]),
            lambda x: x["guidance"]["psv-assessment"].update(urgency=10),
            lambda x: x["guidance"]["psv-assessment"].update(title=" "),
            lambda x: x["guidance"]["psv-assessment"].update(dimension=[]),
            lambda x: x["guidance"]["psv-assessment"].update(scope={}),
            lambda x: x["guidance"]["psv-assessment"].update(source_refs=["domain:Missing"]),
            lambda x: x["guidance"]["psv-assessment"].update(source_refs=["knowledge:psv-assessment:guidance"]),
            lambda x: x["guidance"]["psv-assessment"].update(supersedes=["domain:What moves impact"]),
            lambda x: x["guidance"].update(broken="not an entry"),
        ]
        before = self.store.draft_path.read_bytes()
        for mutate in mutations:
            candidate = deepcopy(self.candidate)
            mutate(candidate)
            with self.subTest(mutation=mutate), self.assertRaises(KnowledgeError):
                self.store.save_draft(candidate, expected_digest=self.digest)
            self.assertEqual(before, self.store.draft_path.read_bytes())

    def test_supersession_is_scoped_acyclic_and_unambiguous(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["replacement"] = deepcopy(candidate["guidance"]["psv-assessment"])
        candidate["guidance"]["replacement"]["supersedes"] = ["psv-assessment"]
        self.store.validate(candidate)
        self.assertEqual(active_guidance(candidate), ("replacement",))
        invalid = deepcopy(candidate)
        invalid["guidance"]["replacement"]["scope"] = "all"
        with self.assertRaises(KnowledgeError):
            self.store.validate(invalid)
        invalid = deepcopy(candidate)
        invalid["guidance"]["psv-assessment"]["supersedes"] = ["replacement"]
        with self.assertRaises(KnowledgeError):
            self.store.validate(invalid)
        invalid = deepcopy(candidate)
        invalid["guidance"]["second"] = deepcopy(candidate["guidance"]["replacement"])
        with self.assertRaises(KnowledgeError):
            self.store.validate(invalid)
        invalid = deepcopy(candidate)
        invalid["guidance"]["replacement"]["source_refs"] = sorted([
            *invalid["guidance"]["replacement"]["source_refs"], "knowledge:psv-assessment:guidance",
        ])
        with self.assertRaises(KnowledgeError):
            self.store.validate(invalid)

    def test_failure_band_declaration_must_match_the_actual_top_band(self):
        candidate = deepcopy(self.candidate)
        candidate["rubric"]["likelihood"][-2]["maximum"] = 9
        candidate["rubric"]["likelihood"][-1]["minimum"] = 10
        with self.assertRaises(KnowledgeError):
            self.store.validate(candidate)

    def test_stale_save_and_stale_review_do_not_publish(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["change_reason"] = "Revised source review."
        self.store.save_draft(candidate, expected_digest=self.digest)
        with self.assertRaisesRegex(KnowledgeError, "changed"):
            self.store.save_draft(self.candidate, expected_digest=self.digest)
        with self.assertRaises(KnowledgeError) as error:
            self.store.publish(self.review(), published_at=CUTOFF)
        self.assertEqual(error.exception.code, "stale_review")
        self.assertFalse((self.store.root / "releases").exists())

    def test_review_is_required_and_times_are_validated(self):
        for review in (replace(self.review(), reviewer=" "),
                       replace(self.review(), reviewed_at="2026-01-01T00:00:00"),
                       replace(self.review(), reviewed_at="2027-01-01T00:00:00+00:00")):
            with self.subTest(review=review), self.assertRaises(KnowledgeError):
                self.store.publish(review, published_at=CUTOFF)

    def test_release_identity_immutability_and_no_fallback(self):
        snapshot = self.publish()
        original = snapshot.release_bytes
        path = self.store.root / "releases" / f"{snapshot.knowledge_version}.json"
        with self.assertRaises(KnowledgeError) as duplicate:
            self.store.publish(self.review(), published_at=CUTOFF)
        self.assertEqual(duplicate.exception.code, "already_exists")
        self.assertEqual(path.read_bytes(), original)
        for version in ("latest", "../drafts/working", "sha256-" + "0" * 64):
            with self.subTest(version=version), self.assertRaises(KnowledgeError):
                self.store.resolve_knowledge(version)
        changed = snapshot.release
        changed["review"]["rationale"] = "Changed bytes."
        path.write_bytes(canonical_bytes(changed))
        with self.assertRaises(KnowledgeError) as error:
            self.store.resolve_knowledge(snapshot.knowledge_version)
        self.assertEqual(error.exception.code, "release_hash")

    def test_publication_metadata_produces_a_new_release(self):
        first = self.publish()
        second = self.store.publish(self.review(rationale="A separate declared review."),
                                    published_at=CUTOFF)
        self.assertNotEqual(first.knowledge_version, second)
        self.assertEqual(first.candidate, self.store.resolve_knowledge(second).candidate)

    def test_snapshot_and_rubric_are_detached_and_frozen(self):
        snapshot = self.publish()
        changed = snapshot.candidate
        changed["guidance"].clear()
        self.assertTrue(snapshot.candidate["guidance"])
        with self.assertRaises(FrozenInstanceError):
            snapshot.rubric.likelihood[0].minimum = 2
        self.domain.write_bytes(DOMAIN.replace(b"\r\n", b"\n"))
        with self.assertRaises(KnowledgeError):
            self.store.resolve_knowledge(snapshot.knowledge_version)
        validate_snapshot(snapshot)
        self.assertEqual(snapshot.domain_bytes, DOMAIN)

    def test_fork_and_field_diff_preserve_existing_release(self):
        snapshot = self.publish()
        new_digest = self.store.fork_release(snapshot.knowledge_version, expected_digest=self.digest)
        candidate, actual = self.store.load_draft()
        self.assertEqual(new_digest, actual)
        self.assertEqual(candidate["base_release_id"], snapshot.knowledge_version)
        candidate["guidance"]["psv-assessment"]["guidance"] = "Review documented functional evidence."
        difference = candidate_diff(snapshot.candidate, candidate)
        self.assertIn("/guidance/psv-assessment/guidance", [item["field"] for item in difference])
        self.assertEqual(self.store.resolve_knowledge(snapshot.knowledge_version).release_bytes,
                         snapshot.release_bytes)

    def test_failed_atomic_save_preserves_previous_draft(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["change_reason"] = "An attempted edit."
        original = self.store.draft_path.read_bytes()
        with patch("triage_knowledge.knowledge.os.replace", side_effect=OSError("Synthetic failure")):
            with self.assertRaises(KnowledgeError) as error:
                self.store.save_draft(candidate, expected_digest=self.digest)
        self.assertEqual(error.exception.code, "storage_write")
        self.assertEqual(self.store.draft_path.read_bytes(), original)
        self.assertEqual(list(self.store.draft_path.parent.glob(".knowledge-*.tmp")), [])

    def test_cleanup_failure_reports_that_destination_may_already_exist(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["change_reason"] = "A saved edit."
        with patch("triage_knowledge.knowledge.Path.unlink", side_effect=OSError("Synthetic cleanup failure")):
            with self.assertRaises(KnowledgeError) as error:
                self.store.save_draft(candidate, expected_digest=self.digest)
        self.assertEqual(error.exception.code, "storage_cleanup")
        self.assertIn("destination may exist", str(error.exception))
        self.assertEqual(self.store.load_draft()[0], candidate)

    def test_domain_sections_preserve_bytes_and_reject_ambiguous_headings(self):
        sections = domain_sections(DOMAIN)
        self.assertIn("\r\n", sections["What moves impact"])
        with self.assertRaises(KnowledgeError):
            domain_sections(DOMAIN + b"\r\n## What moves impact\r\nAmbiguous.\r\n")

    def test_resolution_rejects_noncanonical_artifact_bytes(self):
        snapshot = self.publish()
        path = self.store.root / "releases" / f"{snapshot.knowledge_version}.json"
        path.write_text(json.dumps(snapshot.release, indent=2), encoding="utf-8")
        with self.assertRaises(KnowledgeError):
            self.store.resolve_knowledge(snapshot.knowledge_version)

    def test_domain_physical_location_is_not_release_identity(self):
        snapshot = self.publish()
        relocated = self.root / "relocated-domain.md"
        relocated.write_bytes(DOMAIN)
        store = KnowledgeStore(self.store.root, relocated, domain_locator="domain.md")
        self.assertEqual(store.resolve_knowledge(snapshot.knowledge_version).release_bytes, snapshot.release_bytes)
        with self.assertRaises(KnowledgeError):
            KnowledgeStore(self.store.root, relocated, domain_locator=r"C:\machine-specific\domain.md")

    def test_explicit_recovery_archives_exact_invalid_bytes(self):
        self.store.draft_path.write_bytes(b'{"broken":')
        original = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError):
            self.store.recover_draft(self.candidate, expected_raw_sha256="0" * 64)
        digest = self.store.recover_draft(self.candidate, expected_raw_sha256=sha256(original))
        self.assertEqual(digest, self.digest)
        self.assertEqual((self.store.root / "drafts" / "archive" / f"{sha256(original)}.json").read_bytes(),
                         original)
        with self.assertRaises(KnowledgeError):
            self.store.recover_draft(self.candidate,
                                     expected_raw_sha256=sha256(self.store.draft_path.read_bytes()))
