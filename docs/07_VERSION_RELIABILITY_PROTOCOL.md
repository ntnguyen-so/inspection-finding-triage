# Reliability of a Frozen Triage Version

> **Study status:** three controlled v8 observations completed; the formal
> clean-freeze/reproducibility gate remains **inconclusive**.

## Abstract

This document defines how to evaluate the reliability of one fixed version of
the triage system. The Candidate Brief does not ask for a single reliability
score. It asks for structured failure handling, defensible ticket quality,
human deferral, reproducible execution and low cost. I interpret those
requirements as a need to show that one named version behaves predictably enough
to produce reviewable drafts without hiding model variance.

The study therefore answers six questions separately: deterministic control,
batch completion, decision stability, semantic quality, usefulness, and
reproducibility/cost. No composite score is used. Code and
configuration are held fixed during inference; every run is retained; no tuning
is allowed between repeats. Version 8 supplies a hash-pinned dirty-worktree
observation, not a clean-checkout reliability certification.

## 1. Why this study exists

The operational goal is not to make an LLM deterministic. It is to produce draft
tickets that an integrity engineer can understand and approve, while ensuring
that invalid or unsupported output cannot look like success.

The reliability question is an **author interpretation**, not language supplied
by Falkor. It follows from four expectations in the Candidate Brief:

- section 5 requires system-generated output, one end-to-end command and
  reproducible cost;
- section 6A asks what happens after malformed, structurally invalid,
  semantically wrong or unproducible output;
- section 6D requires explicit deferral to a human; and
- section 8 assesses defensible scores, grounded rationales and system design.

The repository develops that interpretation through dependent stages:

```text
Document 01: extract requirements and domain risks
    -> Document 02: define data, context, split and evidence boundaries
    -> Document 03: preregister A-D plus X01 stability and X02 reproducibility
    -> Documents 04-06: implement the provider, knowledge and workflow identities
    -> Document 07: measure one implemented, frozen version without tuning it
```

Document 07 does not replace the earlier contracts. It operationalizes them for
a named version and makes any additional experiment explicit.

**Rejected alternative.** A single delivery run plus unit tests could be a lucky
model outcome. It cannot show whether decisions, repairs or review routing remain
stable. The additional study therefore reuses existing tooling and is bounded in
advance. For the planned v8 Copilot observation the ceiling is 126 application
sends; hidden transport attempts and monetary cost remain unknown.

## 2. Research questions

Reliability is not one number. Each question has a different unit of evidence
and supports a different claim.

| Question | Why it matters | Source | Highest claim allowed |
|---|---|---|---|
| **RQ1 — Does deterministic control work?** | Schema, identity, urgency arithmetic, attempts and publication must not depend on model judgment. | Brief §6A/§6C; A01-A03; C01-C03 | Control behavior passed its stated tests |
| **RQ2 — Does a batch complete predictably?** | A system that often exhausts retries cannot reliably produce the required 21 drafts. | Brief §5/§7; A02-A03; X02 | Observed completion and failure counts for this route |
| **RQ3 — Are operational decisions stable?** | Wording may vary, but urgency band, review routing and unsupported claims must not change silently. | Document 02 §6; Document 03 X01 | Stability of the preregistered runs, not model determinism |
| **RQ4 — Are tickets semantically defensible?** | Valid JSON can still contain unsupported scores, facts or actions. | Brief §3/§8.3; Document 03 §4 | Provisional reviewer judgment, not domain certification |
| **RQ5 — Is the output useful?** | A stable system that marks everything urgent and review-required provides little prioritization. | Brief §9; X01 score-distribution check | Observed discrimination, not optimal calibration |
| **RQ6 — Can the observation be reproduced at known cost?** | A reviewer must be able to identify what ran and what it consumed. | Brief §5; X02 | Reproduction/accounting for exposed values only |

Human approval is a boundary, not a research question. No automated result
authorizes maintenance or proves that a ticket is operationally correct.

## 3. Method and rationale

### Decision 1 — Measure a frozen identity, not a version label

**Decision.** Before the first measured call, record a clean commit, hashes for
runtime code, prompts, knowledge, activation, evaluator and reviewer instructions,
plus provider route, model settings, assessment time, cache mode, fresh attempt
ledger and cost/request budget.

**Rationale.** A repeat is interpretable only if the system being repeated is the
same. A directory called `v8` is not sufficient evidence.

**Rejected alternative.** Hashing selected files in a dirty worktree allows
unrecorded dependencies and cannot establish clean-checkout reproduction.

**Source.** X02 and the provenance rules in Documents 02 and 03.

### Decision 2 — Keep reliability dimensions separate

**Decision.** Report RQ1-RQ6 independently using raw counts and
`pass`, `fail`, `inconclusive` or `not run`.

**Rationale.** Contract validity, semantic quality and usefulness answer
different questions. Averaging them could hide a semantic failure behind green
unit tests.

**Rejected alternative.** A weighted reliability score looks precise but has no
source-backed weights and would make reviewer judgment appear quantitative.

**Source.** Document 02 reporting policy and Document 03 A-D/X gates.

### Decision 3 — Scope every result to its provider route

