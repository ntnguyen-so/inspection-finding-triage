# Behavior Calibration Study

> **Purpose:** change system behavior through general, versioned policy rather
> than hand-correcting `tickets.json` or adding finding-specific branches.
>
> **Study status:** executed, then post-delivery audited. V9 and v10 were
> rejected; v11 retained the assessment anchors, restored mandatory uncertainty
> review and the v8 urgency formula, and generated the current root delivery.
> V11 remains useful evidence but is not yet a panel-ready output-quality
> baseline: its post-delivery audit found unstable action completeness, one
> unresolved local-to-asset consequence-scope judgment and excessive ticket
> verbosity.

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
formula while retaining the more explicit impact anchors. A subsequent
ticket-level audit changed the delivery interpretation, not the recorded
experiment: v11 is structurally valid and has no semantic `fail`, but its
actions and presentation are not consistently strong enough for submission.
The next calibration must improve consequence-scope handling, acceptance
planning and human-readable projection before another urgency-formula
experiment is justified.

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

## 10. Post-delivery ticket-quality audit

The zero-fail gate was deliberately permissive: it prevented a known semantic
failure from being promoted, but it did not prove that the resulting tickets
were concise, operationally complete or panel-defensible. After the knowledge
experiments exposed additional output concerns, the root v11 artifact was
audited against the Candidate Brief's expected level of detail, the frozen
review constraints and all retained v9-v11 reviews. This is post-hoc diagnosis,
not a relabelled blind test.

### 10.1 V11 is valid JSON, not yet a strong work-queue draft

The root artifact has 54 passed and nine unresolved semantic dimensions. Eight
of the nine are planning judgments:

| Finding | Missing or ambiguous planning evidence |
|---|---|
| F-1003 | witnessed start/performance acceptance |
| F-1005 | explicit post-correction gas-response and voting test |
| F-1009 | explicit underlying-steel condition/thickness inspection |
| F-1011 | witnessed north-quadrant delivery-pattern acceptance |
| F-1013 | independent actual-level reference before control transfer |
| F-1015 | restored readability and local level comparison |
| F-1017 | witnessed pressure/flow acceptance |
| F-1018 | independent actual-level reference coordinated with both legs |

These are not cosmetic wording preferences. They determine whether the
recommended work can demonstrate restoration of the failed or degraded
function. F-1003 and F-1017 remained unresolved in every v9, v10 and v11
review. Six other actions passed in at least one earlier repeat but were
`needs_review` in v11. The system can generate the required checks, but the
current free-text planning contract does not produce them reliably. F-1015 is
also the only v11 ticket with `review_required=false`; its unresolved planning
scope shows that rule-driven review routing is not an output-completeness
validator. The proposed planning gate must reject such an incomplete draft
before it can reach the work queue without targeted review.

This comparison does not isolate generator variance. F-1007 and F-1020 moved
from unresolved planning judgments in at least one earlier review to `pass` in
v11, the runs span different policies, and the reused reviewer was not blind to
earlier outputs. The evidence supports an unstable end-to-end planning judgment,
not a clean estimate of model-only randomness. Reviewer test-retest belongs in
the next experiment.

The ninth unresolved judgment is F-1009 impact grounding. The observation is
coating breakdown with no measured section loss. V11 correctly keeps the B4
crack separate and consistently defines the assessed function as cellar-deck
structural support. The unresolved choice is whether this local C2-C5 coating
observation can inherit the registered asset's whole-function consequence when
the supplied evidence does not establish local section loss, supported loads or
load-path importance. The domain notes say impact depends mainly on what the
equipment does and separately use a coating blister on a critical vessel as a
low-likelihood example. They also reserve the lowest consequence direction for
housekeeping or appearance. The SC-1001 comment says coating reports are
"frequent and mostly cosmetic." These statements support competing readings of
the local observation. The current policy does not resolve that tension. I7 is
therefore an unresolved scope judgment, not a demonstrated change of function
between L and I.

### 10.2 The ticket projection is too verbose

The Candidate Brief's example ticket uses short rationales that explain the
decision. V11 instead exposes most internal policy trace inside each draft:

