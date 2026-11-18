# Official Knowledge Change Study

> **Purpose:** demonstrate how an integrity engineer can change a general PSV
> scoring policy months later without editing orchestration code or adding
> finding-specific answers.
>
> **Status:** completed exploratory lifecycle study. The protocol was amended
> after retained v1-v3 failures; v4 is not a prospective B02 pass.

## Abstract

The Candidate Brief asks how `domain_knowledge.md` and registry comments reach
the decision, and what an integrity engineer changes when PSV scoring guidance
changes six months later. This is a maintainability requirement, not merely a
prompt-content question.

The source-first store is the system's official knowledge base. Its mutable
authoring surface is now named `working-candidate.json`; calling that file
`draft.json` incorrectly suggested that the knowledge base itself was
provisional. Runtime does not consume the working candidate. It consumes an
immutable reviewed release identified by hash and separately pinned by an
activation record.

This study changes an evaluation-only PSV rule through the real
knowledge lifecycle: source import, extraction, review, immutable publication,
activation, retrieval and model assessment. It separates three possible failure
locations: knowledge extraction, knowledge delivery and decision use. The
iteration history is part of the result: the system rejected two score rules
that conflicted with the production assessment policy before accepting a
source-backed likelihood change.

## 1. Requirement and claim

Candidate Brief section 6B requires:

1. an explanation of how domain knowledge reaches the model's decision; and
2. a maintainable answer to a future PSV scoring-policy change.

The architecture therefore claims more than modular code. A domain owner should
be able to add an approved source, review extracted knowledge, publish a new
release and activate it without changing `triage` code. The resulting decision
should change only when the new rule is applicable.

## 2. Why v9 and v10 did not test this

V9 changed the assessment rubric and review-routing code. V10 changed the
urgency formula. Both changed behavior, so the system is not behaviorally rigid,
but neither experiment changed the knowledge base:

- extraction received the same source bytes;
- retrieval used the same immutable release;
- provider-bound knowledge was unchanged;
- only assessment/policy instructions or code changed.

Their rejection therefore cannot be attributed to knowledge extraction. V9 was
rejected because decision routing violated the material-uncertainty contract.
V10 was rejected because its formula affected few final dispositions and added
complexity without demonstrated benefit.

B02 established a narrower fact: an isolated knowledge-policy overlay caused
the intended score change and did not leak to a negative control. It did not
exercise source import, review, publication or activation. This study closes
that lifecycle gap.

## 3. Official store semantics

| Artifact | Meaning |
|---|---|
| `working-candidate.json` | Mutable authoring state awaiting review; never a runtime authority |
| `sources\sha256-*.bin` | Exact imported source bytes |
| `revisions\sha256-*.json` | Immutable extracted or edited item revisions |
| `releases\sha256-*.json` | Immutable reviewed knowledge releases |
| `triage-activation-*.json` | Separate approval that pins one release, selector and application policies |

`working-candidate.json` is intentionally not called `official-knowledge.json`:
the official runtime authority is the immutable release hash. A friendly
filename must not obscure which exact reviewed bytes were activated.

Legacy stores containing `draft.json` remain readable. Their next successful
write migrates the same canonical candidate bytes to
`working-candidate.json`; the old file is then removed. Release identities and
source bytes do not change.

## 4. Research questions

### RQ1 — Extraction

Does a newly imported PSV source produce exact, source-bound items with the
declared `Pressure Safety Valve` scope?

**Pass:** source bytes, spans, extracted text and scope are hash-bound and
reviewable.

### RQ2 — Release maintenance

Can an old reviewed PSV rule be replaced by a new reviewed rule in a new
immutable release while the prior release remains resolvable?

**Pass:** both releases resolve independently; the replacement edge and
effective date are retained; no production release is mutated.

### RQ3 — Retrieval

Does the provider-bound context differ only by the activated knowledge release
and contain the correct old/new rule?

**Pass:** positive and negative inputs use identical finding/registry bytes per
condition pair, release hashes differ as declared, and captured context contains
the expected revision.

### RQ4 — Decision use and isolation

Does a PSV rule change cause the declared positive likelihood change without
being applied to a tag-only negative control?

**Pass:** the positive follows the old/new likelihood guidance while impact
remains fixed; both negative controls preserve the in-date tag-only
interpretation, remain outside both likelihood values and explicitly exclude
the functional-test rule.

## 5. Controlled policy change

The retained v4 experiment uses two artificial, evaluation-only domain-owner
sources:

- **before release:** a 2-3% low set-pressure test with full lift, rated capacity
  and tight reseat is treated as limited degradation at likelihood 4;
- **after release:** an updated fleet-review statement treats the same observed
  pattern as a recurrent precursor with strong progression at likelihood 8;
- both versions hold impact at 7 for the declared single-valve
  compressor-discharge protection scenario; and
- both versions explicitly exclude certification-tag-only observations without
  the functional-test result.

These numbers are diagnostic instruments, not engineering truth. Exact values
make the observed effect falsifiable. The source contains no finding ID or
expected ticket prose, but its impact clause is scenario-shaped. The causal
claim is therefore limited to the likelihood clause; fixed impact is a control,
not independent isolation evidence.