**Decision.** Provider route is part of the frozen identity.

**Rationale.** Copilot and strict Azure expose different retry, cost and control
information. Copilot was economical for the candidate's development because the
models were included in an existing CLI subscription, but the subscription does
not expose per-run USD allocation or hidden attempts. Stability or low marginal
cash spend on that route does not establish delivery reliability or reproducible
cost on another.

**Rejected alternative.** Treating model names as interchangeable ignores
provider behavior and unknown transport attempts.

**Source.** Brief §5 cost/reproduction requirement and X02.

### Decision 4 — Separate X01 from supplementary all-21 observation

**Decision.** X01 uses exactly two isolated development-partition runs. A third
development run may be preregistered as supplementary evidence and cannot rescue
an X01 failure. A three-batch all-21 experiment is a separate, route-specific
observation.

**Rationale.** X01 was designed to compare decisions without repeatedly sampling
until two outputs agree. All-21 runs answer a broader execution question but
reuse previously exposed test findings.

**Rejected alternative.** Calling repeated all-21 runs a held-out test would hide
prior exposure and violate the test-once disclosure.

**Source.** Document 02 split/isolation rules; Document 03 X01; AGENTS phase gates.

### Decision 5 — Fix the sample and prohibit tuning

**Decision.** Run the exact preregistered count, even after an early pass or
failure. Retain every response, repair and terminal failure. A measured output
cannot change that version.

**Rationale.** Optional stopping and mid-study fixes select favorable evidence.
Any correction must become a new version with a new protocol result.

**Rejected alternative.** Continuing until two runs agree measures search effort,
not reliability.

**Source.** X01 and the repository's controlled-change policy.

### Decision 6 — Use three repeats only as a bounded diagnostic

**Decision.** Report raw counts rather than percentages or confidence claims.

**Rationale.** A third run adds one preregistered comparison beyond a two-run
pair while keeping the v8 observation within 126 application sends. Three batches
can reveal gross instability but cannot estimate a population failure rate. The
findings also share equipment and scenario groups, so 21 tickets are not 21
independent samples.

**Rejected alternative.** Statistical significance, confidence intervals or an
accuracy percentage would exceed what this small, non-blind sample supports.

**Source.** Document 02 split rationale and Document 03 X01 limitations.

### Decision 7 — Measure reviewer noise instead of treating review as truth

**Decision.** Use one frozen primary reviewer configuration, calibrated only on
the seeded contradictions. Submit one identical output twice under blinded
labels. A second reviewer is sensitivity evidence, not a voting member.

**Rationale.** AI review is itself variable. A changed verdict on identical
output makes that dimension inconclusive and must not be attributed to generation.

**Rejected alternative.** Re-prompting or majority voting until reviewers agree
would convert disagreement into a success-shaped result.

**Source.** Document 03 semantic-review and reviewer-calibration rules.

### Decision 8 — Unknown accounting remains unknown

**Decision.** Report application sends, tokens, latency, transport attempts and
cost only where exposed. A token/request or money budget and pricing source are
declared before a paid run.

**Rationale.** Unknown retries or price cannot demonstrate the brief's
reproducibility constraint.

**Rejected alternative.** Recording unknown as zero understates both cost and
failure exposure.

**Source.** Brief §5 and X02.

## 4. Decision rules

These rules are fixed before inference.

| Research question | Evidence | Result rule |
|---|---|---|
| RQ1 control | Deterministic suites and fault scenarios | Any applicable failure = `fail` |
| RQ2 execution | Completed batches, sends, repairs, terminal errors and publication hashes | Every planned batch must complete within the observable budget; hidden transport attempts make the SDK-inclusive result `inconclusive` |
| RQ3 stability | Per-finding `(L, I, U, urgency band, review flag, rule set)` and unsupported/forbidden claims | X01 fails or remains unresolved on a band/review flip or a new unsupported claim; every numeric/rule change is reviewed |
| RQ4 semantics | Grounding, planning and uncertainty judgments | Any `fail` blocks provisional pass; `needs_review` or reviewer self-disagreement = `inconclusive` |
| RQ5 usefulness | Urgency, impact and review-flag distributions | Report middle-score collapse or high-urgency/review saturation; no artificial diversity target |
| RQ6 reproduction | Clean-checkout command, hashes, usage, latency and cost | Missing required provenance or accounting = `inconclusive` or `fail`, never pass |

A failed run is not replaced. Remaining preregistered runs continue, and any
comparison that cannot be computed is labelled incomplete.
For a supplementary three-run all-21 observation, compare all three run pairs and
report every band/review flip or new unsupported claim. This is descriptive
route-specific evidence and does not replace the isolated X01 verdict.

## 5. Evidence and reporting

For each run, retain the command, exit code, source/config/context hashes,
provider settings, timestamps, cache mode, sends, errors, usage, latency, cost and
output hash. Summaries link to tracked evidence or a hash-bound archive; local
session-state alone is not durable submission evidence.

The final report shows:

- completed versus planned batches;
- repair and terminal-failure counts by error class;
- every L/I/U, band, review or rule-trace difference;
- primary semantic verdicts and reviewer test-retest disagreement;
- urgency/impact/review distributions; and
- measured or explicitly unknown accounting.