| Field | V11 median length | V11 maximum |
|---|---:|---:|
| Summary | 204 characters | 265 |
| Recommended action | 251 characters | 277 |
| Likelihood rationale | 320 characters | 406 |
| Impact rationale | 332 characters | 550 |
| Urgency rationale | 1,319 characters | 1,983 |
| Review reason | 1,253 characters | 1,917 |

Thirteen of 21 review reasons exceed 1,000 characters. The information is
traceable, but it is not an effective work-queue explanation. Rule identifiers,
all source references and repeated uncertainty prose belong in retained run
evidence. The ticket should state the formula outcome, disposition-changing
override or floor, and a concise human-review reason. Auditability must not be
implemented by copying the full internal decision log into the user-facing
artifact.

### 10.3 Urgency concentration is a symptom, not the root defect

The v11 distribution remains concentrated, but the decomposition does not
support changing the formula merely to improve the histogram:

- 10 of 21 findings have model-assessed impact 8;
- 15 of 21 already have base urgency 7-9 before policy floors;
- six findings are raised above their base by source-directed attention,
  failed-test or material-uncertainty policy;
- applying the rejected v10 formula to the v11 L/I pairs still leaves 15 of 21
  base values at 7-9.

The apparently counter-intuitive F-1016 result also has a source basis. It is a
low-likelihood, high-impact SCE finding, and the supplied domain notes state
that this corner still requires attention this week. The ticket must not call
the tag defect a functional failure, but lowering urgency solely because the
observed defect is administrative would contradict the declared consequence
policy.

The formula remains a legitimate calibration surface, but the current evidence
does not identify it as the main cause of poor tickets. Replacing it again
before fixing function scope and planning completeness would add complexity
without addressing the observed defects.

### 10.4 Root-cause map

| Observed defect | Primary cause | Contract area |
|---|---|---|
| Missing restoration/acceptance checks | Free-text action generation is requested but not structurally represented or validated | A03, D01 |
| F-1009 I7 whole-asset consequence | Local-condition to registered-asset consequence scope is not explicit | C03, D03 |
| Very long urgency/review text | Internal rule trace is used directly as user-facing rationale | A01, A04, D01 |
| 20/21 review flags | Conservative rule-driven routing; poor as a workload queue and unable to detect F-1015's planning omission | D01, D03 |
| 19/21 urgency 7-10 | High-impact sample plus explicit floors; formula-only change has little leverage | C01-C04 |
| Different action quality across repeats | No deterministic completeness gate for model-authored planning | X01, X02 |

Knowledge retrieval is not the primary explanation for these v11 failures. The
official-KB experiment separately found batch-wide delivery and possible
non-target influence, but the same planning omissions occur with unchanged
baseline knowledge and vary across repeated generation.

### 10.5 Required next intervention

The next version must be staged so causes remain attributable:

1. **Planning contract.** Add structured model fields for assessed function,
   diagnostic activity, authorized disposition and post-correction acceptance
   activity. Acceptance must name the restored function and criterion. Where
   the declared policy requires independence or witnessing, code should require
   those explicit attributes rather than infer them from an engineer title.
   Code should reject missing components and compose the bounded action.
2. **Consequence-scope check.** Require an explicit, cited path from the
   observed local condition to the registered function used for impact. Do not
   impose a generic ceiling on coating, label or housekeeping findings:
   F-1015 and F-1016 demonstrate that a minor observed defect can coexist with
   material equipment-failure consequences. Instead, route an unsupported
   local-to-asset scope choice to review and test its effects across contrasting
   cases before adoption. F-1008 is a must-not-lower control because the same
   registered structure has a confirmed primary-connection crack; F-1004 and
   other multi-location assets check that local evidence is not automatically
   treated as trivial.
3. **Concise projection.** Keep complete rule objects and citations in run
   evidence, but render only the base/final urgency explanation, any
   disposition-changing floor or override, and a concise review reason in
   `tickets.json`.