The after release is created through a replacement, not an in-place mutation.
The old release remains replayable.

## 6. Four-condition experiment

| Condition | Activated release | Input | Expected diagnostic |
|---|---|---|---|
| Positive before | old PSV rule | synthetic 2.5%-low lift test | L4/I7 |
| Positive after | replacement PSV rule | same synthetic finding | L8/I7 |
| Negative before | old PSV rule | unchanged development F-1016 tag defect | old rule excluded |
| Negative after | replacement PSV rule | same F-1016 input | new rule excluded |

The execution budget is four nominal and eight maximum application sends. Every
output is experimental and cannot replace root `tickets.json`.

## 7. Decision rules

The study fails or remains inconclusive if:

- extraction loses source fidelity or scope;
- the old release is mutated or becomes unresolved;
- activation does not pin the exact release;
- positive impact changes from I7;
- the positive likelihood does not follow the activated rule;
- either negative control applies the functional-test rule;
- code, prompt, source input or model settings change between paired conditions;
- any output is used as a production delivery.

One successful positive is insufficient. Extraction, immutable release history,
retrieval and negative-control isolation must all pass.

## 8. Results

### 8.1 Amendment history

The original design did not pass unchanged. Each observation was retained rather
than relabelled:

| Version | Change and observed result | Disposition |
|---|---|---|
| v1 | Original F-9001 seat-passing design, L6/I3→L8/I3. All four conditions stopped before dispatch because the workflow allow-list did not yet admit the new isolated release context; zero reservations | Harness failure retained; workflow boundary fixed |
| v2 | Same source design after the harness fix. Both positives returned `unassessable`: the prescribed scores conflicted with the production rubric. Tag controls generated drafts; U7/U6 differed because the model emitted different precautionary flags | Knowledge rule rejected; no terminal `report.json` because the reporting code then raised after the run |
| v3 | Changed to a 2.5%-low set-pressure test, L4/I5→L7/I5. Both positives again returned `unassessable`: impact 5 described present defect severity rather than consequence if protection fails | Impact interpretation rejected |
| v4 | Kept the test condition, corrected impact to the consequence-based I7, and changed only likelihood L4→L8 | Four drafts generated; bounded applicability observation passed |

V1 and v2 used the older unversioned ledger name; its five retained reservations
belong to v2. V1 used zero. V3 and v4 have versioned ledgers. Current tool bytes
cannot recreate v1-v3 exactly because the protocol constants changed; their
prepared sources, plans, captured requests and outputs are retained as
historical observations. V4 is hash-frozen by its plan, but later reporting
improvements changed the current tool hash.

### 8.2 V4 lifecycle and behavior

The v4 plan published two independently resolvable immutable releases, recorded
the predecessor/successor edge and `2026-06-30T00:00:00+00:00` effective date,
and captured evaluation-only provider context under the unchanged production
assessment policy.

| Condition | Observed |
|---|---|
| Positive before | L4/I7/U7 |
| Positive after | L8/I7/U8 |
| Negative before | L2/I7/U6 |
| Negative after | L2/I7/U6 |

The positive rationales cited the active old/new guidance. Both negative
likelihood rationales explicitly state that the low-set-pressure test rule does
not apply. Exact negative L/I equality and L2 being outside `{4, 8}` provide
mechanical supporting evidence; the text applicability check is a bounded
AI-assisted artifact review, not a rerun of the calibrated semantic reviewer.
The positive urgency movement is reported but is not the clean causal claim:
urgency also depends on model-generated flags. V2's U7/U6 negative split shows
that one favorable v4 urgency pair does not establish X01 stability.

Artifacts:

- frozen plan and contexts:
  `eval\results\triage\knowledge-release-change-v4-prepared`;
- four outputs and run records:
  `eval\results\triage\knowledge-release-change-v4-run1`;
- bounded applicability review:
  `bounded-applicability-review.json`; and
- accounting:
  `accounting.json`.

The four observed sends took 100.859 seconds and reported 124,075 input and
5,330 output tokens. Actual Copilot USD allocation and hidden HTTP attempts are
unknown. At the same simple assumed OpenAI rates used elsewhere in this
repository—US$2/M input and US$10/M output, with no cache discount—the
illustrative equivalent is US$0.3015.

### 8.3 Official-store full-batch follow-up

The four-condition probe was not the final end-to-end test. A follow-up used the
existing `triage_knowledge` editor/CLI lifecycle on the repository's official
`knowledge\source-first` store and the production `python -m triage` command:

1. retain the current eight-item release as the baseline;
2. import a PSV-scoped source through the same operation exposed by Streamlit;
3. review and publish a new immutable nine-item release;
4. create an AI-reviewed local activation on the owner's instruction, without
   authenticated human/domain approval or changing root delivery;
5. run two complete 21-ticket baseline batches and two complete 21-ticket
   revised-release batches with the same model, policy and workflow code.

The source targets audible PSV tailpipe hissing with hydrocarbon odour below set
pressure, assigns L9/I8 when the valve is the sole high-criticality protection,
and excludes tag/register/visual-only evidence.

