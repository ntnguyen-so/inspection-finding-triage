# Acceptance Contract and Evidence Rules

This file is the reader-oriented explanation of the acceptance contract. The
machine-readable scenario authority is
[`eval\spec\acceptance.json`](../eval/spec/acceptance.json), which binds the
scenario definitions to the frozen original decision-process document
[`docs\original-decision-process\03_EVALUATION_ACCEPTANCE.md`](original-decision-process/03_EVALUATION_ACCEPTANCE.md)
by path. Its SHA-256 is
`ab6cdaaebb84a6ebf17cc9dbc9021ad2d6d9c4b3eb35d19ff5e931ce0210f86f`
and is pinned separately by
[`eval\spec\split.json`](../eval/spec/split.json) and the
[`original-decision-process` manifest](original-decision-process/manifest.json).
This explanation can improve readability but cannot change those frozen
identities or criteria.

## Abstract

The contract covers structured output, domain knowledge, urgency and system
limits. It converts those concerns into observable scenarios A01-D04, then adds
X01 decision stability and X02 reproducibility/cost.

The contract deliberately prevents three success-shaped shortcuts:

- valid JSON is not treated as semantic correctness;
- a human-review flag cannot legitimize an unsupported score; and
- evaluator self-tests or AI reviewer agreement are not treated as system
  acceptance.

Some rules are stricter project-defined prototype policies, including the
two-attempt budget and precautionary review/urgency floors. They are labelled as
such rather than attributed to the brief or a domain expert.

Sections 2-6 define the scenarios, section 7 explains how semantic review is
performed, section 8 summarizes current evidence without changing the contract,
and section 9 defines how an authorized contract correction is handled.

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

Throughout this document, **L**, **I** and **U** mean likelihood, impact and
code-derived urgency. `review_required` is an exceptional prequeue-review flag;
every draft still requires ordinary human approval. A **fixed identity** means
the exact code, configuration, prompt, knowledge, provider/model settings and
reviewer configuration being compared. The **primary reviewer** is the one
frozen reviewer configuration allowed to determine the semantic gate.
A **partition** is the selected development, test or all-21 finding set. Each
finding has a frozen, AI-assisted expectation record, called an **evidence
card**, in
[`eval\data\development.jsonl`](../eval/data/development.jsonl) or
[`eval\data\test.jsonl`](../eval/data/test.jsonl).

## 2. Area A — Structured output and failure

### A01 — Contract and coverage

**Requirement.** Output must contain exactly one correctly identified ticket for
each selected finding, with closed schema, valid ranges and text limits.

**Pass evidence.** Executable mutation tests plus a complete generated artifact
bound to its input.

**Failure.** Missing, duplicate, extra or mismatched identities; invalid wrapper;
out-of-range values; unvalidated extra fields.

Passing the schema does not establish defensible L/I or planning text.

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

A partial file could masquerade as the required complete planning package.

**Failure.** Placeholder scores, omitted findings or a partial file that makes
failure look like completion.

### A04 — Valid structure, wrong meaning

**Requirement.** Detect machine-checkable contradictions such as invalid
identity, unsupported citation, inexact quotation or a score that violates an
explicit rubric anchor. Submit coherent remaining semantics to frozen review.

**Failure.** Treating “valid JSON” or “review_required=true” as sufficient.

These code checks cannot prove every engineering judgment. AI review remains
provisional and human approval remains mandatory.

## 3. Area B — Knowledge and maintainability

### B01 — Context delivery

**Requirement.** Capture provider-bound evidence that supplied domain guidance,
registry comments and required related context were sent under the declared
configuration.

**Pass evidence.** Hash-bound context and independent validation of selected
source/input identities.

Captured delivery shows what reached the provider, not whether the model used it
causally.

### B02 — Knowledge influence

**Requirement.** Compare preregistered positive and negative controls that differ
only in an isolated knowledge input, with artificial values labelled synthetic.

**Failure.** No intended decision change, uncontrolled context differences or an
uncalibrated negative control.

Run-level influence status belongs in `eval\results`; §8 assesses only whether
this requirement exposed its intended failure modes. Even a passing synthetic
intervention establishes only bounded influence and isolation, not production
knowledge correctness.

