"""Project full policy decisions into concise ticket-facing explanations."""
from __future__ import annotations

from .contracts import nonblank, require

PROJECTION_VERSION = "ticket-projection-v4"
_REVIEW_LABELS = {
    "O-PROTECTION": "confirmed unrecorded protection impairment",
    "O-EVACUATION": "confirmed evacuation-capacity shortfall",
    "P-FAILED-TEST": "confirmed failed protection test",
    "P-EVACUATION": "evacuation capacity remains unverified",
    "P-RESTORATION": "restoration remains unverified",
    "S-SOURCE-TODAY": "source requires same-day attention",
    "P-SAFETY-UNKNOWN": "material safety uncertainty; verify the action checks",
    "R-MATERIAL": "material non-safety uncertainty; verify the action checks",
    "P-SCE-HIGH-IMPACT": "high-impact SCE finding",
    "R-SCE": "SCE draft requires integrity-engineer review",
}


def project_related_context(facts: dict, finding_id: str) -> str:
    """Expose at most two related-finding citations already used by typed facts."""
    priority = (
        "protection_restored", "required_function_failed", "protection_impaired",
        "protection_test_failed", "evacuation_unavailable", "capacity_below_pob",
        "unlogged_impairment_discovered", "recorded_deviation",
    )
    notes = []
    prefix = f"finding:{finding_id}:"
    seen_findings = set()
    for name in priority:
        fact = facts.get(name)
        if not isinstance(fact, dict) or fact.get("applicability") == "not_applicable":
            continue
        for citation in fact["evidence"]:
            source_ref = citation["source_ref"]
            if (not source_ref.startswith("finding:")
                    or source_ref.startswith(prefix)
                    or not source_ref.endswith(":finding_description")):
                continue
            related_id = source_ref.split(":", 2)[1]
            if related_id in seen_findings or not nonblank(fact["reason"]):
                continue
            seen_findings.add(related_id)
            notes.append(
                f'[{name}={fact["state"]}] Fact reason: {fact["reason"].strip()} '
                f'Related quote ({related_id} finding_description): "{citation["quote"]}"'
            )
            if len(notes) == 2:
                break
        if len(notes) == 2:
            break
    if not notes:
        return ""
    return " Related-finding context cited by typed facts: " + " ".join(notes)


def project_ticket_text(decision: dict, likelihood: int, impact: int) -> dict:
    """Render urgency provenance and exceptional-review reasons from rule traces."""
    rules = decision["rules"]
    counts: dict[tuple[str, str, int], int] = {}
    for rule in rules:
        key = (rule["rule_id"], rule["kind"], rule["floor"])
        counts[key] = counts.get(key, 0) + 1
    rule_tokens = [
        (
            f"{identifier}[{kind}]" if kind == "review"
            else f"{identifier}[{kind},U{floor}]"
        ) + (f"x{count}" if count > 1 else "")
        for (identifier, kind, floor), count in counts.items()
    ]
    binding = [rule["rule_id"] for rule in rules if rule["floor"] == decision["final"]
               and rule["floor"] > decision["base"]]
    explained = list(dict.fromkeys([
        *binding,
        *[
            rule["rule_id"] for rule in rules
            if rule["kind"] == "confirmed_override"
        ],
    ]))
    rationale = (
        f"{decision['policy_version']}: ceil(0.7*I+0.3*L), L={likelihood}, I={impact}, "
        f"base=U{decision['base']}, final=U{decision['final']}."
    )
    if rule_tokens:
        rationale += " Rules: " + ", ".join(rule_tokens) + "."
    if explained:
        rationale += " Basis: "
        reasons = list(dict.fromkeys(
            rule["reason"].strip()
            for rule in rules if rule["rule_id"] in explained
        ))
        rationale += " ".join(
            reason if reason.endswith(".") else reason + "."
            for reason in reasons
        )

    if decision["review_required"]:
        review_rules = [rule for rule in rules if rule.get("requires_review", True)]
        grouped: dict[str, int] = {}
        for rule in review_rules:
            grouped[rule["rule_id"]] = grouped.get(rule["rule_id"], 0) + 1
        triggers = []
        for identifier, count in grouped.items():
            label = _REVIEW_LABELS.get(identifier, "policy review trigger")
            suffix = f" ({count})" if count > 1 else ""
            activities = list(dict.fromkeys(
                rule["activity"] for rule in review_rules
                if rule["rule_id"] == identifier and rule.get("activity")
            ))
            reasons = list(dict.fromkeys(
                rule["reason"].strip() for rule in review_rules
                if rule["rule_id"] == identifier
            ))
            why = " Why: " + " ".join(
                reason if reason.endswith(".") else reason + "."
                for reason in reasons
            )
            detail = f"; checks: {', '.join(activities)}" if activities else ""
            triggers.append(f"{identifier}{suffix}: {label}.{why}{detail}")
        review_reason = "Review: " + "; ".join(triggers) + ". Full reasons and citations are in run evidence."
    else:
        review_reason = None
    require(nonblank(rationale)
            and (not decision["review_required"] or nonblank(review_reason)),
            "policy_projection", "Ticket projection must preserve decision explanation")
    return {
        "projection_version": PROJECTION_VERSION,
        "urgency_rationale": rationale,
        "review_reason": review_reason,
    }