4. **Disclosed test-informed preflight.** The current diagnosis has already used
   frozen reference-card judgments, including test-partition action constraints.
   The intervention cannot restore blindness by paraphrasing them as generic
   rules. Implement and tune only on development findings and newly declared
   isolated fixtures, but label the policy itself test-informed and justify any
   independence or witnessing requirement as an explicit prototype engineering
   choice rather than supplied domain truth.
5. **Frozen full-batch repeats.** Only after the planning and projection gates
   pass, freeze a new version, run repeated all-21 generation and apply the same
   semantic review. Retain every output; do not select the better repeat or
   describe test-partition improvement as held-out performance.
6. **Urgency ablation last.** Revisit the formula only if defensible L/I and
   concise tickets still show an operational prioritisation problem. Hold
   safety floors fixed and require a finding-level benefit, not a prettier
   distribution.

Until that sequence succeeds, the root `tickets.json` is retained historical
evidence rather than promoted as submission-ready output.

## 11. Prompt-length hypothesis and management decision

The assessment system prompt is 17,198 characters, about 2,249 words and roughly
4,000 tokens. It combines task boundaries, fact semantics, citation mechanics,
scoring guidance, retry behavior, action composition and character-budget
instructions. That is a maintainability problem and creates plausible
instruction collisions, but the retained evidence does **not** show that prompt
length is the primary cause of ticket instability.

### 11.1 Arguments against shortening first

- The prompt hash was unchanged across v9, v10 and v11, while several planning
  elements appeared and disappeared between repeats. Sampling variance and the
  absence of a planning-completeness gate explain this better than a changed
  instruction set.
- F-1003 and F-1017 lacked witnessed acceptance in every retained review. The
  current prompt does not declare that general requirement; this is missing
  structure, not evidence that an existing instruction was lost in length.
- The v9 impact-anchor sentence changed several findings despite the long
  prompt, demonstrating that prominent instructions can influence behavior.
- The prompt is less than ten percent of a typical provider-bound request.
  Shortening it would reduce cost modestly but would not materially reduce the
  much larger finding, registry, history, knowledge and citation context.
- Urgency and review verbosity are code-generated. A shorter prompt cannot fix
  those ticket fields.

### 11.2 Arguments for controlled reduction

- The prompt contains route-inapplicable citation instructions, retry-only text
  sent on first attempts, schema-enforced rules, duplicated assessment-policy
  anchors and detailed action-budget arithmetic that code should own.
- Accumulated clauses encode behavior learned from individual development and
  test findings. Removing finding IDs does not make those clauses independent
  of the observed cases. This increases overfitting risk and weakens the claim
  that maintainable domain changes belong in `triage_knowledge`.
- Summary and action instructions compete for many facts inside hard
  300-character limits. Moving planning structure and composition to schema and
  code reduces that collision without deleting safety meaning.
- A separately versioned prompt artifact gives the panel a reviewable
  model/code/knowledge boundary and permits exact hash pinning.

### 11.3 Decision

Do not use a prompt rewrite as the immediate quality fix. Use two separate,
reviewed changes:

1. **Byte-preserving extraction.** Move the current prompt unchanged from
   `triage\assessment.py` to a packaged UTF-8 prompt artifact. Give it an
   independent version and SHA-256, pin compatibility with the assessment,
   schema and context contracts, fail before provider dispatch on any mismatch,
   and prove that the provider-bound `system_sha256` is unchanged. This is a
   maintainability and reproducibility refactor, not a behavior improvement.
2. **Behavioral shortening after planning structure.** First implement the
   structured planning contract in section 10.5. Then run a prompt-only,
   test-informed ablation with policy, schema, knowledge, provider settings and
   user context held byte-identical. Remove dead or route-specific text first,
   then prose already enforced by code, and consolidate semantic guidance last.

Every removed clause must be mapped to one of four dispositions: enforced by
code/schema, maintained in cited knowledge, retained in the prompt with a stated
reason, or deliberately deleted with an explicit regression risk. Test-card
derived behavior remains disclosed as test-informed wherever it moves.

### 11.4 Promotion and rejection evidence