No composite score is produced. Failed observations remain visible after a later
version is created.

## 6. Worked example: policy/activation v8

`triage-policy-v8` is the eighth labelled revision of the code-owned execution
and urgency policy. `triage-activation-v8.json` binds that policy to selected
knowledge and the assessment rubric. The current preregistration proposes GitHub
Copilot `gpt-6.1-sol` at medium reasoning effort against reference 1.3. V8 demonstrates both the value and the limit of the protocol: the runs provide
useful route-specific variability evidence, while their dirty identity and
activation timing prevent a clean-freeze pass.

| Gate | Current evidence | Status |
|---|---|---|
| Clean identity | Runtime/prompt/config hashes match all three runs, but the preregistration declares `clean_commit=false` | **Controlled dirty-worktree observation; clean reproduction inconclusive** |
| Activation provenance | The recorded review time follows repeat 1 start by seconds | **Invalid for a formal frozen-study claim; retained rather than rewritten** |
| Acceptance reference | Runs used the pinned reference-1.3 bytes; later layout/spec changes occurred after all three runs | **Comparable within the three runs; current layout hashes differ** |
| Preregistration | The historical `triage-reliability-v8.json` existed before the measured sends and fixed route, three-run order, 126-send ceiling and no-tuning rule | **Useful prospective control, but not a committed clean-freeze record** |
| Copilot series | 3/3 completed in 21/23/21 sends; two malformed responses repaired | **Observed execution completion; hidden transport attempts remain unknown** |
| Reviewer | Primary reviewer uses the same model family as generation | **Separate session only; not independent engineering judgment** |
| Budget/pricing | 21-send delivery took 635.64 s and reported 983,821 input plus 40,200 output tokens. OpenAI standard short-context rates imply US$2.37 under a simple no-cache-discount assumption | **Useful reproducibility estimate; actual Copilot USD allocation and hidden transport attempts remain unknown** |
| Stability | Exact L/I/U agreement 15/21, 19/21 and 17/21; urgency bands 21/21; review flags 20/21 | **Operational bands stable in these runs; numeric and routing variance remains visible** |
| Semantic review | Primary passes 54/63, 59/63 and 60/63 with 9/4/3 pending and no fail; sensitivity disagreement 8/7/15 dimensions and one failed repeat | **Inconclusive, not all-green or domain-certified** |
| Delivery | Fresh root `tickets.json`: 21 tickets/21 sends, contract pass, primary 61 pass/2 pending/0 fail | **Real provisional deliverable; human approval and clean reproduction remain pending** |

The result is therefore a **completed controlled observation with an
inconclusive formal freeze gate**, not `not run` and not an accepted reliability
pass. Raw evidence, reviews and hashes are retained under
Git commit `071d29e62be419bb7443a6e18bf55d2763d46e69`; the current panel-facing
tree retains the v31 result and material v29/v30 failures instead of this
superseded raw series.

Root `tickets.json` is a single generated delivery artifact, not the preregistered
repeat series required by this protocol. Its existence must not be used to
backfill a reliability claim.

Before a protocol-grade reproduction, the owner must commit a clean freeze, create a new
activation identity with ordered provenance rather than repinning the invalid
file in place, and use fresh ledgers. This remaining work does not erase the
observed variability.

### 6.1 Post-v8 calibration evidence

Document 08 records a separate behavior-calibration study, not a retroactive v8
reliability pass. V9 and v10 each completed two all-21 runs but were rejected:
their review routing hid material uncertainty, and v10's formula added no
demonstrated operational benefit. Exact v9/v10 policy bytes and all outputs are
retained.

V11 restored the v8 urgency formula and conservative review gate while retaining
the explicit assessment-v2 impact anchors. Its one declared delivery completed
in 21 sends, generated the current root artifact and received 54 pass, 9
`needs_review`, 0 fail from the primary AI-only reviewer. This supports a
provisional delivery decision, not version-reliability: v11 has not completed
the multi-repeat clean-freeze protocol defined by this document.

## 7. Interpretation and limitations

This study can show that one identified version completed specified runs, enforced
its controls, and exhibited an observed level of decision agreement and semantic
review. It cannot establish:

- accuracy on unseen findings or future models;
- domain calibration of L/I or urgency;
- deterministic model behavior;
- AI reviewer accuracy or domain expertise;
- reliability of a provider route that was not measured; or
- operational approval of any ticket.

The reference is AI-assisted, non-blind and test-informed. Three repeats are a
diagnostic, not a statistical sample. Unknown cost or retry counts remain unknown.
Every generated ticket still requires human approval.

## Appendix: reader glossary

| Term | Plain meaning |
|---|---|
| Frozen version | Clean, hash-identified code, context, model, route, config and reviewer |
| X01 | Two-run development-partition decision-stability scenario |
| X02 | Clean reproduction, accounting, cost and delivery scenario |
| Application send | One orchestration-level request; it may not expose provider-internal retries |
| Route | Provider/API path and controls, not only the model name |
| Ledger | Persistent record that prevents attempts from being reset |
