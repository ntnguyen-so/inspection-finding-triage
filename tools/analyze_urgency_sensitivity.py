"""Compare urgency-policy alternatives without changing generated tickets."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def current_formula(likelihood: int, impact: int) -> int:
    return (7 * impact + 3 * likelihood + 9) // 10


def interaction_formula(likelihood: int, impact: int) -> int:
    return math.ceil(
        (5 * impact + 2 * likelihood + 3 * math.sqrt(impact * likelihood)) / 10
    )


def quadratic_formula(likelihood: int, impact: int) -> int:
    return math.ceil((7 * impact * impact + 3 * likelihood * likelihood) / 100)


def evaluate(tickets: dict, decisions: dict, formula, safety_unknown_floor: int) -> dict:
    values = []
    changes = []
    for finding_id, ticket in tickets.items():
        likelihood = ticket["likelihood_of_failure"]["score"]
        impact = ticket["impact_of_failure"]["score"]
        base = formula(likelihood, impact)
        floors = [
            safety_unknown_floor if rule["rule_id"] == "P-SAFETY-UNKNOWN" else rule["floor"]
            for rule in decisions[finding_id]["rules"]
        ]
        final = max([base, *floors])
        values.append(final)
        current = ticket["urgency"]["score"]
        if final != current:
            changes.append({
                "finding_id": finding_id,
                "likelihood": likelihood,
                "impact": impact,
                "current": current,
                "candidate": final,
                "candidate_base": base,
                "maximum_rule_floor": max(floors, default=1),
            })
    counts = Counter(values)
    return {
        "distribution": {str(score): counts.get(score, 0) for score in range(1, 11)},
        "bands": {
            "1-3": sum(value <= 3 for value in values),
            "4-6": sum(4 <= value <= 6 for value in values),
            "7-10": sum(value >= 7 for value in values),
        },
        "changed_ticket_count": len(changes),
        "changes": changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickets", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ticket_payload = json.loads(args.tickets.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    tickets = {item["finding_id"]: item for item in ticket_payload["tickets"]}
    decisions = {item["finding_id"]: item for item in evidence["decisions"]}

    scenarios = {
        "current_linear_floor7": evaluate(tickets, decisions, current_formula, 7),
        "v10_interaction_floor7": evaluate(tickets, decisions, interaction_formula, 7),
        "quadratic_floor7": evaluate(tickets, decisions, quadratic_formula, 7),
        "quadratic_floor6": evaluate(tickets, decisions, quadratic_formula, 6),
    }
    if scenarios["current_linear_floor7"]["changed_ticket_count"] != 0:
        raise ValueError("Current formula does not reproduce the retained ticket urgency values")

    base_high = sum(decision["base"] >= 7 for decision in decisions.values())
    raised = [
        {
            "finding_id": finding_id,
            "base": decision["base"],
            "final": decision["final"],
            "raising_rules": [
                {"rule_id": rule["rule_id"], "floor": rule["floor"]}
                for rule in decision["rules"] if rule["floor"] > decision["base"]
            ],
        }
        for finding_id, decision in decisions.items()
        if decision["final"] > decision["base"]
    ]
    report = {
        "scope": "offline_sensitivity_only_no_ticket_or_policy_change",
        "ticket_sha256": __import__("hashlib").sha256(args.tickets.read_bytes()).hexdigest(),
        "finding_count": len(tickets),
        "current_decomposition": {
            "base_urgency_7_to_10": base_high,
            "final_urgency_7_to_10": sum(
                ticket["urgency"]["score"] >= 7 for ticket in tickets.values()
            ),
            "raised_above_base": raised,
        },
        "scenarios": scenarios,
        "interpretation": {
            "formula_only": (
                "Neither the prior interaction formula nor quadratic compression changes "
                "the 19/21 high-band count while the frozen floor of 7 remains."
            ),
            "spread_candidate": (
                "Quadratic compression plus lowering only P-SAFETY-UNKNOWN from 7 to 6 "
                "produces 2 low, 8 medium and 11 high tickets, but changes two policy "
                "levers and lowers several confirmed degradation cases."
            ),
            "decision": (
                "Reject promotion from this offline analysis. A lower uncertainty floor "
                "changes the frozen acceptance policy and requires explicit domain/owner "
                "approval, worked safety review and fresh generation/review evidence."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
