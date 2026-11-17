# Behavior Calibration Study

> **Purpose:** change system behavior through general, versioned policy rather
> than hand-correcting `tickets.json` or adding finding-specific branches.
>
> **Study status:** executed. V9 and v10 were rejected; v11 retained the
> assessment anchors, restored mandatory uncertainty review and the v8 urgency
> formula, and generated the current root delivery.

## Abstract

The v8 system completed three all-21 runs and generated the required root
`tickets.json`, but the evidence exposed two calibration problems. First,
adjacent impact scores remained unresolved where the hazard was credible but
consequence modifiers were missing. Second, 19 of 21 tickets received urgency
7-10 and 20 of 21 required targeted review, which provides weak prioritisation
beyond the Candidate Brief's global human-approval requirement.

This study uses two stages so that causal attribution is not lost. The v9
ablation changes ordinal impact anchors and the meaning of `review_required`
while holding urgency mathematics constant. The v10 full calibration retains
those changes and replaces the urgency formula with a prospectively declared
interaction formula. Confirmed overrides, safety floors, source package and
knowledge release remain unchanged. Two all-21 runs per stage measure the
resulting behavior. A separate frozen B02 experiment reruns the reference-1.3
knowledge-influence probe to test whether a knowledge-only change causes the
intended assessment change without leaking to an inapplicable control. The
study is designed to reveal trade-offs, not to force a preferred score
distribution. The result was deliberately non-linear: B02 passed, but both v9
and v10 failed semantic review because reduced review routing hid material
uncertainty. V10 also added formula complexity without measurable operational
benefit. V11 therefore restores mandatory review and the original urgency
formula while retaining the more explicit impact anchors.

## 1. Why this study exists

The Candidate Brief evaluates output quality, score defensibility, the
model/code boundary and maintainable knowledge. V8 established structural
reliability, but structural success did not answer four panel questions:

1. Does missing consequence detail prevent unjustified escalation as well as
   prevent unjustified dismissal?
2. Does `review_required` identify additional targeted review, or merely restate
   that every generated ticket requires human approval?
3. Can calibration reduce alarm concentration without weakening explicit safety
   rules?
4. Can a knowledge-only change cause the intended model behavior while leaving
   an inapplicable negative control unchanged?

The correct response is a bounded experiment. Editing the final JSON, adding
finding-ID conditions or repeatedly tuning until the desired distribution
appears would make the system less defensible.

## 2. Baseline observation

The baseline is `triage-policy-v8` with assessment policy
`triage-assessment-v1`.

| Measure | V8 observation |
|---|---:|
| Completed all-21 repeats | 3/3 |
| Application sends | 21 / 23 / 21 |
| Exact L/I/U agreement | 15/21, 19/21, 17/21 |
| Urgency-band agreement | 21/21 |
| Root urgency 7-10 | 19/21 |
| Root `review_required=true` | 20/21 |
| Root primary semantic review | 61 pass, 2 pending, 0 fail |

The two root pending judgments are F-1010 and F-1019 impact grounding. F-1010
has a confirmed refuge-pressurisation failure and an explicit life-safety
function, but no external anchor resolves impact 8 versus 9. F-1019 has a
credible dropped-object mechanism, but mass, fall height and personnel exposure
are absent, so impact 7 versus an adjacent lower band is unresolved.

The review flag is code-derived. V8 uses `bool(rules)`, so every uncertainty,
floor, source-directed action or explicit review rule activates it. The root
artifact contains 62 `P-SAFETY-UNKNOWN` rule instances. This behavior is
traceable but insufficiently selective.

### 2.1 Before/after policy contract

The study distinguishes a **declared policy change** from an **observed behavior
change**. The first table records what each experimental version declared before
inference. It is not evidence that the model responded as intended.

