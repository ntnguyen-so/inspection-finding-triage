# Behavior Calibration: Observed Changes and Remaining Work

> **Document status:** executed, test-informed calibration study. This document
> reports observed system-level behavior changes and rejected interventions; it
> is not a controlled single-variable experiment, domain-certified scorecard or
> evidence of unseen-case accuracy.

## Open the two ticket sets side-by-side

| Artifact | Open | Identity | SHA-256 |
|---|---|---|---|
| Retained baseline experiment | [baseline 21-ticket JSON](../eval/results/behavior-calibration/baseline-triage-policy-v5-tickets.json) | model `gpt-6-sol`; application policy `triage-policy-v5`; experimental and not acceptance-eligible | `2c6b2a0d85e0462ebe589eadeb3522b078e4c364b9472220ec5ad1e944037381` |
| Current delivery artifact | [root `tickets.json`](../tickets.json) | model `gpt-6.1-sol`; assessment prompt v7; application policy `triage-policy-v16`; provisional AI-only review | `2bb8d0f34da36142042c6f5f983622be358e45fc4690378a935e28ba189f1f98` |

Open both files and compare tickets with the same `finding_id`. Section 5 below
highlights five representative changes; section 4 gives the complete aggregate
comparison.

In this document, **v5 means `triage-policy-v5`**, the baseline version of the
code-owned urgency and review policy recorded in each ticket's urgency
rationale. It is not model version 5, Document 05 or the version of the whole
system. The baseline also used a different model, prompt/context and assessment
implementation, so the two files are a system-level before/after comparison,
not a policy-only A/B test.

The baseline link is a byte-identical panel-facing copy of
`eval/results/triage/copilot-gpt6-current-all21/tickets.experimental.json` from
the retained lossless archive. Its hash matches the archived manifest; no ticket
was regenerated or edited for this comparison.

## Abstract

Calibration began because a retained complete experimental ticket set was
structurally valid but operationally unconvincing. Nineteen of 21 tickets were
at U7-U9, 13 were at impact 8 and all 21 had `review_required=true`. The field
then represented broad review obligations, including SCE and material-
uncertainty review, rather than only exceptional prequeue arbitration.

The current 21-ticket delivery artifact behaves differently:

- exceptional prequeue review is 6/21 rather than a universal broad-review flag;
- U7-U9 concentration is 15/21 rather than 19/21, while U9 remains 7/21;
- likelihood changed on 7 findings, impact on 9 and numeric urgency on 7;
- five findings changed scheduling band; and
- representative cases now apply a narrower operational-function assessment
  convention instead of automatically transferring a possible whole-equipment
  consequence to the observed local defect.

These are improvements against the declared current design, not proof of numeric
risk truth. Model, prompt, assessment policy, ticket projection and application
policy all changed. Review routing and model-proposed rule inputs also interact,
so the 15 removed flags cannot be assigned to independent additive causes. The
result must be read as a system-level calibration outcome with explicit causal
limits.

## 1. Why this study exists

This document began as the record of consequence-anchor, review-routing and
urgency-policy experiments. Knowledge lifecycle architecture now belongs in
Document 05, the knowledge change experiment in Document 07, and workflow policy
in Document 06. This study returns to one question:

**What changed in generated triage behavior, why did it change, and what remains
to calibrate?**

The trigger was not a schema failure. A retained complete experimental output
passed important software controls but still provided weak prioritisation:

| Baseline symptom | Observed result | Why it was a problem |
|---|---:|---|
| High urgency concentration | 19/21 at U7-U9 | The queue provided little separation between local defects, material degradation and immediate protection decisions |
| Broad review saturation | 21/21 flagged | `review_required` did not distinguish ordinary approval from exceptional prequeue arbitration |
| Impact concentration | 13/21 at I8 | Different consequence types frequently collapsed onto one anchor |
| Weak decision distinction | SCE and uncertainty frequently implied review | Asset class or missing information became a routing shortcut rather than a fact-sensitive decision |

This baseline is the retained experimental ticket file, not root `tickets.json`
and not a hand-written scorecard. Distribution located suspicious uniformity;
it did not define the desired answer. Each retained change still required
source-grounded case review and deterministic safety checks.

## 2. What calibration meant

