# Evaluation-First Acceptance Contract

## What this version changes

Reference version 1.2 completes the candidate-pack coverage audit of the v1.1
acceptance specification and executable ticket-output assessor. The split, all
21 evidence cards, and the candidate pack remain unchanged.

The purpose is to constrain development before implementation, not to manufacture
proof that a system which does not yet exist is correct. The acceptance scenarios
in `eval\acceptance.json` are preregistered specifications. Their current status
is `not_run_no_system`. Tests of the evaluator are not results for the future
system. No generated ticket or model result exists in this phase.

This contract supplements `DATA_EVALUATION_PLAN.md`. Where it closes an open policy
decision in that document, this version takes precedence. All references remain
AI-assisted, provisional, non-blind, and not domain-expert-certified.

## 1. Scope and readiness

Three small layers serve different purposes:

1. **Reference integrity:** validate the inputs, split, cards, sources, and hashes.
2. **Output assessment:** check real ticket files and collect evidence-based
   semantic review. This tool is executable now, without a provider.
3. **System acceptance scenarios:** specify context, retries, knowledge changes,
   urgency, and failure behavior. These run only after a real system/adapter exists.

The suite is ready to guide implementation when A-D have named scenarios, explicit
expected outcomes and evidence requirements; the assessor detects seeded invalid
outputs; pending semantic review cannot be reported as pass; and reviewers have
challenged the contract. This is **evaluation-design readiness**, not system
acceptance, accuracy, deployment readiness, or a guarantee against every error.

The existing 13 development / 8 test split is preserved. These are 9 / 4 groups,
not independent statistical samples. Do not tune against test outputs. Synthetic
fixtures below are software/behavior probes, never additions to the final 21
findings or certified engineering labels.

## 2. A-D traceability and development gates

| Panel question (brief section 6) | Decision to defend | Acceptance evidence | Not established by that evidence |
|---|---|---|---|
| A: structured output | Typed validation plus bounded recovery; structural validity is separate from semantic support | A01-A04; output-assessor report; request/attempt diagnostics for failures | A schema cannot certify whether every valid numeric score is correct |
| B: domain knowledge | Source-controlled knowledge and item comments reach the decision; changes have a narrow maintenance surface | B01-B03; captured requests, knowledge diff, small paired probe with a negative control | A source in a prompt does not prove causal use or general domain competence |
| C: urgency | Code derives urgency from L/I and explicit policy facts; chosen constraints are testable | C01-C04; independent boundary expectations, all 100 base inputs, override matrix, derivation trace | Passing policy tests does not establish operational calibration or optimal risk mathematics |
| D: limits | Separate supported assessment, material uncertainty, and inability to assess; no fake scored fallback | D01-D04; grounded review reasons, failure diagnostics, documented exclusions | Review flags do not make unsupported scores valid or automate human approval |
| Cross-cutting: stability | Repeatability concerns decisions, not identical wording; do not hide score collapse | X01; one fixed-config development repeat and per-case adjudication | Two agreeing runs do not prove deterministic model behavior |
| Cross-cutting: reproducibility | One documented command, bounded cost, allowed tooling and honest submission provenance | X02; fresh-environment log, usage/budget report, dependency and Git inspection | Cheap execution and deliverability cannot be measured before implementation |

Use the sequence:

1. Build the smallest implementation capable of running these scenarios.
2. Pass deterministic development scenarios and review development ticket outputs.
3. Run the small knowledge-change probe; record failure if the model ignores it.
4. Freeze model/prompt/knowledge/policy versions, then evaluate test once.
5. Any test-informed change is disclosed as regression/test-informed development.
6. Final generation must automatically cover all 21 findings. Failed findings must
   not disappear or receive placeholder scores to satisfy coverage.

An accepted development baseline requires all applicable deterministic scenarios
to pass, all selected case-review dimensions to pass provisionally, and no open
blocker. A test failure is a defect to report and address, not a result to hide.
Known limitations can remain documented, but missing execution or `needs_review`
is not pass.

## 3. Concrete criteria, including engineering choices

### A. Output and recovery

For each selected run, require exactly one ticket per selected finding, correct
equipment mapping, unique `TKT-####` identifiers, the required wrapper, integer
scores 1-10, non-empty rationales, and summary/action lengths 1-300 characters.
Booleans are not integer scores. `review_required` is a boolean; its reason is a
string or null, non-empty when true.