### B03 — Maintenance path

**Requirement.** Demonstrate that general PSV guidance changes through a reviewed
knowledge source/release and activation, not through prompt surgery or
finding-ID code.

**Pass evidence.** Source/release lifecycle checks, explicit edit surface and a
bound active release identity.

The current repository demonstrates the maintenance mechanics; it does not
contain a domain-owner-approved PSV behavior change.

## 4. Area C — Code-derived urgency

### C01 — Function properties

**Requirement.** Urgency is code-derived for all 100 L/I pairs, remains in 1-10
and is monotone in each input.

**Contract boundary.** The frozen acceptance contract tests range, monotonicity,
corner behavior, provenance and code ownership; it does not select a formula.
The current design response, `ceil(0.7I + 0.3L)`, is documented in `DESIGN.md`
and Document 06 as ordinal project policy rather than calibrated risk.

### C02 — Asymmetric corners and alternatives

**Requirement.** Show worked high-L/low-I and low-L/high-I corners and explain why
plain mean, plain maximum and model-authored urgency were rejected.

**Failure.** Merely asserting that the formula is “balanced” without observable
corner behavior.

### C03 — Overrides, precautions and fact states

**Requirement.** Apply supplied overrides only on confirmed facts. Keep
project-defined precautionary floors and review policies separately identified.

**Failure.** Converting unknown deviation, capacity or restoration state into a
confirmed trigger, or fabricating an override condition by inflating L/I.

### C04 — Fact assessment before urgency

**Requirement.** Extracted known and unknown facts must match the source before
code applies urgency. Missing personnel-on-board, capacity or deviation data is
not confirmed absence; a reopened valve is not verified restored coverage.

The published urgency rationale must still identify its base inputs, applicable
rule IDs and why the final value changed. A correct trace proves application
consistency, not correct upstream fact assessment.

## 5. Area D — Limits and deferral

### D01 — Supported uncertainty

**Requirement.** A supportable draft with material uncertainty identifies a
specific check and routes it for human review.

**Failure.** Generic “investigate further,” review without a target, or using
review to excuse unsupported scores.

### D02 — Inability to assess

**Requirement.** If required L/I cannot be justified, fail visibly. Do not assign
midpoint, minimum or placeholder values.

### D03 — SCE and local-defect distinctions

**Requirement.** Do not label every Safety Critical Element finding as an
immediate functional failure. Distinguish the observed defect mechanism and
decision-changing evidence; any all-SCE review policy must remain explicit and
must not replace consequence assessment.

### D04 — Exclusions, assumptions and AI assistance

**Requirement.** Disclose material assumptions, AI-assisted development,
where AI suggestions were overridden, use of exposed evaluation evidence and
unresolved limits. State deliberate exclusions with reasons: no live work-order
action, shutdown authority, autonomous web authority or domain certification.

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

For the semantic part of this comparison, apply §7 to each artifact with the
development partition: 13 findings across three dimensions, or 39 judgments per
artifact. This development-partition semantic review is a supplementary
protocol extension rather than a preregistered gate. It can expose unsupported
claims but cannot by itself establish X01 acceptance. It is not the all-21
semantic delivery gate.

This evaluates observed stability of one configuration, not model determinism or
future reliability.

### X02 — Reproducibility, accounting and delivery

A result must identify code/config/context hashes, provider route, model settings,
assessment time, cache mode, application sends, errors, exposed usage, latency,
cost and output hash. Cost reporting separates measured usage, a reproducible
API-equivalent estimate under declared rates, and the provider's actual billed
or allocated USD. The current contract caps total provider attempts per finding,
including SDK/transport retries, at two. If a route hides those attempts, the
SDK-inclusive attempt result is inconclusive rather than accepted as an
application-send pass. An unavailable provider billing conversion remains
unknown; it does not erase a separately labelled equivalent estimate.

Passing `eval.validate` proves artifact consistency only. A complete delivery
also requires the generated root `tickets.json`, successful declared route and
applicable semantic evidence. Run-level delivery status belongs in root
`README.md` and `eval\results\README.md`; §8 assesses the contract design rather
than serving as a current status source.

