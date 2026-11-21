"""Schemas and evidence validation for model-authored assessments and plans."""
from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator

from llm_inference import InferenceRequest
from llm_inference.contracts import canonical, strict_json

from .assessment_policy import CONFIRMED_FAILURE_MINIMUM
from .contracts import TriageError, digest, nonblank, require, score
from .prompt import (
    ASSESSMENT_CONTRACT, GROUNDED_PLAN_ASSESSMENT_CONTRACT,
    PLANNED_ASSESSMENT_CONTRACT, assessment_prompt,
)

FACT_NAMES = (
    "required_function_failed", "protection_impaired", "recorded_deviation",
    "protection_test_failed", "evacuation_unavailable", "capacity_below_pob",
    "unlogged_impairment_discovered", "protection_restored",
)
STATES = ("confirmed_true", "confirmed_false", "suspected", "unknown")
APPLICABILITY = ("applicable", "not_applicable", "uncertain")


def closed(properties: dict) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def text(nullable: bool = False, limit: int | None = None) -> dict:
    result = {"type": ["string", "null"] if nullable else "string", "minLength": 1}
    if limit is not None:
        result["maxLength"] = limit
    return result


EVIDENCE = {"type": "array", "items": closed({"source_ref": text(), "quote": text()})}
FACT = closed({
    "applicability": {"enum": list(APPLICABILITY)},
    "state": {"enum": list(STATES)},
    "reason": text(), "evidence": EVIDENCE,
    "sources_checked": {"type": "array", "items": text(), "minItems": 1, "uniqueItems": True},
    "verification_activity": text(nullable=True),
})
SCORE = closed({"score": {"type": "integer", "minimum": 1, "maximum": 10},
                "rationale": text(), "evidence": {**EVIDENCE, "minItems": 1}})
SCHEMA = closed({
    "status": {"enum": ["assessed", "unassessable"]},
    "finding_id": text(), "equipment_id": text(),
    "likelihood_of_failure": {"anyOf": [SCORE, {"type": "null"}]},
    "impact_of_failure": {"anyOf": [SCORE, {"type": "null"}]},
    "facts": {"anyOf": [closed({name: FACT for name in FACT_NAMES}), {"type": "null"}]},
    "uncertainties": {"type": "array", "items": closed({
        "material": {"type": "boolean"}, "safety": {"type": "boolean"},
        "affected_decision": {"enum": [
            "likelihood", "impact", "redundancy", "protection", "evacuation", "disposition",
        ]},
        "reason": text(), "verification_activity": text(),
        "evidence": EVIDENCE,
        "sources_checked": {"type": "array", "items": text(), "minItems": 1, "uniqueItems": True},
    })},
    "summary": text(nullable=True, limit=300),
    "recommended_action": text(nullable=True, limit=300),
    "inability_reason": text(nullable=True),
})
PLAN_SCHEMA = closed({
    "diagnose": {
        "type": "array", "items": text(limit=40),
        "maxItems": 3, "uniqueItems": True,
    },
    "disposition": {"anyOf": [closed({
        "authority": text(limit=28), "decision": text(),
    }), {"type": "null"}]},
    "correction": {"anyOf": [closed({
        "text": text(limit=40), "conditional": {"type": "boolean"},
    }), {"type": "null"}]},
    "acceptance": {"anyOf": [closed({
        "kind": {"enum": ["functional_test", "inspection"]},
        "test": text(limit=40), "criterion": text(nullable=True, limit=32),
        "witnessed": {"type": "boolean"}, "independent_reference": {"type": "boolean"},
    }), {"type": "null"}]},
})
FAILURE_BASIS = closed({
    "assessed_item": text(),
    "required_function": text(),
    "failure_event": text(),
    "evidence": {**EVIDENCE, "minItems": 1},
})
GROUNDED_PLAN_SCHEMA = closed({
    "planning_requirements": {
        "type": "array",
        "items": closed({
            "activity": text(limit=64),
            "phase": {"enum": ["diagnose", "acceptance"]},
            "reason": text(),
            "evidence": {**EVIDENCE, "minItems": 1},
        }),
        "minItems": 1,
        "maxItems": 4,
    },
    "diagnose": {
        "type": "array", "items": text(limit=64),
        "maxItems": 4, "uniqueItems": True,
    },
    "disposition": {"anyOf": [closed({
        "authority": text(limit=28), "decision": text(),
    }), {"type": "null"}]},
    "correction": {"anyOf": [closed({
        "text": text(limit=64), "conditional": {"type": "boolean"},
    }), {"type": "null"}]},
    "acceptance": {"anyOf": [closed({
        "kind": {"enum": ["functional_test", "inspection"]},
        "test": text(limit=64), "criterion": text(nullable=True, limit=48),
        "witnessed": {"type": "boolean"}, "independent_reference": {"type": "boolean"},
    }), {"type": "null"}]},
})
VALIDATOR = Draft202012Validator(SCHEMA)
SAME_DAY_SCHEMA = {"type": "array", "items": closed({
    "reason": text(),
    "directive_evidence": {**EVIDENCE, "minItems": 1},
    "trigger_evidence": {**EVIDENCE, "minItems": 1},
})}
SAME_DAY_VALIDATOR = Draft202012Validator(SAME_DAY_SCHEMA)
NATIVE_ASSESSMENT_CONTRACT = ASSESSMENT_CONTRACT


