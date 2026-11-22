# Behavior Calibration Study

This study asks one question: **did the generated ticket set become more useful
for prioritisation, what changed to produce that result, and what evidence is
still missing?**

Calibration here does not mean model fine-tuning or hand-editing tickets. It
means changing general assessment, prompt, routing or projection behavior,
regenerating all 21 tickets, and retaining both successful and failed
observations.

The comparison is test-informed and non-blind. It shows a system-level behavior
change; it does not establish domain-certified scores, accuracy on unseen cases
or the isolated effect of one parameter.

## 1. What is being compared

Open the two ticket sets and compare rows with the same `finding_id`:

| Artifact | Link | System identity | SHA-256 |
|---|---|---|---|
| Retained baseline experiment | [Baseline 21-ticket JSON](../eval/results/behavior-calibration/baseline-triage-policy-v5-tickets.json) | model `gpt-6-sol`; application policy `triage-policy-v5`; experimental and not acceptance-eligible | `2c6b2a0d85e0462ebe589eadeb3522b078e4c364b9472220ec5ad1e944037381` |
| Current delivery artifact | [Root `tickets.json`](../tickets.json) | model `gpt-6.1-sol`; assessment prompt v7; application policy `triage-policy-v16`; provisional AI-only review | `2bb8d0f34da36142042c6f5f983622be358e45fc4690378a935e28ba189f1f98` |

The baseline link is a byte-identical retained copy of the archived experimental
output. It was not regenerated or edited for this study.

The two systems differ in model, prompt, assessment implementation, projection
and application policy. This is therefore a before/after comparison of the
whole system, not an A/B test of `triage-policy-v5` versus
`triage-policy-v16`.

### 1.1 Terms used in this document

- **L** is model-proposed likelihood on the 1-10 assessment scale.
- **I** is model-proposed impact on the 1-10 assessment scale.
- **U** is code-derived urgency on the 1-10 scale.
- **Review flag** means the published `review_required` field. Its meaning
  changed: the baseline used it for broad review obligations, while the current
  system uses it only for exceptional human arbitration before normal queuing.
  Every ticket still requires ordinary human approval.
- **Scheduling band** groups numeric urgency into the ticket's operational
  action window. A numeric change does not always cross a band boundary.
- **SCE** means Safety Critical Element.
- **PSV** means pressure safety valve.
- **Projection** is the deterministic code that turns validated assessment and
  policy decisions into ticket fields and reader-facing text.
- **Near-control** means one retained `gpt-6.1-sol` run on the older assessment
  implementation and `triage-policy-v5`. Its complete context hash differed
  from the baseline, so it is supporting evidence rather than a formal control.
- **Replay** means taking retained model-proposed scores, facts and uncertainty
  from an older run and passing them through the current deterministic routing
  code. It isolates routing effects without claiming that the retained model
  inputs were correct.
- **Activation** is the reviewed manifest that pins the exact knowledge release,
  retrieval implementation, assessment policy, execution code and prompt for a
  run. Document 07 section 1.1 shows how it is regenerated and approved.

## 2. Bottom line

| Measure | Baseline | Current | Interpretation |
|---|---:|---:|---|
| Tickets | 21 | 21 | Complete coverage preserved |
| Published review flag | 21 broad-review flags | 6 exceptional-review flags | Lower count, but the field semantics changed |
| U7-U9 | 19 | 15 | More separation, but the current queue remains urgency-heavy |
| U9 | 7 | 7 | Unchanged in this selected pair; not a stability result |
| I8 | 13 | 10 | Less impact concentration |
| Likelihood changed | - | 7 findings | Five adjacent moves; two changed by at least two points |
| Impact changed | - | 9 findings | Five adjacent moves; four changed by at least two points |
| Numeric urgency changed | - | 7 findings | Six adjacent moves; one changed by at least two points |
| Scheduling band changed | - | 5 findings | Fewer changes than the numeric urgency count |

The current tickets are more differentiated under the declared current design.
That is useful prototype evidence, not proof that each numeric score is
operationally correct.

The largest caveat is the review reduction. Current routing alone explains nine
of the 15 removed flags. The remaining six also depend on changed model-proposed
facts and uncertainty in protection cases. Those six require domain scrutiny
before the lower review count can be treated as safe.

## 3. Why calibration was needed

The baseline was structurally valid but weak as a prioritisation queue:

| Baseline symptom | Observed result | Why it mattered |
|---|---:|---|
| High urgency concentration | 19/21 at U7-U9 | Local defects, material degradation and immediate protection decisions were poorly separated |
| Review saturation | 21/21 flagged | The field did not distinguish ordinary approval from exceptional arbitration |
| Impact concentration | 13/21 at I8 | Different consequence types frequently collapsed onto one anchor |
| Routing shortcuts | SCE status and broad uncertainty frequently implied review | Asset class or missing information could replace a fact-sensitive decision |

