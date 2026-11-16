"""Assess ticket outputs; never generate tickets or claim full system acceptance."""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from eval.validate import ROOT, nonempty_string, profile_sources, require, validate


DIMENSIONS = ("grounding", "planning", "uncertainty")
SCORE_FIELDS = ("likelihood_of_failure", "impact_of_failure", "urgency")
TICKET_FIELDS = {
    "ticket_id", "finding_id", "equipment_id", "summary", *SCORE_FIELDS,
    "recommended_action", "review_required", "review_reason",
}
EVIDENCE_FIELDS = {
    "summary", "recommended_action", "review_required", "review_reason",
    *(f"{name}.{field}" for name in SCORE_FIELDS for field in ("score", "rationale")),
}
EXPECTATION_FIELDS = {
    "grounding": ("observed_facts", "required_evidence", "expected_behavior", "forbidden_claims"),
    "planning": ("action_constraints",),
    "uncertainty": ("unknowns",),
}


def reject_constant(value):
    raise ValueError(f"Non-JSON numeric constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def parse_json(raw):
    try:
        return json.loads(
            raw.decode("utf-8-sig"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"Malformed JSON: {error}") from error


def read_json(path):
    return parse_json(path.read_bytes())


def contract_errors(payload, expected):
    errors = []

    def fields(value, names, location):
        if not isinstance(value, dict):
            errors.append(f"{location}: expected object")
            return False
        if set(value) != names:
            errors.append(f"{location}: missing/extra fields")
        return True

    if not fields(payload, {"generated_at", "tickets_generated", "tickets"}, "wrapper"):
        return errors
    timestamp = payload.get("generated_at")
    try:
        require(isinstance(timestamp, str) and "T" in timestamp, "Not a timestamp")
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None, "Missing timezone")
    except ValueError:
        errors.append("generated_at: expected ISO-8601 timestamp with timezone")
    tickets = payload.get("tickets")
    if not isinstance(tickets, list):
        errors.append("tickets: expected array")
        return errors
    count = payload.get("tickets_generated")
    if type(count) is not int or count != len(tickets) or count != len(expected):
        errors.append("tickets_generated: count must equal tickets and selected input count")
    seen_findings = set()
    seen_tickets = set()
    for position, ticket in enumerate(tickets):
        location = f"tickets[{position}]"
        if not fields(ticket, TICKET_FIELDS, location):
            continue
        finding_id = ticket.get("finding_id")
        if not isinstance(finding_id, str) or finding_id not in expected:
            errors.append(f"{location}.finding_id: unknown/unselected finding")
        else:
            location = finding_id
            if finding_id in seen_findings:
                errors.append(f"{finding_id}: duplicate finding")
            seen_findings.add(finding_id)
            if ticket.get("equipment_id") != expected[finding_id]["equipment_id"]:
                errors.append(f"{finding_id}.equipment_id: input mapping mismatch")
        ticket_id = ticket.get("ticket_id")
        if not isinstance(ticket_id, str) or re.fullmatch(r"TKT-\d{4}", ticket_id) is None:
            errors.append(f"{location}.ticket_id: expected TKT-####")
        elif ticket_id in seen_tickets:
            errors.append(f"{location}.ticket_id: duplicate ticket ID")
        else:
            seen_tickets.add(ticket_id)
        for field in ("summary", "recommended_action"):
            value = ticket.get(field)
            if not nonempty_string(value) or len(value) > 300:
                errors.append(f"{location}.{field}: expected non-empty string <=300 characters")
        for field in SCORE_FIELDS:
            score = ticket.get(field)
            if fields(score, {"score", "rationale"}, f"{location}.{field}"):
                value = score.get("score")
                if type(value) is not int or not 1 <= value <= 10:
                    errors.append(f"{location}.{field}.score: expected integer 1-10, not boolean")
                if not nonempty_string(score.get("rationale")):
                    errors.append(f"{location}.{field}.rationale: non-empty string required")
        flag = ticket.get("review_required")
        reason = ticket.get("review_reason")
        if type(flag) is not bool:
            errors.append(f"{location}.review_required: boolean required")
        if reason is not None and not isinstance(reason, str):
            errors.append(f"{location}.review_reason: expected string or null")
        if flag is True and not nonempty_string(reason):
            errors.append(f"{location}.review_reason: required when review_required is true")
    if seen_findings != set(expected):
        errors.append(f"coverage: missing findings {sorted(set(expected) - seen_findings)}")
    return errors


def review_template(cards, partition, version, output_hash):
    return {
        "reference_version": version,
        "partition": partition,
        "output_sha256": output_hash,
        "reviewer": {"kind": "unassigned", "independent_of_generation": False},
        "items": [
            {
                "finding_id": card["finding_id"],
                "dimension": dimension,
                "verdict": "needs_review",
                "reason": "",
                "evidence": [],
                "expectations": {
                    field: card[field] for field in EXPECTATION_FIELDS[dimension]
                },
            }
            for card in cards for dimension in DIMENSIONS
        ],
    }


def reviewer_identity(reviewer):
    require(isinstance(reviewer, dict) and isinstance(reviewer.get("kind"), str)
            and reviewer["kind"] in {"human", "ai_assisted", "ai_only"}
            and type(reviewer.get("independent_of_generation")) is bool,
            "Review requires declared reviewer kind and independence")
    return reviewer


def check_quote(quote, ticket, location):
    require(isinstance(quote, dict) and isinstance(quote.get("field"), str)
            and quote["field"] in EVIDENCE_FIELDS
            and nonempty_string(quote.get("quote")), f"Invalid output evidence: {location}")
    value = ticket
    for part in quote["field"].split("."):
        value = value[part]
    text = value if isinstance(value, str) else json.dumps(value)
    require(quote["quote"] in text, f"Review quote not present in output: {location}")


def check_reviews(review, tickets, cards, partition, version, output_hash):
    require(isinstance(review, dict), "Review must be an object")
    require(review.get("reference_version") == version, "Review reference version mismatch")
    require(review.get("partition") == partition, "Review partition mismatch")
    require(nonempty_string(output_hash) and review.get("output_sha256") == output_hash,
            "Review does not match the exact ticket-file SHA-256")
    reviewer = reviewer_identity(review.get("reviewer"))
    items = review.get("items")
    require(isinstance(items, list), "Review items must be an array")
    expected = {(card["finding_id"], dimension) for card in cards for dimension in DIMENSIONS}
    card_map = {card["finding_id"]: card for card in cards}
    seen = {}
    for item in items:
        require(isinstance(item, dict), "Review item must be an object")
        finding_id, dimension = item.get("finding_id"), item.get("dimension")
        require(isinstance(finding_id, str) and isinstance(dimension, str),
                "Review identity and dimension must be strings")
        key = (finding_id, dimension)
        require(key in expected and key not in seen, f"Unknown/duplicate review item: {key}")
        if "expectations" in item:
            authoritative = {
                field: card_map[finding_id][field] for field in EXPECTATION_FIELDS[dimension]
            }
            require(item["expectations"] == authoritative, f"Edited review expectations: {key}")
        verdict = item.get("verdict")
        require(isinstance(verdict, str) and verdict in {"pass", "fail", "needs_review"},
                f"Invalid review verdict: {key}")
        require(isinstance(item.get("reason"), str), f"Missing review reason: {key}")
        evidence = item.get("evidence")
        require(isinstance(evidence, list), f"Review evidence must be an array: {key}")
        if verdict in {"pass", "fail"}:
            require(nonempty_string(item["reason"]) and evidence,
                    f"Pass/fail requires reason and quoted output evidence: {key}")
        for quote in evidence:
            check_quote(quote, tickets[finding_id], key)
        seen[key] = verdict
    return seen, reviewer


def calibrate(review, probes):
    require(isinstance(review, dict)
            and review.get("reference_version") == probes["reference_version"],
            "Calibration review reference version mismatch")
    reviewer = reviewer_identity(review.get("reviewer"))
    cases = {case["probe_id"]: case for case in probes["review_calibration"]["cases"]}
    judgments = review.get("judgments")
    require(isinstance(judgments, list), "Calibration judgments must be an array")
    seen = {}
    for item in judgments:
        require(isinstance(item, dict), "Calibration judgment must be an object")
        identifier = item.get("probe_id")
        require(isinstance(identifier, str) and identifier in cases and identifier not in seen,
                f"Unknown/duplicate calibration probe: {identifier}")
        case = cases[identifier]
        require(item.get("dimension") == case["expected_dimension"],
                f"Wrong calibration dimension: {identifier}")
        verdict = item.get("verdict")
        require(isinstance(verdict, str) and verdict in {"pass", "fail", "needs_review"},
                f"Invalid calibration verdict: {identifier}")
        evidence = item.get("evidence")
        require(isinstance(item.get("reason"), str) and isinstance(evidence, list),
                f"Missing calibration reason/evidence: {identifier}")
        if verdict != "needs_review":
            require(nonempty_string(item["reason"]) and evidence,
                    f"Calibration pass/fail needs reason and evidence: {identifier}")
        for quote in evidence:
            check_quote(quote, case["ticket"], identifier)
        seen[identifier] = verdict
    pending = [identifier for identifier in cases if seen.get(identifier, "needs_review") == "needs_review"]
    wrong = [identifier for identifier, verdict in seen.items()
             if verdict != "needs_review" and verdict != cases[identifier]["expected_verdict"]]
    return {
        "scope": "known_fixture_conformance",
        "reference_version": probes["reference_version"],
        "review_provenance": reviewer,
        "calibration_status": "fail" if wrong else ("needs_review" if pending else "pass"),
        "wrong_fixture_judgments": wrong,
        "pending": pending,
        "limitation": "Checks these seeded contradictions only; not arbitrary semantic truth or a system result.",
    }


def assess(payload, expected, cards, partition, version, output_hash, review=None):
    require({card["finding_id"] for card in cards} == set(expected),
            "Evaluator reference coverage does not match selected input")
    errors = contract_errors(payload, expected)
    report = {
        "scope": "ticket_outputs_only_not_full_A_D_system_acceptance",
        "reference_version": version,
        "partition": partition,
        "output_sha256": output_hash,
        "contract": {"status": "fail" if errors else "pass", "errors": errors},
        "semantic": {"status": "not_reviewed", "reviewer": None},
        "overall": "fail" if errors else "needs_review",
        "review_provenance": None,
        "system_scenario_results": "not_provided_not_implied_by_this_report",
    }
    if errors:
        return report
    tickets = {ticket["finding_id"]: ticket for ticket in payload["tickets"]}
    reviewed, reviewer = ({}, None) if review is None else check_reviews(
        review, tickets, cards, partition, version, output_hash,
    )
    pending = []
    failed = []
    passed = 0
    for card in cards:
        for dimension in DIMENSIONS:
            key = (card["finding_id"], dimension)
            verdict = reviewed.get(key, "needs_review")
            if verdict == "fail":
                failed.append({"finding_id": key[0], "dimension": key[1]})
            elif verdict == "pass":
                passed += 1
            else:
                pending.append({"finding_id": key[0], "dimension": key[1]})
    report["semantic"] = {
        "status": "fail" if failed else ("needs_review" if pending else "provisional_pass"),
        "reviewer": reviewer,
        "passed_dimensions": passed,
        "applicable_dimensions": len(cards) * len(DIMENSIONS),
        "failed": failed,
        "pending": pending,
        "limitation": "Declared review agreement is not independent engineering truth or accuracy.",
    }
    report["overall"] = report["semantic"]["status"]
    report["review_provenance"] = reviewer
    if review is None:
        report["review_template"] = review_template(cards, partition, version, output_hash)
    return report


def load_references(partition):
    validate()
    manifest = read_json(ROOT / "eval" / "spec" / "split.json")
    findings, _, _ = profile_sources(ROOT / manifest["source_root"])
    partitions = ("development", "test") if partition == "all" else (partition,)
    selected = [identifier for name in partitions for identifier in manifest["partitions"][name]]
    cards = []
    for name in partitions:
        cards.extend(json.loads(line) for line in
                     (ROOT / "eval" / "data" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines())
    return manifest["version"], {identifier: findings[identifier] for identifier in selected}, cards


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition", required=True, choices=("development", "test", "all"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--checklist", action="store_true")
    mode.add_argument("--tickets", type=Path)
    mode.add_argument("--calibration-reviews", type=Path)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args(argv)
    if not args.tickets and args.reviews:
        parser.error("--reviews requires --tickets")
    if args.calibration_reviews and args.partition != "development":
        parser.error("Seeded calibration is development-only")
    try:
        version, expected, cards = load_references(args.partition)
        if args.checklist:
            print(json.dumps(review_template(cards, args.partition, version, None), indent=2))
            return 0
        if args.calibration_reviews:
            report = calibrate(
                read_json(args.calibration_reviews), read_json(ROOT / "eval" / "spec" / "probes.json"),
            )
            print(json.dumps(report, indent=2))
            return {"pass": 0, "fail": 1, "needs_review": 2}[report["calibration_status"]]
        raw_output = args.tickets.read_bytes()
        payload = parse_json(raw_output)
        output_hash = hashlib.sha256(raw_output).hexdigest()
        review = read_json(args.reviews) if args.reviews else None
        report = assess(payload, expected, cards, args.partition, version, output_hash, review)
        print(json.dumps(report, indent=2))
        return {"provisional_pass": 0, "fail": 1, "needs_review": 2}[report["overall"]]
    except (ValueError, OSError) as error:
        print(f"Ticket assessment FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