def assessment_schema(assessment_contract: str) -> dict:
    """Build the exact schema variant pinned by the selected prompt contract."""
    require(assessment_contract in {
        ASSESSMENT_CONTRACT, PLANNED_ASSESSMENT_CONTRACT,
        GROUNDED_PLAN_ASSESSMENT_CONTRACT,
    },
            "assessment_schema", "Unknown assessment contract")
    schema = deepcopy(SCHEMA)
    if assessment_contract in {
        PLANNED_ASSESSMENT_CONTRACT, GROUNDED_PLAN_ASSESSMENT_CONTRACT,
    }:
        properties = schema["properties"]
        fact_properties = properties["facts"]["anyOf"][0]["properties"]
        verification_limit = (
            64 if assessment_contract == GROUNDED_PLAN_ASSESSMENT_CONTRACT else 40
        )
        for name in FACT_NAMES:
            fact_properties[name]["properties"]["verification_activity"][
                "maxLength"
            ] = verification_limit
        properties["uncertainties"]["items"]["properties"][
            "verification_activity"
        ]["maxLength"] = verification_limit
        action_index = list(properties).index("recommended_action")
        items = list(properties.items())
        plan_schema = (
            GROUNDED_PLAN_SCHEMA
            if assessment_contract == GROUNDED_PLAN_ASSESSMENT_CONTRACT
            else PLAN_SCHEMA
        )
        items[action_index] = ("plan", {"anyOf": [deepcopy(plan_schema), {"type": "null"}]})
        schema["properties"] = dict(items)
        schema["required"][schema["required"].index("recommended_action")] = "plan"
    if assessment_contract == GROUNDED_PLAN_ASSESSMENT_CONTRACT:
        properties = schema["properties"]
        likelihood_index = list(properties).index("likelihood_of_failure")
        items = list(properties.items())
        items.insert(likelihood_index, ("failure_basis", {
            "anyOf": [deepcopy(FAILURE_BASIS), {"type": "null"}],
        }))
        schema["properties"] = dict(items)
        schema["required"].insert(likelihood_index, "failure_basis")
    return schema


def citation_catalog(index: dict) -> dict:
    """Assign stable short IDs to nonblank source lines in the context index."""
    catalog = {}
    for address in sorted(index):
        for line in index[address].split("\n"):
            if line.strip():
                catalog[f"c{len(catalog):04d}"] = {"source_ref": address, "quote": line}
    return catalog


def attention_addresses(finding_id: str, equipment_id: str) -> set[str]:
    """Return target-local sources permitted to trigger same-day attention."""
    return {f"finding:{finding_id}:finding_description", f"equipment:{equipment_id}:engineer_comment"}


