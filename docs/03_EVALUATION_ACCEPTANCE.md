# Acceptance Contract and Evidence Rules

This file explains the acceptance contract for readers. It does not change the
contract. The authoritative machine-readable scenarios are in
[`eval\spec\acceptance.json`](../eval/spec/acceptance.json). That file names the
frozen original decision-process document
[`docs\original-decision-process\03_EVALUATION_ACCEPTANCE.md`](original-decision-process/03_EVALUATION_ACCEPTANCE.md)
by path. The frozen document's SHA-256 file hash is
`ab6cdaaebb84a6ebf17cc9dbc9021ad2d6d9c4b3eb35d19ff5e931ce0210f86f`
and is recorded separately in
[`eval\spec\split.json`](../eval/spec/split.json) and the
[`original-decision-process` manifest](original-decision-process/manifest.json).
This explanation may improve readability. It cannot change those frozen files,
hashes or criteria.

## Abstract

The contract defines checks for structured output, domain knowledge, urgency and
system limits: scenarios A01-D04. X01 checks decision stability. X02 checks
reproduction and cost.

Three shortcuts do not count as success:

- valid JSON does not prove that a ticket's meaning is correct;
- a human-review flag does not make an unsupported score acceptable; and
- evaluator self-tests or agreement between AI reviewers do not prove system
  acceptance.

Some rules are stricter policies chosen for this prototype. Examples are the
two-attempt limit and precautionary review rules and urgency floors (minimum
urgency values). They are labelled as project policy, not requirements from the
brief or rules certified by a domain expert.

Sections 2-6 define the scenarios. Section 7 explains **semantic review**: review
of ticket evidence and meaning. Section 8 summarizes current evidence without
changing the contract. Section 9 explains authorized contract corrections.

## 1. Acceptance model

| Area | Question | Scenario IDs |
|---|---|---|
| A — Structured output | Does the system enforce output rules, recover within limits, cover all findings and handle contradictions? | A01-A04 |
| B — Knowledge | Does approved context reach the model, change behavior as intended and remain editable? | B01-B03 |
| C — Urgency | Does code calculate urgency correctly, including extreme input pairs and rules that depend on facts? | C01-C04 |
| D — Limits | Does the system request human help, fail visibly and leave authority with humans? | D01-D04 |
| X — Cross-cutting | Can we inspect decision stability, identify and repeat a run, and report its cost? | X01-X02 |

Each scenario defines the evidence required and what that evidence can prove.
There is no combined score that substitutes for these separate checks.

Throughout this document, **L**, **I** and **U** mean likelihood, impact and
code-derived urgency. `review_required` marks extra review before a ticket enters
the normal work queue. Every draft still needs ordinary human approval.

A **fixed identity** means the exact code, configuration, prompt, knowledge,
provider/model settings and reviewer configuration used in a comparison. The
**primary reviewer** is the one fixed reviewer configuration allowed to decide
the semantic acceptance check (the **semantic gate**).
A **partition** is the selected development, test or all-21 finding set. Each
finding has a fixed, AI-assisted checklist of expectations, called an **evidence
card**, in
[`eval\data\development.jsonl`](../eval/data/development.jsonl) or
[`eval\data\test.jsonl`](../eval/data/test.jsonl).

## 2. Area A — Structured output and failure

### A01 — Contract and coverage

**Requirement.** Output must contain exactly one correctly identified ticket for
each selected finding. It must follow a **closed schema**: only the allowed
fields and types, valid value ranges and required text limits.

**Pass evidence.** Tests that deliberately change fields to check rejection,
plus a complete generated file linked to its exact input.

**Failure.** Missing, duplicate, extra or mismatched identities; an invalid outer
JSON object; out-of-range values; or extra fields that were not validated.

Passing schema checks does not prove that L/I or planning text is defensible.

### A02 — Recoverable malformed or structural output

**Requirement.** Distinguish unreadable JSON from valid JSON that breaks the
schema. Allow repairs only within the declared limit. Keep every attempt.

