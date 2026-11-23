# Behavior Calibration Study

This study asks: **did the generated tickets become more useful for deciding
which work comes first, what changed, and what evidence is still missing?**

Here, **calibration** means adjusting general assessment rules, prompts, review
routing or the code that creates ticket fields, then generating all 21 tickets
again. Successful and failed observations are both kept. It does not mean
training the model further or editing tickets by hand.

The comparison used test evidence, and the findings were already known to the
developers. It shows a change in the whole system's behavior. It does not prove
that experts have certified the scores, that the system is accurate on unseen
cases, or that one setting alone caused the change.

## 1. What is being compared

Open the two ticket sets and compare rows with the same `finding_id`:

| Artifact | Link | System identity | SHA-256 |
|---|---|---|---|
| Retained baseline experiment | [Baseline 21-ticket JSON](../eval/results/behavior-calibration/baseline-triage-policy-v5-tickets.json) | model `gpt-6-sol`; application policy `triage-policy-v5`; experimental and not acceptance-eligible | `2c6b2a0d85e0462ebe589eadeb3522b078e4c364b9472220ec5ad1e944037381` |
| Current delivery artifact | [Root `tickets.json`](../tickets.json) | model `gpt-6.1-sol`; assessment prompt v7; application policy `triage-policy-v16`; provisional AI-only review | `2bb8d0f34da36142042c6f5f983622be358e45fc4690378a935e28ba189f1f98` |

The baseline link points to a saved copy of the archived experimental output.
Every byte matches. The study did not regenerate or edit it.

The two systems use different models, prompts, assessment code, ticket-field
generation and application policies. This is a before/after comparison of the
whole system. It is not an A/B experiment changing only `triage-policy-v5` to
`triage-policy-v16`.

### 1.1 Terms used in this document

- **L** is likelihood proposed by the model on the 1-10 assessment scale.
- **I** is impact proposed by the model on the 1-10 assessment scale.
- **U** is urgency calculated by code on the 1-10 scale.
- **Review flag** means the published `review_required` field. Its meaning
  changed. The baseline used it for broad review obligations. The current system
  uses it only for a specific unresolved decision needing an exceptional human
  check before normal queuing. Every ticket still needs ordinary human approval.
- **Scheduling band** groups urgency scores into an action window, such as today
  or this week. A score change does not always change the action window.
- **SCE** means Safety Critical Element.
- **PSV** means pressure safety valve.
- **Projection** is code that turns validated assessments and policy decisions
  into ticket fields and text. With the same inputs, it gives the same result.
- **Near-control** means one retained `gpt-6.1-sol` run on the older assessment
  implementation and `triage-policy-v5`. Its complete context hash did not match
  the baseline. It is therefore supporting evidence, not a formal control that
  holds all other conditions fixed.
- **Replay** means passing saved model-proposed scores, facts and uncertainty
  through the current routing code. It makes no new model calls. Replaying the
  same inputs shows the code's routing effect; it does not prove those inputs
  were correct.
- **Activation** is the reviewed manifest, or record, fixing the exact knowledge
  release, retrieval code, assessment policy, execution code and prompt for a
  run. Document 07 section 1.1 shows how to regenerate and approve it.

## 2. Bottom line

| Measure | Baseline | Current | Interpretation |
|---|---:|---:|---|
| Tickets | 21 | 21 | Complete coverage preserved |
| Published review flag | 21 broad-review flags | 6 exceptional-review flags | Lower count, but the field has a different meaning |
| U7-U9 | 19 | 15 | More separation, but the current queue remains urgency-heavy |
| U9 | 7 | 7 | Unchanged in this selected pair; not a stability result |
| I8 | 13 | 10 | Fewer findings share the same impact score |
| Likelihood changed | - | 7 findings | Five one-point moves; two changed by at least two points |
| Impact changed | - | 9 findings | Five one-point moves; four changed by at least two points |
| Numeric urgency changed | - | 7 findings | Six one-point moves; one changed by at least two points |
| Scheduling band changed | - | 5 findings | Fewer changes than the numeric urgency count |

The current design separates the tickets more clearly. That is useful prototype
evidence, not proof that each score is correct for operational decisions.

The review reduction needs the most caution. Replay of saved baseline
assessments under current routing changes 21 flags to 12: routing alone removes
nine. Under that same routing, current assessments produce six flags instead
of 12. Those additional six removals depend on changed assessment inputs.
All six are protection cases with unresolved decision risk. They need domain
review before anyone can treat the lower count as safe.

## 3. Why calibration was needed