def request_schema(context: dict, finding_id: str, equipment_id: str,
                   assessment_contract: str = ASSESSMENT_CONTRACT) -> dict:
    """Bind the assessment schema to addresses and citations in one context."""
    schema = assessment_schema(assessment_contract)
    planned = assessment_contract in {
        PLANNED_ASSESSMENT_CONTRACT, GROUNDED_PLAN_ASSESSMENT_CONTRACT,
    }
    grounded_plan = assessment_contract == GROUNDED_PLAN_ASSESSMENT_CONTRACT
    addresses = sorted(context.get("source_index", {}))
    native = context.get("contract_version") == 3
    require(not native or bool(addresses), "context_integrity", "Native source addresses are required")
    attention = deepcopy(SAME_DAY_SCHEMA)
    definitions = {}
    if addresses:
        definitions["source_address"] = {"type": "string", "enum": addresses}
        if native:
            catalog = citation_catalog(context["source_index"])
            definitions["source_citation"] = {"type": "string", "enum": list(catalog)}
            allowed = attention_addresses(finding_id, equipment_id)
            definitions["target_citation"] = {"type": "string", "enum": [
                key for key, value in catalog.items() if value["source_ref"] in allowed
            ]}

        def bind(value):
            if isinstance(value, dict):
                properties = value.get("properties", {})
                if "source_ref" in properties:
                    if native:
                        value.clear()
                        value["$ref"] = "#/$defs/source_citation"
                        return
                    properties["source_ref"] = {"$ref": "#/$defs/source_address"}
                if "sources_checked" in properties:
                    properties["sources_checked"]["items"] = {"$ref": "#/$defs/source_address"}
                for child in value.values():
                    bind(child)
            elif isinstance(value, list):
                for child in value:
                    bind(child)
        bind(schema)
        if native:
            for name in ("directive_evidence", "trigger_evidence"):
                attention["items"]["properties"][name]["items"] = {"$ref": "#/$defs/target_citation"}
    schema["$defs"] = definitions
    fact_schema = schema["properties"]["facts"]["anyOf"][0]
    facts = fact_schema["properties"]
    original = next(iter(facts.values()))
    branches = []
    for applicability, states in (
        ("applicable", list(STATES)), ("not_applicable", ["unknown"]),
        ("uncertain", ["unknown", "suspected"]),
    ):
        branch = deepcopy(original)
        branch["properties"]["applicability"]["enum"] = [applicability]
        branch["properties"]["state"]["enum"] = sorted(states)
        if applicability == "uncertain":
            branch["properties"]["verification_activity"] = text()
        branches.append(branch)
    definitions["policy_fact"] = {"anyOf": branches}
    for name in facts:
        facts[name] = {"$ref": "#/$defs/policy_fact"}
    if native:
        likelihood = schema["properties"]["likelihood_of_failure"]["anyOf"][0]
        pairs = []
        for confirmed in (True, False):
            pair = deepcopy(likelihood)
            choices = deepcopy(branches)
            if confirmed:
                choices = choices[:1]
                choices[0]["properties"]["state"]["enum"] = ["confirmed_true"]
            else:
                choices[0]["properties"]["state"]["enum"].remove("confirmed_true")
            pair["properties"] = {"required_function_failed": {"anyOf": choices}, **pair["properties"]}
            pair["required"].insert(0, "required_function_failed")
            pair["properties"]["score"] = {
                "type": "integer",
                "enum": list(range(CONFIRMED_FAILURE_MINIMUM if confirmed else 1, 11)),
            }
            pairs.append(pair)
        schema["properties"]["likelihood_of_failure"] = {"anyOf": [*pairs, {"type": "null"}]}
        del facts["required_function_failed"]
        fact_schema["required"].remove("required_function_failed")
    schema["properties"]["finding_id"]["enum"] = [finding_id]
    schema["properties"]["equipment_id"]["enum"] = [equipment_id]
    if not native:
        return schema
    definitions["assessment_uncertainty"] = schema["properties"]["uncertainties"]["items"]
    schema["properties"]["uncertainties"]["items"] = {"$ref": "#/$defs/assessment_uncertainty"}
    schema.pop("$defs")
    unable = deepcopy(schema)
    unable["properties"]["status"] = {"type": "string", "enum": ["unassessable"]}
    unable["properties"]["inability_reason"] = text()
    planning_name = "plan" if planned else "recommended_action"
    for name in ("summary", planning_name, "likelihood_of_failure", "impact_of_failure", "facts"):
        unable["properties"][name] = {"type": "null"}
    if grounded_plan:
        unable["properties"]["failure_basis"] = {"type": "null"}
    schema["properties"]["status"] = {"type": "string", "enum": ["assessed"]}
    schema["properties"]["inability_reason"] = {"type": "null"}
    schema["properties"]["summary"]["type"] = "string"
    if planned:
        schema["properties"]["plan"] = schema["properties"]["plan"]["anyOf"][0]
    else:
        schema["properties"]["recommended_action"]["type"] = "string"
    for name in ("facts", "impact_of_failure"):
        schema["properties"][name] = schema["properties"][name]["anyOf"][0]
    if grounded_plan:
        schema["properties"]["failure_basis"] = schema["properties"]["failure_basis"]["anyOf"][0]
    schema["properties"]["likelihood_of_failure"]["anyOf"] = pairs
    envelope = closed({
        "same_day_attention": attention, "assessment": {"anyOf": [schema, unable]},
        "citation_catalog_sha256": {"type": "string", "enum": [digest(canonical(catalog).encode())]},
    })
    envelope["$defs"] = definitions
    return envelope