### Fixed-identity reliability protocol

X01 and X02 measure one fixed system identity; they do not select a favorable
run or produce a composite reliability score. Reliability remains separated
into dimensions because each supports a different claim:

| Dimension | Evidence | Highest defensible claim |
|---|---|---|
| Deterministic control | Schema, identity, urgency, attempt and publication tests | Tested control behavior |
| Batch execution | Planned completions, repairs, terminal failures and publication hashes | Observed completion for the declared route |
| Decision stability | L/I/U, bands, review routing, rules and unsupported claims across fixed repeats | Stability of those repeats, not model determinism |
| Semantic quality | Grounding, planning and uncertainty review | Provisional reviewer judgment |
| Usefulness | Urgency, impact and exceptional-review distributions | Observed discrimination, not optimal calibration |
| Reproduction and cost | Clean identity, command, hashes, exposed usage, latency and price | Reproduction/accounting for exposed values only |

Before measured inference, freeze the exact code, configuration, prompt,
knowledge, activation, provider route, model settings, assessment time and
reviewer identity. Fix the sample, repeat count, fresh ledgers and attempt/cost
budget. Retain every response, repair and terminal failure; do not tune between
repeats, stop early after agreement or add runs to rescue a failed comparison.
Supplementary all-21 repeats use already exposed findings and remain
route-specific bounded diagnostics, not a held-out test or population estimate.

Report raw counts and `pass`, `fail`, `inconclusive` or `not run` for each
dimension. Provider routes are separate observations. Reviewer disagreement on
identical or preregistered repeat evidence makes the affected dimension
inconclusive rather than inviting majority voting. Hidden retries, unavailable
prices and missing clean-checkout provenance remain unknown or inconclusive,
never zero or pass.

Run results and limitations are observations under `eval\results`; they do not
alter this protocol.

## 7. Current semantic reviewer protocol

Semantic review checks one generated artifact against the declared evidence
cards. It does not redesign the ticket, invent engineering best practice or
search for a new issue after every run. `eval.assess` validates review structure
and output-bound quotations; it does not generate reviewer judgments.

The workflow is:

1. generate a checklist bound to the exact ticket file and partition;
2. record and calibrate one reviewer configuration on the seeded probes;
3. have that reviewer complete grounding, planning and uncertainty judgments;
4. submit the completed review against the same artifact and partition; and
5. retain the first complete result, including failures and `needs_review`.

The semantic-review procedure below is explanatory; binding acceptance
identities and criteria remain under `eval\spec`. Unbound checklists, ad hoc
cross-review, reviewer voting and repeated review until green cannot establish
or overturn the gate.

### 7.1 Reviewer and reference authority

The semantic reference and reviewers are AI-assisted and non-blind. Therefore:

- seeded calibration proves only that the reviewer rejected those fixtures;
- `needs_review` is not a pass;
- repeat disagreement makes the disputed dimension inconclusive;
- a secondary reviewer is sensitivity evidence, not a majority vote;
- output-bound quotations and provenance are required; and
- independent human/domain review remains outside the current evidence.

Reference expectations may not be changed merely to make an observed failure
pass. A genuine correction requires preserved replaced bytes, rationale,
comparability analysis, explicit semantic change and rerun of affected checks.

### 7.2 Required review inputs

Run the commands below from the repository root with Python 3.11 or later.
Values in angle brackets are placeholders and must be replaced with the selected
partition and repository-relative artifact paths.

Before reviewing, record:

- exact ticket-file SHA-256;
- reference identity and partition;
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
The resulting `review_template` contains the exact ticket SHA-256 and is the
review input. Use the same partition again when submitting the completed review.
Before reviewing real output, test the same reviewer configuration against the
seeded probes:

```powershell
python -B -m eval.assess --partition development `
  --calibration-reviews <calibration-reviews.json>
```

The reviewer may use only supplied source records, domain knowledge and the
unchanged expectation fields embedded in the artifact-bound template.
Production prompts and generation context must never consume evidence cards or
expected answers.

After the primary reviewer completes the artifact-bound template, produce the
semantic result with the same partition and ticket artifact:

```powershell
python -B -m eval.assess --partition <partition> `
  --tickets <tickets.json> --reviews <primary-reviews.json>
```

