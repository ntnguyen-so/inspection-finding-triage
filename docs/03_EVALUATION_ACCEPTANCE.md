# Acceptance Contract and Evidence Rules

> **Document status:** panel summary of the acceptance contract. Requirements
> below are specifications, not presumed results. The exact pre-rewrite v1.3
> working contract
> is preserved at
> `docs\original-decision-process\03_EVALUATION_ACCEPTANCE.md`; executable
> scenarios are authoritative in `eval\spec\acceptance.json`.

## Abstract

The Candidate Brief asks how the system handles structure, domain knowledge,
urgency and limits. This contract converts those questions into observable
scenarios A01-D04, then adds X01 decision stability and X02 reproducibility/cost.

The contract deliberately prevents three success-shaped shortcuts:

- valid JSON is not treated as semantic correctness;
- a human-review flag cannot legitimize an unsupported score; and
- evaluator self-tests or AI reviewer agreement are not treated as system
  acceptance.

Some rules are stricter candidate-owned prototype policies, including the
two-attempt budget and precautionary review/urgency floors. They are labelled as
such rather than attributed to Falkor or a domain expert.

## 1. Acceptance model

| Area | Question | Scenario IDs |
|---|---|---|
| A — Structured output | Does the system enforce contract, recovery, complete coverage and semantic contradiction handling? | A01-A04 |
| B — Knowledge | Does approved context reach assessment, influence behavior as intended, and remain maintainable? | B01-B03 |
| C — Urgency | Does code derive monotone, corner-aware urgency and apply fact-sensitive rules? | C01-C04 |
| D — Limits | Does the system defer, fail visibly and preserve human authority? | D01-D04 |
| X — Cross-cutting | Are decisions stable enough to inspect, and can a run be identified and reproduced at known cost? | X01-X02 |

Each scenario defines required evidence and the highest claim that evidence can
support. No composite score is used.

## 2. Area A — Structured output and failure

### A01 — Contract and coverage

**Requirement.** Output must contain exactly one correctly identified ticket for
each selected finding, with closed schema, valid ranges and text limits.

**Pass evidence.** Executable mutation tests plus a complete generated artifact
bound to its input.

**Failure.** Missing, duplicate, extra or mismatched identities; invalid wrapper;
out-of-range values; unvalidated extra fields.

**Limit.** Schema success does not establish defensible L/I or planning text.

### A02 — Recoverable malformed or structural output

**Requirement.** Classify malformed JSON separately from structural violations,
allow only the declared bounded repair, and retain every attempt.

**Chosen policy.** At most two total provider attempts per finding, including
SDK/transport retries. This is stricter than the brief and exists to make cost
and failure finite. A route that cannot expose or disable hidden retries cannot
establish this pass condition.

**Failure.** Hidden/unbounded retries, resettable accounting, or silent local
rewriting that makes an invalid response appear provider-valid.

### A03 — Exhaustion and publication

**Requirement.** If one finding cannot be produced within budget, exit nonzero,
publish no partial batch and preserve any previous output.

**Rationale.** A partial file could masquerade as the required complete planning
package.

**Rejected alternative.** Placeholder scores or omitted findings make failure
look like completion.

### A04 — Valid structure, wrong meaning

**Requirement.** Detect machine-checkable contradictions such as invalid
identity, unsupported citation, inexact quotation or a score that violates an
explicit rubric anchor. Submit coherent remaining semantics to frozen review.

**Failure.** Treating “valid JSON” or “review_required=true” as sufficient.

**Limit.** Code cannot prove every engineering judgment. AI review remains
provisional and human approval remains mandatory.

## 3. Area B — Knowledge and maintainability

### B01 — Context delivery

**Requirement.** Capture provider-bound evidence that supplied domain guidance,
registry comments and required related context were sent under the declared
configuration.

**Pass evidence.** Hash-bound context and independent validation of selected
source/input identities.

**Limit.** Delivery does not prove causal use.

### B02 — Knowledge influence

**Requirement.** Compare preregistered positive and negative controls that differ
only in an isolated knowledge input, with artificial values labelled synthetic.

**Failure.** No intended decision change, uncontrolled context differences or an
uncalibrated negative control.

**Current status.** Retained v1.2 B02 evidence remains failed/inconclusive: the
likelihood-only overlay left impact unsupported, so both positive cases were
unassessable and no complete strict L/I draft existed to compare. The negative
controls remained unchanged. Reference v1.3 is a test-informed correction that
adds the same synthetic impact 3 to both policies while likelihood varies from 6
to 8. The v1.3 rerun completed all four conditions: the positive changed
L6/I3→L8/I3 and calibrated semantic review confirmed both unchanged tag-only
negative controls excluded the synthetic passing rule. This is a bounded pass
for influence and isolation, not production knowledge correctness.

### B03 — Maintenance path

**Requirement.** Demonstrate that general PSV guidance changes through a reviewed
knowledge source/release and activation, not through prompt surgery or
finding-ID code.

**Pass evidence.** Source/release lifecycle checks, explicit edit surface and a
bound active version.

**Limit.** The current repository demonstrates mechanics, not a
domain-owner-approved PSV behavior change.

## 4. Area C — Code-derived urgency

### C01 — Function properties

**Requirement.** Urgency is code-derived for all 100 L/I pairs, remains in 1-10
and is monotone in each input.