The baseline had valid structure, but was weak at separating work priorities:

| Baseline symptom | Observed result | Why it mattered |
|---|---:|---|
| High urgency concentration | 19/21 at U7-U9 | Local defects, material degradation and immediate protection decisions were poorly separated |
| Review saturation | 21/21 flagged | The field did not distinguish ordinary approval from an exceptional decision check |
| Impact concentration | 13/21 at I8 | Different consequence types often received the same score anchor |
| Routing shortcuts | SCE status and broad uncertainty frequently implied review | Asset class or missing information could replace a fact-sensitive decision |

The distribution suggested that scores and flags were too uniform. It did not
tell us the correct answer. Each change still needed review of individual case
evidence and safety checks in code.

A working-capacity target of no more than seven exceptional routes was used to
check whether the queue remained usable. This limits review workload. It is not
a score-quality or safety threshold.

## 4. What changed in the system

The result did not come from changing one threshold. The assessed failure,
handling of uncertainty, meaning of the review flag and ticket generation code
changed together.

### 4.1 Assessment target and anchors

The current assessment first asks which required function the observation shows
to be failing. It does not automatically assign a possible whole-equipment
consequence to every local defect.

For example, degraded coating is assessed first as loss of corrosion protection,
and an illegible PSV tag as loss of identification. Severe personnel or
major-accident consequences remain high where the evidence supports them.

The current impact anchors (descriptions of what each score means) distinguish
production disruption, ability to maintain equipment, personnel exposure and
major-accident potential. Assessing the observed operational function first is
a project design choice. It is not a supplied domain rule or a choice certified
by independent experts.

### 4.2 Facts and uncertainty

The current assessment records facts as confirmed, false, suspected or unknown.
Missing evidence is not treated as confirmed absence.

For some unknowns not about protection, minimum score rules or broad review flags
were replaced by explicit verification actions. This reduced the number of
flagged tickets. It is not simply the same precaution in different words:
the decision now relies more on people carrying out the action plan.

### 4.3 Urgency formula

The code-owned base formula did not change:

```text
base  = ceil(0.7 * impact + 0.3 * likelihood)
final = max(base, applicable floors and confirmed overrides)
```

Urgency changed because L/I proposals, structured facts, uncertainty and
application-policy rules changed. The model still does not choose urgency.

### 4.4 Review semantics

The baseline flag covered broad obligations, including SCE review and review of
uncertainty that matters to a decision. The current flag is narrower. It marks
an unresolved decision needing an exceptional human check before normal
queuing. Routine checks remain in the recommended action.

A confirmed urgent condition can therefore be U9 without an exceptional review
flag. High urgency and exceptional review are separate decisions.

## 5. What caused the review-count reduction

The count fell from 21 to six, but the old broad flag and new exceptional flag
have different definitions. This is not a like-for-like count of the same
review obligation.

A deterministic replay reused saved assessments through routing code. It made
no model calls. The replay separated the code effect from differences in the
assessment inputs.

First, current routing processed the saved baseline scores, facts and uncertainty
without changing them. It produced 12 flags instead of the original 21.
Thus, routing alone accounts for nine removals:

| Cause | Findings | Count |
|---|---|---:|
| Current routing alone removes the baseline flag | F-1001, F-1004, F-1006, F-1007, F-1009, F-1014, F-1015, F-1016, F-1019 | 9 |
| Current routing still flags the baseline inputs | F-1002, F-1003, F-1005, F-1008, F-1010, F-1011, F-1012, F-1013, F-1017, F-1018, F-1020, F-1021 | 12 |

Second, current assessment inputs passed through the same routing code.
This reproduced the six flags in the published file exactly:
F-1002, F-1008, F-1012, F-1013, F-1017 and F-1020.

The change from 12 to six therefore depends on changed assessment inputs under
the same routing. It is not another routing-only reduction:

| Finding | Relevant input change |
|---|---|
| F-1003, F-1005 | The assessment no longer lists uncertainty that affects the protection function |
| F-1010, F-1011 | The assessment no longer lists uncertainty that can change the decision |
| F-1018, F-1021 | `protection_impaired` changes from `suspected` to `unknown`; the assessment no longer lists uncertainty that affects the protection function |

All six are protection cases with unresolved decision risk. The changed inputs
may be defensible if a confirmed failed test already requires immediate
attention and uncertainty affects only diagnosis or redundancy. The study has
not resolved that question.

These six cases are the highest-risk dependency in the calibration. A lower
review count must not come from hiding an unresolved protection decision.
The replay explains how code routes the saved inputs. It does not prove safety
or isolate a causal improvement in the model.