The assessor validates review structure, ticket hash and output-bound quotations.
Its `overall` values map to the gate as follows: `fail` fails, `needs_review`
remains pending and `provisional_pass` is an AI-only provisional pass. When a
JSON report is produced, exit codes are 1, 2 and 0 respectively. Exit 1 with no
JSON report and a `Ticket assessment FAILED` diagnostic means the input or review
binding is invalid; it is not a semantic-gate verdict.

### 7.3 Dimension checklist

#### Grounding

Check only `observed_facts`, `required_evidence`, `expected_behavior` and
`forbidden_claims`.

- **fail:** direct source contradiction, forbidden claim, fabricated material
  fact, materially absent required evidence or violation of an applicable
  expected behavior;
- **needs_review:** adjacent score or consequence-scope judgment that the
  supplied evidence cannot resolve;
- **pass:** every applicable expectation is met and the judgment is defensible
  within the supplied evidence, even if another engineering choice could also
  be reasonable.

Do not fail for score concentration, stylistic preference or a more conservative
alternative that the card does not require.

#### Planning

Check only the card's `action_constraints`. Every listed constraint applies by
default. If applicability is genuinely disputed, use `needs_review`; never
silently exclude the item and pass.

- **fail:** a listed required activity or closure condition is absent, or the
  action directs a forbidden/unsafe operation;
- **needs_review:** the requirement may be covered but the wording is genuinely
  ambiguous;
- **pass:** every explicit constraint is materially covered.

Do not add preferred maintenance steps, authorities, tests, thresholds or
wording that the card and source do not require. Concision and telegraphic
phrasing are not failures when the required activity remains clear.

#### Uncertainty

Check only the card's `unknowns`, `review_required` and `review_reason`. Every
listed unknown applies by default. If applicability or materiality is disputed,
use `needs_review`; never silently exclude it and pass.

- **fail:** a listed unknown is asserted as known, a confirmed fact is treated
  as absent, or a listed unknown is omitted without a concrete verification
  route;
- **needs_review:** the materiality or decision effect cannot be resolved from
  supplied evidence;
- **pass:** relevant uncertainty is preserved and routed without fabrication.

Do not require missing data or generic engineering unknowns that are not listed
in the card.

### 7.4 Stability and rerun rules

The primary reviewer must:

1. pass both seeded contradiction probes before real-output review;
2. review each selected finding across all three dimensions exactly once: 63
   pairs for the all-21 delivery gate, or 39 pairs for a declared
   development-partition X01 review;
3. quote the exact ticket field supporting every pass or fail;
4. use `needs_review` rather than guessing;
5. reject any proposed issue that cannot be mapped to one frozen expectation;
   and
6. retain the first complete result, including failures.

No rerun is allowed merely to obtain a better count. A changed reviewer
implementation is a new reviewer configuration: it must be calibrated again,
both configurations remain recorded and the change must be disclosed. A rerun
requires a changed ticket artifact, a changed approved reference or a
preregistered reliability repeat. A preregistered repeat that disagrees with the
first review makes that dimension inconclusive; it is not a green-seeking retry.

### 7.5 Gate interpretation

| Primary result | Semantic-gate interpretation |
|---|---|
| Any `fail` | Fail |
| No fail and one or more `needs_review` | Pending |
| All 63 pass after calibration | Provisional AI-only pass for the all-21 delivery gate |
| All 39 pass for a development-partition X01 review | Supplementary X01 evidence only; not a standalone acceptance gate |
| Primary/secondary or preregistered-repeat disagreement | Preserve both; disputed dimensions remain inconclusive and the gate stays pending unless a primary fail already fails it |

Even 63/63 is not domain certification, human approval or full A-D system
acceptance.

## 8. Non-authoritative current status summary

