# Current Acceptance Evidence Status

This report maps the 17 scenarios in the frozen
[`acceptance.json`](../spec/acceptance.json) contract to retained observations.
It summarizes evidence; it does not modify the frozen specification, certify
domain correctness or authorize operational use.

Status meanings:

- **Supported** — retained evidence directly covers the scenario within its
  stated scope.
- **Partial** — relevant evidence exists, but at least one required
  observation, provenance field or calibration claim remains unresolved.
- **Inconclusive** — the experiment was informative, but the declared protocol
  cannot award a pass or fail.
- **Not met** — retained evidence contradicts at least one pass criterion.

The submitted root `tickets.json` is contract-valid and received a provisional
63/63 AI-only semantic review. The final configuration was calibrated after the
test findings had been exposed, so this is test-informed regression evidence,
not an untouched test result. It is ticket-content evidence, not a substitute
for the system-level scenarios below.

## Why B01 is not met

This is an **evaluation-isolation failure**, not a failure to generate the final
21 tickets.

- A DEV run was intended to assess only the 13 DEV findings.
- The workflow selected those 13 outputs, but built the model context from all
  21 findings.
- The model therefore received the descriptions of all eight TEST findings
  while generating the DEV outputs.
- This violated B01's declared rule that TEST finding descriptions must stay
  out of development inference context.

Using all 21 findings in the **final delivery run is correct**, because the
candidate brief requires 21 generated tickets. The problem applies only to the
claim that the 13/8 evaluation split isolated the TEST cases.

This is also separate from **test-informed tuning**. Context leakage means the
model could see TEST descriptions during DEV inference. Test-informed tuning
means later system changes were made after TEST results had been observed. Both
reduce evaluation independence, but only the first is the direct reason B01 is
marked **Not met**.

## Scenario status

| Scenario | Status | Retained evidence | Remaining limit |
|---|---|---|---|
| A01 — Output contract | **Supported** | [Current-revision validation](offline-validation-20261121.json); [mutation tests](../tests/test_assess.py); [final exact-artifact review](triage/structured-planning-v31/final/reviewer-observation.json) | Contract validity does not establish semantic correctness. |
| A02 — Bounded recovery | **Partial** | [Malformed/schema recovery observations](design-behavior-demonstration.json); [Azure parity replay](inference/azure-gpt61-parity-20261118-summary.json) | Application sends are bounded, but hidden Copilot HTTP/SDK attempts are not observable. |
| A03 — Exhaustion and publication failure | **Supported** | [Current-revision validation](offline-validation-20261121.json); [fail-closed fault report](triage/native-v2-fault-evidence-1/report.json); [production tests](../../tests/test_triage.py) | Evidence is deterministic fault injection rather than a production outage. |
| A04 — Valid but semantically wrong output | **Partial** | [Calibrated final semantic observation](triage/structured-planning-v31/final/reviewer-observation.json) | Reviewer identity was incomplete, and the required unresolved adjacent-score `needs_review` behavior was not exercised. |
| B01 — Actual knowledge/context delivery | **Not met** | [Development-context audit](triage/structured-planning-v31/b01-development-context-audit.json); [final provider-bound context](triage/structured-planning-v31/final/evidence/run.json) | Evaluation isolation failed: DEV selected 13 outputs, but every DEV provider input contained all eight TEST finding records. Final all-21 generation remains valid. |
| B02 — Bounded knowledge influence | **Partial** | [Frozen-protocol execution](triage/v10-calibration/b02-execution/report.json); [semantic negative-control review](triage/v10-calibration/b02-execution/negative-control-semantic-review.json) | The SDK-inclusive attempt bound is inconclusive, each condition has one observation, and the study predates the delivered implementation and knowledge release. |
| B03 — Six-month maintenance path | **Supported** | [DESIGN.md section B](../../DESIGN.md); [knowledge-change study](../../docs/07_KNOWLEDGE_CHANGE_STUDY.md); [official-store edit study](controlled-studies/knowledge-kb-edit-v1-study.json); [release disposition](controlled-studies/knowledge-kb-edit-v1-release-disposition.json) | The policy-v11 study was test-informed by F-1002 and exposed an editor-scope defect; its experimental guidance was rejected rather than promoted. |
| C01 — Urgency grid and monotonicity | **Supported** | [Current-revision validation](offline-validation-20261121.json); [100-cell urgency-grid evidence](design-behavior-demonstration.json); [design rationale](../../DESIGN.md) | The formula is a declared prototype attention policy, not calibrated operational risk truth. |
| C02 — Corner behavior and alternatives | **Supported** | [DESIGN.md section C](../../DESIGN.md); [evaluation-contract rationale](../../docs/03_EVALUATION_ACCEPTANCE.md) | The selected asymmetric behavior remains candidate-owned. |
| C03 — Override and fact-state matrix | **Supported** | [Current-revision validation](offline-validation-20261121.json); [policy tests](../../tests/test_triage.py); [policy implementation](../../triage/policy.py) | Precautionary floors are declared policy and must not be presented as confirmed regulatory facts. |
| C04 — Fact assessment before urgency | **Partial** | [Final semantic observation](triage/structured-planning-v31/final/reviewer-observation.json); [final tickets](../../tickets.json) | The test-informed case review is AI-only and does not provide domain-expert certification. |
| D01 — Supported deferral and review | **Partial** | [Final review-route observation](triage/structured-planning-v31/final/reviewer-observation.json); [final tickets](../../tickets.json) | The six test-informed exceptional routes are concrete, but routing thresholds remain operationally uncalibrated. |
| D02 — Inability to assess and invalid inputs | **Supported** | [Current-revision validation](offline-validation-20261121.json); [fail-closed fault report](triage/native-v2-fault-evidence-1/report.json); [production tests](../../tests/test_triage.py) | These are tested failure paths, not evidence about every future malformed input. |
| D03 — SCE and local-defect distinctions | **Partial** | [Final semantic observation](triage/structured-planning-v31/final/reviewer-observation.json); [behavior calibration study](../../docs/08_BEHAVIOR_CALIBRATION_STUDY.md) | The test-informed distinctions passed AI-only review; adjacent numeric judgments remain candidate-owned. |
| D04 — Limits, assumptions and AI assistance | **Supported** | [DESIGN.md](../../DESIGN.md); [current evidence index](README.md) | Disclosure does not remove the stated production, calibration and approval gaps. |
| X01 — Repeat stability | **Inconclusive** | [Development repeat adjudication](triage/structured-planning-v31/x01-development-adjudication.json); [development-context audit](triage/structured-planning-v31/b01-development-context-audit.json) | All urgency bands and review flags were stable, but the DEV context contained TEST records, reviewer identity was incomplete and configuration selection was non-independent. Those protocol failures prevent an X01 result rather than merely limiting one semantic judgment. |
| X02 — Reproducibility and delivery | **Partial** | [Final run evidence](triage/structured-planning-v31/final/evidence/run.json); [cost summary](delivery-cost-summary.json); [current-code replay](inference/doc04-all21-replay-20261118/summary.json) | Clean-checkout reproduction, hidden Copilot attempts and actual Copilot USD allocation remain unresolved. |

## Overall interpretation

| Status | Count |
|---|---:|
| Supported | 8 |
| Partial | 7 |
| Inconclusive | 1 |
| Not met | 1 |

This is sufficient to show a complete generated prototype with substantial
evidence and explicit limits. The development/test context-isolation criterion
was not met, so the 13/8 split supports workflow regression analysis but not
case-isolated generalization. This is not full protocol acceptance,
domain-expert approval or production readiness.