def project_native_assessment(raw: str, index: dict) -> tuple[str, list]:
    """Resolve native citation IDs into source references before validation."""
    try:
        result = strict_json(raw)
    except (ValueError, RecursionError) as error:
        raise TriageError("malformed_json", "Assessment is not strict JSON") from error
    require(isinstance(result, dict)
            and set(result) == {"assessment", "same_day_attention", "citation_catalog_sha256"},
            "assessment_schema", "Native assessment requires the exact native-assessment-v2 envelope")
    catalog = citation_catalog(index)
    require(result["citation_catalog_sha256"] == digest(canonical(catalog).encode()),
            "assessment_evidence", "Source-line catalog differs from the trusted context snapshot")

    def resolve(value):
        if isinstance(value, dict):
            for name, child in value.items():
                if name in {"evidence", "directive_evidence", "trigger_evidence"}:
                    require(isinstance(child, list)
                            and all(isinstance(key, str) and key in catalog for key in child),
                            "assessment_evidence", "Unknown or invalid source-line citation selection")
                    value[name] = [deepcopy(catalog[key]) for key in child]
                else:
                    resolve(child)
        elif isinstance(value, list):
            for child in value:
                resolve(child)

    resolve(result)
    assessment = result["assessment"]
    require(isinstance(assessment, dict), "assessment_schema", "Assessment must be an object")
    if assessment.get("status") == "assessed":
        likelihood, facts = assessment.get("likelihood_of_failure"), assessment.get("facts")
        require(isinstance(likelihood, dict) and isinstance(facts, dict)
                and "required_function_failed" in likelihood and "required_function_failed" not in facts,
                "assessment_schema", "Native assessment requires the joint function/likelihood contract")
        facts["required_function_failed"] = likelihood.pop("required_function_failed")
    return canonical(assessment), result["same_day_attention"]


def request_for(model: str, context_text: str, finding_id: str, equipment_id: str,
                timeout: float, effort: str | None, feedback: str | None = None,
                required_activities: list[str] | None = None, *,
                system_prompt: str | None = None,
                possible_policy_activities: list[str] | None = None,
                feedback_detail: str | None = None, previous_draft: str | None = None,
                fixed_appended_activities: list[str] | None = None,
                model_appended_activities: list[str] | None = None,
                retry_action_budget: dict | None = None,
                assessment_contract: str = ASSESSMENT_CONTRACT) -> InferenceRequest:
    """Build one self-contained inference request for a target finding."""
    context = strict_json(context_text)
    message = {"context": context, "target_finding_id": finding_id,
               "primary_equipment_id": equipment_id, "validation_error": feedback,
               "validation_message": feedback_detail, "previous_assessment": previous_draft,
               "fixed_appended_verification_activities": fixed_appended_activities or [],
               "model_appended_verification_activities": model_appended_activities or [],
               "retry_action_budget": retry_action_budget,
               "required_verification_activities": required_activities or [],
               "possible_policy_activities": possible_policy_activities or []}
    if context.get("contract_version") == 3:
        message["assessment_contract"] = assessment_contract
        message["citation_catalog"] = citation_catalog(context["source_index"])
        message["citation_catalog_sha256"] = digest(canonical(message["citation_catalog"]).encode())
        history = context["payload"]["history"]
        timeline = history["equipment_timelines"].get(equipment_id, [])
        links = [
            item for item in history["case_links"]
            if finding_id in item["finding_ids"]
        ]
        related_ids = sorted({
            identifier for item in links for identifier in item["finding_ids"]
            if identifier != finding_id
        } | {
            item["finding_id"] for item in timeline if item["finding_id"] != finding_id
        })
        message["target_query_facts"] = {
            "finding": context["payload"]["findings"][finding_id],
            "equipment": context["payload"]["registry"][equipment_id],
            "history": {
                "equipment_timeline": timeline,
                "case_links": links,
                "related_findings": {
                    identifier: context["payload"]["findings"][identifier]
                    for identifier in related_ids
                },
                "limitations": history["limitations"],
            },
        }
    request = InferenceRequest(
        model=model, system=system_prompt if system_prompt is not None else assessment_prompt().text,
        user=canonical(message),
        response_schema=request_schema(context, finding_id, equipment_id, assessment_contract),
        reasoning_effort=effort, timeout_seconds=timeout,
    )
    request.prepared()
    return request


