from __future__ import annotations

from .assessment import SAME_DAY_VALIDATOR, validate_facts
from .contracts import nonblank, require, score

POLICY_VERSION = "triage-policy-v9"
CAPACITY_COMPARISON_ACTIVITY = "Verify current POB against certified available evacuation capacity."
SAME_DAY_ATTENTION_ACTIVITY = "Obtain source-required attention today."
CONTROL_ALIGNMENT_ACTIVITY = "Verify current protection control alignment."
IMPAIRMENT_RECORD_ACTIVITY = "Reconcile impairment/deviation record."
RESTORATION_CLOSURE_ACTIVITY = "Witness function test; close impairment only after pass."


def gap_verification_activity(gap: dict) -> str:
    return f"Verify availability and capability of {gap['partner_equipment_id']}."


def base_urgency(likelihood: int, impact: int) -> int:
    return (3 * score(likelihood) + 7 * score(impact) + 9) // 10


def targeted_review_required(base: int, rules: list[dict]) -> bool:
    always_review = {"P-FAILED-TEST", "P-EVACUATION", "P-RESTORATION"}
    return any(
        rule["kind"] in {"review", "confirmed_override", "source_directed_attention"}
        or rule["floor"] > base
        or rule["rule_id"] in always_review
        for rule in rules
    )


