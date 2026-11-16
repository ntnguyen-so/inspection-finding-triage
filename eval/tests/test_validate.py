import copy
import json
import tempfile
import unittest
from pathlib import Path

from eval.validate import (
    ROOT,
    check_hashes,
    digest,
    headings,
    profile_sources,
    validate,
    validate_cards,
    validate_manifest,
)


class EvaluationIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "eval" / "spec" / "split.json").read_text(encoding="utf-8"))
        cls.source_root = ROOT / cls.manifest["source_root"]
        cls.findings, cls.equipment, _ = profile_sources(cls.source_root)
        cls.sections = {
            "brief": headings(cls.source_root / "README.md"),
            "domain": headings(cls.source_root / "reference" / "domain_knowledge.md"),
        }
        cls.group_map = validate_manifest(
            cls.manifest, cls.findings, cls.equipment, cls.sections,
        )
        cls.cards = {
            partition: [
                json.loads(line) for line in
                (ROOT / "eval" / "data" / f"{partition}.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            for partition in ("development", "test")
        }

    def check_manifest(self, manifest):
        return validate_manifest(manifest, self.findings, self.equipment, self.sections)

    def check_cards(self, cards, partition="development"):
        validate_cards(
            cards, partition, self.manifest, self.findings,
            self.equipment, self.sections, self.group_map,
        )

    def test_partition_omission_and_overlap_are_rejected(self):
        for overlap in (False, True):
            with self.subTest(overlap=overlap):
                manifest = copy.deepcopy(self.manifest)
                identifier = manifest["partitions"]["development"].pop()
                if overlap:
                    manifest["partitions"]["development"].append(identifier)
                    manifest["partitions"]["test"].append(identifier)
                with self.assertRaisesRegex(ValueError, "cover all|Repeated partition"):
                    self.check_manifest(manifest)

    def test_moving_only_one_pump_breaks_the_binding_group(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["partitions"]["development"].remove("F-1003")
        manifest["partitions"]["test"].append("F-1003")
        with self.assertRaisesRegex(ValueError, "crosses partitions"):
            self.check_manifest(manifest)

    def test_redundancy_cannot_be_hidden_by_redefining_groups(self):
        manifest = copy.deepcopy(self.manifest)
        group = next(group for group in manifest["groups"] if group["group_id"] == "firewater-pair")
        group["finding_ids"].remove("F-1003")
        manifest["groups"].append({
            "group_id": "separated-pump",
            "finding_ids": ["F-1003"],
            "reason": "Invalid mutation for test",
            "sources": ["finding:F-1003:finding_description"],
        })
        with self.assertRaisesRegex(ValueError, "Redundant pair split"):
            self.check_manifest(manifest)

    def test_cross_partition_and_unresolvable_citations_are_rejected(self):
        for partition, foreign_id in (("development", "F-1002"), ("test", "F-1001")):
            for reference, message in (
                (f"finding:{foreign_id}:finding_description", "Cross-partition"),
                ("equipment:K-3401:nonexistent", "Unresolved citation"),
                ("domain:Invented policy", "Unresolved citation"),
            ):
                with self.subTest(partition=partition, reference=reference):
                    cards = copy.deepcopy(self.cards[partition])
                    cards[0]["required_evidence"][0]["sources"] = [reference]
                    with self.assertRaisesRegex(ValueError, message):
                        self.check_cards(cards, partition)

    def test_literal_cross_partition_finding_ids_in_prose_are_rejected(self):
        for partition, foreign_id in (("development", "F-1002"), ("test", "F-1001")):
            with self.subTest(partition=partition):
                cards = copy.deepcopy(self.cards[partition])
                cards[0]["required_evidence"][0]["text"] = f"Read {foreign_id} for this decision."
                with self.assertRaisesRegex(ValueError, "finding ID in prose"):
                    self.check_cards(cards, partition)

    def test_card_omission_duplicate_and_mapping_are_rejected(self):
        mutations = (
            (lambda cards: cards.pop(), "do not cover"),
            (lambda cards: cards.append(copy.deepcopy(cards[0])), "duplicate evidence card"),
            (lambda cards: cards[0].update(equipment_id="UNKNOWN-0000"), "equipment mismatch"),
            (lambda cards: cards[0].update(related_findings=[]), "context mismatch"),
            (lambda cards: cards[0].update(expected_score=9), "evidence-card fields"),
        )
        for partition in ("development", "test"):
            for mutate, message in mutations:
                with self.subTest(partition=partition, message=message):
                    cards = copy.deepcopy(self.cards[partition])
                    mutate(cards)
                    with self.assertRaisesRegex(ValueError, message):
                        self.check_cards(cards, partition)

    def test_source_or_annotation_drift_fails_hash_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "reference.jsonl"
            path.write_text("original", encoding="utf-8")
            expected = {"reference.jsonl": digest(path)}
            check_hashes(root, expected, {"reference.jsonl"})
            path.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                check_hashes(root, expected, {"reference.jsonl"})

    def test_complete_references_pass(self):
        summary = validate(allow_draft=True)
        self.assertEqual(summary["partition_counts"]["development"]["cases"],
                         len(self.cards["development"]))
        self.assertEqual(summary["findings"], sum(
            partition["cases"] for partition in summary["partition_counts"].values()
        ))


if __name__ == "__main__":
    unittest.main()