Chosen stricter serialization rules: reject duplicate JSON object keys,
NaN/Infinity, extra wrapper/ticket/score fields, and a timestamp without an explicit
timezone. The brief does not explicitly require those stricter choices; they
reduce ambiguous output and make the contract auditable.

Fault injection distinguishes:

- One malformed/invalid response followed by a valid response: bounded recovery
  succeeds without duplicate or missing tickets.
- Invalid responses on every allowed attempt: fail with non-zero exit, finding ID
  and error class; no new final `tickets.json`. Separate partial diagnostics are
  allowed. An old successful file must not be presented as this failed run's result.
- Valid structure but known semantic contradiction: reject as an acceptable
  assessment or require correction/review; a blind retry is not proof of repair.
- An ambiguous 8-versus-9 judgment without an independent rubric: record unresolved
  semantic review, not invented numeric certainty.

Malformed outputs, retries, and file publication are future-system scenarios;
`eval\assess.py` is an independent reader, not the production validator or runner.
The prototype budget is two provider inference attempts per finding, counting
SDK retries too; do not hide additional attempts in nested retry layers. Successful
publication uses `tickets.json`. Failure exits non-zero and emits a JSON diagnostic
on stderr with `run_status`, `finding_id`, `error_class`, `attempts`, and
`published_output=false`. If a previous output exists, it stays byte-identical
and is not identified as this run's result. Capture its before/after hashes.

### B. Knowledge and the PSV maintenance exercise

B01 captures actual provider-bound input and checks both relevant knowledge and
the correct equipment comment. It also checks related findings and exclusion of
evaluation annotations/test findings during development.

B02's input and policy change are frozen in `eval\probes.json`: synthetic F-9001
reports seat passing on a bench device, and development F-1016 is the tag-only
negative control. A deliberately artificial test overlay assigns likelihood 6
for matching seat-passing observations under probe-A, and 8 under probe-B.
The predicate is mechanism/type-based, not a finding-ID branch. These invented
numbers are an instruction/policy-following diagnostic, not correct engineering
scores, a shipping rule, or gold for any of the original 21 findings. Unlike a
healthy-PSV fixture, this positive control exercises the changed predicate.
The original source package is immutable; edit a managed test policy copy or
overlay, never the supplied domain notes.

The rule change must be implementable through the declared knowledge/policy edit
without case-ID branches or changes to orchestration. Capture the diff, input
versions and before/after outputs. A real model probe is necessary to claim an
observed behavioral response. A mocked request proves delivery only.

Run one observation per input/policy condition: four nominal calls, at most eight
including the two-attempt budget. Keep model/configuration fixed and record it.
Do not demand exact score stability from the negative control; require the correct
conclusion that tag illegibility does not establish passing or relief failure.
No positive model outcome is presumed. If behavior does not respond as expected,
record that failure and investigate; do not keep redefining the expectation until
it passes. Repeated probes or ablations are optional, budgeted follow-up. F-1002
is test-only and cannot be used to tune this experiment.

### C. Urgency constraints fixed before choosing the formula

The brief requires a derived function and corner behavior but does not prescribe
specific numeric answers. The following **prototype policy anchors are our design
choices**, not expert-calibrated scores or supplied gold labels:

| Base L / I (no escalation) | Allowed urgency | Reason |
|---|---|---|
| 1 / 1 | 1-2 | Backlog for the least concerning base combination |
| 10 / 1 | 3-4 | Near-certain inconsequential failure need not demand today's intervention |
| 1 / 10 | 7-8 | High consequence is not averaged away; satisfies the low-L/high-I SCE example |
| 10 / 10 | 9-10 | Strong evidence and high consequence require immediate attention |

Also choose nondecreasing urgency as either base input increases with everything
else fixed. Verify range/integer output for all 100 input pairs, anchor bands,
and monotonicity. Use independently worked examples; never compare a function to
itself and claim that is an oracle. Show how mean/max differ at the two asymmetric
anchors. The numeric formula remains an implementation design choice within these
constraints; changing anchors requires a versioned contract change.

Test fact extraction separately from escalation code. Protection impairment plus
confirmed absence of a recorded deviation, or confirmed evacuation capacity below
POB, produces urgency 9-10 with the applicable rule named in the rationale.
Unknown facts cannot be presented as confirmed conditions.

### D. Review and precautionary policy

The following conservative prototype choices close the prior routing-policy gap:

- Material uncertainty about a safety/protection decision requires
  `review_required=true`, a specific reason and a concrete verification activity.
- A confirmed failed protection-function test, a known unavailable evacuation
  craft with unverified remaining capacity, or unverified protection after an
  explicitly discovered unlogged impairment requires **immediate human attention**
  (urgency 9-10). If deviation/POB/restoration facts are unknown, label the reason
  as this precautionary policy, not a proven regulatory/capacity override.
- Other material safety uncertainty requires attention at least this week
  (urgency at least 7), with the policy and evidence explained.
- These routing floors do not force likelihood or impact upward and do not supply
  missing evidence for either score. If defensible required scores cannot be
  produced at all, fail visibly rather than emit a scored placeholder.
- Tag illegibility with verified in-date certification is not automatically a
  failed protection function. If all-SCE review is adopted as a separate policy,
  state that explicitly; do not use it to imply all SCE defects need immediate
  maintenance or that every review flag proves uncertainty.

These are rules for human attention to drafts, not instructions authorizing
shutdown, continued operation, or live maintenance. They need domain-owner review
before operational use. The brief still requires human approval of drafts;
`review_required` identifies mandatory case-specific checks before the work queue,
not permission for autonomous execution when false. No target review-rate quota
is used.

The fact-assessment layer (model or explicit evidence rules) proposes states and
source-backed explanations; code validates their shape/identity and owns all
urgency calculation and floors. Confirmed true, confirmed false, unknown, and
suspected are not interchangeable. C03 tests policy on supplied fact states; C04
tests whether the assessment layer supplied the right facts. No hidden model
reasoning is required as evidence.

"Material" means an unresolved or contradictory fact could change justified L/I,
available protection, evacuation capacity, usable redundancy or necessary human
disposition. Missing POB, an unhealthy backup, and unknown restoration qualify;
a missing reporter name alone does not. This is a prototype review gate subject
to semantic review, not a claim that code can infer materiality perfectly.

For F-1020, distinguish the immediate action warranted at discovery from unknown
current protection after reopening. Do not claim the valve remains closed or
that reopening proves nozzle delivery has been restored.

## 4. Semantic review rubric

Each selected finding has three review dimensions. The evaluator attaches the
existing card evidence and expectations; it does not invent new gold scores.

| Dimension | Pass only if | Fail examples |
|---|---|---|
| `grounding` | L/I and rationales are consistent with known facts and domain rules; decision-changing evidence is retained; no forbidden claims | Healthy backup claimed despite partner finding; invented measurements; concealed corrosion described as a confirmed leak |
| `planning` | Summary explains what/where/why without mere paraphrase; action names an evidence-appropriate activity | Generic \"investigate further\"; dropped-object consequence omitted; unsubstantiated replacement instruction |
| `uncertainty` | Important unknowns, review gates, urgency/policy reasoning and limits are explicit and consistent | Invented POB comparison; unknown deviation treated as confirmed absence; middle scores used to hide inability to assess |

Use `pass`, `fail`, or `needs_review`. Record a non-empty reason and at least one
exact quote with its output field for each pass/fail. Missing judgments and
`needs_review` keep the result pending. A fail blocks a provisional pass. Review
provenance states human, AI-assisted, or AI-only and claimed independence. These
are disclosures, not machine-verifiable qualifications.

A pass requires evidence across the ticket, not every number in a 300-character
summary. Score plausibility is a reasoned judgment: use the top-end confirmed
failure rule and other supported constraints, not exact matching to the example
or arbitrary score intervals. If reviewers cannot defend a score, use
`needs_review` instead of assuming correctness.

An AI-only or same-author review remains provisional even when every dimension
passes. Human review is not claimed to be domain certification either. The
assessor never turns review agreement into accuracy or an assurance certificate.
`review_provenance` appears next to the top-level result so a consumer need not
interpret a nested object to see AI-only/non-independent judgment. Exit 0 still
means only the declared provisional scope, never independent assurance.

### Reviewer calibration, not a semantic oracle

`eval\probes.json` includes two complete, schema-valid tickets with deliberately
false claims: verified healthy firewater standby, and failed relief function
proved by an illegible certification tag. Their grounding judgments must be
`fail`, for the cited source reasons. This tests that the actual output reviewer
rejects these known contradictions; it does not teach a keyword classifier or
guarantee that the reviewer detects other errors.