| System dimension | Before: frozen v8 | Ablation: v9 | Full calibration: v10 |
|---|---|---|---|
| Assessment policy | `triage-assessment-v1` | `triage-assessment-v2` | Same as v9 |
| Execution policy | `triage-policy-v8` | `triage-policy-v9` | `triage-policy-v10` |
| Impact 7-8 threshold | Broad severe operational, delayed-integrity or major-accident exposure | Specific supported severe consequence path, exposure, scale or delayed-integrity threat | Same as v9 |
| Missing severity modifiers | Recorded as uncertainty, but the anchor did not explicitly prevent them from supporting the higher adjacent band | Remain unknown and trigger verification; they cannot supply evidence for a higher band | Same as v9 |
| Generic serious-injury possibility | Could be interpreted as sufficient for impact 7-8 | Is insufficient without a supported severe consequence path, exposure or scale | Same as v9 |
| Targeted-review calculation | `bool(rules)` | Explicit rule classification plus whether a floor changes disposition | Same as v9 |
| Non-binding `P-SAFETY-UNKNOWN` | Always sets `review_required=true` | Does not set targeted review by itself when the formula base already meets the floor | Same as v9 |
| Explicit review/override/source attention | Sets targeted review | Continues to set targeted review | Continues to set targeted review |
| Failed test, evacuation and restoration cases | Set targeted review | Continue to set targeted review even when their floors are non-binding | Same as v9 |
| Urgency formula | `ceil(0.7I + 0.3L)` | Held constant to isolate assessment/routing effects | `ceil((5I + 2L + 3sqrt(IL)) / 10)` |
| Asymmetric corners `(L=10,I=1)` / `(L=1,I=10)` | `4 / 8` | `4 / 8` | `4 / 7` |
| Safety floors and confirmed overrides | v8 values | Unchanged | Unchanged |
| Human approval | Required for every draft | Required for every draft | Required for every draft |
| Finding-specific branches | Prohibited | Prohibited | Prohibited |

This design should make `review_required` mean “additional targeted review is
needed for this disposition,” rather than “this draft requires approval.”
Approval remains universal and is not encoded by that field.

The experiment rejected that intended v9 meaning. The acceptance contract
requires every material uncertainty to remain review-routed even when its
urgency floor is non-binding. V11 therefore returns to `bool(rules)` and treats
the field as a conservative review gate, not a selective workload queue.

### 2.2 Before/after observed behavior

The second table is the empirical comparison a panel should use to judge the
calibration. Values come from both declared all-21 runs and the same semantic
review configuration; they are observations, not preferred targets.

| Measure | Before: retained v8 | Ablation: v9 | Full calibration: v10 |
|---|---:|---:|---:|
| Completed all-21 runs | 3/3 | 2/2 | 2/2 |
| Application sends | 21 / 23 / 21 | 23 / 22 | 21 / 21 |
| Exact L/I/U agreement | 15/21, 19/21, 17/21 | 17/21, 17/21, 18/21 | 18/21, 16/21, 19/21 |
| Urgency-band agreement | 21/21 | 20/21 | 20/21 |
| Findings with urgency 7-10 | 19/21 in root artifact | 18/21 and 19/21 | 19/21 and 18/21 |
| Findings with targeted review | 20/21 in root artifact | 18/21 and 19/21 | 19/21 and 18/21 |
| Primary semantic judgments | 61 pass, 2 pending, 0 fail | 54/6/3 and 56/5/2 | 57/4/2 and 54/6/3 |
| F-1010 impact | 9; adjacent 8/9 unresolved | 8 in both repeats | 8 in both repeats |
| F-1019 impact | 7; severe-band grounding unresolved | 5 in both repeats | 5 in both repeats |
| Safety-invariant regressions | None observed in retained deterministic checks | Material-uncertainty review lost for F-1004/F-1013 and once for F-1018 | Same D01 regression |
| Wall time, tokens and equivalent API cost | 635.64 s, 983,821 input, 40,200 output, about US$2.37 for root delivery | 1,341.14 s; 2,118,966 input; 84,529 output; about US$5.08 | 1,368.69 s; 1,972,976 input; 81,448 output; about US$4.76 |

The retained result includes a 21-row transition matrix with v8 and both v9
values for likelihood, impact, urgency, urgency band and targeted review. Every
changed finding requires a source-grounded explanation; unchanged findings are
retained so that the report cannot hide regressions through selective examples.

## 3. Research questions and hypotheses

### RQ1 — Impact calibration

Can explicit evidence thresholds distinguish a supported severe consequence
from a merely possible severe consequence?

**H1.** A generic anchor that requires a supported exposure, scale or protection
path for impact 7-8 will reduce unsupported severe-band choices without treating
missing evidence as confirmed absence.

**Disconfirmation.** New outputs still choose severe bands solely because a
hazard could theoretically cause serious injury, or they suppress source-backed
major-accident consequences.

### RQ2 — Targeted review