A shorter prompt can be called a quality improvement only if repeated
development runs show non-inferior semantic verdicts and planning-element
coverage, no D01 regression, no loss of known safety behavior, and an
improvement outside reviewer test-retest noise. All-21 observations remain
non-blind and cannot justify tuning.

Reject the short-prompt quality hypothesis if shorter outputs omit acceptance or
uncertainty content, score/band stability worsens, supposedly redundant text
proves behaviorally necessary, or gains occur only on tuning-exposed findings.
If quality is equivalent but every hard gate passes, the shorter artifact may
still be adopted honestly as a maintainability refactor.

## 12. Prompt-authority result

The subsequent experiment did not attempt the broad shortening proposed above.
It created authority-only prompt v2 by generalising the seven clause edits in
the frozen ledger while preserving the remainder of v1. The paired development
study, causal fixtures and disclosed all-21 regression are recorded under
`eval\results\triage\prompt-authority-v1`.

The main result is positive but narrower than promotion:

- v2 had no high-confidence source, registry or knowledge-authority regression
  in 52 paired development tickets;
- knowledge-only, equipment-only, observation-only and isolated
  operational-state changes moved outputs in the preregistered directions;
- code-owned failed-test closure removed the F-1003/F-1005 retest omission and
  all six failed-test tickets in the all-21 run contained the fixed witnessed
  post-correction test;
- every prior planning gap listed in section 10.1 has an explicit verification
  or acceptance activity in the all-21 v2 artifact.

The experiment also confirms that prompt editing alone is not the final quality
solution. Seven of 21 all-batch tickets needed action-length repair, F-1016
still treats identity-to-certificate verification as a safety uncertainty, and
the strict documentation-only no-review fixture failed even though it avoided
a safety floor. The all-21 deterministic contract passed, but calibrated
semantic review remains pending.

The real F-1014 regression is blocking: v2 changed the non-SCE, bypassable,
out-of-service test separator from U4 to U7 by treating unverified current
isolation as safety uncertainty, despite no established severe consequence
path and a registry statement that this class of work can usually wait for a
planned shutdown. The isolated fixture demonstrated the desired direction but
did not establish that the real unconfirmed branch was acceptable.

Therefore v2 remains experimental and root v11 remains unchanged. This is not a
failure of the authority direction; it is evidence that the next improvement
belongs in a reviewed operational-state rule and a structured
planning/uncertainty contract rather than another equipment-specific prompt
example or an urgency-formula change.

## 13. V3 correction: what improved and what did not

V3 tested the smallest generic correction after the v2 rejection. It required a
cited current safety path before classifying a missing current-state fact as
safety uncertainty, kept documentation-only identity checks in planning or
non-safety review, and reused one shorter code-owned failed-test closure.

The targeted cases demonstrate the intended fixes. F-1014 returned to U4 in two
valid repeats, F-1016 stopped using identity matching itself as a safety-floor
basis, and failed-test actions completed in one send with one closure. However,
the preregistered study failed because one F-1019 repeat moved two likelihood
points from the selected v2 all-21 control. The movement did not change urgency
or exposure rules and matches earlier/root observations, but it remains a
formal failed control.

The subsequent all-21 run was explicitly diagnostic, not a replacement
promotion test. It completed 21 tickets in 21 sends. Secondary review found
F-1015 and F-1018 fixed, F-1009 covered but ordered incorrectly, F-1003,
F-1005, F-1011 and F-1013 partial, and F-1017 still missing witnessed
acceptance. Compared with root v11, the remaining quality picture is:

| Measure | Root v11 | V3 diagnostic |
|---|---:|---:|
| Application sends | 21 | 21 |
| Tickets requiring review | 20 | 21 |
| Tickets at urgency 7-9 | 19 | 19 |
| Median action length | 251 | 261 |
| Median urgency rationale | 1,319 | 1,465 |
| Median review reason | 1,253 | 1,400 |

This separates the problems cleanly. The authority and failed-test closure fixes
work. Prompt edits do not solve the remaining dominant defects: free-text
planning order, incomplete witnessed acceptance, verbose user-facing
projection, a non-selective review queue and score instability such as F-1014
L4-5 in targeted runs versus L7 in the grouped diagnostic. The next
implementation should therefore be the structured planning and
concise-projection work already specified in section 10.5, not another
urgency-formula calibration or more case examples in the prompt.