def derive_policy(likelihood: int, impact: int, facts: dict, uncertainties: list,
                  *, sce: bool, gaps: list, same_day_attention: list | None = None) -> dict:
    base = base_urgency(likelihood, impact)
    validate_facts(facts)
    require(type(sce) is bool and isinstance(uncertainties, list) and isinstance(gaps, list),
            "policy_contract", "Invalid policy input")
    rules, activities, fixed_activities = [], [], []
    attention = [] if same_day_attention is None else same_day_attention
    require(SAME_DAY_VALIDATOR.is_valid(attention)
            and all(nonblank(item["reason"]) for item in attention),
            "policy_contract", "Invalid source-directed attention input")

    def state(name: str) -> str | None:
        fact = facts[name]
        return fact["state"] if fact["applicability"] == "applicable" else None

    def unverified(name: str) -> bool:
        fact = facts[name]
        return fact["applicability"] != "not_applicable" and fact["state"] in {"unknown", "suspected"}

    def add(identifier: str, kind: str, floor: int, reason: str, sources: list,
            activity: str | None = None, *, fixed: bool = False) -> None:
        rules.append({"rule_id": identifier, "kind": kind, "floor": floor,
                      "reason": reason, "sources": sources})
        if activity is not None:
            require(nonblank(activity), "policy_verification", "Specific verification required")
            activities.append(activity)
            if fixed:
                fixed_activities.append(activity)

    def refs(*names: str) -> list:
        return sorted({ref for name in names for ref in facts[name].get("sources_checked", [])}
                      | {x["source_ref"] for name in names for x in facts[name].get("evidence", [])})

    for trigger, dependent, trigger_states in (
        ("protection_impaired", "recorded_deviation", {"confirmed_true", "suspected"}),
        ("evacuation_unavailable", "capacity_below_pob", {"confirmed_true"}),
        ("unlogged_impairment_discovered", "protection_restored", {"confirmed_true"}),
    ):
        require(not (state(trigger) in trigger_states
                     and facts[dependent]["applicability"] == "not_applicable"),
                "fact_contract", f"Triggered {trigger} makes {dependent} relevant")

    if state("protection_impaired") == "confirmed_true" and state("recorded_deviation") == "confirmed_false":
        add("O-PROTECTION", "confirmed_override", 9,
            "Confirmed protection impairment without recorded deviation.",
            refs("protection_impaired", "recorded_deviation"))
    if state("capacity_below_pob") == "confirmed_true":
        add("O-EVACUATION", "confirmed_override", 9,
            "Confirmed evacuation capacity below POB.", refs("capacity_below_pob"))
    if state("protection_test_failed") == "confirmed_true":
        add("P-FAILED-TEST", "precautionary_policy", 9,
            "Confirmed failed protection-function test; immediate human attention.",
            refs("protection_test_failed"))
    if state("evacuation_unavailable") == "confirmed_true" and unverified("capacity_below_pob"):
        add("P-EVACUATION", "precautionary_policy", 9,
            "Craft unavailable; remaining capacity/POB comparison unverified, not proven shortfall.",
            refs("evacuation_unavailable", "capacity_below_pob"),
            facts["capacity_below_pob"].get("verification_activity"))
        require(facts["capacity_below_pob"].get("verification_activity") is not None,
                "policy_verification", "Capacity verification activity required")
        activities.append(CAPACITY_COMPARISON_ACTIVITY)
        fixed_activities.append(CAPACITY_COMPARISON_ACTIVITY)
    if state("unlogged_impairment_discovered") == "confirmed_true" and (
        state("protection_restored") == "confirmed_false" or unverified("protection_restored")
    ):
        uncertain = unverified("protection_restored")
        for activity in (
            CONTROL_ALIGNMENT_ACTIVITY,
            IMPAIRMENT_RECORD_ACTIVITY,
            RESTORATION_CLOSURE_ACTIVITY,
        ):
            activities.append(activity)
            fixed_activities.append(activity)
        add("P-RESTORATION", "precautionary_policy", 9,
            "Unlogged impairment discovered; restored protection not verified.",
            refs("unlogged_impairment_discovered", "protection_restored"),
            facts["protection_restored"].get("verification_activity") if uncertain else None)
        require(not uncertain or facts["protection_restored"].get("verification_activity") is not None,
                "policy_verification", "Restoration verification activity required")
    for item in attention:
        sources = sorted({citation["source_ref"] for name in ("directive_evidence", "trigger_evidence")
                              for citation in item[name]})
        add("S-SOURCE-TODAY", "source_directed_attention", 9,
                "Explicit source-directed same-day attention: " + item["reason"], sources,
                SAME_DAY_ATTENTION_ACTIVITY, fixed=True)
    impairment = state("protection_impaired")
    deviation = state("recorded_deviation")
    if impairment in {"confirmed_true", "suspected"} and deviation in {"unknown", "suspected"}:
        activity = facts["recorded_deviation"].get("verification_activity")
        require(nonblank(activity), "policy_verification", "Deviation verification activity required")
        add("P-SAFETY-UNKNOWN", "precautionary_policy", 7,
            ("Protection impaired; deviation status unverified, not confirmed absent."
             if impairment == "confirmed_true" else
             "Protection impairment suspected; deviation status unverified, not confirmed absent."),
            refs("protection_impaired", "recorded_deviation"), activity)
    if impairment == "suspected" and deviation == "confirmed_false":
        activity = facts["protection_impaired"].get("verification_activity")
        require(nonblank(activity), "policy_verification", "Protection verification activity required")
        add("P-SAFETY-UNKNOWN", "precautionary_policy", 7,
            "Protection impairment suspected; no recorded deviation.",
            refs("protection_impaired", "recorded_deviation"), activity)
    for name, fact in facts.items():
        if fact["applicability"] == "uncertain":
            activity = fact.get("verification_activity")
            require(nonblank(activity), "policy_verification", "Applicability verification required")
            safety = name != "required_function_failed"
            add("P-SAFETY-UNKNOWN" if safety else "R-MATERIAL", "precautionary_policy" if safety else "review",
                7 if safety else 1, f"Uncertain policy applicability: {name}.", refs(name), activity)
    for item in uncertainties:
        require(isinstance(item, dict) and type(item.get("material")) is bool
                and type(item.get("safety")) is bool and nonblank(item.get("reason")),
                "policy_contract", "Invalid material-uncertainty input")
        if item["material"]:
            activity = item.get("verification_activity")
            require(nonblank(activity), "policy_verification", "Material uncertainty needs verification")
            safety = item["safety"]
            add("P-SAFETY-UNKNOWN" if safety else "R-MATERIAL", "precautionary_policy" if safety else "review",
                7 if safety else 1, item["reason"], item.get("sources_checked", []), activity)
    for gap in gaps:
        require(gap.get("kind") == "tagged_partner_not_in_registry",
                "policy_gap", "Unsupported context gap")
        add("P-SAFETY-UNKNOWN" if sce else "R-MATERIAL", "precautionary_policy" if sce else "review",
            7 if sce else 1, f"Partner {gap['partner_equipment_id']} has no registry record.",
            gap["source_refs"], gap_verification_activity(gap), fixed=True)
    if sce and impact >= 8:
        add("P-SCE-HIGH-IMPACT", "precautionary_policy", 7,
            f"Registry SCE finding assessed at I={impact} requires attention at least this week.", [])
    if sce:
        add("R-SCE", "review", 1,
            "SCE draft requires integrity-engineer review; SCE status alone adds no floor.", [])
    final = max([base, *(x["floor"] for x in rules)])
    details = " ".join(
        f"{x['rule_id']} ({x['kind']}): {x['reason']} Sources: {', '.join(x['sources']) or 'registry SCE flag'}."
        for x in rules
    )
    return {
        "policy_version": POLICY_VERSION, "base": base, "final": final, "rules": rules,
        "rationale": f"{POLICY_VERSION}: ceil(0.7*I+0.3*L), L={likelihood}, I={impact}, base={base}, final={final}. {details}".strip(),
        "review_required": targeted_review_required(base, rules),
        "review_reason": details if targeted_review_required(base, rules) else None,
        "verification_activities": list(dict.fromkeys(activities)),
        "fixed_verification_activities": list(dict.fromkeys(fixed_activities)),
    }