Can `review_required` carry information beyond mandatory global approval?

**H2.** Requiring targeted review for explicit review rules, disposition-changing
floors, confirmed overrides and source-directed attention will reduce saturation
while retaining every safety-critical and materially uncertain case that changes
disposition.

**Disconfirmation.** The flag remains almost universal, or a confirmed
override/floor case loses review.

### RQ3 — Operational prioritisation and urgency mathematics

Can an impact-led but interaction-sensitive formula preserve the required
asymmetric corners while avoiding urgency that is almost a restatement of
impact?

**H3.** The v10 formula
`ceil((5I + 2L + 3sqrt(IL)) / 10)` remains monotone, preserves impact dominance
and yields the required corners 4 and 7. Its interaction term raises urgency
when likelihood and impact are jointly high instead of applying the same impact
weight independently of likelihood. No target distribution is a pass criterion.
Confirmed failed protection, evacuation, restoration and source-directed
same-day cases must retain their code-owned floors.

**Disconfirmation.** The function violates range, monotonicity or corner
constraints; lower concentration is achieved by weakening a safety invariant;
or the change creates unjustified low urgency for source-supported cases.

### RQ4 — Knowledge influence

Does a knowledge-only change produce the intended isolated score change?

**H4.** Under reference 1.3, the synthetic positive PSV case changes likelihood
6 to 8 while impact remains 3; the tag-only negative control does not receive
the synthetic passing rule.

**Disconfirmation.** The positive case is unassessable, impact changes, the
negative control receives the rule, or orchestration/code changes are required.

## 4. Interventions

### 4.1 Assessment policy v2

The likelihood definition and confirmed-failure minimum remain unchanged.
Impact anchors become more explicit:

- 1-2: appearance, housekeeping or similarly limited low-energy consequence;
- 3-4: localized, recoverable consequence with supported containment or
  functional alternatives;
- 5-6: material operational or personnel consequence where severe exposure,
  scale or protection loss is not established;
- 7-8: a specific supported severe consequence path, delayed integrity threat or
  major-accident exposure, accounting for actual protection;
- 9-10: extreme consequence supported by the actual scenario, not by an SCE
  label, generic hazard possibility or missing mitigating evidence.

Missing evidence remains unknown. It neither proves safety nor supplies the
evidence required for a higher consequence band. When adjacent bands are
plausible, the model selects the highest band directly supported by known facts
and routes the unresolved modifier to review.

### 4.2 Review-routing policy v9

The code continues to own `review_required`. A ticket requires targeted review
when at least one of the following is true:

1. an explicit `review` rule applies;
2. a rule raises urgency above the formula base;
3. a confirmed override applies;
4. source evidence requires same-day attention; or
5. a failed protection test, unresolved evacuation capacity or unresolved
   restoration rule applies.

A generic uncertainty that is already represented in the action and does not
change urgency does not by itself set the targeted flag. Global human approval
still applies to every draft.

### 4.3 Urgency policy v10

V9 deliberately holds `ceil(0.7I + 0.3L)` constant as an ablation control. V10
then changes only the base formula:

`U_base = ceil((5I + 2L + 3sqrt(IL)) / 10)`

The linear impact term preserves consequence dominance, the likelihood term
preserves sensitivity at the high-likelihood/low-impact corner, and the
geometric interaction term increases urgency when both inputs are high. At the
four acceptance anchors the function returns 1, 4, 7 and 10. It is neither a
plain average nor a plain maximum. The formula is still a prototype ordinal
policy, not a calibrated probability or domain-certified risk equation.

All 100 input pairs require independently worked expected values, range checks
and monotonicity checks before inference. Existing floors and overrides apply
after the base score and are not lowered.

### 4.4 What does not change

- no finding-ID or expected-answer branch;
- no change to confirmed override or safety-floor values;
- no change to the supplied package or production knowledge;
- no manual edit to generated tickets;
- no tuning after the first calibrated send.

## 5. Experimental method

### 5.1 Calibration runs

1. Hash-pin v9, assessment policy v2, prompt, activation, configuration, source
   and knowledge release.
2. Run two all-21 v9 ablation batches with identical settings and fresh ledgers.
3. Freeze v10 as a sequential, explicitly test-informed intervention after v9;
   change only the base urgency formula and its independently worked tests.