The distribution identified suspicious uniformity; it did not define the
correct answer. Each change still needed case-level evidence review and
deterministic safety checks.

A working-capacity target of no more than seven exceptional routes was used to
test whether the queue remained usable. It is a workload constraint, not a
quality threshold.

## 4. What changed in the system

The result did not come from one threshold adjustment. Assessment target,
uncertainty handling, review semantics and ticket projection changed together.

### 4.1 Assessment target and anchors

The current assessment asks about failure of the observed required function,
rather than automatically transferring a possible whole-equipment consequence
to every local defect.

For example, degraded coating is assessed first as loss of corrosion protection,
and an illegible PSV tag as loss of identification. Severe personnel or
major-accident consequences remain high where the evidence supports them.

The current impact anchors also distinguish production disruption,
maintainability, personnel exposure and major-accident potential. This
operational-function convention is a project-defined design choice, not a
supplied domain rule or independently certified truth.

### 4.2 Facts and uncertainty

The current assessment records facts as confirmed, false, suspected or unknown.
Missing evidence is not treated as confirmed absence.

Some non-protection unknowns moved from score floors or broad review flags into
explicit verification actions. This reduced queue saturation, but it is not the
same precaution expressed differently: it places more reliance on executing the
action plan.

### 4.3 Urgency formula

The code-owned base formula did not change:

```text
base  = ceil(0.7 * impact + 0.3 * likelihood)
final = max(base, applicable floors and confirmed overrides)
```

Observed urgency changes came from changed L/I proposals, changed structured
facts and uncertainty, and application-policy rules. The model still does not
choose urgency.

### 4.4 Review semantics

The baseline review flag covered broad obligations, including SCE and material
uncertainty review. The current flag is narrower: it identifies an unresolved
decision that needs exceptional human arbitration before normal queuing.
Routine checks remain in the recommended action.

A confirmed urgent condition can therefore be U9 without an exceptional review
flag. High urgency and exceptional review are separate decisions.

## 5. What caused the review-count reduction

The review flag fell from 21 to 6, but the two fields are not semantically
identical. A deterministic replay was used to separate two causes.

First, the baseline assessment inputs were passed through the current routing
code without changing their model-proposed scores, facts or uncertainty. This
produced 12 flags instead of 21:

| Cause | Findings | Count |
|---|---|---:|
| Current routing alone removes the baseline flag | F-1001, F-1004, F-1006, F-1007, F-1009, F-1014, F-1015, F-1016, F-1019 | 9 |
| Current routing still flags the baseline inputs | F-1002, F-1003, F-1005, F-1008, F-1010, F-1011, F-1012, F-1013, F-1017, F-1018, F-1020, F-1021 | 12 |

Second, the current assessment inputs were replayed through the same routing
code. The replay reproduced the six flags in the published artifact exactly:
F-1002, F-1008, F-1012, F-1013, F-1017 and F-1020.

The additional six removals therefore require changed assessment inputs as well
as current routing:

| Finding | Relevant input change |
|---|---|
| F-1003, F-1005 | No longer emit protection-affecting uncertainty |
| F-1010, F-1011 | No longer emit material uncertainty |
| F-1018, F-1021 | Change `protection_impaired` from `suspected` to `unknown` and drop protection-affecting uncertainty |

All six are protection cases. Their changed inputs may be defensible where a
confirmed failed test already fixes immediate attention and the uncertainty
only changes diagnosis or redundancy. They are also the highest-risk
calibration dependency: a lower review count must not come from hiding an
unresolved protection decision.

The replay evidence is retained in
[`behavior-calibration-replay.json`](../eval/results/behavior-calibration-replay.json).

## 6. Comparison identities and causal limits

| Observation | Model and system surface | Result | Use in this study |
|---|---|---|---|
| Baseline | `gpt-6-sol`; prompt-context hash `746e29...b1b5`; assessment implementation `2605dd...601e`; `triage-policy-v5` | 19/21 U7-U9; 21/21 review flags; 13/21 at I8 | Starting behavior |
| Near-control | `gpt-6.1-sol`; older assessment implementation and `triage-policy-v5`; context hash `7118d3...9024` | 19/21 U7-U9; 20/21 flags; 13/21 at I8 | Shows that one newer-model run on the older surface retained the concentration; not a formal control |
| Current | `gpt-6.1-sol`; `assessment-system-v7`; `native-assessment-v4`; `ticket-projection-v4`; `triage-policy-v16` | 15/21 U7-U9; 6/21 exceptional flags; 10/21 at I8 | Current delivered behavior |