The calibration report has scope `known_fixture_conformance` and a separate
`calibration_status`, not the normal ticket-output `overall` field. Calibration
must pass before relying on that reviewer for a provisional development baseline.
Changing reviewers requires recalibration. Evaluator self-tests use software-fixture
judgments. The final-readiness audit also records two actual, disclosed AI review
judgments separately under `eval\results`; see section 7 for their narrow scope.
The preregistered fixtures remain disclosed and non-blind; this is a basic
review-protocol check, not an independent experiment on reviewer competence.

## 5. Using the output assessor

From the repository root on Windows, Python 3.11+, no third-party dependencies:

```powershell
python -B eval\validate.py
python -B -m unittest discover -s eval -p "test_*.py"
python -B eval\assess.py --partition development --checklist
```

Once an actual ticket file exists:

```powershell
python -B eval\assess.py --partition development --tickets <path-to-output>
python -B eval\assess.py --partition development --tickets <path-to-output> --reviews <path-to-review-json>
```

The first output-assessment invocation creates a review template tied to the exact
ticket-file SHA-256. It exits 2 while semantic review is pending. Fill its
`review_template` object and save that object as the review file; the outer report
is not the review input. The generic `--checklist` has no output hash and cannot be
submitted unchanged as an actual review.

Exit codes: 0 means a **provisional ticket-output pass only**, 1 means invalid input
or failed assessment, 2 means valid output with pending semantic review.
`--checklist` exits 0 for successful checklist generation, not assessed quality.
`--partition all` is for final all-21 coverage, after the test protocol.

An item may omit the template's explanatory `expectations` block; if it includes
one, the assessor requires it to match the frozen card. It never trusts a reviewer
to redefine the expectations.

For reviewer calibration:

```powershell
python -B eval\assess.py --partition development --calibration-reviews <path-to-calibration-json>
```

The calibration input contains `reference_version`, `reviewer` (same provenance
fields as output review), and `judgments`. Each judgment contains `probe_id`,
`dimension`, `verdict`, `reason`, and `evidence` with `field`/`quote`, using the
exact seeded ticket text. Missing judgments stay pending; a `pass` verdict on a
seeded contradiction fails calibration. Its exit codes are 0 pass, 1 fail, 2 pending
for this known-fixture check only.

The report explicitly says system scenarios are unexecuted. Even a provisional
ticket-output pass does not prove request construction, knowledge influence,
code-derived urgency, retry behavior or failure publication. Those require the
scenario evidence. The assessor must not be imported by production to force
case-specific answers into generated tickets.

## 6. What remains unobserved, and what is deliberately not built

No provider adapter, production runner, urgency formula, or model evaluation is
implemented. Fault injection and B/C/D behavioral scenarios remain unexecuted.
The evaluation gate specifications precede the system rather than pretending
to have measured it. There is no live deployment, trained risk model, vector
database, autonomous maintenance execution, or large evaluation platform.

We use named requirements, counts and case IDs rather than one composite score.
Zero observed blocker cases is required for a provisional baseline pass, but
only over the checks actually reviewed; it does not establish zero real-world
errors. No statistically meaningful accuracy claim is possible with these
non-blind, AI-assisted references.

### Review and version record

- v1.0: data/card integrity and qualitative references only.
- v1.1: add explicit A-D scenarios, precautionary routing/urgency constraints,
  a strict output assessor, evidence-bound semantic review and evaluator self-tests.
  Original sources, cards, and membership are unchanged.
- v1.2: add X01 stability and score-collapse review, X02 reproducibility/cost/
  delivery, and B01 row-order context invariance. Refactor evaluator self-tests
  to read the reference version rather than hard-coding it.
- First actual-artifact review identified missing concrete B02 and A04 fixtures:
  accepted and fixed in `eval\probes.json`, with a scoped calibration checker.
- Second agent cross-reviewed those criticisms and the assessor: accepted the
  artificial 6-to-8 probe only as policy conformance, not engineering truth;
  rejected an invalid `S-` ID and arbitrary +/- score tolerance.
- Both reviews requested a fixed attempt budget and an explicit materiality/fact
  boundary: accepted and specified above.
- Minimum quote length and a canary platform were rejected: a score quote may
  legitimately be short, and known-fixture calibration is sufficient here.
- Reviewer provenance is exposed at the top level; edited expectation blocks
  are rejected. A provisional output pass still is not A-D system assurance.