This is explicitly test-informed. F-1002 is in the test partition, and the rule
closely follows its wording; F-1016 is the development negative control. The
rule was also revised after observing F-1002's first output. It therefore cannot
be presented as independent or blind knowledge validation. The test reference
describes suspected passing separately from proven inability to relieve, while
the experimental source classifies seat tightness itself as a failed required
function. That semantic conflict remains unresolved.

The first published source incorrectly contained the sentence that it was an
“evaluation-only proposed policy.” Delivery worked, but F-1002 remained L7/I8:
the model explicitly said that this was not activated assessment authority.
That release was rejected. The correction did not strengthen the numeric rule.
It moved experiment status to publication/activation metadata and kept domain
content limited to the rule itself.

| Finding | Baseline repeat 1 | Baseline repeat 2 | Revised repeat 1 | Revised repeat 2 |
|---|---:|---:|---:|---:|
| F-1002 audible passing | L7/I8/U8 | L7/I8/U8 | L9/I8/U9 | L9/I8/U9 |
| F-1016 tag-only control | L2/I7/U7 | L2/I8/U7 | L2/I8/U7 | L2/I8/U7 |

Both revised F-1002 rationales state that the active guidance establishes failed
seat tightness while not claiming failure to lift. One revised F-1016 rationale
explicitly cites the tag-only exclusion; the other preserves L2 and distinguishes
the other valve without citing the rule. The target transition is repeat-stable.
F-1016 likelihood provides one explicitly defined control, not general scope
isolation. Its impact is not clean evidence because baseline repeats already
varied I7/I8.

The first amended release exposed an editor bug: `edit_item` cleared structured
scope and source evidence, so the amended item became general even though its
text still contained `Scope: Pressure Safety Valve`. This was a stored-metadata
defect, but it did not cause the all-21 exposure. Knowledge is assembled once
for the batch: because the batch contains PSV findings, a correctly scoped PSV
item is admitted to the same batch-wide pool and appears in every finding
assessment. Per-finding knowledge isolation is not implemented, so exclusion
for non-PSV findings depends on model judgment. Non-target variance remains
material: five score tuples changed between the two
baseline repeats and six between revised repeats. The study therefore supports
a test-informed delivery/influence observation for target likelihood/urgency and
one negative-control likelihood, not general deterministic stability. F-1005
was L10 in both baselines and L9 in all three runs containing either rule
revision. That possible side effect is not resolved by ticket text alone.

The editor was corrected to deterministically re-extract scope, aliases and
source evidence on each text amendment and to reject a one-item edit that
extracts into multiple items. Focused tests pass. A new immutable verification
release retained `Pressure Safety Valve` as structured scope with one source
evidence record. Its full 21-ticket run again produced F-1002 L9/I8/U9,
F-1016 L2/I8/U7 and F-1005 L9/I6/U9. This verifies the editor fix and target
behavior; it did not narrow provider delivery. It therefore does not resolve
whether F-1005's repeat-stable L10→L9 movement is model variance or an indirect
shared-context effect.

The four retained full-batch runs used 87 application sends, 2,836.141 seconds,
4,164,475 input tokens and 166,348 output tokens. The illustrative equivalent
API cost is US$9.9924 under the stated rates. The rejected first-source run used
another 21 sends and an estimated US$2.4603. Actual Copilot USD and hidden HTTP
attempts remain unknown. Full details are in
`eval\results\triage\knowledge-kb-edit-v1-study.json`.

All four 21-ticket files pass deterministic contract assessment. Their
63-dimension semantic status remains `needs_review` because the calibrated
reviewer was not rerun. The synthetic release is therefore not promoted to root `tickets.json` or
production activation. The official store's working candidate was reset to the
eight-item baseline release after the experiment; immutable experiment releases
remain only as replayable evidence with explicit dispositions.

Because the editor implementation hash changed, the unchanged baseline release
was repinned in `config\triage-activation-v12.json`. Context preparation for all
21 findings passed without inference. Root `tickets.json` remains the retained
v11 artifact and was not overwritten.

## 9. Interpretation limits

This is an AI-assisted synthetic maintainability experiment. V4 demonstrates
that reviewed source bytes can propagate through extraction, immutable release,
replacement, activation and captured provider context, and that one applicable
likelihood assessment followed the activated old/new values while one tag-only
control did not. It does not show what the model would decide without either
rule, certify the artificial scores, establish repeated decision stability,
prove all future knowledge changes will extract correctly, or replace
domain-owner review and activation approval. Because the protocol was tuned
after retained failures, v4 is exploratory B03 lifecycle evidence plus a bounded
influence observation, not a prospective B02 acceptance result.

The official-store full-batch follow-up strengthens the maintainability claim:
the existing editor/CLI and production triage path generated complete
`tickets.json` artifacts, and the test-informed F-1002 transition repeated in
both arms. The numeric L9 is not an independent calibration result: once the
source reclassifies seat tightness as a confirmed failed required function, the
existing production policy already requires likelihood at least 9. The study
does not certify that reclassification or the L9/I8 rule. More aggressive
scoring is not the next action; authenticated domain review and calibrated
semantic review are.