4. Run two all-21 v10 batches with identical settings and fresh ledgers.
5. Retain every malformed response, retry, failure and output.
6. Apply the same calibrated primary semantic reviewer to all outputs.
7. Compare v8, v9 and v10; do not select only the better repeat.

### 5.2 Measures

- completion and application sends;
- L/I/U scores and urgency bands;
- number and cause of targeted-review flags;
- semantic pass/pending/fail by dimension;
- changes for every finding, not only F-1010/F-1019;
- runtime, token usage and illustrative equivalent API cost;
- invariant checks for confirmed overrides, failed tests and safety floors.

### 5.3 Decision rules

The calibrated policy is rejected if it introduces a structural failure, a
finding-specific branch, a safety-invariant regression or a new semantic fail
that is attributable to the intervention. A lower high-urgency count or lower
review count is evidence only when the changed tickets remain defensible.

Two repeats are insufficient to establish general reliability. They are adequate
to demonstrate whether the intervention moves behavior in the intended
direction without hiding immediate regressions.

## 6. B02 reference-1.3 rerun

### 6.1 Why B02 exists

The architecture makes a stronger claim than “the request contains a knowledge
section.” It claims that `triage_knowledge` owns maintainable domain knowledge,
retrieves applicable material, and supplies it to an otherwise independent
triage workflow. Request capture already proves **delivery**: selected knowledge
reaches the model boundary. Delivery alone does not prove **influence**. The
model could ignore the material, apply it to the wrong equipment, or reproduce
the expected score from its own prior behavior.

B02 therefore tests a causal question:

> When only an applicable knowledge rule changes, does the assessment change in
> the direction specified by that rule while an inapplicable control remains
> unchanged?

This matters to the Candidate Brief's knowledge-encapsulation criterion. Without
such evidence, separating `triage_knowledge` from orchestration is a clean code
boundary but not yet a demonstrated behavioral capability.

### 6.2 Why the experiment is synthetic and isolated

A production-knowledge edit would be a poor causal test. Real policy changes can
alter several facts at once, may require domain authorization, and can make it
impossible to determine whether a score changed because of knowledge, prompt
wording, model variability or code. B02 instead uses the preregistered reference
1.3 probe as an evaluation-only overlay:

- production knowledge and final ticket generation remain unchanged;
- code, model, prompt, source inputs and inference settings are held constant;
- the positive rule changes only the declared likelihood value;
- impact is fixed, providing an internal check against unrelated drift;
- a tag-only negative control tests scope isolation;
- outputs are labelled synthetic and can never become delivery tickets.

The artificial scores are diagnostic instruments, not asserted engineering
truth. Their purpose is to make the expected causal effect observable and
falsifiable.

### 6.3 Four-condition design

B02 executes four conditions:

| Condition | Synthetic rule | Expected diagnostic |
|---|---|---|
| Positive before | L=6, I=3 | exact synthetic scores |
| Positive after | L=8, I=3 | likelihood changes; impact fixed |
| Negative before | before rule | no passing-rule inference |
| Negative after | after rule | no passing-rule inference |

The positive pair tests sensitivity: the applicable knowledge-only change must
move likelihood from 6 to 8 while impact stays 3. The negative pair tests
specificity: an equipment tag without the rule's required applicability
conditions must not inherit the synthetic passing rule. Both are required.
Passing only the positive pair could mean the model applies any nearby text
indiscriminately; passing only the negative pair could mean the model ignores
knowledge entirely.

The experiment has four nominal and eight maximum application sends. A numeric
positive response alone is insufficient. The negative outputs require semantic
review because “not equal to the expected positive score” does not establish
that the rule was correctly excluded; the model might fail for an unrelated
reason.

### 6.4 Relationship to v9/v10 calibration

B02 is run after the calibration code is frozen because its plan fingerprints
the exact runtime. It is not used to select the v9 impact anchors or the v10
urgency formula. The calibration study asks whether general assessment and
prioritisation behavior improves; B02 asks whether the knowledge module has
causal, correctly scoped influence. Keeping those questions separate prevents a
successful calibration run from being misrepresented as evidence for knowledge
encapsulation.

### 6.5 Interpretation boundary

A B02 pass supports three narrow claims: the isolated knowledge was delivered,
the applicable assessment responded in the declared direction, and the negative
control did not receive that rule. It does not prove that the synthetic scores
are operationally correct, that all production knowledge is influential, or
that unseen retrieval cases will behave correctly. A fail or inconclusive result
is retained as a module-boundary limitation rather than repaired by changing the
probe after seeing its output.