Calibration was not model fine-tuning and did not hand-correct the final
`tickets.json`. It changed general system surfaces and regenerated the batch:

1. inspect generated experimental tickets and identify a repeated failure mode;
2. map the failure to its authority surface: assessment rubric, knowledge,
   prompt protocol, application policy or projection;
3. define the intended behavioral change and the safety condition that must not
   regress;
4. change a bounded general surface rather than branch on finding ID;
5. run deterministic tests, targeted provider experiments and semantic review;
6. reject changes that improved one metric while weakening grounding,
   uncertainty handling, planning completeness or X01 stability; and
7. regenerate rather than edit published ticket text.

The protected invariants were:

- the model proposes L/I, while code derives urgency;
- unknown is not converted into confirmed absence;
- a review flag cannot legitimize unsupported scores;
- supported high-consequence corners and confirmed overrides retain their floors;
- every draft still requires ordinary human approval; and
- evaluation expectations are not weakened to make a run pass.

A requested working capacity target of no more than seven exceptional prequeue
routes was used to test whether the queue remained usable. It is a workload
constraint, not a quality threshold. Per-ticket evidence and semantic review
remain the quality checks.

### 2.1 Comparison identities and causal limits

| Observation | Model | Assessment/policy surface | Result |
|---|---|---|---|
| retained baseline experiment | `gpt-6-sol` | prompt-context hash `746e29...b1b5`; assessment-implementation hash `2605dd...601e`; `triage-policy-v5` | 19/21 U7-U9; 21/21 review flags; 13/21 at I8 |
| same-model near-control | `gpt-6.1-sol` | `copilot-gpt61-current-all21` retry; same assessment implementation hash as baseline; `triage-policy-v5`; context hash `7118d3...9024` rather than baseline `746e29...b1b5` | 19/21 U7-U9; 20/21 review flags; 13/21 at I8 |
| current artifact | `gpt-6.1-sol` | `assessment-system-v7`; `triage-assessment-v2`; `native-assessment-v4`; `ticket-projection-v4`; `triage-policy-v16` | 15/21 U7-U9; 6/21 exceptional review routes; 10/21 at I8 |

Model, prompt, assessment policy, projection and application policy did not
remain fixed between baseline and current. The comparison therefore demonstrates
system-level behavior change, not the isolated causal effect of one parameter.
The same-model near-control is useful but not a formal control. It retained the
baseline assessment implementation and policy hashes, but not the same complete
context hash. It is also recorded as a failed experiment whose two semantic
reviews each passed 60/63 dimensions. It still shows that one `gpt-6.1-sol` run
on the older implementation/policy surface retained the earlier urgency
concentration, impact-8 concentration and review saturation. F-1009 and F-1016
also retained their baseline L2/I8/U7/review pattern in that run.

## 3. What changed in the system

The outcome did not come from one threshold adjustment. It came from separating
assessment, uncertainty, routing and projection concerns that the baseline
conflated.

### 3.1 Assessment target and anchors

The current prompt and assessment surface make a narrower operational-function
interpretation more explicit instead of treating generic deterioration or any
possible consequence as the scored failure event. The underlying "required
function" language predates this calibration; prompt v7 adds the more specific
failure-basis instruction. This explains the largest likelihood changes for
local defects such as degraded coating and lost identification.

Impact anchors also distinguish production disruption, maintainability,
personnel exposure and major-accident potential rather than assigning one
default high anchor. Severe personnel or major-accident consequences remain high
where evidence supports them.

The operational-function interpretation is a candidate design choice, not a
supplied domain rule or independently certified truth. It remains a point for
domain-owner confirmation.

### 3.2 Fact and uncertainty treatment

Confirmed, false, suspected and unknown states are explicit. Unknown facts are
not automatically treated as proof of the worst consequence.

This was not uniformly a stronger precaution. Several non-protection unknowns
moved from score floors or broad review into required action checks. That change
reduces queue saturation but places more weight on action-plan execution. It
must not be described as preserving the same precaution through a different
label.

### 3.3 Urgency derivation

The code-owned base calculation was unchanged between baseline and current:

```text
base  = ceil(0.7 * impact + 0.3 * likelihood)
final = max(base, applicable floors and confirmed overrides)
```

