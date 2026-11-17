"""Offline integrity checks for this package's evaluation references, not tickets."""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "README.md",
    "data\\equipment_registry.csv",
    "data\\inspection_findings.csv",
    "reference\\README.md",
    "reference\\domain_knowledge.md",
    "reference\\example_ticket.json",
}
ARTIFACTS = {
    "docs\\original-decision-process\\02_DATA_EVALUATION_PLAN.md",
    "docs\\original-decision-process\\03_EVALUATION_ACCEPTANCE.md",
    "eval\\spec\\acceptance.json",
    "eval\\assess.py",
    "eval\\spec\\probes.json",
    "eval\\data\\development.jsonl",
    "eval\\data\\test.jsonl",
    "eval\\validate.py",
    "eval\\tests\\test_validate.py",
    "eval\\tests\\test_assess.py",
}
FINDING_FIELDS = (
    "finding_id", "reported_date", "equipment_id", "equipment_type",
    "inspection_type", "inspection_method", "finding_description",
    "reported_by", "reporter_role",
)
EQUIPMENT_FIELDS = (
    "equipment_id", "equipment_type", "service_description", "criticality_score",
    "reliability_score", "safety_critical_element", "redundancy", "engineer_comment",
)
NOTE_FIELDS = (
    "observed_facts", "required_evidence", "expected_behavior",
    "forbidden_claims", "unknowns", "action_constraints",
)
CARD_FIELDS = {
    "finding_id", "equipment_id", "group_id", "related_findings", "tags",
    "reference_status", *NOTE_FIELDS,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and all(nonempty_string(item) for item in value)


def local_path(root, relative):
    require(nonempty_string(relative), "Path must be a non-empty relative string")
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), f"Path escapes root: {relative}")
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hashes(root, expected, required):
    require(isinstance(expected, dict) and set(expected) == required,
            "Hash inventory does not match required files")
    for relative, expected_hash in expected.items():
        require(isinstance(expected_hash, str)
                and re.fullmatch(r"[a-f0-9]{64}", expected_hash) is not None,
                f"Invalid SHA-256: {relative}")
        require(digest(local_path(root, relative)) == expected_hash,
                f"SHA-256 mismatch: {relative}; review/version the change")


def read_csv(path, fields):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == list(fields), f"Unexpected CSV header: {path.name}")
        rows = list(reader)
    for number, row in enumerate(rows, start=2):
        require(set(row) == set(fields)
                and all(nonempty_string(value) for value in row.values()),
                f"Missing/extra/blank CSV cell: {path.name}, record {number}")
    counts = Counter(row[fields[0]] for row in rows)
    require(all(count == 1 for count in counts.values()),
            f"Duplicate primary key: {path.name}")
    return {row[fields[0]]: row for row in rows}


def profile_sources(source_root):
    findings = read_csv(source_root / "data" / "inspection_findings.csv", FINDING_FIELDS)
    equipment = read_csv(source_root / "data" / "equipment_registry.csv", EQUIPMENT_FIELDS)
    require(len(findings) == 21 and len(equipment) == 18,
            "Expected the supplied 21 findings and 18 equipment records")
    missing_partners = []
    for identifier, row in equipment.items():
        require(re.fullmatch(r"[A-Z]+-\d{4}", identifier) is not None,
                f"Invalid equipment ID: {identifier}")
        for field in ("criticality_score", "reliability_score"):
            require(re.fullmatch(r"(?:[1-9]|10)", row[field]) is not None,
                    f"Invalid {field}: {identifier}")
        require(row["safety_critical_element"] in {"Yes", "No"},
                f"Invalid SCE value: {identifier}")
        for partner in re.findall(r"\(([A-Z]+-\d+)\)", row["redundancy"]):
            if partner not in equipment:
                missing_partners.append({"equipment_id": identifier, "partner": partner})
    for identifier, row in findings.items():
        require(re.fullmatch(r"F-\d{4}", identifier) is not None,
                f"Invalid finding ID: {identifier}")
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["reported_date"]) is not None,
                f"Invalid ISO date format: {identifier}")
        try:
            date.fromisoformat(row["reported_date"])
        except ValueError as error:
            raise ValueError(f"Invalid calendar date: {identifier}") from error
        require(row["equipment_id"] in equipment, f"Orphan finding: {identifier}")
        require(row["equipment_type"] == equipment[row["equipment_id"]]["equipment_type"],
                f"Equipment type mismatch: {identifier}")
    summary = {
        "findings": len(findings),
        "equipment": len(equipment),
        "blank_cells": 0,
        "duplicate_primary_keys": 0,
        "orphan_findings": 0,
        "equipment_type_mismatches": 0,
        "invalid_ids_dates_scores_sce": 0,
        "date_range": [
            min(row["reported_date"] for row in findings.values()),
            max(row["reported_date"] for row in findings.values()),
        ],
        "sce_counts": dict(Counter(row["safety_critical_element"] for row in equipment.values())),
        "redundancy_counts": dict(Counter(row["redundancy"] for row in equipment.values())),
        "missing_redundant_partners": missing_partners,
    }
    return findings, equipment, summary


