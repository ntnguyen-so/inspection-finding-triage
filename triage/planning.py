from __future__ import annotations

from .contracts import nonblank, require
from .policy import (
    CONTROL_ALIGNMENT_ACTIVITY, IMPAIRMENT_RECORD_ACTIVITY,
    RESTORATION_CLOSURE_ACTIVITY, SAME_DAY_ATTENTION_ACTIVITY,
)

PLAN_CONTRACT = "plan-v1"
GROUNDED_PLAN_CONTRACT = "plan-v2"
_FIXED_PROJECTION = {
    CONTROL_ALIGNMENT_ACTIVITY: "Verify control alignment.",
    IMPAIRMENT_RECORD_ACTIVITY: "Reconcile impairment record.",
    RESTORATION_CLOSURE_ACTIVITY: "Witness; close.",
    SAME_DAY_ATTENTION_ACTIVITY: "Obtain attention today.",
}


def _distinct(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _state_requires_acceptance(facts: dict) -> bool:
    return any(
        facts[name]["applicability"] in {"applicable", "uncertain"}
        and facts[name]["state"] in {"confirmed_true", "suspected"}
        for name in ("required_function_failed", "protection_impaired")
    )


def fixed_plan_activities(decision: dict) -> list[str]:
    return _distinct(decision["fixed_verification_activities"])


def _project_fixed(activity: str) -> str:
    return _FIXED_PROJECTION.get(activity, activity)


def validate_plan(plan: dict, decision: dict, facts: dict, uncertainties: list) -> dict:
    require(isinstance(plan, dict), "plan_contract", "Assessed output requires plan-v1")
    diagnose = plan["diagnose"]
    disposition = plan["disposition"]
    correction = plan["correction"]
    acceptance = plan["acceptance"]
    requirements = plan.get("planning_requirements", [])
    require(all(nonblank(item) for item in diagnose), "plan_contract", "Diagnosis steps must be nonblank")
    require(len(diagnose) == len(set(diagnose)), "plan_contract", "Diagnosis steps must be distinct")
    requirement_activities = [item["activity"] for item in requirements]
    require(len(requirement_activities) == len(set(requirement_activities)),
            "plan_contract", "Planning requirements must be distinct")
    require(correction is None or disposition is not None,
            "plan_contract", "Correction requires an authorized disposition")
    require(correction is None or acceptance is not None,
            "plan_contract", "Correction requires an acceptance test")
    if correction is not None and correction["conditional"]:
        require(bool(diagnose), "plan_contract", "Conditional correction requires diagnosis")

    authored = _distinct([
        *[
            fact["verification_activity"] for fact in facts.values()
            if fact.get("verification_activity") is not None
        ],
        *[item["verification_activity"] for item in uncertainties],
        *requirement_activities,
    ])
    fixed = set(fixed_plan_activities(decision))
    policy_covered = set(decision.get("covered_verification_activities", []))
    model_required = [
        activity for activity in authored
        if activity not in fixed and activity not in policy_covered
    ]
    placed = [*diagnose]
    if acceptance is not None:
        require(
            acceptance["test"] not in fixed
            and acceptance["test"] not in policy_covered,
            "plan_contract",
            "Acceptance cannot repeat a policy pre-work activity",
        )
        placed.append(acceptance["test"])
    for requirement in requirements:
        activity = requirement["activity"]
        count = (
            diagnose.count(activity)
            if requirement["phase"] == "diagnose"
            else int(acceptance is not None and acceptance["test"] == activity)
        )
        require(count == 1, "plan_contract",
                "Each grounded planning requirement must appear exactly once in its declared phase: "
                + activity)
    missing = [activity for activity in model_required if placed.count(activity) != 1]
    unexpected = [
        activity for activity in diagnose
        if activity not in model_required
        and activity not in fixed
        and activity not in policy_covered
    ]
    require(not missing, "plan_contract",
            "Model verification activities need exact diagnose/acceptance placement: " + "; ".join(missing))
    require(not unexpected, "plan_contract",
            "Diagnosis steps must exactly match required verification activities: "
            + "; ".join(unexpected))
    require(len(placed) == len(set(placed)),
            "plan_contract", "A verification activity cannot appear in multiple plan phases")
    triggered = _state_requires_acceptance(facts)
    closure_required = RESTORATION_CLOSURE_ACTIVITY in fixed
    require(not (triggered or closure_required) or acceptance is not None,
            "plan_contract", "Function impairment requires acceptance")
    if triggered or closure_required:
        require(disposition is not None and correction is not None,
                "plan_contract", "Function impairment requires disposition and correction")
        require(acceptance["kind"] == "functional_test",
                "plan_contract", "Function impairment requires functional acceptance")
        require(acceptance["witnessed"] is True,
                "plan_contract", "Function impairment requires witnessed acceptance")
    if triggered:
        require(acceptance["independent_reference"] is True,
                "plan_contract", "Function impairment requires an independent reference")
    return plan


def compose_plan(plan: dict, decision: dict) -> dict:
    fixed = fixed_plan_activities(decision)
    prework = [activity for activity in fixed if activity != RESTORATION_CLOSURE_ACTIVITY]
    projected_prework = _distinct([_project_fixed(activity) for activity in prework])
    projected_diagnose = [
        activity for activity in plan["diagnose"]
        if activity not in set(fixed) and activity not in set(
            decision.get("covered_verification_activities", [])
        )
    ]
    parts = [*projected_prework, *projected_diagnose]
    disposition = plan["disposition"]
    correction = plan["correction"]
    if disposition is not None and correction is None:
        parts.append(f"{disposition['authority']} disposition")
    if correction is not None:
        parts.append(
            f"{disposition['authority']}: {correction['text']}"
            if disposition is not None else correction["text"]
        )
    acceptance = plan["acceptance"]
    if acceptance is not None:
        criterion = f"; {acceptance['criterion']}" if acceptance["criterion"] else ""
        reference = (
            "; independent ref" if acceptance["independent_reference"] else ""
        )
        parts.append(f"{acceptance['test']}{criterion}{reference}")
        if acceptance["witnessed"]:
            parts.append(_FIXED_PROJECTION[RESTORATION_CLOSURE_ACTIVITY])
    rendered = []
    for part in parts:
        value = part.strip()
        if value and value[-1] not in ".;":
            value += "."
        rendered.append(value)
    composed = " ".join(rendered)
    return {
        "contract": (
            GROUNDED_PLAN_CONTRACT
            if "planning_requirements" in plan
            else PLAN_CONTRACT
        ),
        "planning_requirements": list(plan.get("planning_requirements", [])),
        "fixed_prework": prework,
        "projected_fixed_prework": projected_prework,
        "diagnose": list(plan["diagnose"]),
        "projected_diagnose": projected_diagnose,
        "disposition": disposition,
        "has_correction": correction is not None,
        "has_acceptance": acceptance is not None,
        "composed": composed,
    }
