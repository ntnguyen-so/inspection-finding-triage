from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def band(score: int) -> str:
    if score <= 2:
        return "backlog"
    if score <= 4:
        return "next_planned_shutdown"
    if score <= 6:
        return "this_month"
    if score <= 8:
        return "this_week"
    return "today"


def ticket_index(payload: dict) -> dict[str, dict]:
    return {ticket["finding_id"]: ticket for ticket in payload["tickets"]}


def decision_index(run: dict) -> dict[str, dict]:
    return {decision["finding_id"]: decision for decision in run["decisions"]}


def receipt_check(run_path: Path, run: dict) -> dict:
    receipt_path = run_path.parent / run["publication_receipt"]
    receipt = load(receipt_path)
    output_path = Path(receipt["output_path"])
    return {
        "path": str(receipt_path),
        "sha256": sha256(receipt_path),
        "recorded_sha256": run["publication_receipt_sha256"],
        "output_path": str(output_path),
        "output_sha256": sha256(output_path),
        "recorded_output_sha256": receipt["output_sha256"],
        "valid": (
            run["run_status"] == "published"
            and run["published_output"] is True
            and receipt["verified_after_replace"] is True
            and sha256(receipt_path) == run["publication_receipt_sha256"]
            and sha256(output_path) == receipt["output_sha256"] == run["output_sha256"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickets-a", type=Path, required=True)
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--tickets-b", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tickets_a, tickets_b = load(args.tickets_a), load(args.tickets_b)
    run_a, run_b = load(args.run_a), load(args.run_b)
    index_a, index_b = ticket_index(tickets_a), ticket_index(tickets_b)
    decisions_a, decisions_b = decision_index(run_a), decision_index(run_b)
    finding_ids = sorted(set(index_a) | set(index_b))
    rows = []
    for finding_id in finding_ids:
        left, right = index_a.get(finding_id), index_b.get(finding_id)
        if left is None or right is None:
            rows.append({"finding_id": finding_id, "coverage_match": False})
            continue
        left_scores = {
            "likelihood": left["likelihood_of_failure"]["score"],
            "impact": left["impact_of_failure"]["score"],
            "urgency": left["urgency"]["score"],
        }
        right_scores = {
            "likelihood": right["likelihood_of_failure"]["score"],
            "impact": right["impact_of_failure"]["score"],
            "urgency": right["urgency"]["score"],
        }
        left_rules = sorted(rule["rule_id"] for rule in decisions_a[finding_id]["rules"])
        right_rules = sorted(rule["rule_id"] for rule in decisions_b[finding_id]["rules"])
        rows.append({
            "finding_id": finding_id,
            "coverage_match": True,
            "run_a": {
                **left_scores,
                "urgency_band": band(left_scores["urgency"]),
                "review_required": left["review_required"],
                "rule_ids": left_rules,
            },
            "run_b": {
                **right_scores,
                "urgency_band": band(right_scores["urgency"]),
                "review_required": right["review_required"],
                "rule_ids": right_rules,
            },
            "numeric_score_match": left_scores == right_scores,
            "urgency_band_match": band(left_scores["urgency"]) == band(right_scores["urgency"]),
            "review_flag_match": left["review_required"] == right["review_required"],
            "rule_set_match": left_rules == right_rules,
        })

    stable_fields = [
        "input_sha256", "context_hash", "knowledge_content_hash", "assessment_prompt",
        "policy_version", "ticket_projection", "implementation_sha256",
        "knowledge_implementation_sha256",
    ]
    configuration_match = {
        field: run_a.get(field) == run_b.get(field) for field in stable_fields
    }
    receipt_a = receipt_check(args.run_a, run_a)
    receipt_b = receipt_check(args.run_b, run_b)
    automated_pass = (
        len(index_a) == len(index_b) == 21
        and all(row.get("coverage_match") for row in rows)
        and all(row.get("urgency_band_match") for row in rows)
        and all(row.get("review_flag_match") for row in rows)
        and all(row.get("rule_set_match") for row in rows)
        and all(configuration_match.values())
        and receipt_a["valid"]
        and receipt_b["valid"]
    )
    result = {
        "contract": "x01-repeat-comparison-v1",
        "claim_boundary": (
            "Automated comparison covers scores, urgency bands, review flags, rule sets, "
            "configuration identity and publication receipts. Unsupported-claim review "
            "remains a separate semantic gate."
        ),
        "run_a": {
            "tickets": str(args.tickets_a),
            "tickets_sha256": sha256(args.tickets_a),
            "run": str(args.run_a),
            "run_sha256": sha256(args.run_a),
            "publication": receipt_a,
        },
        "run_b": {
            "tickets": str(args.tickets_b),
            "tickets_sha256": sha256(args.tickets_b),
            "run": str(args.run_b),
            "run_sha256": sha256(args.run_b),
            "publication": receipt_b,
        },
        "configuration_match": configuration_match,
        "findings": rows,
        "summary": {
            "finding_count": len(rows),
            "numeric_score_matches": sum(row.get("numeric_score_match", False) for row in rows),
            "urgency_band_matches": sum(row.get("urgency_band_match", False) for row in rows),
            "review_flag_matches": sum(row.get("review_flag_match", False) for row in rows),
            "rule_set_matches": sum(row.get("rule_set_match", False) for row in rows),
        },
        "automated_status": "pass" if automated_pass else "fail",
        "unsupported_claim_status": "not_reviewed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"]))
    return 0 if automated_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
