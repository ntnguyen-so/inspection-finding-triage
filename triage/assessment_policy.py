"""Workflow-owned ordinal choices; never extracted or imported from old knowledge."""
from __future__ import annotations

from llm_inference.contracts import strict_json
from triage_knowledge.contracts import canonical_bytes

from .contracts import digest


CONFIRMED_FAILURE_MINIMUM = 9
_POLICY = {
    "version": "triage-assessment-v2",
    "authority": "Document 05 section 4; approved prototype ordinal anchors, not calibrated probabilities.",
    "likelihood_definition": "Near-term failure of the assessed item's required function.",
    "impact_definition": "Consequence if that failure occurs; credit only available and capable redundancy.",
    "bands": [
        {"minimum": 1, "maximum": 2,
         "likelihood": "Little supported indication of near-term function loss; supported margin/service state matters.",
         "impact": "Appearance, housekeeping or similarly limited low-energy consequence without a supported injury or functional-loss path."},
        {"minimum": 3, "maximum": 4,
         "likelihood": "Credible limited degradation with supported margin, without strong progression evidence.",
         "impact": "Localized recoverable consequence with supported containment, limited exposure or justified functional alternatives."},
        {"minimum": 5, "maximum": 6,
         "likelihood": "Active degradation or meaningful precursor; near-term progression uncertain.",
         "impact": "Material operational or personnel consequence where severe exposure, scale or protection loss is not established."},
        {"minimum": 7, "maximum": 8,
         "likelihood": "Strong progression, advanced damage or recurrent functional interruption.",
         "impact": "Specific supported severe consequence path, delayed integrity threat or major-accident exposure, accounting for actual protection."},
        {"minimum": 9, "maximum": 10,
         "likelihood": "Direct evidence of imminent loss; a confirmed failed required function belongs at this top end.",
         "impact": "Extreme consequences supported by the actual scenario, not merely an SCE label, generic hazard possibility, missing mitigation or repair cost."},
    ],
    "confirmed_required_function_failure_minimum": CONFIRMED_FAILURE_MINIMUM,
    "test_result_interpretation": (
        "A test confirms required-function failure only when cited evidence establishes an "
        "applicable criterion for that required function and adequate test conditions. A "
        "shortfall in one measured parameter while another necessary performance parameter "
        "is unmeasured, or while test-path validity is unresolved, supports suspected "
        "impairment rather than confirmed function loss. Retain material protection "
        "uncertainty and plan a complete functional test."
    ),
    "priors": "Reliability runs inversely to likelihood; criticality is only an impact prior. Neither is an answer.",
    "uncertainty": (
        "Do not inflate scores to obtain human attention. Missing evidence neither proves safety nor "
        "supplies the exposure, scale or protection-loss evidence required for a higher consequence "
        "band. Select the highest adjacent band directly supported by known facts and route unresolved "
        "decision modifiers to review. Unsupported required scores mean inability."
    ),
}
_ENCODED = canonical_bytes(_POLICY)
ASSESSMENT_POLICY_SHA256 = digest(_ENCODED)


def assessment_policy() -> dict:
    return strict_json(_ENCODED.decode("utf-8"))