## 7. Cost and stopping policy

The four calibration runs used 87 application sends: 45 for v9 and 42 for v10.
B02 used four more sends, and the selected v11 delivery used 21. The four
calibration runs consumed 4,091,942 input and 165,977 output tokens, implying
about US$9.84 under the simple equivalent-rate assumption. V11 separately
implies about US$2.37. These are reproducibility estimates, not actual Copilot
subscription charges; hidden HTTP attempts remain unknown.

The study stops after the declared runs. A failed or inconclusive result is
reported as such. Further changes require a new version and a new prospective
study; they cannot be folded into this result.

## 8. Results

### 8.1 V9 ablation: rejected

Both runs completed, but all four v9/v10 semantic reviews found the same
contract failure: F-1004 and F-1013 had material safety uncertainty while
`review_required=false`. F-1018 showed the same failure in one v9 repeat and one
v10 repeat. Higher base urgency could therefore remove review even though the
uncertainty itself remained material. This violated D01 and contradicted the
assessment instruction to route unresolved decision modifiers to review.

V9 reduced impact for the two original challenge cases: F-1010 was 8 in both
repeats and F-1019 was 5 in both repeats. That is useful evidence that the new
anchors changed behavior, but it does not rescue the intervention. Other
grounding/planning judgments remained pending, reviewer comparability with the
v8 root is limited, and the complete v9 policy failed its preregistered gate.

### 8.2 V10 urgency formula: rejected

V10 passed the 100-cell range, monotonicity and corner tests, and both runs
completed without repair. It did not improve the observed prioritisation:
urgency 7-10 remained 19/21 and 18/21, compared with 19/21 for the v8 root.
Only three observed score combinations exposed a different base value. One was
masked by a safety floor, one increased urgency and one reduced it.

The formula therefore added a square-root interaction and a new explanation
surface without a demonstrated operational benefit. It also inherited the v9
review-routing failure. V10 is retained as a falsified design experiment, not
promoted production policy.

### 8.3 B02: bounded pass

All four conditions completed in one send each with code fingerprints stable.
The positive case changed from L6/I3 to L8/I3 exactly. Independent semantic
review confirmed that both unchanged F-1016 negative controls remained in-date,
tag-only observations and did not receive the synthetic passing rule. This is a
bounded pass for knowledge delivery, causal influence and scope isolation; it
does not certify production knowledge correctness or general retrieval quality.

### 8.4 V11 adoption result

Two critical reviews accepted the v9 D01 finding and rejected the v10 formula.
V11 makes the smallest correction:

- retain assessment-policy v2 as a disclosed post-hoc selection;
- restore `ceil(0.7I + 0.3L)`;
- restore `review_required = bool(rules)`;
- keep every safety floor, confirmed override, source and knowledge release
  unchanged.

The v11 delivery generated 21 tickets in 21 sends and replaced root
`tickets.json` with SHA-256
`641c8ee358544d562267e40b215ed2bdbe3f2221259437783156a90d889b9694`.
It took 688.11 seconds, reported 986,488 input and 39,404 output tokens, and has
an illustrative equivalent API cost of US$2.37 under the stated uncached-input
assumption. The primary AI-only review returned 54 pass, 9 `needs_review` and
0 fail. The preregistered zero-fail gate passed, but human approval remains
mandatory and the nine pending judgments are not hidden.

The current urgency distribution is one U4, one U5, six U7, six U8 and seven U9;
19/21 remain at urgency 7-10 and 20/21 require review. Calibration therefore did
not create a selective review queue or materially reduce urgency concentration.
The accepted benefit is narrower: clearer consequence evidence thresholds
without weakening uncertainty handling.

## 9. Interpretation limits

This study is AI-assisted, non-blind and based on the supplied 21 findings. It
cannot establish domain truth, unseen-case accuracy or calibrated operational
risk. Its value is narrower: it shows whether behavior can be changed through
maintainable generic policy, whether code preserves safety invariants, and
whether the resulting trade-offs are measured rather than asserted.

The semantic reviewer was reused across runs, and many review explanations were
textually similar. Counts against the earlier v8 review are therefore not clean
causal estimates. V11 is accepted only against its declared zero-fail gate, not
because its pass count exceeds v8.