The observed urgency changes came from changed model-proposed L/I scores and
changed structured fact, uncertainty and policy-rule inputs, plus application
policy changes - not from replacing the base formula.

### 3.4 Review semantics and decomposition

The meaning of the published review field was narrowed. In the baseline it
represented broad "needs review" obligations, including SCE and material
uncertainty. In the current artifact it represents exceptional human arbitration
before normal queuing. Routine verification remains in the recommended action.
A confirmed urgent condition can therefore be U9 without exceptional review.

Policy and model inputs interact, so the 15 removed flags were tested by replay,
not inferred from projected ticket text. Replaying the baseline assessment
inputs through current `derive_policy` reproduces this split:

| Replay result | Findings | Count |
|---|---|---:|
| Current routing alone removes the baseline flag | F-1001, F-1004, F-1006, F-1007, F-1009, F-1014, F-1015, F-1016, F-1019 | 9 |
| Current routing still flags the baseline inputs; changed assessment inputs are also required | F-1003, F-1005, F-1010, F-1011, F-1018, F-1021 | 6 |

The replay was checked by feeding the current run's own inputs through the same
function; it reproduced the six published exceptional-review routes exactly.

All six input-dependent removals are protection cases. F-1003 and F-1005 no
longer emit protection-affecting uncertainties; F-1010 and F-1011 no longer emit
any material uncertainties; and F-1018 and F-1021 change
`protection_impaired` from `suspected` to `unknown` while also dropping
protection-affecting uncertainties. This may be justified where a confirmed
failed test already fixes immediate attention and the remaining uncertainty
only changes diagnosis or redundancy. It is also the highest-risk calibration
dependency: lower review counts must not be achieved by suppressing unresolved
protection decisions.

The reduction from 21 to 6 is therefore not a pure routing-policy result and not
an unqualified quality improvement. It combines an intentional field-semantics
change with changed model outputs that require case-level scrutiny.

### 3.5 Retained and rejected interventions

Several plausible changes were rejected:

- an early selective-review policy removed review from cases that still had
  unresolved safety decisions;
- a more complex interaction-sensitive urgency formula passed mathematical
  checks but produced little defensible operational benefit;
- a prompt-only provenance repair changed urgency bands and review routing in
  the fixed comparison; and
- a broader prompt-authority reduction introduced a real-case semantic
  regression and frequent action repair.

Calibration did not mean keeping every intervention that lowered urgency or
review count.

## 4. Aggregate before-and-after result

The baseline aggregate is summarized in
`eval\results\design-behavior-demonstration.json`; its raw ticket bytes remain
in the lossless archive indexed by
`eval\results\artifacts-manifest.json`. The current column is computed from root
`tickets.json`.

| Measure | Baseline | Current | Observed change |
|---|---:|---:|---:|
| Tickets | 21 | 21 | Complete coverage preserved |
| Published review flag | 21 broad review | 6 exceptional review | -15 flags, with changed semantics |
| U7-U9 | 19 | 15 | -4 |
| U9 | 7 | 7 | Unchanged |
| Likelihood values changed | - | 7 findings | 5 adjacent; 2 changed by at least 2 |
| Impact values changed | - | 9 findings | 5 adjacent; 4 changed by at least 2 |
| Urgency values changed | - | 7 findings | 6 adjacent; 1 changed by at least 2 |
| Scheduling band changed | - | 5 findings | Fewer than numeric urgency changes |

In this selected baseline/current pair U9 remains seven, so calibration did not
suppress every supported urgent case merely to flatten the histogram. A sibling
retained `gpt-6-sol` / `triage-policy-v5` run produced eight U9 tickets, which
confirms run-to-run variation and prevents treating "7 unchanged" as a stability
result. Fifteen of 21 current tickets remain at U7-U9, so the result is improved
discrimination rather than a balanced or low-urgency queue.

### 4.1 Distribution change

| Score | Baseline likelihood | Current likelihood | Baseline impact | Current impact | Baseline urgency | Current urgency |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 2 | 0 | 0 | 1 | 0 | 0 |
| 3 | 0 | 0 | 0 | 3 | 0 | 0 |
| 4 | 2 | 2 | 2 | 0 | 1 | 2 |
| 5 | 3 | 2 | 0 | 1 | 1 | 1 |
| 6 | 1 | 2 | 1 | 5 | 0 | 3 |
| 7 | 3 | 2 | 5 | 1 | 4 | 2 |
| 8 | 2 | 3 | 13 | 10 | 8 | 6 |
| 9 | 8 | 8 | 0 | 0 | 7 | 7 |
| 10 | 0 | 2 | 0 | 0 | 0 | 0 |

