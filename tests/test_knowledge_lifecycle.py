from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from tests.knowledge_support import CUTOFF, KnowledgeCase, tables
from triage_knowledge import (
    ContextBundle, KnowledgeError, build_context, candidate_digest, canonical_context_bytes,
    effective_guidance, verify_context,
)
from triage_knowledge.contracts import canonical_bytes, sha256
from triage_knowledge.workflow_export import WorkflowExport


class LifecycleTests(KnowledgeCase):
    def save(self, candidate):
        self.digest = self.store.save_draft(candidate, expected_digest=self.digest)
        self.candidate = candidate

    def test_invalid_lifecycle_states_and_windows_preserve_the_draft(self):
        original = self.store.draft_path.read_bytes()
        mutations = [
            {"status": "deleted"}, {"status": True}, {"extra": "unknown"},
            {"status": "retired"}, {"retirement_reason": "An active rule cannot have this."},
            {"effective_from": "2026-01-01"}, {"effective_until": False},
            {"effective_from": CUTOFF, "effective_until": CUTOFF},
            {"effective_from": "2027-01-01T00:00:00Z", "effective_until": CUTOFF},
        ]
        for mutation in mutations:
            candidate = deepcopy(self.candidate)
            candidate["guidance"]["psv-assessment"]["lifecycle"].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(KnowledgeError):
                self.store.save_draft(candidate, expected_digest=self.digest)
            self.assertEqual(self.store.draft_path.read_bytes(), original)

    def test_edit_retire_restore_preserves_pinned_history_and_requires_fresh_review(self):
        first = self.publish()
        selected, registry = tables()
        first_context = build_context(selected, registry, first, CUTOFF)
        self.digest = self.store.fork_release(first.knowledge_version, expected_digest=self.digest)
        candidate, _ = self.store.load_draft()
        candidate["guidance"]["psv-assessment"]["guidance"] = "Revised source-grounded assessment instruction."
        self.save(candidate)
        edited = self.publish()
        self.assertNotEqual(first.knowledge_version, edited.knowledge_version)
        self.digest = self.store.fork_release(edited.knowledge_version, expected_digest=self.digest)
        old_review = self.review()
        self.digest = self.store.retire_guidance(
            "psv-assessment", "Withdraw this obsolete instruction.", expected_digest=self.digest)
        self.assertEqual(self.store.load_draft()[0]["guidance"]["psv-assessment"]["change_reason"],
                         candidate["guidance"]["psv-assessment"]["change_reason"])
        with self.assertRaises(KnowledgeError):
            self.store.publish(old_review, published_at=CUTOFF)
        withdrawn = self.publish()
        empty = build_context(selected, registry, withdrawn, CUTOFF)
        self.assertEqual(empty.payload["managed_knowledge"]["guidance"], {})
        self.assertIn("Revised source-grounded", withdrawn.release_bytes.decode())
        self.assertNotIn("Revised source-grounded", empty.encoded.decode())
        self.assertEqual(build_context(selected, registry, first, CUTOFF).encoded, first_context.encoded)
        self.assertEqual(self.store.resolve_knowledge(first.knowledge_version).release_bytes, first.release_bytes)
        self.digest = self.store.fork_release(withdrawn.knowledge_version, expected_digest=self.digest)
        candidate, _ = self.store.load_draft()
        candidate["guidance"]["psv-assessment"]["lifecycle"].update(status="active", retirement_reason=None)
        candidate["guidance"]["psv-assessment"]["change_reason"] = "Explicit reviewed restoration."
        self.save(candidate)
        restored = self.publish()
        self.assertEqual(effective_guidance(restored.candidate, CUTOFF)[0], ("psv-assessment",))
        self.assertEqual(effective_guidance(withdrawn.candidate, CUTOFF)[0], ())

    def test_published_id_hard_deletion_is_rejected_but_unpublished_topic_can_be_removed(self):
        first = self.publish()
        self.digest = self.store.fork_release(first.knowledge_version, expected_digest=self.digest)
        candidate, _ = self.store.load_draft()
        candidate["guidance"].clear()
        self.save(candidate)
        with self.assertRaises(KnowledgeError) as error:
            self.publish()
        self.assertEqual(error.exception.code, "guidance_removal")
        self.assertEqual(len(list((self.store.root / "releases").glob("*.json"))), 1)
        candidate["guidance"] = deepcopy(first.candidate["guidance"])
        candidate["guidance"]["draft-only"] = deepcopy(candidate["guidance"]["psv-assessment"])
        self.save(candidate)
        del candidate["guidance"]["draft-only"]
        self.save(candidate)
        self.assertNotIn("draft-only", self.publish().candidate["guidance"])

    def test_inclusive_start_exclusive_end_and_timezone_equivalence(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["lifecycle"].update(
            effective_from=CUTOFF, effective_until="2026-02-01T00:00:00Z")
        self.save(candidate)
        snapshot = self.publish()
        cases = [
            ("2025-12-31T23:59:59Z", (), {"psv-assessment": "not_yet_effective"}),
            ("2026-01-01T07:00:00+07:00", ("psv-assessment",), {}),
            ("2026-01-31T23:59:59Z", ("psv-assessment",), {}),
            ("2026-02-01T00:00:00Z", (), {"psv-assessment": "expired"}),
        ]
        for cutoff, included, excluded in cases:
            with self.subTest(cutoff=cutoff):
                self.assertEqual(effective_guidance(snapshot.candidate, cutoff), (included, excluded))
                context = build_context(*tables(), snapshot, cutoff)
                self.assertEqual(tuple(context.payload["managed_knowledge"]["guidance"]), included)

    def test_scheduled_supersession_is_transitive_and_does_not_resurrect(self):
        candidate = deepcopy(self.candidate)
        first = deepcopy(candidate["guidance"]["psv-assessment"])
        first["supersedes"] = ["psv-assessment"]
        first["lifecycle"]["effective_from"] = "2026-03-01T00:00:00Z"
        second = deepcopy(first)
        second["supersedes"] = ["replacement"]
        second["lifecycle"].update(effective_from="2026-02-01T00:00:00Z",
                                   effective_until="2026-04-01T00:00:00Z")
        candidate["guidance"].update(replacement=first, successor=second)
        self.save(candidate)
        snapshot = self.publish()
        for cutoff, expected in [(CUTOFF, ("psv-assessment",)),
                                 ("2026-02-01T00:00:00Z", ("successor",)),
                                 ("2026-03-01T00:00:00Z", ("successor",)),
                                 ("2026-04-01T00:00:00Z", ())]:
            with self.subTest(cutoff=cutoff):
                self.assertEqual(effective_guidance(snapshot.candidate, cutoff)[0], expected)
        candidate["guidance"]["successor"]["lifecycle"].update(
            status="retired", retirement_reason="Cancel this instruction without reviving its ancestors.")
        self.save(candidate)
        self.assertEqual(effective_guidance(self.candidate, "2026-02-01T00:00:00Z")[0], ())

    def test_reference_windows_reject_future_dangling_dependencies_at_save(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["supporting"] = deepcopy(candidate["guidance"]["psv-assessment"])
        refs = candidate["guidance"]["psv-assessment"]["source_refs"]
        refs.append("knowledge:supporting:guidance")
        refs.sort()
        candidate["guidance"]["supporting"]["lifecycle"]["effective_until"] = "2026-02-01T00:00:00Z"
        with self.assertRaises(KnowledgeError) as error:
            self.store.validate(candidate)
        self.assertEqual(error.exception.code, "source_ref_window")
        candidate["guidance"]["psv-assessment"]["lifecycle"]["effective_until"] = "2026-02-01T00:00:00Z"
        self.store.validate(candidate)
        candidate["rubric"]["impact"][0]["source_refs"].append("knowledge:supporting:guidance")
        candidate["rubric"]["impact"][0]["source_refs"].sort()
        with self.assertRaises(KnowledgeError):
            self.store.validate(candidate)
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["supporting"] = deepcopy(candidate["guidance"]["psv-assessment"])
        candidate["guidance"]["supporting"]["lifecycle"].update(
            status="retired", retirement_reason="Withdraw the cited instruction.")
        candidate["guidance"]["psv-assessment"]["source_refs"].append("knowledge:supporting:guidance")
        with self.assertRaises(KnowledgeError):
            self.store.validate(candidate)

    def test_rehashed_old_context_cannot_bypass_expiration(self):
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["lifecycle"]["effective_until"] = CUTOFF
        self.save(candidate)
        snapshot = self.publish()
        selected, registry = tables()
        prior = build_context(selected, registry, snapshot, "2025-12-31T00:00:00Z").to_dict()
        prior["assessment_time"] = CUTOFF
        prior["context_hash"] = sha256(canonical_context_bytes(prior))
        forged = ContextBundle(canonical_bytes(prior))
        with self.assertRaises(KnowledgeError):
            verify_context(forged, snapshot, selected, registry, CUTOFF)
        with self.assertRaises(KnowledgeError):
            WorkflowExport.from_bundle(snapshot, forged, selected, registry, CUTOFF)

    def test_legacy_release_and_projection_are_preserved_by_explicit_upgrade(self):
        legacy = deepcopy(self.candidate)
        legacy["schema_version"] = 1
        for entry in legacy["guidance"].values():
            del entry["lifecycle"]
        body = {"candidate": legacy, "review": asdict(self.review(candidate_digest(legacy))),
                "published_at": CUTOFF}
        version = "sha256-" + sha256(canonical_bytes(body))
        raw = canonical_bytes({**body, "release_id": version})
        path = self.store.root / "releases" / f"{version}.json"
        path.parent.mkdir()
        path.write_bytes(raw)
        snapshot = self.store.resolve_knowledge(version)
        before = build_context(*tables(), snapshot, CUTOFF)
        self.assertEqual(before.payload["managed_knowledge"], {
            "rubric": legacy["rubric"], "guidance": legacy["guidance"],
            "active_guidance_ids": ["psv-assessment"], "superseded_guidance_ids": [],
            "authority": "Supplied domain notes remain authoritative. Only active managed guidance "
                         "is included. Superseded text is excluded from assessment context.",
        })
        self.save(legacy)
        old_review = self.review()
        with self.assertRaises(KnowledgeError) as error:
            self.publish()
        self.assertEqual(error.exception.code, "schema_upgrade")
        self.digest = self.store.upgrade_draft(expected_digest=self.digest)
        upgraded, _ = self.store.load_draft()
        self.assertEqual(upgraded["schema_version"], 2)
        self.assertEqual(upgraded["base_release_id"], legacy["base_release_id"])
        self.assertEqual(upgraded["guidance"]["psv-assessment"]["guidance"],
                         legacy["guidance"]["psv-assessment"]["guidance"])
        with self.assertRaises(KnowledgeError):
            self.store.publish(old_review, published_at=CUTOFF)
        self.digest = self.store.fork_release(version, expected_digest=self.digest)
        self.assertEqual(self.store.load_draft()[0]["base_release_id"], version)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(build_context(*tables(), self.store.resolve_knowledge(version), CUTOFF).encoded,
                         before.encoded)

    def test_stale_retirement_does_not_overwrite_newer_draft(self):
        old = self.digest
        candidate = deepcopy(self.candidate)
        candidate["guidance"]["psv-assessment"]["change_reason"] = "A newer saved change."
        self.save(candidate)
        before = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError):
            self.store.retire_guidance("psv-assessment", "A stale withdrawal.", expected_digest=old)
        self.assertEqual(before, self.store.draft_path.read_bytes())

    def test_legacy_maintenance_citations_need_explicit_repair_not_silent_retargeting(self):
        legacy = deepcopy(self.candidate)
        legacy["schema_version"] = 1
        legacy["guidance"]["supporting"] = deepcopy(legacy["guidance"]["psv-assessment"])
        for entry in legacy["guidance"].values():
            del entry["lifecycle"]
        refs = legacy["guidance"]["psv-assessment"]["source_refs"]
        refs.append("knowledge:supporting:change_reason")
        refs.sort()
        self.save(legacy)
        before = self.store.draft_path.read_bytes()
        with self.assertRaises(KnowledgeError) as error:
            self.store.upgrade_draft(expected_digest=self.digest)
        self.assertEqual(error.exception.code, "source_ref")
        self.assertEqual(self.store.draft_path.read_bytes(), before)