def validate_facts(facts: dict) -> None:
    """Enforce complete, internally consistent policy fact states."""
    require(isinstance(facts, dict) and set(facts) == set(FACT_NAMES),
            "fact_contract", "Every named policy fact is required")
    for name, fact in facts.items():
        require(isinstance(fact, dict) and fact.get("state") in STATES
                and fact.get("applicability") in APPLICABILITY,
                "fact_contract", "Invalid fact state or applicability")
        state, applicability = fact["state"], fact["applicability"]
        require(not (applicability == "not_applicable" and state != "unknown")
                and not (applicability == "uncertain" and state.startswith("confirmed")),
                "fact_contract", f"Inconsistent applicability/state for {name}: "
                "not_applicable requires unknown; uncertain permits unknown or suspected")


def citation_problems(citations: list, index: dict, location: str) -> list[tuple[str, str]]:
    """Collect exact-address and exact-quote violations for one evidence list."""
    problems = []
    for number, citation in enumerate(citations):
        address, quote = citation["source_ref"], citation["quote"]
        if address not in index:
            problems.append(("assessment_evidence",
                             f"{location}[{number}]: source_ref={address} is outside context.source_index; "
                             "use an exact supplied field or knowledge address, not an aggregate identifier."))
        elif not nonblank(quote) or quote not in index[address]:
            problems.append(("assessment_evidence",
                             f"{location}[{number}]: quote {quote[:100]!r} is not an exact "
                             f"substring of source_ref={address}. Copy a short exact clause from this "
                             "source only; do not join wrapped lines or relabel related-item evidence."))
    return problems


def validate_same_day_attention(items: list, finding: dict, index: dict) -> list:
    """Require target-local evidence for any source-directed same-day route."""
    require(SAME_DAY_VALIDATOR.is_valid(items), "assessment_schema", "Invalid same-day routing evidence")
    allowed = attention_addresses(finding["finding_id"], finding["equipment_id"])
    for number, item in enumerate(items):
        require(nonblank(item["reason"]), "assessment_evidence", "Same-day attention explanation is blank")
        for name in ("directive_evidence", "trigger_evidence"):
            citations = item[name]
            require(bool(citations) and all(citation["source_ref"] in allowed for citation in citations),
                    "assessment_evidence", "Same-day directive and trigger must cite the target's own sources")
            problems = citation_problems(citations, index, f"same_day_attention[{number}].{name}")
            require(not problems, "assessment_evidence", problems[0][1] if problems else "")
    return items