This non-authoritative assessment summarizes current evidence but does not
redefine gates. If it differs from the scenario-by-scenario status file, that
file governs. Run-level authority remains in root `README.md` and
[`eval\results\README.md`](../eval/results/README.md). The frozen,
machine-readable scenario contract is
[`eval\spec\acceptance.json`](../eval/spec/acceptance.json), and its current
scenario-by-scenario evidence status is
[`eval\results\acceptance-status.md`](../eval/results/acceptance-status.md).

| Contract area | Current evidence | Interpretation and remaining limit |
|---|---|---|
| A — Structure and failure | Current tests exercise malformed output, bounded repair, exhaustion, complete coverage and publication rollback. The experimental 21-ticket output has a verified publication receipt; root `tickets.json` is contract-valid and byte-identical by SHA-256 after separate promotion. | **Mixed: A01 and A03 are Supported; A02 and A04 are Partial.** Hidden provider retries remain unobservable, semantic-review limitations remain, the root copy has no separate workflow receipt, and contract validity does not establish semantic quality. |
| B — Knowledge | Source delivery and maintenance mechanics were exercised; one synthetic intervention showed bounded influence and negative-control isolation. However, every retained development provider input contained all eight test finding records. | **Partially supported overall, with B01 Not met.** Broad causal use and domain correctness remain unproven, and the development/test partition does not provide case-isolated inference evidence. |
| C — Urgency | Code ownership, range, monotonicity, corners and fact-sensitive escalation are tested. | **Mostly supported: C01-C03 are Supported; C04 is Partial.** Numeric calibration is not operational risk truth, and current fact assessment has AI-only rather than domain-expert review. |
| D — Limits and deferral | Unsupported scores fail visibly; uncertainty and exceptional review are explicit. | **Mixed: D02 and D04 are Supported; D01 and D03 are Partial.** The exceptional routes and local-defect distinctions are test-informed, while routing thresholds remain project-defined and uncalibrated. |
| X01 — Stability | Two development runs kept all 13 urgency bands and review flags unchanged. Two numeric scores and one rule trace differed without changing a scheduling or review decision, so the retained run records an operational `x01.status: pass`. However, those runs sent all eight TEST finding records in provider context, the runtime did not expose the semantic reviewer's model, settings or prompt identity required by §7.2, and the configuration was selected using development evidence. | **Inconclusive for formal acceptance.** The observed pair supports stable operational decisions, but context leakage, missing reviewer identity and non-independent configuration selection prevent a protocol-level pass. Treat it as useful repeat-run evidence, not proof of deterministic model behavior. |
| X02 — Reproducibility | Hashes, configs, latency, application sends, publication evidence, exact producer bytes and measured token usage are retained. Applying the declared public-rate convention gives US$2.350286 for the retained delivery. | **Partial.** The API-equivalent estimate is reproducible; clean-checkout reproduction, hidden provider attempts and the actual Copilot billing allocation remain unresolved. |
| Semantic reviewer protocol | The retained review recorded 63 passing dimensions after calibration on two seeded contradiction fixtures, but the runtime did not expose every reviewer identity and prompt field required by §7.2. The required unresolved adjacent-score `needs_review` behavior was not exercised, and the evidence is not independent of configuration selection. | **Protocol deviation; A04 remains Partial.** Treat the result as an AI-only regression observation, not fully protocol-conformant acceptance. |

## 9. Controlled change and authority

[`eval\spec\acceptance.json`](../eval/spec/acceptance.json) is the
machine-readable scenario authority. Its
`design_contract` field names the frozen design-contract document. Its SHA-256
is pinned separately by `eval\spec\split.json` and the preserved
`original-decision-process` manifest, as described in the opening paragraph.
The rationale and review method above do not overwrite executable
specifications or results.

A genuine source-backed correction, grader bug or authorized requirement change
must preserve replaced bytes and failures, state comparability impact, update
only intentional semantic identities and rerun affected checks.

For navigation:

- frozen scenario authority:
  [`eval\spec\acceptance.json`](../eval/spec/acceptance.json);
- scenario-by-scenario current status:
  [`eval\results\acceptance-status.md`](../eval/results/acceptance-status.md);
- observed evidence and limitations:
  [`eval\results\README.md`](../eval/results/README.md); and
- current delivery and commands: [root `README.md`](../README.md).