**Chosen policy.** At most two total provider attempts per finding, including
SDK/transport retries. These are retries made by the provider library or
connection layer, not just by application code. This limit is stricter than the
brief. It bounds cost and prevents endless retries. A provider route cannot
prove this pass condition unless it exposes or disables hidden retries.

**Failure.** Hidden or unlimited retries, attempt counts that can be reset, or
silent local edits that make an invalid response look valid as received.

### A03 — Exhaustion and publication

**Requirement.** If the system cannot produce a ticket within the attempt budget,
the command must exit with a nonzero status. It must publish no partial batch
and leave any previous output unchanged.

Readers could mistake a partial file for the required complete planning package.

**Failure.** Placeholder scores, omitted findings or a partial file that makes
failure look like completion.

### A04 — Valid structure, wrong meaning

**Requirement.** Code must detect contradictions it can check: invalid identity,
unsupported citations, quotations that do not match, or a score that breaks an
explicit anchor in the scoring guide (**rubric**). Send the remaining judgments
that need interpretation to the fixed semantic reviewer.

**Failure.** Treating “valid JSON” or “review_required=true” as sufficient.

Code cannot prove every engineering judgment. AI review remains provisional.
Human approval is still required.

## 3. Area B — Knowledge and maintainability

### B01 — Context delivery

**Requirement.** Save **provider-bound context**, the context prepared for the
model request. It must show that supplied domain guidance, registry comments and
required related context were sent using the declared configuration.

**Pass evidence.** Context identified by hashes, plus independent checks that the
selected source and input identities match.

Saved context shows what reached the provider. It does not prove that the model
used those inputs to make its decision.

### B02 — Knowledge influence

**Requirement.** Define positive and negative controls before the run
(**preregister** them). The positive control should change; the negative control
should not be affected by the rule. Compare inputs that differ only in one
isolated knowledge change. Label artificial values as synthetic.

**Failure.** The intended decision does not change, other context changes too,
or the negative control has not been calibrated.

Record influence results under `eval\results`. Section 8 summarizes evidence
without changing this requirement. A successful synthetic experiment shows only
limited influence and isolation. It does not prove that production knowledge is
correct.

### B03 — Maintenance path

**Requirement.** Show that general pressure safety valve (PSV) guidance can change
through a reviewed knowledge source, release and activation (approval for use).
Do not implement the change by editing the prompt or adding code for specific
finding IDs.

**Pass evidence.** Checks of the source-to-release process, a clear place to edit
guidance, and the exact identity of the active release.

The repository demonstrates how to maintain knowledge. It does not contain a PSV
behavior change approved by the domain owner.

## 4. Area C — Code-derived urgency

### C01 — Function properties

**Requirement.** Code must calculate urgency for all 100 L/I pairs. Urgency stays
in 1-10 and is **monotone** in each input: increasing L or I must not reduce U.

**Contract boundary.** The frozen contract tests range, monotonicity, extreme
input pairs, calculation records and code ownership. It does not choose a formula.
The current design response, `ceil(0.7I + 0.3L)`, is documented in `DESIGN.md`
and Document 06. It is project policy for ranked priorities, not calibrated risk.

### C02 — Asymmetric corners and alternatives

**Requirement.** Show worked examples for high-L/low-I and low-L/high-I pairs
(the two **corners**). Explain why a plain mean, a plain maximum and
model-chosen urgency were rejected.

**Failure.** Calling the formula “balanced” without showing its corner results.

### C03 — Overrides, precautions and fact states

**Requirement.** Apply supplied overrides only when their facts are confirmed.
Label project-defined precautionary minimum urgency values and review policies
separately.

**Failure.** Treating unknown deviation, capacity or restoration states as
confirmed override conditions, or raising L/I to invent an override condition.

### C04 — Fact assessment before urgency

**Requirement.** Before code applies urgency, the assessed known and unknown
facts must match the source. Missing personnel-on-board, capacity or deviation
data does not prove absence. A reopened valve does not prove that protection
coverage was restored.