def validate_assessment(raw: str, finding: dict, index: dict,
                        assessment_contract: str = ASSESSMENT_CONTRACT) -> dict:
    """Validate identity, scores, evidence, facts and inability semantics."""
    try:
        result = strict_json(raw)
    except (ValueError, RecursionError) as error:
        raise TriageError("malformed_json", "Assessment is not strict JSON") from error
    planned = assessment_contract in {
        PLANNED_ASSESSMENT_CONTRACT, GROUNDED_PLAN_ASSESSMENT_CONTRACT,
    }
    grounded_plan = assessment_contract == GROUNDED_PLAN_ASSESSMENT_CONTRACT
    validator = Draft202012Validator(assessment_schema(assessment_contract))
    errors = sorted(validator.iter_errors(result), key=lambda x: list(map(str, x.path)))
    require(not errors, "assessment_schema", "Assessment violates schema")
    require(result["finding_id"] == finding["finding_id"]
            and result["equipment_id"] == finding["equipment_id"],
            "assessment_identity", "Assessment identity differs from input")
    if result["status"] == "unassessable":
        planning_name = "plan" if planned else "recommended_action"
        nullable = [
            "summary", planning_name, "likelihood_of_failure", "impact_of_failure", "facts",
        ]
        if grounded_plan:
            nullable.append("failure_basis")
        require(nonblank(result["inability_reason"]) and all(result[name] is None for name in nullable),
                "assessment_schema", "Unassessable assessment must not invent scores/text")
        raise TriageError("unassessable", "Assessment cannot support required scores")
    require(result["inability_reason"] is None
            and nonblank(result["summary"])
            and (isinstance(result["plan"], dict) if planned else nonblank(result["recommended_action"]))
            and all(result[name] is not None for name in
                    ("facts", "likelihood_of_failure", "impact_of_failure")),
            "assessment_schema", "Assessed output requires supported scores and text")
    require(not grounded_plan or result["failure_basis"] is not None,
            "assessment_schema", "Grounded assessment requires one shared failure basis")
    validate_facts(result["facts"])
    problems: list[tuple[str, str]] = []

    def check(condition: bool, code: str, message: str) -> None:
        if not condition:
            problems.append((code, message))

    def evidence(item: dict, location: str, required: bool = False) -> None:
        check(nonblank(item.get("reason", item.get("rationale"))),
                "assessment_evidence", "Evidence explanation is blank")
        check(not required or bool(item["evidence"]), "assessment_evidence", f"{location}: quoted evidence required")
        problems.extend(citation_problems(item["evidence"], index, f"{location}.evidence"))
        for address in item.get("sources_checked", []):
            check(address in index, "assessment_evidence", f"{location}: checked source {address} is outside context")

    for name in ("likelihood_of_failure", "impact_of_failure"):
        require(type(result[name]["score"]) is int, "assessment_schema", "Scores must be JSON integers")
        score(result[name]["score"])
        evidence(result[name], name, required=True)
    if grounded_plan:
        check(bool(result["failure_basis"]["evidence"]),
              "assessment_evidence", "failure_basis: quoted evidence required")
        problems.extend(citation_problems(
            result["failure_basis"]["evidence"], index, "failure_basis.evidence",
        ))
        for number, item in enumerate(result["plan"]["planning_requirements"]):
            evidence(item, f"plan.planning_requirements[{number}]", required=True)
    for name, fact in result["facts"].items():
        evidence(fact, f"facts.{name}",
                 required=fact["state"] != "unknown" or fact["applicability"] == "not_applicable")
        check(fact["verification_activity"] is None or nonblank(fact["verification_activity"]),
                "assessment_schema", "Verification activity is blank")
    for number, item in enumerate(result["uncertainties"]):
        evidence(item, f"uncertainties[{number}]")
        check(nonblank(item["verification_activity"]), "assessment_schema", "Verification required")
    failure = result["facts"]["required_function_failed"]
    check(not (failure["state"] == "confirmed_true"
               and result["likelihood_of_failure"]["score"] < CONFIRMED_FAILURE_MINIMUM),
          "assessment_contradiction", "Confirmed required-function failure needs top-end likelihood: "
          f"state=confirmed_true requires likelihood>={CONFIRMED_FAILURE_MINIMUM}; "
          f"received {result['likelihood_of_failure']['score']}")
    if problems:
        problems.sort(key=lambda problem: problem[0] != "assessment_contradiction")
        messages = list(dict.fromkeys(message for _, message in problems))
        detail = " | ".join(messages[:3])
        if len(messages) > 3:
            detail += f" | {len(messages)-3} additional validation errors."
        raise TriageError(problems[0][0], detail)
    return result