Most numeric changes were adjacent-anchor moves and may reflect ordinary model
variation as well as policy calibration. The stronger evidence is concentrated
in the large L/I changes, deterministic routing changes and repeated aggregate
pattern.

### 4.2 Partition check

| Partition | Review flags | U7-U9 | L changes | I changes | U changes |
|---|---:|---:|---:|---:|---:|
| development (13 findings) | 13 -> 3 | 13 -> 9 | 6 | 5 | 4 |
| test (8 findings) | 8 -> 3 | 6 -> 6 | 1 | 4 | 3 |

The review change was not limited to development findings. This is not a blind
generalisation claim: the split is non-blind and AI-assisted, and the complete
system surface changed.

## 5. Representative decision changes

| Finding | Baseline | Current | Interpretation |
|---|---|---|---|
| F-1009, degraded deck coating | L2 / I8 / U7 / broad review | L9 / I2 / U5 / no exceptional review | The baseline explicitly did not claim section loss, but assigned I8 to a possible structural-support consequence. The current run instead scores the observed corrosion-barrier failure. This aligns with the revised convention; it does not independently prove the convention or score is correct. |
| F-1016, illegible PSV tag | L2 / I8 / U7 / broad review | L10 / I3 / U6 / no exceptional review | The current run treats identification as the failed local function while the register supports in-date recertification. This demonstrates the effect of the revised target, not domain certification of the anchors. |
| F-1001, compressor vibration trend | L7 / I8 / U9 / broad review | L7 / I6 / U9 / no exceptional review | Both artifacts cite the same production consequence. The current anchor classifies it as material operational loss rather than severe personnel or major-accident loss. U9 remains because the supplied source requires same-day specialist attention. |
| F-1019, loose cladding | L7 / I7 / U7 / broad review | L8 / I5 / U6 / no exceptional review | Both artifacts exclude compressor process loss. The current run treats unknown drop exposure as a required field check rather than established high consequence. This is less precautionary and depends on execution of the verification action. |
| F-1017, uncertain firewater duty | L5 / I8 / U8 / broad review | L6 / I8 / U8 / exceptional review retained | Missing flow and unresolved test-path validity still change the protection decision. Selective routing retains review where uncertainty is decision-material. |

These examples cannot be summarized as "lower scores." The intended change is
different function definition, evidence scope and decision routing. Whether
those choices are operationally correct still requires domain-owner calibration.

## 6. Current result and its limits

The current artifact contains six exceptional-review routes: F-1002, F-1008,
F-1012, F-1013, F-1017 and F-1020. Each names a concrete protection, evacuation,
restoration or related verification decision. Six meets the requested working
capacity target of no more than seven; meeting that target is not a quality
result. Current routing applied to the baseline and same-model near-control
assessment inputs would still produce 12 and 13 flags respectively. Reaching six
therefore depends on the new assessment surface as well as routing policy, and
the six protection-case input changes above remain a specific regression risk.
All 21 drafts still require ordinary human approval.

Current urgency is U4=2, U5=1, U6=3, U7=2, U8=6 and U9=7. It is more
discriminating than the baseline, but it is not evidence that fifteen
weekly-or-faster tickets are operationally optimal.

The exact current artifact received one complete primary semantic review and
recorded `provisional_pass` with 63/63 applicable dimensions. That review is
AI-only, non-blind and not domain certification. X01 remains inconclusive for full protocol acceptance
because its semantic procedure was supplementary and reviewer identity was
incomplete.

## 7. Claim boundaries

- The before/after comparison is confounded by changes to model, prompt,
  assessment policy, projection and application policy.
- The baseline and current `review_required` fields have different operational
  meanings; 21 to 6 is not a like-for-like semantic metric.
- Review-policy and model-input changes overlap. Six protection cases required
  changed assessment inputs as well as current routing, so fewer flags could
  otherwise hide less uncertainty surfacing.
- Most score changes are adjacent-anchor moves and may include normal model
  variation.