The replay evidence is retained in
[`behavior-calibration-replay.json`](../eval/results/behavior-calibration-replay.json).

## 6. Comparison identities and causal limits

| Observation | Model and system setup | Result | Use in this study |
|---|---|---|---|
| Baseline | `gpt-6-sol`; prompt-context hash `746e29...b1b5`; assessment implementation `2605dd...601e`; `triage-policy-v5` | 19/21 U7-U9; 21/21 review flags; 13/21 at I8 | Starting behavior |
| Near-control | `gpt-6.1-sol`; older assessment implementation and `triage-policy-v5`; context hash `7118d3...9024` | 19/21 U7-U9; 20/21 flags; 13/21 at I8 | One newer-model run with the older setup kept the concentration; not a formal control |
| Current | `gpt-6.1-sol`; `assessment-system-v7`; `native-assessment-v4`; `ticket-projection-v4`; `triage-policy-v16` | 15/21 U7-U9; 6/21 exceptional flags; 10/21 at I8 | Current delivered behavior |

The near-control had two reviews of meaning. Each passed 60/63 applicable
dimensions, and the experiment remains failed. Its complete context differed
from the baseline, so it does not isolate the effect of model choice.

Model, prompt, assessment policy, ticket projection and application policy all
changed between baseline and current. No result here establishes the isolated
causal effect of one setting.

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

Most score changes were one point and may include normal model variation.
Larger L/I changes, replayed routing changes and patterns seen in repeated runs
give stronger evidence that behavior changed. They still do not prove accuracy.

### 7.1 Development/test partition check

| Partition | Review flags | U7-U9 | L changes | I changes | U changes |
|---|---:|---:|---:|---:|---:|
| Development, 13 findings | 13 -> 3 | 13 -> 9 | 6 | 5 | 4 |
| Designated test, 8 findings | 8 -> 3 | 6 -> 6 | 1 | 4 | 3 |

Review counts changed in both partitions, not just development. This does not
show blind performance on new cases. All findings were exposed, and every saved
development request also contained all eight designated TEST records.
The runs therefore failed B01 context isolation. The split supports analysis of
changes and regressions, not inference isolated from test cases. The whole
system setup also changed.

## 8. Representative ticket changes

| Finding | Baseline | Current | What changed and what remains uncertain |
|---|---|---|---|
| F-1009, degraded deck coating | L2 / I8 / U7 / broad review | L9 / I2 / U5 / no exceptional review | The baseline did not claim section loss, but scored a possible consequence for structural support. The current run scores the observed failure of the corrosion barrier. This shows the revised convention; it does not independently justify L9/I2 |
| F-1016, illegible PSV tag | L2 / I8 / U7 / broad review | L10 / I3 / U6 / no exceptional review | The current run scores loss of identification. The register supports recertification still being in date. A domain owner must still confirm the score anchors |
| F-1001, compressor vibration trend | L7 / I8 / U9 / broad review | L7 / I6 / U9 / no exceptional review | Both cite production consequences. The current impact anchor treats these as material operational loss, not severe personnel or major-accident loss. U9 remains because the supplied source requires same-day specialist attention |
| F-1019, loose cladding | L7 / I7 / U7 / broad review | L8 / I5 / U6 / no exceptional review | Both exclude compressor process loss. The current run requires a field check of unknown exposure to falling cladding instead of treating high consequence as established. This is less precautionary and depends on completing that check |
| F-1017, uncertain firewater duty | L5 / I8 / U8 / broad review | L6 / I8 / U8 / exceptional review retained | Flow is missing and the validity of the test path is unresolved. Both still affect the protection decision, so exceptional review remains |

The scores do not all go down. These examples assess different failure targets,
use different evidence scope and make different review decisions. A domain owner
still needs to check whether those choices are operationally correct.

## 9. Rejected interventions

Failed observations were kept. Not every change that lowered urgency or review
count was accepted:

- an early selective-review policy removed review from cases that still had
  unresolved safety decisions;
- a more complex urgency formula accounting for interactions passed mathematical
  checks but showed little defensible operational benefit;
- a prompt-only correction to event ordering changed urgency bands and review
  routing in a fixed comparison; and
- a broader reduction in prompt authority made the meaning of a real-case
  assessment worse and frequently required action repair.

The base urgency formula remained unchanged.

## 10. Current evidence status

The six current exceptional-review routes are F-1002, F-1008, F-1012, F-1013,
F-1017 and F-1020. Each names a concrete protection, evacuation, restoration or
verification decision.