The near-control had two semantic reviews, each with 60/63 applicable dimensions
passing, and remains a failed experiment. It does not isolate model choice
because its complete context differed from the baseline.

Model, prompt, assessment policy, projection and application policy all changed
between baseline and current. No result in this study should be read as the
isolated causal effect of one parameter.

## 7. Score distributions

| Score | Baseline L | Current L | Baseline I | Current I | Baseline U | Current U |
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

Most numeric changes were adjacent-anchor moves and may include normal model
variation. Stronger evidence comes from large L/I changes, deterministic routing
changes and repeated aggregate patterns.

### 7.1 Development/test partition check

| Partition | Review flags | U7-U9 | L changes | I changes | U changes |
|---|---:|---:|---:|---:|---:|
| Development, 13 findings | 13 -> 3 | 13 -> 9 | 6 | 5 | 4 |
| Designated test, 8 findings | 8 -> 3 | 6 -> 6 | 1 | 4 | 3 |

The review change was not limited to development findings. This is not a blind
generalisation result. All findings were exposed, and every retained development
provider input also contained all eight designated TEST finding records. B01
context isolation was therefore not met; the split supports regression analysis,
not case-isolated inference. The complete system surface also changed.

## 8. Representative ticket changes

| Finding | Baseline | Current | What changed and what remains uncertain |
|---|---|---|---|
| F-1009, degraded deck coating | L2 / I8 / U7 / broad review | L9 / I2 / U5 / no exceptional review | The baseline did not claim section loss but scored a possible structural-support consequence. The current run scores the observed corrosion-barrier failure. This demonstrates the revised convention, not that L9/I2 is independently correct |
| F-1016, illegible PSV tag | L2 / I8 / U7 / broad review | L10 / I3 / U6 / no exceptional review | The current run scores loss of identification while the register supports in-date recertification. The anchors still require domain confirmation |
| F-1001, compressor vibration trend | L7 / I8 / U9 / broad review | L7 / I6 / U9 / no exceptional review | Both cite production consequence. The current impact anchor treats it as material operational loss rather than severe personnel or major-accident loss. U9 remains because the supplied source requires same-day specialist attention |
| F-1019, loose cladding | L7 / I7 / U7 / broad review | L8 / I5 / U6 / no exceptional review | Both exclude compressor process loss. The current run treats unknown drop exposure as a required field check rather than established high consequence. This is less precautionary and depends on executing that check |
| F-1017, uncertain firewater duty | L5 / I8 / U8 / broad review | L6 / I8 / U8 / exceptional review retained | Missing flow and unresolved test-path validity still change the protection decision, so exceptional review remains |

These examples are not uniformly lower scores. They reflect a different failure
target, evidence scope and review decision. Operational correctness still needs
domain-owner calibration.

## 9. Rejected interventions

Calibration retained failed observations rather than keeping every change that
reduced urgency or review count:

- an early selective-review policy removed review from cases that still had
  unresolved safety decisions;
- a more complex interaction-sensitive urgency formula passed mathematical
  checks but produced little defensible operational benefit;
- a prompt-only provenance repair changed urgency bands and review routing in a
  fixed comparison; and
- a broader prompt-authority reduction introduced a real-case semantic
  regression and frequent action repair.

The base urgency formula remained unchanged.

## 10. Current evidence status

The six current exceptional-review routes are F-1002, F-1008, F-1012, F-1013,
F-1017 and F-1020. Each names a concrete protection, evacuation, restoration or
verification decision.

Six meets the requested working-capacity target of no more than seven. Meeting
that target is not a quality result. Current routing applied to baseline and
near-control assessment inputs would still produce 12 and 13 flags respectively,
so reaching six depends on the changed assessment surface.

Current urgency is U4=2, U5=1, U6=3, U7=2, U8=6 and U9=7. Fifteen tickets remain
at U7-U9. The queue is more differentiated than the baseline, but this does not
show that the current concentration is operationally optimal. A sibling retained
baseline run produced eight U9 tickets, so seven U9 in the selected pair is not
a repeat-stability result.

The exact current artifact received one complete primary semantic review and
recorded `provisional_pass` with 63/63 applicable dimensions. That review is:

- AI-only and not domain certification;
- non-blind and test-informed; and
- a protocol deviation because the runtime did not expose the reviewer identity
  fields required by Document 03 section 7.2.

The reviewer was calibrated on only two seeded contradiction fixtures, and the
required unresolved adjacent-score `needs_review` behavior was not exercised.
Scenario A04 (valid structure but wrong meaning) therefore remains Partial.

