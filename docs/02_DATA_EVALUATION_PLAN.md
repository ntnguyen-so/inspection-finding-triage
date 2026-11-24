# Data, Context and Evaluation Boundaries

This document explains what we can learn from the supplied data, how we separate
cases and model context, and why different kinds of evidence must stay separate.
Exact case membership and file hashes are stored in
[`eval\spec\split.json`](../eval/spec/split.json); this prose does not override
that executable specification.

## Abstract

There are only 21 findings. Many are related, and all were available during
development. They cannot show how well the system performs on unseen data.
Instead, we use them to check named behaviors, document context limits and
record failures. We do not turn them into a hidden answer key.

Three questions need separate evidence: are the saved files intact, does code
follow its rules, and are the tickets supported by evidence? Passing one check
does not answer the other two.

The retained development runs broke the intended context boundary: all eight
test finding records reached the provider. B01 is therefore not met. The split
now organizes **regression evidence**: checks of behavior on already exposed
cases. It does not show inference with test cases kept out of development
requests.

Sections 2-3 explain the dataset's limits. Sections 4-6 define evaluation and
context rules. Sections 7-8 report current evidence and its limits.

## 1. Research questions

The evaluation asks four questions:

1. **Claim boundary:** what can 21 already exposed findings show? What would
   wrongly imply unseen-data performance or domain certification?
2. **Case grouping:** which findings share evidence? Would splitting them leak
   information or wrongly suggest that they are independent?
3. **Context boundary:** what may the production model receive? What must stay
   available only to the evaluator?
4. **Evidence meaning:** what shows code behavior, ticket quality, stability or
   maintainability? What does each observation leave unknown?

## 2. Dataset and claim boundary

The supplied package contains 21 findings, 18 equipment records, domain notes and
one example ticket. The split has 13 development cases in nine relationship
groups and eight test cases in four groups. All source rows and the example were
available during development. AI helped create the reference used to judge
ticket meaning. It is not independent, expert-verified truth.

A **partition** is the named development or test membership. A
**relationship group** keeps findings together when shared evidence can change
their assessments. **L**, **I** and **U** mean likelihood, impact and code-derived
urgency. Their 1-10 scales are **ordinal**: higher numbers mean higher priority,
not measured probabilities or expected losses.

The evaluation may support claims about:

- behavior on named scenarios;
- source and context delivery;
- code enforcing the contract rules;
- how stable the observed decisions were; and
- saved model and reviewer results.

It cannot establish accuracy across a wider population, performance on unseen
data, statistical failure rates or domain certification. Report individual
outcomes and limits instead of accuracy percentages for this small sample.

## 3. Data risks that shaped the evaluation

| Data characteristic | Evaluation implication |
|---|---|
| Reliability runs in the opposite direction to likelihood | Check the scale direction and use test inputs with deliberate contradictions |
| Criticality and reliability are priors, or starting points | Do not treat registry values as exact expected scores |
| Related findings share equipment or protection state | Keep findings together when shared evidence changes the assessment |
| Redundancy (backup) labels do not prove partner health | Check the partner evidence actually sent to the model |
| Deviation records, personnel-on-board (POB) counts or restoration evidence may be missing | Keep the state unknown; missing records do not prove absence |
| The example ticket was available during development | Use it for format and detail, not as a scoring key |
| Only 21 findings exist | Report named outcomes, not accuracy or statistical confidence claims |

The deluge findings show why grouping matters. **Deluge** is the water-spray
protection system. One finding records poor delivery above producing wellheads.
A related finding records a closed branch valve, its reopening and a missing
impairment entry. Either finding can change how the other is understood. Neither
proves that nozzle performance was restored. Treating them as independent would
remove evidence that changes the assessment.

Inspecting the source data identifies these risks. It does not test the triage
system.

## 4. Evaluation decisions

### 4.1 Group by shared assessment-changing evidence

Findings stay in the same partition when one can meaningfully change the other's
L/I, impact reduction for backup equipment, fact state or planned activity.