**Contract boundary.** The frozen acceptance contract tests range, monotonicity,
corner behavior, provenance and code ownership; it does not select a formula.
The current design response, `ceil(0.7I + 0.3L)`, is documented in `DESIGN.md`
and Document 06 as ordinal candidate policy rather than calibrated risk.

### C02 — Asymmetric corners and alternatives

**Requirement.** Show worked high-L/low-I and low-L/high-I corners and explain why
plain mean, plain maximum and model-authored urgency were rejected.

**Failure.** Merely asserting that the formula is “balanced” without observable
corner behavior.

### C03 — Overrides, precautions and fact states

**Requirement.** Apply supplied overrides only on confirmed facts. Keep
candidate-owned precautionary floors and review policies separately identified.

**Failure.** Converting unknown deviation, capacity or restoration state into a
confirmed trigger, or fabricating an override condition by inflating L/I.

### C04 — Rationale consistency

**Requirement.** The published urgency rationale identifies base inputs,
applicable rule IDs and why the final value changed.

**Limit.** A correct trace proves application consistency, not correctness of the
model-proposed L/I.

## 5. Area D — Limits and deferral

### D01 — Supported uncertainty

**Requirement.** A supportable draft with material uncertainty identifies a
specific check and routes it for human review.

**Failure.** Generic “investigate further,” review without a target, or using
review to excuse unsupported scores.

### D02 — Inability to assess

**Requirement.** If required L/I cannot be justified, fail visibly. Do not assign
midpoint, minimum or placeholder values.

### D03 — Exclusions and authority

**Requirement.** State what the prototype does not do: no live work-order action,
shutdown authority, autonomous web authority or domain certification.

### D04 — Assumptions and AI assistance

**Requirement.** Disclose material assumptions, AI-assisted development,
candidate overrides, test-informed changes and unresolved limits.

## 6. Cross-cutting evidence

### X01 — Decision stability

Two isolated development-partition runs compare:

- L/I/U values;
- urgency band;
- review flag;
- applied rule set; and
- unsupported or forbidden claims.

A band/review flip or new unsupported claim fails or leaves the scenario
unresolved. Numeric drift is never hidden, even when the operational band stays
stable. A supplementary third run cannot rescue a failed pair.

This evaluates observed stability of one configuration, not model determinism or
future reliability.

### X02 — Reproducibility, accounting and delivery

A result must identify code/config/context hashes, provider route, model settings,
assessment time, cache mode, application sends, errors, exposed usage, latency,
cost and output hash. The current contract caps total provider attempts per
finding, including SDK/transport retries, at two. If a route hides those attempts,
the SDK-inclusive attempt result is inconclusive rather than accepted as an
application-send pass. Unknown price also remains unknown.

Passing `eval.validate` proves artifact consistency only. A complete delivery
also requires the generated root `tickets.json`, successful declared route and
applicable semantic evidence.

The current root artifact satisfies the file-presence and deterministic-contract
parts of that statement. It does not satisfy the remaining parts: its assessor
status is `needs_review`, human approval is pending, the receipt is
`acceptance_eligible=false`, and the declared generating workflow hash differs
from current `main`.

## 7. Reviewer and reference policy

The semantic reference and reviewers are AI-assisted and non-blind. Therefore:

- calibrating on seeded contradictions proves only that the reviewer rejected
  those fixtures;
- `needs_review` is not a pass;
- repeat reviewer disagreement makes that dimension inconclusive;
- a second reviewer is sensitivity evidence, not majority-vote truth;
- output-bound quotations and provenance are required; and
- independent human/domain review remains outside the current evidence.

The operational reviewer checklist and verdict boundaries are frozen in
`docs\11_SEMANTIC_REVIEW_PROTOCOL.md`. Ad hoc free-form agent reviews are
sensitivity observations only and cannot establish or overturn the semantic
gate.

Reference expectations may not be changed merely to make an observed failure
pass. Genuine corrections require preserved prior bytes, rationale,
comparability analysis, versioned semantic change and rerun of affected checks.

## 8. Evidence status

| Evidence | What it currently establishes |
|---|---|
| Reference validator | Current spec/artifact integrity; no ticket/model assessment |
| Evaluator unit tests | Assessor software behavior on fixtures |
| Deterministic workflow evidence | D-pass for stated contract, urgency, budget and publication paths |
| Real-model observations | Mixed route/version-specific outcomes, including retained failures |
| AI-only semantic reviews | Provisional judgments, not certification |
| Final acceptance-eligible output | Missing |

Scenario-by-scenario observed status is maintained in
`eval\results\README.md`. The frozen-version reliability method is
`docs\07_VERSION_RELIABILITY_PROTOCOL.md`.

## 9. Controlled layout migration

The pre-rewrite reference-v1.3 working contract was snapshotted at
`docs\original-decision-process\03_EVALUATION_ACCEPTANCE.md` with its exact
pre-rewrite bytes and SHA-256 digest. `eval\spec\acceptance.json` points to that
preserved contract. The committed v1.2 contract remains in Git at revision
`92734d6` with SHA-256
`ed0d6488673615857d47d396f148217e218469d2289704e3410308ea4a662e70`.

Reference v1.3 is a semantic, test-informed B02 correction. Layout revision 2 is
the separate path move into `original-decision-process`; it changes no v1.3
scenario semantics or membership. Historical evidence retains the hashes and
paths recorded at execution time.