def headings(path):
    return set(re.findall(r"^#{1,6}\s+(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE))


def check_reference(reference, findings, equipment, sections, allowed_findings):
    require(nonempty_string(reference), "Citation must be a string")
    parts = reference.split(":")
    if len(parts) == 3 and parts[0] in {"finding", "equipment"}:
        kind, identifier, field = parts
        rows = findings if kind == "finding" else equipment
        require(identifier in rows and field in rows[identifier],
                f"Unresolved citation: {reference}")
        if kind == "finding":
            require(identifier in allowed_findings,
                    f"Cross-partition finding citation: {reference}")
    else:
        require(len(parts) == 2 and parts[0] in sections
                and parts[1] in sections[parts[0]], f"Unresolved citation: {reference}")


def validate_manifest(manifest, findings, equipment, sections):
    require(isinstance(manifest, dict), "Manifest must be an object")
    require(manifest.get("status") in {"draft", "frozen"}, "Invalid freeze status")
    require(nonempty_string(manifest.get("version")), "Missing reference version")
    require(manifest.get("reference_status") == "ai_assisted_provisional_not_expert_certified",
            "Missing provisional-reference disclosure")
    require(manifest.get("test_claim") ==
            "non_blind_procedural_freeze_prior_exposure_to_all_21_findings",
            "Missing prior-exposure disclosure")
    partitions = manifest.get("partitions")
    require(isinstance(partitions, dict) and set(partitions) == {"development", "test"},
            "Expected development and test partitions")
    owners = {}
    for partition, identifiers in partitions.items():
        require(string_list(identifiers) and identifiers, f"Empty/invalid partition: {partition}")
        for identifier in identifiers:
            require(identifier in findings, f"Unknown partition finding: {identifier}")
            require(identifier not in owners, f"Repeated partition finding: {identifier}")
            owners[identifier] = partition
    require(set(owners) == set(findings), "Partitions do not cover all findings")
    require(owners.get("F-1005") == "development", "Published example must stay in development")
    groups = manifest.get("groups")
    require(isinstance(groups, list) and groups, "Missing binding groups")
    group_ids = set()
    group_by_finding = {}
    for group in groups:
        require(isinstance(group, dict), "Group must be an object")
        group_id = group.get("group_id")
        require(nonempty_string(group_id) and group_id not in group_ids,
                f"Missing/duplicate group ID: {group_id}")
        group_ids.add(group_id)
        members = group.get("finding_ids")
        require(string_list(members) and members and len(members) == len(set(members)),
                f"Invalid group members: {group_id}")
        require(all(member in owners for member in members), f"Unknown group member: {group_id}")
        require(len({owners[member] for member in members}) == 1,
                f"Binding group crosses partitions: {group_id}")
        require(nonempty_string(group.get("reason")), f"Missing group reason: {group_id}")
        require(string_list(group.get("sources")) and group["sources"],
                f"Missing group sources: {group_id}")
        allowed = set(partitions[owners[members[0]]])
        for reference in group["sources"]:
            check_reference(reference, findings, equipment, sections, allowed)
        for member in members:
            require(member not in group_by_finding, f"Repeated group member: {member}")
            group_by_finding[member] = group_id
    require(set(group_by_finding) == set(findings), "Groups do not cover all findings")
    by_equipment = defaultdict(list)
    for identifier, row in findings.items():
        by_equipment[row["equipment_id"]].append(identifier)
    for identifier, members in by_equipment.items():
        require(len({group_by_finding[member] for member in members}) == 1,
                f"Same-equipment findings split across groups: {identifier}")
        for partner in re.findall(r"\(([A-Z]+-\d+)\)", equipment[identifier]["redundancy"]):
            combined = members + by_equipment.get(partner, [])
            require(len({group_by_finding[member] for member in combined}) == 1,
                    f"Redundant pair split across groups: {identifier}, {partner}")
    return group_by_finding


def validate_cards(cards, partition, manifest, findings, equipment, sections, group_map):
    require(isinstance(cards, list), f"Cards must be a list: {partition}")
    expected = set(manifest["partitions"][partition])
    seen = set()
    for card in cards:
        require(isinstance(card, dict) and set(card) == CARD_FIELDS,
                f"Unexpected/missing evidence-card fields: {partition}")
        identifier = card["finding_id"]
        require(isinstance(identifier, str) and identifier in expected and identifier not in seen,
                f"Unexpected/duplicate evidence card: {identifier}")
        seen.add(identifier)
        require(card["equipment_id"] == findings[identifier]["equipment_id"],
                f"Card equipment mismatch: {identifier}")
        require(card["group_id"] == group_map[identifier], f"Card group mismatch: {identifier}")
        related = card["related_findings"]
        require(string_list(related) and len(related) == len(set(related)),
                f"Invalid related findings: {identifier}")
        group_peers = {other for other, group in group_map.items()
                       if group == card["group_id"] and other != identifier}
        require(set(related) == group_peers, f"Card group context mismatch: {identifier}")
        require(string_list(card["tags"]) and card["tags"], f"Missing coverage tags: {identifier}")
        require(card["reference_status"] == "ai_assisted_provisional",
                f"Missing card provenance: {identifier}")
        for field in NOTE_FIELDS:
            require(isinstance(card[field], list) and card[field], f"Missing {field}: {identifier}")
            for note in card[field]:
                require(isinstance(note, dict) and set(note) == {"text", "basis", "sources"},
                        f"Invalid statement shape: {identifier}/{field}")
                require(nonempty_string(note["text"])
                        and note["basis"] in {"data", "domain", "design"},
                        f"Invalid statement text/basis: {identifier}/{field}")
                mentioned = set(re.findall(r"\bF-\d{4}\b", note["text"]))
                require(mentioned <= expected,
                        f"Cross-partition finding ID in prose: {identifier}/{field}")
                require(field != "observed_facts" or note["basis"] == "data",
                        f"Observed fact is not data-derived: {identifier}")
                require(string_list(note["sources"]) and note["sources"],
                        f"Missing statement citation: {identifier}/{field}")
                for reference in note["sources"]:
                    check_reference(reference, findings, equipment, sections, expected)
    require(seen == expected, f"Evidence cards do not cover {partition}: {sorted(expected - seen)}")


def validate_acceptance_spec(spec, version, findings, equipment, sections):
    require(isinstance(spec, dict) and spec.get("reference_version") == version,
            "Acceptance specification reference version mismatch")
    require(spec.get("status") == "specification_only_no_system_results",
            "Acceptance spec must not claim system execution")
    require(spec.get("review_dimensions") == ["grounding", "planning", "uncertainty"],
            "Unexpected semantic review dimensions")
    scenarios = spec.get("scenarios")
    require(isinstance(scenarios, list), "Acceptance scenarios must be an array")
    expected_ids = {
        f"{question}{number:02d}"
        for question, count in (("A", 4), ("B", 3), ("C", 4), ("D", 4), ("X", 2))
        for number in range(1, count + 1)
    }
    seen = set()
    for scenario in scenarios:
        require(isinstance(scenario, dict), "Acceptance scenario must be an object")
        identifier = scenario.get("id")
        require(isinstance(identifier, str) and identifier in expected_ids
                and identifier not in seen, f"Unexpected/duplicate acceptance scenario: {identifier}")
        seen.add(identifier)
        require(scenario.get("question") == identifier[0]
                and scenario.get("status") == "not_run_no_system",
                f"Scenario question/execution disclosure mismatch: {identifier}")
        for field in ("kind", "basis"):
            require(nonempty_string(scenario.get(field)), f"Missing {field}: {identifier}")
        for field in ("setup", "pass_criteria", "evidence_required", "sources"):
            require(string_list(scenario.get(field)) and scenario[field],
                    f"Missing scenario {field}: {identifier}")
        for reference in scenario["sources"]:
            check_reference(reference, findings, equipment, sections, set(findings))
    require(seen == expected_ids, "Acceptance scenarios do not cover the declared A-D/cross-cutting cases")
    policy = spec.get("urgency_constraints")
    require(isinstance(policy, dict) and policy.get("basis") == "design"
            and policy.get("formula_selected") is False
            and policy.get("base_monotonic") is True,
            "Urgency constraints must disclose design basis and unselected formula")
    anchors = policy.get("anchors")
    require(isinstance(anchors, list), "Missing urgency anchors")
    combinations = set()
    for anchor in anchors:
        require(isinstance(anchor, dict), "Anchor must be an object")
        likelihood, impact = anchor.get("likelihood"), anchor.get("impact")
        require(type(likelihood) is int and type(impact) is int
                and likelihood in {1, 10} and impact in {1, 10}, "Invalid anchor inputs")
        require((likelihood, impact) not in combinations, "Duplicate urgency anchor")
        combinations.add((likelihood, impact))
        band = anchor.get("allowed_urgency")
        require(isinstance(band, list) and len(band) == 2
                and all(type(value) is int for value in band)
                and 1 <= band[0] <= band[1] <= 10, "Invalid anchor urgency band")
    require(combinations == {(1, 1), (10, 1), (1, 10), (10, 10)}, "Incomplete urgency anchors")
    return len(scenarios)


def validate_probes(probes, manifest, findings, equipment, sections):
    require(isinstance(probes, dict) and probes.get("reference_version") == manifest["version"],
            "Probe reference version mismatch")
    b02 = probes.get("b02")
    require(isinstance(b02, dict) and b02.get("status") == "not_run_no_model",
            "PSV probe must disclose no model execution")
    require(b02.get("nominal_requests") == 4 and b02.get("repeats_per_condition") == 1
            and b02.get("maximum_requests_including_retries") == 8,
            "PSV probe request budget mismatch")
    positive = b02.get("positive_input")
    require(isinstance(positive, dict) and isinstance(positive.get("finding"), dict)
            and isinstance(positive.get("equipment"), dict), "Missing synthetic PSV input")
    finding, row = positive["finding"], positive["equipment"]
    require(set(finding) == set(FINDING_FIELDS) and set(row) == set(EQUIPMENT_FIELDS),
            "Synthetic input must use the supplied CSV field shape")
    require(re.fullmatch(r"F-[0-9]{4}", finding["finding_id"]) is not None
            and finding["finding_id"] not in findings, "Synthetic finding must have a distinct valid ID")
    require(finding["equipment_id"] == row["equipment_id"]
            and row["equipment_id"] not in equipment, "Invalid synthetic equipment identity")
    require(b02.get("negative_control_finding") in manifest["partitions"]["development"],
            "PSV negative control must remain in development")
    policies = b02.get("policies")
    require(isinstance(policies, dict) and set(policies) == {"before", "after"},
            "Missing PSV policy pair")
    for policy in policies.values():
        require(isinstance(policy, dict)
                and all(nonempty_string(policy.get(field)) for field in ("version", "rule_id", "text")),
                "Incomplete PSV test policy")
        require(finding["finding_id"] not in policy["text"], "Do not branch policy on synthetic finding ID")
    expected = b02.get("expected")
    require(isinstance(expected, dict) and expected.get("positive_before_likelihood") == 6
            and expected.get("positive_after_likelihood") == 8
            and expected.get("positive_impact") == 3,
            "PSV probe score conventions must be explicit")
    before_text, after_text = policies["before"]["text"], policies["after"]["text"]
    require(before_text.count("likelihood_of_failure.score 6") == 1
            and after_text == before_text.replace(
                "likelihood_of_failure.score 6", "likelihood_of_failure.score 8", 1
            ), "PSV policies may differ only in the declared likelihood convention")
    require(before_text.count("impact_of_failure.score 3") == 1,
            "PSV policies must share one fixed impact convention")
    calibration = probes.get("review_calibration")
    require(isinstance(calibration, dict)
            and calibration.get("status") == "fixtures_only_not_reviewed_by_actual_output_reviewer",
            "Calibration must not claim a real reviewer result")
    cases = calibration.get("cases")
    require(isinstance(cases, list) and len(cases) == 2, "Expected two seeded semantic controls")
    seen = set()
    for case in cases:
        require(isinstance(case, dict) and nonempty_string(case.get("probe_id")),
                "Invalid calibration case")
        require(case["probe_id"] not in seen, "Duplicate calibration probe ID")
        seen.add(case["probe_id"])
        require(case.get("finding_id") in manifest["partitions"]["development"]
                and case.get("expected_dimension") == "grounding"
                and case.get("expected_verdict") == "fail", "Invalid seeded calibration expectation")
        require(isinstance(case.get("ticket"), dict)
                and case["ticket"].get("finding_id") == case["finding_id"],
                "Calibration ticket identity mismatch")
        require(string_list(case.get("sources")) and case["sources"]
                and nonempty_string(case.get("reason")), "Seeded control requires source rationale")
        for reference in case["sources"]:
            check_reference(reference, findings, equipment, sections,
                            set(manifest["partitions"]["development"]))


def validate(root=ROOT, allow_draft=False):
    manifest = json.loads((root / "eval" / "spec" / "split.json").read_text(encoding="utf-8"))
    require(isinstance(manifest, dict), "Manifest must be an object")
    source_root = local_path(root, manifest.get("source_root"))
    check_hashes(source_root, manifest.get("sources_sha256"), SOURCES)
    findings, equipment, summary = profile_sources(source_root)
    sections = {
        "brief": headings(source_root / "README.md"),
        "domain": headings(source_root / "reference" / "domain_knowledge.md"),
    }
    group_map = validate_manifest(manifest, findings, equipment, sections)
    for partition in ("development", "test"):
        path = root / "eval" / "data" / f"{partition}.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        require(all(line.strip() for line in lines), f"Blank JSONL record: {path.name}")
        cards = [json.loads(line) for line in lines]
        validate_cards(cards, partition, manifest, findings, equipment, sections, group_map)
    spec = json.loads((root / "eval" / "spec" / "acceptance.json").read_text(encoding="utf-8"))
    scenario_count = validate_acceptance_spec(
        spec, manifest["version"], findings, equipment, sections,
    )
    probes = json.loads((root / "eval" / "spec" / "probes.json").read_text(encoding="utf-8"))
    validate_probes(probes, manifest, findings, equipment, sections)
    if manifest["status"] == "frozen":
        check_hashes(root, manifest.get("artifacts_sha256"), ARTIFACTS)
    else:
        require(allow_draft, "References are draft; use --allow-draft for pre-freeze checks")
    summary["reference_version"] = manifest["version"]
    summary["status"] = manifest["status"]
    summary["acceptance_scenarios"] = scenario_count
    summary["system_scenarios_execution"] = "not_run_no_system"
    summary["partition_counts"] = {
        name: {"cases": len(ids), "groups": len({group_map[item] for item in ids})}
        for name, ids in manifest["partitions"].items()
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-draft", action="store_true", help="Permit explicit pre-freeze checking")
    args = parser.parse_args()
    try:
        summary = validate(allow_draft=args.allow_draft)
    except (ValueError, OSError) as error:
        print(f"Evaluation artifact validation FAILED: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    print("Artifact integrity checks passed; no ticket/model assessment was performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