Splitting linked observations could give development the evidence needed to
assess the paired test finding, while still calling that test finding independent.

We rejected grouping all nearby or process-linked equipment together. That would
leave too few groups without evidence that every link changes the assessment.

### 4.2 Label the split non-blind

The development and designated test sets remain separate. But all source rows
were available during development, and evaluation evidence influenced the
current system. We disclose this as **non-blind** evaluation.

Keeping the sets separate can reduce direct tuning on some cases. It cannot
undo source exposure or AI assistance in building the reference. Calling the
test set “held out” or “unseen” would overstate its independence.

We rejected the term “blind test.” Separating files does not prove performance
on new cases.

### 4.3 Keep test descriptions out of development provider context

Development model requests may use the shared registry and approved domain
material. They must not include test finding descriptions, evaluator checklists
(**evidence cards**), reviewer judgments or expected answers to test probes.

Shared domain sources are legitimate production inputs. Case-specific test
answers belong to evaluation. Sending them to the model would reveal what the
test expects.

We rejected adding test examples to shared knowledge. That could improve the
measured results by teaching the model the test cases.

This was the intended rule. The retained development runs broke it, as section 7
reports. Evaluator cards and expected answers stayed out of production context.
Test finding descriptions did not.

### 4.4 Use evidence cards instead of exact gold scores