Scenario X01 (decision stability, Document 03) remains Inconclusive. The
development repeats preserved urgency bands and review flags, but their provider
context contained TEST records, reviewer identity was incomplete, and the
configuration was selected using development evidence. Those protocol failures
prevent a formal stability result.

## 11. How to perform the next calibration

Treat the following as a sequence, unlike the independent maintenance paths in
Document 07:

1. **State one hypothesis.** Example: "Unknown non-safety exposure should create
   a verification action rather than an exceptional review flag."
2. **Choose one primary surface.**
   - assessment anchors: `triage\assessment_policy.py`;
   - deterministic urgency/review routing: `triage\policy.py`;
   - ticket-facing projection: `triage\projection.py`;
   - prompt protocol: `triage\prompts\assessment-system-v7.txt`; or
   - model/settings: explicit run configuration.
3. **Record the baseline identity.** Retain model, prompt, policy, activation,
   input and output hashes before changing anything.
4. **Update focused tests.** For policy and projection behavior, run:

   ```powershell
   python -B -m unittest tests.test_triage
   ```

5. **Refresh activation when a pinned surface changes.** Follow the activation
   generation and approval procedure in Document 07 section 1.1.
6. **Generate into a new run directory.** Use the run-specific activation,
   configuration and explicit comparison command in Document 07 section 1.1,
   step 5. Do not overwrite root `tickets.json` during comparison.
7. **Compare decisions, not only histograms.** Review changed L/I values,
   urgency, scheduling band, exceptional routing, uncertainty and action text.
8. **Replay routing where applicable.** Use retained assessment inputs to
   separate deterministic policy effects from changed model inputs.
9. **Run semantic review and repeat generation.** One successful batch does not
   establish stability.
10. **Promote or reject.** Promotion requires grounded case behavior, preserved
    safety constraints, disclosed comparability impact and the controlled-change
    process in Document 03.

The next credible study should also obtain domain-owner review of the
operational-function convention and disputed anchors, repeat the same
configuration to estimate stability, adjudicate the six protection cases in
section 5, calibrate exceptional-review capacity against actual staffing, and
use unseen or newly collected findings.

## 12. Claim boundaries

This study supports:

- complete before/after ticket comparison;
- more differentiated current behavior under the declared design;
- deterministic decomposition of routing-only versus assessment-input effects;
- retention of failed interventions; and
- a bounded list of unresolved protection cases.

It does not support:

- isolated causal attribution to model, prompt or policy;
- like-for-like interpretation of the 21-to-6 review count;
- independent correctness of the current L/I anchors;
- stable behavior across repeated identical runs;
- blind generalisation to unseen findings;
- domain-owner approval; or
- operational validation of the current staffing target.

Score distributions show discrimination, not score accuracy.

## 13. Evidence map

| Claim | Evidence |
|---|---|
| Baseline concentration and software checks | [`design-behavior-demonstration.json`](../eval/results/design-behavior-demonstration.json) |
| Baseline raw tickets | [Retained baseline copy](../eval/results/behavior-calibration/baseline-triage-policy-v5-tickets.json) and [`artifacts-manifest.json`](../eval/results/artifacts-manifest.json) |
| Routing replay for baseline, near-control and current inputs | [`behavior-calibration-replay.json`](../eval/results/behavior-calibration-replay.json) |
| Current L/I/U and review dispositions | [Root `tickets.json`](../tickets.json) |
| Current artifact review and run identity | [`reviewer-observation.json`](../eval/results/triage/structured-planning-v31/final/reviewer-observation.json) |
| Current status and remaining limits | [Root `README.md`](../README.md) and [`eval\results\README.md`](../eval/results/README.md) |
| Knowledge lifecycle architecture | [Document 05](05_KNOWLEDGE_LIFECYCLE.md) |
| Knowledge change experiment | [Document 07](07_KNOWLEDGE_CHANGE_STUDY.md) |
| Urgency and routing implementation | `triage\policy.py`, `triage\projection.py` and focused tests |
| Assessment anchors and failure-basis instruction | `triage\assessment_policy.py` and `triage\prompts\assessment-system-v7.txt` |

## 14. Controlled-change disclosure

Calibration used exposed findings and is test-informed rather than blind.
Failed experiments and prior outputs remain retained; the final file was
regenerated through general mechanisms rather than hand-corrected. No source
package, split, evidence card, expected answer or evaluator rule was weakened to
produce the current distribution.

Future changes to anchors, floors, review routing, urgency-band mapping, prompt
semantics or model identity must preserve the prior artifact, state affected
scenarios and comparability impact, and rerun relevant validation and semantic
review.