- The operational-function assessment convention is candidate-owned and awaits
  domain-owner confirmation.
- The reviewer is AI-only and not an independent domain expert.
- The split is non-blind and AI-assisted.
- Score distributions show discrimination, not score accuracy.

## 8. Calibration authority and future work

The calibration surface has three authority classes.

### 8.1 Source-owned constraints

These are inputs to honor, not candidate tuning knobs:

- explicit source timing or attention instructions;
- supplied override conditions and domain rules; and
- recorded equipment and finding facts.

Changing them requires source-backed correction or an authorized contract
change.

### 8.2 Candidate-owned policy

These can be calibrated with controlled evidence:

- likelihood and impact anchor wording;
- precautionary floors for unknown protection state and other material unknowns;
- exceptional-review thresholds and SCE routing;
- urgency-band mapping from numeric urgency to scheduling action;
- action-plan checks and closure evidence; and
- prompt/schema requirements for structured uncertainty.

The 0.7 impact and 0.3 likelihood weights can also be studied, but the current
behavior change did not come from changing them. Current choices are code and
prompt artifacts, not runtime sliders. A change requires focused tests, retained
before/after evidence and an explicit comparability note.

### 8.3 Model-influenced assessments

The model proposes facts, fact states, uncertainty materiality, safety
relevance, affected decisions and L/I scores. Code validates structure and then
applies deterministic urgency and review policy. These outputs are sensitive to
prompt and model behavior but must not be tuned indirectly toward a preferred
histogram.

High urgency and exceptional review are intentionally separate. A confirmed
urgent condition can justify U9 without exceptional arbitration; review is for
an unresolved decision, not a second severity scale.

### 8.4 Next credible calibration

1. run repeated same-configuration generations to estimate score and route
   stability;
2. obtain domain-owner review of the assessment-target convention and disputed
   L/I anchors;
3. test one model, prompt or policy change at a time against the frozen
   scenarios;
4. replay and adjudicate F-1003, F-1005, F-1010, F-1011, F-1018 and F-1021 to
   verify that lower review counts do not come from suppressing unresolved
   protection uncertainty;
5. calibrate exceptional-review capacity against actual staffing rather than
   treating the current count target as a quality threshold;
6. use unseen or newly collected findings to test generalisation; and
7. retain both improved and failed observations.

Until that work exists, the current result is stronger prototype behavior, not a
completed or universally transferable calibration.

## 9. Evidence map

| Claim | Evidence |
|---|---|
| Baseline 19/21 U7-U9, 21/21 review and impact concentration | `eval\results\design-behavior-demonstration.json` |
| Baseline raw tickets | [Direct panel copy](../eval/results/behavior-calibration/baseline-triage-policy-v5-tickets.json), lossless archive and manifest under `eval\results` |
| Current-policy replay of baseline, near-control and current assessment inputs | `eval\results\behavior-calibration-replay.json` |
| Current L/I/U and review dispositions | Root `tickets.json` |
| Current exact-artifact review and run identity | `eval\results\triage\structured-planning-v31\final\reviewer-observation.json` |
| Current status and remaining limits | Root `README.md` and `eval\results\README.md` |
| Knowledge lifecycle architecture | `docs\05_KNOWLEDGE_LIFECYCLE.md` |
| Knowledge change experiment | `docs\07_KNOWLEDGE_CHANGE_STUDY.md` |
| Controlled failures and rejected experiments | `eval\results\README.md` |
| Current urgency and routing implementation | `triage\policy.py`, `triage\projection.py` and focused tests |
| Current assessment anchors and failure-basis instruction | `triage\assessment_policy.py` and `triage\prompts\assessment-system-v7.txt` |

## 15. Controlled-change disclosure

This section number remains because the owner-controlled `DESIGN.md` references
it. Calibration used exposed findings and is therefore test-informed rather than
blind. Failed experiments and prior outputs remain retained; the final file was
regenerated through general mechanisms rather than hand-corrected. No source
package, split, evidence card, expected answer or evaluator rule was weakened to
produce the current distribution.

Any future calibration that changes anchors, floors, review routing,
urgency-band mapping, prompt semantics or model must preserve the prior artifact,
state affected scenarios and comparability impact, and rerun relevant validation
and semantic review.