An **evidence card** is a checklist used only by the evaluator. It lists relevant
source evidence, contradictions to check, distinctions to preserve and claims
that must not appear. The cards support semantic review in
[Document 03 section 7](03_EVALUATION_ACCEPTANCE.md#7-current-semantic-reviewer-protocol).
They limit what the reviewer may judge without requiring one exact L/I pair.
Nearby scores may both be defensible.

The source package does not supply calibrated “true” scores. Requiring exact
scores would invent precision and encourage code that answers specific cases.

We rejected one “correct” L/I/U combination per finding. The source does not
provide such an answer key.

### 4.5 Keep observations outside specifications

Membership, scenarios and evidence rules live under `eval\spec`. Results of
executed checks live under `eval\results`.

A specification defines what counts as success. A result records what happened.
Mixing them makes it easy to overwrite a failure with a newer status.

We rejected using scenario definitions to track progress. That would let us
change the target after seeing failures.

## 5. Context boundary

Production assessment may receive:

- the selected finding;
- the supplied registry and `engineer_comment` fields;
- related history selected by code and declared relationships;
- approved domain knowledge that preserves the supplied source meaning; and
- prompt, scoring guide (rubric) and policy versions needed to explain the run.

Production assessment must not receive:

- evidence cards or expected answers;
- semantic reviewer judgments;
- test contradictions deliberately added by the evaluator, or their expected labels;
- rules for specific findings learned from test results; or
- copied final tickets or reference-answer tickets.

**Provider-bound context** is the exact context prepared for a model request.
Saving it shows which inputs were sent. It does not prove that those inputs
caused a decision or that the model used them correctly.

## 6. Evidence model

| Evidence class | What it can establish | What it cannot establish |
|---|---|---|
| Source/profile validation | Counts, keys, linked records, hashes and membership agree | Ticket quality or model behavior |
| Evaluator self-tests | The evaluator detects deliberately added test errors | Evaluator accuracy on real outputs |
| Deterministic production tests | Code follows tested schema, urgency, budget and publication rules | Correct L/I or action wording |
| Captured provider context | Named inputs were sent at the provider boundary | Whether those inputs caused the right decision |
| Multi-model development trials | Recorded model labels, completed batches and failures for each saved setup | A fair model ranking, accuracy on unseen findings or a fixed-identity repeat |
| Token-based cost calculation | An API-equivalent estimate can be repeated using declared public rates | Actual per-run USD allocated to the Copilot subscription |
| Bounded intervention | One isolated input change produced the effect defined before the run; controls remained outside that rule's meaning | General correctness of the knowledge |
| AI semantic review | Provisional judgment using one reviewer configuration | Independent expert certification |
| Human/domain review | Operational judgment within that reviewer's scope | General model reliability without a study |

`needs_review`, unexecuted checks and unknown accounting are not passes.

## 7. Current assessment of the evaluation design

This table compares the evaluation design with current evidence. It does not
change the specifications.

| Evaluation decision | Current evidence | Interpretation and remaining limit |
|---|---|---|
| Group related findings | The split keeps shared equipment and protection evidence together when it changes assessments. | **Supported as leakage control.** It does not prove that all operational dependencies are known. |
| Label the split non-blind | All findings were exposed. Exposed evaluation evidence influenced the current configuration. | **Honest but non-independent.** Test results support regression claims, not performance on unseen cases. |
| Explore alternative generation models | Real development attempts used several model labels. Some failed to produce valid output; others produced valid structure but failed AI semantic review. The [model-trial history](04_INFERENCE_LIBRARY.md#51-models-tried-during-development) keeps both successful and failed observations. | **Useful development evidence, not a controlled benchmark.** This was an additional project choice, not a multi-model requirement in the brief. Prompts, code, references and reviewers differed across trials, and all findings were exposed. |
| Isolate test descriptions and answers | Boundary tests show that production did not import evaluator cards or expected answers. But every retained development provider input contained all eight test finding records. | **B01 is not met for the retained development runs.** Test descriptions leaked; evaluator answers did not. The 13/8 split organizes regression work, not inference on isolated new cases. See the [B01 audit](../eval/results/triage/structured-planning-v31/b01-development-context-audit.json) and [Document 03 B01](03_EVALUATION_ACCEPTANCE.md#b01--context-delivery). |
| Use cards rather than exact scores | Review checks evidence, planning and uncertainty. It can leave nearby-score choices unresolved. | **Supported provisionally.** Reviewer calibration covers few cases and is AI-assisted. |
| Separate specifications from results | Specifications remain under `eval\spec`; observations remain under `eval\results`. | **Supported structurally.** Read current status in root `README.md` and [`eval\results\README.md`](../eval/results/README.md). |

## 8. Threats to validity and claim limits

- **Small, exposed sample.** All findings were read during development. We cannot
  make claims about a wider population or unseen data.
- **Development-context leakage.** The saved development runs generated tickets
  for 13 findings. Every provider request also included all eight test finding
  descriptions. Later test results are test-informed regression evidence, not
  evidence from an isolated test set.
- **Related cases.** Grouping reduces obvious leakage. It does not prove that all
  operationally linked equipment is independent across groups.
- **AI-assisted reference and review.** Cards and semantic judgments provide
  structured evidence, not domain-expert truth.
- **Configuration chosen using evaluation evidence.** Exposed results influenced
  current behavior and policy. New observations therefore support regression
  claims, not blind evaluation.
- **Hidden provider behavior.** Token and cache usage are exposed. Public rates
  allow a repeatable API-equivalent estimate. Hidden HTTP attempts and actual
  Copilot billing allocation remain unknown.
- **Origin of the producing code.** Exact source bytes used to produce the output
  are saved and identified by hashes. Reproduction from a clean checkout is not
  established.

The evidence is still useful. These limits define what we may claim from it.

## 9. Controlled-change boundary

This document does not add another change procedure. Specifications checked by
code remain under `eval\spec`. Observations remain under `eval\results`. Failed
or replaced evidence must be kept. Changes to the evaluation contract follow
[Document 03 section 9](03_EVALUATION_ACCEPTANCE.md#9-controlled-change-and-authority).

## 10. Reader path

- Source package:
  [`docs\candidate-pack\candidate-pack`](candidate-pack/candidate-pack/README.md)
- Current split and hashes: [`eval\spec\split.json`](../eval/spec/split.json)
- Acceptance scenarios and semantic reviewer protocol:
  [Document 03](03_EVALUATION_ACCEPTANCE.md)
- Observed outcomes, evidence and limitations:
  [`eval\results\README.md`](../eval/results/README.md)
- Current delivery status and run instructions: [root `README.md`](../README.md)