## 14. V19 structured-planning diagnostic

V19 replaced the free-text action core with typed diagnosis, disposition,
correction and acceptance slots. Code now owns phase order, exactly-once
activity coverage, functional/witnessed closure requirements and the concise
ticket projection. Full rule reasons and citations remain in run evidence.
Two bounded implementation reviews initially rejected the change for incomplete
activity coverage, replaceable closure wording, missing implementation pins and
loss of C04 factual basis. Those blockers were fixed and the same reviewers
subsequently returned a live-test go decision.

The provider study was test-informed and underwent several disclosed revisions
after fail-closed observations exposed schema-budget, retry-cascade and lossy
projection defects. Intermediate sharded and atomic failures remain retained.
They must not be selected or merged into a delivery artifact.

The final intervention removed semantic phrase rewriting from the active v4
path. The model now owns concise wording inside length-bounded typed slots.
Code owns exact activity coverage, phase order, typed conditional/witnessed/
independent-reference flags, policy activities, the 300-character cap, attempts
and atomic publication. A model-authored deviation-record alias may be covered
by the code-owned reconciliation activity and is deduplicated structurally,
without keyword matching or paraphrase.

Seven same-pin preflight shards then generated all 21 tickets in 23 application
sends. A separate same-pin atomic run generated all 21 tickets in 22 application
sends and 680.109 seconds. The CLI returned `published_output=true`, and the
output file exists at the intended hash. The retained `run.json` is intentionally
a pre-publication record (`ready_to_publish`, `published_output=false`); this
version does not persist a separate post-publication receipt:

- output:
  `eval\results\triage\structured-planning-v19\atomic-text-agnostic\tickets.experimental.json`;
- output SHA-256:
  `a9b74137b79210eefdce84f24b70abf190f9061bc9fa30ed2eea672490857721`;
- prompt SHA-256:
  `f59afc09cfe79c84a4f1ea2de4d013a419014418cc132173cf21917733ee72d4`;
- execution-policy SHA-256:
  `a7f35706e7b19eb4219a5d0c32cc810f329ee264b657c13d553f278965b15b8b`;
- knowledge content SHA-256:
  `b215857575e443ba5fd9cb56a19f3079003cd68acb03fdf0e33ca7fbed59e097`.

The output contract passed. A bounded AI-only exact-artifact review found no
high-confidence semantic fail, so the declared zero-fail output gate has a
provisional go observation. It retained needs-review judgments for planning or
scope questions including the local level comparison, independent level
references, lifeboat recertification, the F-1009 consequence scope and related
DEL-8300 chronology. This review is not calibrated domain certification and
does not establish full A-D acceptance. The run remains
`acceptance_eligible=false`; HTTP-attempt and USD-cost evidence are unknown.

Root `tickets.json` remains unchanged. Final provenance and limitations are in
`eval\results\triage\structured-planning-v19\atomic-text-agnostic\summary.json`;
earlier run history remains indexed in `diagnostic-summary.json`.

### 14.1 Provenance correction and reviewer sensitivity

Follow-up review found that v19 still inferred some code ownership from exact
activity text and allowed acceptance to duplicate policy pre-work. V21 removed
text-equality ownership, made the capacity check model-owned, rejected fixed or
covered pre-work in acceptance, and required closure for suspected uncertain
impairment. Seven parallel shards then generated 21/21 tickets in 23 sends.

V22 added one disclosed test-informed, generic planning rule: when an obscured
local indication has an independent live indication, post-correction acceptance
must compare them rather than establish readability alone. Its targeted F-1015
run passed in one send. The same-pin atomic run generated 21 tickets in 24 sends
and 646.781 seconds:

- output:
  `eval\results\triage\structured-planning-v22\atomic\tickets.experimental.json`;
- output SHA-256:
  `5ea7ca03863a4eebf4f2e250c2204287eaf4bbfd5cd3deb253d88d6280b7c60c`;