The published urgency rationale must name its base inputs, applicable rule IDs
and why the final value changed. A correct calculation record proves that code
applied the rules consistently. It does not prove that the model assessed the
facts correctly.

## 5. Area D — Limits and deferral

### D01 — Supported uncertainty

**Requirement.** A draft with supported scores but important uncertainty must
name a specific check and request human review.

**Failure.** Generic “investigate further,” review with no specific target, or
using review to excuse unsupported scores.

### D02 — Inability to assess

**Requirement.** If required L/I cannot be justified, fail visibly. Do not assign
midpoint, minimum or placeholder values.

### D03 — SCE and local-defect distinctions

**Requirement.** Do not treat every Safety Critical Element (SCE) finding as an
immediate loss of function. Identify the defect mechanism and evidence that
changes the decision. If project policy sends every SCE finding for extra
review, label that policy explicitly. It must not replace consequence assessment.

### D04 — Exclusions, assumptions and AI assistance

**Requirement.** Disclose important assumptions, AI assistance, rejected AI
suggestions, use of exposed evaluation evidence and unresolved limits. Explain
what was deliberately excluded and why: live work-order actions, shutdown
authority, automatic use of web guidance as authority, and domain certification.

## 6. Cross-cutting evidence

### X01 — Decision stability

Compare two isolated runs on the development partition:

- L/I/U values;
- urgency band;
- review flag;
- applied rule set; and
- unsupported or forbidden claims.

A change in urgency band or review flag, or a new unsupported claim, fails the
scenario or leaves it unresolved. Report every numeric change, even if the
scheduling band stays the same. An extra third run cannot rescue a failed pair.

For the semantic comparison, apply section 7 to each output using the development
partition. That is 13 findings across three review dimensions: 39 judgments per
output. This review is an extra protocol extension, not a gate defined before
the study. It can reveal unsupported claims, but cannot establish X01 acceptance
by itself. It is not the all-21 semantic delivery gate.

This checks observed stability for one configuration. It does not prove that
the model always gives the same answer or will be reliable in future.

### X02 — Reproducibility, accounting and delivery

A result must record code, configuration and context hashes; provider route;
model settings; assessment time; cache mode; application sends; errors; exposed
usage; elapsed request time (latency); cost; and output hash.

Report three cost measures separately: measured usage, an API-equivalent estimate
using declared rates, and actual billed or allocated USD. The equivalent estimate
is what the measured tokens would cost at those API rates. It is not the actual
provider bill.

The contract allows at most two total provider attempts per finding, including
SDK/transport retries. If the route hides retries, the total-attempt check is
inconclusive. Counting application sends does not make it pass. If actual
billing cannot be converted to USD, report it as unknown. A separately labelled
equivalent estimate is still valid as an estimate.

Passing `eval.validate` proves only that artifacts are consistent. Complete
delivery also requires generated root `tickets.json`, a successful run through
the declared route and applicable semantic evidence. Read run-level delivery
status in root `README.md` and `eval\results\README.md`. Section 8 is a summary,
not the authoritative current status record.

### Fixed-identity reliability protocol

X01 and X02 measure one fixed system identity. They do not select the best run or
combine reliability into one score. Each dimension supports a different claim:

| Dimension | Evidence | Highest defensible claim |
|---|---|---|
| Deterministic control | Tests of schema, identity, urgency, attempts and publication | Code follows the tested rules |
| Batch execution | Planned completions, repairs, final failures and publication hashes | Observed completion for the declared route |
| Decision stability | L/I/U, bands, review routing, rules and unsupported claims across fixed repeats | Stability in those repeats, not identical answers from the model every time |
| Semantic quality | Review of evidence, planning and uncertainty | Provisional reviewer judgment |
| Usefulness | Spread of urgency, impact and extra-review decisions | Observed differences between tickets, not optimal score calibration |
| Reproduction and cost | Clean source identity, command, hashes, exposed usage, latency and price | Reproduction and accounting only for values that are exposed |