Six meets the requested working-capacity target of no more than seven.
That is not evidence of quality or safety. Current routing applied to baseline
and near-control inputs still produces 12 and 13 flags respectively.
Reaching six therefore depends on changed assessment inputs, not routing alone.

Current urgency is U4=2, U5=1, U6=3, U7=2, U8=6 and U9=7. Fifteen tickets remain
at U7-U9. The queue separates priorities more than the baseline, but the study
does not show that this urgency distribution is best for operations.
Another saved baseline run produced eight U9 tickets. Seven U9 in the selected
pair therefore does not establish stable results across repeats.

The exact current file received one complete primary review of meaning.
It recorded `provisional_pass` with 63/63 applicable dimensions. That review is:

- AI-only and not domain certification;
- based on known findings and test evidence; and
- a deviation from the required procedure because the runtime did not expose the reviewer identity
  fields required by Document 03 section 7.2.

The reviewer was calibrated on only two fixtures with deliberately added
contradictions. The calibration did not test the required `needs_review` response
for an unresolved score near a defensible anchor. Scenario A04 (valid structure
but wrong meaning) therefore remains Partial.

Scenario X01 (decision stability, Document 03) remains Inconclusive.
Development repeats kept the same urgency bands and review flags. However, their
requests contained TEST records, reviewer identity was incomplete, and the
configuration was chosen using development evidence. Those failures of the
required procedure prevent a formal stability result.

## 11. How to perform the next calibration

Follow these steps in order. Unlike Document 07's separate maintenance options,
this is a sequence:

1. **State one hypothesis.** Example: "Unknown non-safety exposure should create
   a verification action rather than an exceptional review flag."
2. **Choose one main component to change.**
   - assessment anchors: `triage\assessment_policy.py`;
   - deterministic urgency/review routing: `triage\policy.py`;
   - ticket-facing projection: `triage\projection.py`;
   - prompt protocol: `triage\prompts\assessment-system-v7.txt`; or
   - model/settings: explicit run configuration.
3. **Record the exact baseline setup.** Retain model, prompt, policy, activation,
   input and output hashes before changing anything.
4. **Update focused tests.** For policy and projection behavior, run:

   ```powershell
   python -B -m unittest tests.test_triage
   ```

5. **Refresh activation when a pinned component changes.** Follow the activation
   generation and approval procedure in Document 07 section 1.1.
6. **Generate into a new run directory.** Use the run-specific activation,
   configuration and explicit comparison command in Document 07 section 1.1,
   step 5. Do not overwrite root `tickets.json` during comparison.
7. **Compare decisions, not only score distributions.** Review changed L/I values,
   urgency, scheduling band, exceptional routing, uncertainty and action text.
8. **Replay routing where applicable.** Pass saved assessment inputs through code,
   without model calls, to separate routing effects from changed assessment inputs.
9. **Review meaning and repeat generation.** One successful batch does not show
   stable behavior.
10. **Promote or reject.** Promotion requires case decisions supported by evidence,
    preserved safety constraints, a clear account of which comparisons remain
    valid, and the controlled-change process in Document 03.

The next credible study also needs to:

- obtain domain-owner review of the operational-function convention and disputed
  score anchors;
- repeat the same configuration to estimate stability;
- resolve the six protection-case decisions in section 5;
- check exceptional-review capacity against actual staffing; and
- use unseen or newly collected findings.

## 12. Claim boundaries

This study supports:

- complete before/after ticket comparison;
- more differentiated current behavior under the declared design;
- replay separating routing-only changes from assessment-input differences;
- retention of failed interventions; and
- a specific, limited list of unresolved protection cases.

It does not support:

- proof that model, prompt or policy alone caused the change;
- like-for-like interpretation of the 21-to-6 review count;
- independent correctness of the current L/I anchors;
- stable behavior across repeated identical runs;
- blind performance evidence on unseen findings;
- domain-owner approval; or
- operational validation of the current staffing target.

Score distributions show that scores differ. They do not show that the scores
are accurate.

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

Calibration used known findings and test evidence. It was not blind.
Failed experiments and earlier outputs are still saved. General system
mechanisms regenerated the final file; nobody corrected it by hand.
No source package, split, evidence card, expected answer or evaluator rule was
weakened to obtain the current score distribution.

Future changes to score anchors, urgency floors, review routing, urgency-band
mapping, prompt meaning or model identity must preserve the previous file.
State which scenarios are affected and which comparisons remain valid.
Rerun the relevant validation and review of meaning.