- Review limits: first agent read contract/scenarios/assessor and ran the 17
  then-current self-tests, but only skimmed test code. Second read assessor/B02
  and cross-critiqued, without rerunning tests or re-auditing all scenarios.
  Final fixture/checker changes were verified by focused self-tests, not an
  additional claim of independent domain review.

Copilot authored these additions with AI-assisted review. Suggestions are subject
to adjudication, not majority vote; no independent domain validation is claimed.

## 7. Final pre-implementation coverage audit

The brief is the scope boundary, not a reason to build every evaluation technique.
The final audit found two missing explicit scenario groups: decision stability
and reproducible, low-cost delivery. They are now X01/X02; B01 also tests context
independence from CSV row order. These additions do not require new domain gold
labels or changes to the development/test partition.

| Candidate-pack expectation | Evaluation coverage |
|---|---|
| Output schema, full coverage, mapping and concrete text requirements | A01, three-dimensional review, and all-21 final scope |
| Invalid structure versus valid-but-wrong scores and inability to produce a ticket | A02-A04, D02, seeded reviewer controls |
| Domain notes, equipment comments, real redundancy and maintainable PSV changes | B01-B03, unchanged source-cited cards |
| Code-derived urgency, asymmetric corners, overrides and uncertainty | C01-C04 and D01 |
| Avoid safety overconfidence, omitted decision facts and uniform middle scores | Grounding/planning/uncertainty rubric, D03, X01 |
| Consistency of repeated assessments | X01 with fixed assessment time and explicit cache mode |
| Single command, dependency manifest, low cost and no prohibited orchestration | X02 |
| No hand-edited output or committed secrets; DESIGN, assumptions, AI disclosure and history | D04 and X02 |

Before the first paid baseline, System Design must select the model/provider,
explicit L/I assessment rubric, knowledge packaging, formula satisfying the
declared urgency constraints, configuration/usage budget, and the concrete
failure-publication mechanism. Those are design decisions to implement and test,
not reasons to postpone System Design or invent successful eval results.

The stopping rule for this phase is: close source-backed gaps, verify the grader
and frozen references, challenge the coverage with two agents, and report a
bounded readiness decision. Do not start a new round of dataset expansion,
benchmarking, model selection or synthetic-policy tuning without a concrete
unresolved requirement.

Actual final-audit and known-fixture calibration results are recorded separately
under `eval\results`; they are not generated tickets or future system results.
The calibration is disclosed/non-blind and does not qualify a reviewer as a domain
expert. Any new reviewer/configuration used later must be checked again.

### Readiness decision and actual audit evidence

**Ready to start System Design, then implement against this contract.** No
high-confidence, source-backed omission remains that requires another evaluation
design phase. Actual system acceptance remains pending.

Two agents challenged this conclusion:

- Reviewer A read the candidate brief/domain notes, probes and source rows, but
  did not inspect the acceptance scenarios or assessor in this pass. Its
  conditional yes is not treated as a full coverage audit.
- Reviewer B inspected all 17 scenario definitions, source requirements, probes,
  relevant source rows and the policy/readiness portions of this document. It
  cross-critiqued A and found no blocking omission. It did not rerun tests or
  independently re-audit all grader code.
- Both actually rejected the two disclosed false-claim tickets with exact output
  quotes and source-backed reasons. The calibration checker accepted their
  judgments. These are real known-fixture results, not fabricated model-run
  metrics. There is no positive-control measurement: a reviewer that rejects
  everything could also pass, so no reviewer-competence/accuracy claim follows.
- A's blanket objection to exact numbers was qualified: declared policy anchors
  and artificial conformance expectations are valid, unlike claimed numeric
  engineering truth. The domain's "maximum is closer" remark is qualitative,
  not a numeric distance constraint.
- B's concern about a historical "17 then-current self-tests" count was not
  applied as a correction: it describes the earlier v1.1 review, not today's
  suite. The final result records the actual current count separately.
- A positive calibration control is not forbidden by the user or brief; it is
  simply outside this narrow negative-control result. Supported real outputs
  still require the full three-dimensional rubric, not calibration alone.

The final execution summary is `eval\results\readiness-1.2.json`. It records the
verified reference snapshot, current self-test result, actual calibration checks,
and every still-unexecuted system scenario. Results are evidence artifacts, not
additional runtime knowledge or new expert labels. The results are not part of
the reference-manifest hash inventory; the summary binds itself to the frozen
manifest and reviewer-input hashes. This is traceability, not a tamper-proof log.