Before measured model calls, fix the exact code, configuration, prompt,
knowledge, activation, provider route, model settings, assessment time and
reviewer identity. Also fix the sample, repeat count, new attempt ledgers
(attempt records) and attempt/cost budget.

Keep every response, repair and final failure. Do not tune between repeats, stop
early when results agree, or add runs to rescue a failed comparison. Extra
all-21 repeats use exposed findings. They are limited diagnostics for that
provider route, not an unseen-data test or a population estimate.

Report raw counts and `pass`, `fail`, `inconclusive` or `not run` for each
dimension. Report each provider route separately. If reviewers disagree on the
same evidence or on a preregistered repeat, the affected dimension is
inconclusive. Do not use majority voting. Hidden retries, unavailable prices and
missing evidence of clean-checkout reproduction stay unknown or inconclusive.
Never report them as zero or pass.

Keep run results and limits under `eval\results`. They do not change this protocol.

## 7. Current semantic reviewer protocol

Semantic review checks one generated output against its declared evidence cards.
It does not redesign tickets, add engineering best practice or look for a new
issue after every run. `eval.assess` checks review structure and quotations
linked to the exact output. It does not generate reviewer judgments.

The workflow is:

1. generate a checklist linked to the exact ticket file and partition;
2. record one reviewer configuration and calibrate it on test probes with
   deliberately added contradictions;
3. have that reviewer complete grounding, planning and uncertainty judgments;
4. submit the completed review against the same artifact and partition; and
5. retain the first complete result, including failures and `needs_review`.

The procedure below explains the review. Binding identities and criteria remain
under `eval\spec`. A checklist not linked to the output cannot establish the
gate. Neither can an unplanned second review, reviewer voting or repeated review
until a pass appears. These methods also cannot overturn the gate.

### 7.1 Reviewer and reference authority

AI helped create the reference and reviews, and the cases were already exposed.
Therefore:

- calibration on deliberate contradictions proves only that the reviewer rejected
  those test fixtures;
- `needs_review` is not a pass;
- repeat disagreement makes the disputed dimension inconclusive;
- a second reviewer shows whether judgments depend on reviewer choice; it is not
  a vote;
- exact output-linked quotations and records of review origin are required; and
- independent human/domain review remains outside the current evidence.

Do not change reference expectations just to turn a failure into a pass. For a
genuine correction, preserve the replaced bytes, explain the reason and effect
on comparison with earlier results, identify the change in meaning, and rerun
affected checks.

### 7.2 Required review inputs

Run the commands below from the repository root with Python 3.11 or later.
Values in angle brackets are placeholders and must be replaced with the selected
partition and repository-relative artifact paths.

Before reviewing, record:

- exact ticket-file SHA-256;
- reference version/identity and partition;
- reviewer provider, model, reasoning setting and prompt SHA-256;
- calibration result for `eval\spec\probes.json`; and
- the generic checklist generated by:

```powershell
python -B -m eval.assess --partition all --checklist
```

The generic checklist has `output_sha256=null` and is guidance only. Bind the
review to the actual artifact and selected partition with:

```powershell
python -B -m eval.assess --partition <partition> --tickets <tickets.json>
```

Use `all` for the 21-ticket delivery gate and `development` for an X01 artifact.
The resulting `review_template` is the review input. It contains the exact ticket
SHA-256. Use the same partition when submitting the completed review. Before
reviewing real output, test that same reviewer configuration against the probes
with deliberately added contradictions:

```powershell
python -B -m eval.assess --partition development `
  --calibration-reviews <calibration-reviews.json>
```

The reviewer may use only supplied source records, domain knowledge and the
unchanged expectation fields in the output-linked template. Production prompts
and generation context must never receive evidence cards or expected answers.

After the primary reviewer completes the output-linked template, produce the
semantic result using the same partition and ticket file:

```powershell
python -B -m eval.assess --partition <partition> `
  --tickets <tickets.json> --reviews <primary-reviews.json>
```

The assessor checks review structure, the ticket hash and exact output-linked
quotations. Its `overall` result means:

- `fail`: the semantic gate fails; exit code 1 when a JSON report is produced;
- `needs_review`: the gate remains pending; exit code 2;
- `provisional_pass`: an AI-only provisional pass; exit code 0.

Exit 1 without a JSON report, with a `Ticket assessment FAILED` diagnostic,
means the input or its link to the review is invalid. It is not a verdict on
ticket meaning.

### 7.3 Dimension checklist

#### Grounding

Check only `observed_facts`, `required_evidence`, `expected_behavior` and
`forbidden_claims`.

- **fail:** a direct source contradiction, forbidden claim, invented important
  fact, missing important required evidence, or violation of an applicable
  expected behavior;
- **needs_review:** the evidence cannot resolve a choice between nearby scores
  or the scope of a consequence;
- **pass:** every applicable expectation is met and the judgment is defensible
  within the supplied evidence, even if another engineering choice could also
  be reasonable.

Do not fail because many scores are similar, because of style preferences, or
because a more conservative option exists but the card does not require it.

#### Planning

Check only the card's `action_constraints`. Every listed constraint applies by
default. If it is genuinely unclear whether one applies, use `needs_review`.
Never silently skip it and pass.

- **fail:** a required activity or condition for closing the issue is missing,
  or the action directs a forbidden/unsafe operation;
- **needs_review:** the requirement may be covered but the wording is genuinely
  ambiguous;
- **pass:** the action covers the substance of every explicit constraint.

Do not add preferred maintenance steps, authorities, tests, thresholds or
wording that the card and source do not require. Short wording or sentence
fragments are not failures if the required activity is clear.

#### Uncertainty

Check only the card's `unknowns`, `review_required` and `review_reason`. Every
listed unknown applies by default. If it is unclear whether an unknown applies
or matters to the decision, use `needs_review`. Never silently skip it and pass.

- **fail:** a listed unknown is presented as known, a confirmed fact is treated
  as absent, or a listed unknown is omitted without a specific way to check it;
- **needs_review:** supplied evidence cannot show whether the uncertainty matters
  or changes the decision;
- **pass:** relevant uncertainty is kept visible and directed to review without
  invented facts.

Do not require missing data or generic engineering unknowns that are not listed
in the card.

### 7.4 Stability and rerun rules

The primary reviewer must:

1. pass both seeded contradiction probes before real-output review;
2. review each selected finding across all three dimensions exactly once: 63
   finding/dimension pairs for the all-21 delivery gate, or 39 pairs for a declared
   development-partition X01 review;
3. quote the exact ticket field supporting every pass or fail;
4. use `needs_review` rather than guessing;
5. reject any proposed issue that does not match one frozen expectation;
   and
6. retain the first complete result, including failures.

Do not rerun just to get a better count. A changed reviewer implementation is a
new configuration. Calibrate it again, keep both configuration records and
disclose the change.

A rerun requires a changed ticket file, a changed approved reference or a
preregistered reliability repeat. If a preregistered repeat disagrees with the
first review, that dimension is inconclusive. The repeat is not another chance
to obtain a pass.

### 7.5 Gate interpretation

| Primary result | Semantic-gate interpretation |
|---|---|
| Any `fail` | Fail |
| No fail and one or more `needs_review` | Pending |
| All 63 pass after calibration | Provisional AI-only pass for the all-21 delivery gate |
| All 39 pass for a development-partition X01 review | Extra X01 evidence only; not an acceptance gate by itself |
| Primary/secondary or preregistered-repeat disagreement | Keep both results. Disputed dimensions are inconclusive. The gate stays pending unless a primary fail already makes it fail |

Even 63/63 does not establish domain certification, human approval or full A-D
system acceptance.

## 8. Non-authoritative current status summary

This table summarizes current evidence. It does not redefine gates. If it
differs from the scenario-by-scenario status file, use that status file. Root
`README.md` and [`eval\results\README.md`](../eval/results/README.md) record
run-level status.

The frozen machine-readable contract is
[`eval\spec\acceptance.json`](../eval/spec/acceptance.json). Current evidence
status for each scenario is in
[`eval\results\acceptance-status.md`](../eval/results/acceptance-status.md).