- prompt SHA-256:
  `28f18321afc4ee71a8ab644de7e4758b66f7340c28d20642ba60afd21e390c2e`;
- execution-policy SHA-256:
  `16ced0ccdf2f6610b81ac96b0b78cffba64086f8dbe139c3751e39e583d71d47`.

Deterministic validation passed: 315 production tests, 127 evaluator tests,
reference validation and `git diff --check`. Exact-artifact AI reviews were not
stable enough to establish a semantic gate: one returned 61 pass / 2 fail while
the sensitivity reviewer returned 61 pass / 2 needs-review / 0 fail. Document
03 requires disagreement to remain inconclusive and forbids treating a second
reviewer as majority-vote truth. These ad hoc agents were not one frozen,
calibrated reviewer configuration; rerunning them until green would be reviewer
shopping. V22 therefore remains `acceptance_eligible=false`, semantic status
inconclusive, and not a replacement for root `tickets.json`.

After Document 11 froze the checklist and prohibited new rubric items, one
primary reviewer configuration was calibrated against both seeded contradictions
and reviewed the exact v22 artifact once. Evaluator verification returned
63 pass / 0 needs-review / 0 fail and `provisional_pass`. The earlier ad hoc
disagreement remains recorded as sensitivity history rather than being deleted.
This result is still AI-only: the agent runtime did not expose model,
reasoning-effort or prompt identity, so those fields are recorded as
`unknown_not_exposed`. It establishes the provisional semantic output gate, not
human approval, domain certification, hidden HTTP-attempt accounting, cost
evidence, full A-D acceptance or promotion of the root artifact.

The project owner subsequently approved the disclosed equivalent-cost assumption
and promoted the v22 output byte-for-byte to root `tickets.json`. The promoted
root SHA-256 is
`5ea7ca03863a4eebf4f2e250c2204287eaf4bbfd5cd3deb253d88d6280b7c60c`.

### 14.2 Urgency-spread sensitivity

The panel concern that 19 of 21 tickets fall in U7-U9 is legitimate. It must be
answered with a controlled sensitivity analysis rather than a formula selected
because it produces a prettier histogram. The v22 L/I assessments and applied
rules were therefore held fixed while four code-only policies were replayed
offline:

| Scenario | U1-U3 | U4-U6 | U7-U10 | Interpretation |
|---|---:|---:|---:|---|
| Current `ceil(0.7I+0.3L)`, uncertainty floor 7 | 0 | 2 | 19 | Retained policy |
| Rejected v10 interaction formula, floor 7 | 0 | 2 | 19 | Two ticket values move; concentration does not |
| Quadratic compression, floor 7 | 2 | 0 | 19 | Mid-band values collapse into the floor |
| Quadratic compression, uncertainty floor 6 | 2 | 8 | 11 | Material spread, but two policy levers change |

The decomposition explains the result. Sixteen tickets already have formula
base U7 or higher. Five are raised above base, including three raised into U7+
by the material-safety-uncertainty floor. Formula-only changes cannot provide a
meaningful spread while that floor remains 7.

The 2/8/11 candidate is not promoted. It lowers cases including the repeatedly
interrupted inhibitor pump from U8 to U6 and the confirmed structural crack from
U7 to U6, while also changing the frozen acceptance policy for material safety
uncertainty. That may eventually be defensible, but it requires an explicit
owner/domain decision about whether U7 means prompt human disposition or
completed corrective work, independently worked safety expectations, a
reference-version change and fresh end-to-end evidence. It cannot be justified
only by queue size.

For the retained policy, the operational explanation is:

- U9: immediate human disposition or source-required same-day attention;
- U7-U8: expedited review/attention within the declared weekly band, not a claim
  that every repair must be completed that week;
- U4-U6: planned work with ordinary prioritisation;
- the numeric score remains the tie-breaker inside a band.

The reproducible result is
`eval\results\triage\structured-planning-v22\urgency-sensitivity.json`, generated
by `tools\analyze_urgency_sensitivity.py`. This is sensitivity evidence, not a
retrospective claim that the current formula is calibrated risk truth.