| Contract area | Current evidence | Interpretation and remaining limit |
|---|---|---|
| A — Structure and failure | Tests cover unreadable output, limited repair, exhausted attempts, complete coverage and keeping old output on failure. The experimental 21-ticket output has a verified publication receipt. Root `tickets.json` meets the structural contract and is an exact copy, verified by SHA-256, after separate promotion. | **Mixed: A01 and A03 are Supported; A02 and A04 are Partial.** Hidden provider retries cannot be observed. Semantic review still has limits. The root copy has no separate workflow receipt. Structural validity does not prove ticket quality. |
| B — Knowledge | Source delivery and knowledge maintenance were exercised. One synthetic experiment showed limited influence while keeping the negative control outside the rule. Every retained development provider input also contained all eight test finding records. | **Partially supported overall, with B01 Not met.** Wider use of knowledge and domain correctness are unproven. The development/test split does not show inference with test cases isolated from development context. |
| C — Urgency | Tests cover code ownership, range, monotonicity, corners and escalation based on fact states. | **Mostly supported: C01-C03 are Supported; C04 is Partial.** Numeric calibration does not establish true operational risk. Facts have AI-only review, not domain-expert review. |
| D — Limits and deferral | Unsupported scores cause visible failure. Uncertainty and extra review are explicit. | **Mixed: D02 and D04 are Supported; D01 and D03 are Partial.** Exposed test evidence influenced extra-review routing and local-defect distinctions. The project chose routing thresholds; they remain uncalibrated. |
| X01 — Stability | Two development runs kept all 13 urgency bands and review flags unchanged. Two numeric scores and one rule trace changed, but scheduling and review decisions did not. The saved run therefore records operational `x01.status: pass`. However, both runs sent all eight TEST finding records to the provider. The runtime did not expose the semantic reviewer's model, settings or prompt identity required by §7.2. Development evidence also influenced configuration selection. | **Inconclusive for formal acceptance.** The pair shows stable scheduling and review decisions. Context leakage, missing reviewer identity and non-independent configuration selection prevent a protocol-level pass. It is useful repeat-run evidence, not proof that the model always behaves identically. |
| X02 — Reproducibility | Saved evidence includes hashes, configurations, latency, application sends, publication records, exact producing code bytes and measured token usage. The declared public-rate calculation gives US$2.350286 for the delivery. | **Partial.** The API-equivalent estimate can be reproduced. Clean-checkout reproduction, hidden provider attempts and actual Copilot billing allocation remain unresolved. |
| Semantic reviewer protocol | The saved review recorded 63 passing dimensions after calibration on two deliberate contradiction fixtures. The runtime did not expose every reviewer identity and prompt field required by §7.2. The required `needs_review` behavior for an unresolved nearby-score choice was not tested. Configuration selection was not independent of the evidence. | **Protocol deviation; A04 remains Partial.** This is an AI-only regression observation, not acceptance that fully follows the protocol. |

## 9. Controlled change and authority

[`eval\spec\acceptance.json`](../eval/spec/acceptance.json) is the
machine-readable scenario authority. Its
`design_contract` field names the frozen design-contract document. That
document's SHA-256 is recorded separately in `eval\spec\split.json` and the preserved
`original-decision-process` manifest, as described in the opening paragraph.
The explanations and review method above do not replace specifications or results.

For a genuine correction backed by source evidence, an evaluator bug, or an
authorized requirement change: keep replaced bytes and failures, explain how
comparison with earlier results is affected, update only the intended identities
for changes in meaning, and rerun affected checks.

For navigation:

- frozen scenario authority:
  [`eval\spec\acceptance.json`](../eval/spec/acceptance.json);
- scenario-by-scenario current status:
  [`eval\results\acceptance-status.md`](../eval/results/acceptance-status.md);
- observed evidence and limitations:
  [`eval\results\README.md`](../eval/results/README.md); and
- current delivery and commands: [root `README.md`](../README.md).