### 14.3 Decision trace for `ceil(0.7I + 0.3L)`

The numeric weights are not supplied domain truth. Their authority chain is:

1. **Candidate Brief:** urgency must be code-derived from L/I by a documented
   function, must be neither a plain average nor a plain maximum, must explain
   both asymmetric corners, and must support overrides. It supplies no formula.
2. **Domain notes:** a near-certain inconsequential failure may wait for the next
   shutdown (U3-U4), while a low-likelihood/high-impact SCE still needs attention
   this week (U7-U8). Urgency means time to human attention, not repair
   completion.
3. **Document 01:** identifies urgency as a transparent attention policy and
   explicitly says the package does not prescribe a complete numeric formula.
4. **Document 02:** defines the corner experiments and deterministic ownership,
   but explicitly leaves formula selection to implementation design.
5. **Document 03:** freezes range, monotonicity, corner evidence, provenance and
   code ownership. It explicitly does not select a formula.
6. **DESIGN.md:** chooses the linear family
   `ceil(wI + (1-w)L)` as the simplest monotone, explainable candidate response.

For the extreme high-L/low-I corner `(L=10,I=1)` to remain in the
next-shutdown band:

```text
3 <= ceil(10 - 9w) <= 4  =>  2/3 <= w < 8/9
```

For the extreme low-L/high-I corner `(L=1,I=10)` to remain in the weekly band:

```text
7 <= ceil(1 + 9w) <= 8  =>  5/9 < w <= 7/9
```

Thus the qualitative source constraints admit approximately
`0.667 <= w <= 0.778`. The implementation chose `w=0.7` because it is a simple
interior decimal with exact integer arithmetic, not because historical failure
data calibrated 70/30 as optimal.

This derivation makes the policy non-arbitrary but not empirically calibrated.
Three additional assumptions remain candidate-owned: use of a weighted-linear
family, mapping the qualitative examples to the extreme 1/10 corners, and using
the upper endpoints U4/U8 as inequalities. The later
`P-SCE-HIGH-IMPACT` floor also demonstrates that the base formula alone does not
encode every domain statement. The section 14.2 sensitivity result therefore
supports a precise panel answer: 70/30 is a transparent constrained heuristic;
the observed queue concentration is a calibration risk, and changing the
weights alone does not solve it on the current evidence.

## 15. Disclosed test-informed chronology repair

The frozen v29 delivery generated all 21 tickets and passed the deterministic
contract, but its first calibrated exact-artifact review failed F-1011
grounding and uncertainty. The ticket retained the failed north-quadrant
delivery test but omitted the related later observation that the branch valve
was found chained closed, reopened, and not followed by evidence of restored
spray coverage. The failed artifact and 61/63 review remain retained under
`eval\results\triage\structured-planning-v29\final`.

This is a test-informed result and is not relabelled blind. The first prompt-only repair, v30, was rejected: its two development repeats
changed two urgency bands and one review flag. No v30 all-21 run was made.

The replacement keeps prompt v7 unchanged and does not copy F-1011/F-1020 fact
states, change expected answers, propagate a related finding's directive, or
alter urgency. Ticket projection v4 makes provenance already selected by the
model visible: when a typed fact cites another finding, the ticket carries at
most two neutral, source-labelled fact notes containing the fact name/state,
model-authored reason and exact related finding-description quote. This is
deterministic provenance projection, not new semantic inference; related facts
remain scoped to their own finding. A dry run over the failed v29 delivery
changes only F-1011 and F-1018, adding one related-finding note to each
likelihood rationale (559 and 591 characters respectively). F-1018 is
therefore included explicitly in the new
exact-artifact review even though F-1011 triggered the change.

The affected gates are semantic grounding/uncertainty, D01 uncertainty
visibility and X01 comparability. Any rerun is disclosed as test-informed,
uses a new execution/configuration identity, reruns development stability first,
and preserves the failed v29 observation. Promotion remains prohibited unless
the new development pair, one all-21 delivery, exact-artifact semantic review,
publication receipt and final contract checks all pass.
