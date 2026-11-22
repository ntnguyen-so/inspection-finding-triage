# Knowledge Change: Maintenance Path and Observed Impact

This test-informed study demonstrates the maintenance mechanism and a bounded
behavior influence. It does not certify the experimental PSV guidance or
authorize production use.

## Abstract

The Candidate Brief asks:

> An integrity engineer needs to change how PSV findings are scored six months
> from now. What do they modify?

For a new source-backed PSV interpretation **inside the existing assessment
rubric**, they add or replace an approved knowledge source, review the extracted
item, publish a new immutable release and separately activate that release. They
do not edit the prompt, add finding-ID branches or hand-correct tickets.

The retained evidence shows that this path works:

- an isolated assessment-context intervention changed the synthetic positive
  result from L6/I3 to L8/I3 while the tag-only negative control remained
  semantically unaffected;
- an official-store full-batch exercise changed target F-1002 from
  L7/I8/U8 in two baseline runs to L9/I8/U9 in two runs using a release whose
  structured scope was later found defective;
- one run using the corrected scoped release reproduced F-1002 at L9/I8/U9;
- tag-only control F-1016 remained L2 in all four full-batch runs; and
- the experiment exposed an editor scope defect, non-target variance and a
  domain-semantics conflict, so the working candidate was reset, no experimental
  release was promoted and production activation stayed on the baseline release.

The study supports a narrower conclusion: the system makes knowledge change
observable, reviewable and reversible, but a visible output change does not
prove that the new engineering rule is correct.

## 1. Knowledge-change surfaces

The correct edit surface depends on what the engineer is actually changing:

| Requested change | What must be modified | What must not be modified |
|---|---|---|
| New approved PSV evidence or interpretation within the existing L/I rubric | A source under the knowledge lifecycle, followed by review, immutable publication and separate activation; if it overlaps prompt-embedded interpretation, complete the Document 06 compatibility review before activation | Ad-hoc prompt surgery, orchestration code or finding-specific branches |
| A new generic likelihood or impact anchor | `triage\assessment_policy.py` and focused tests | Knowledge text pretending to override the scoring contract |
| A new urgency floor or exceptional-review rule | `triage\policy.py` and focused tests | Model instructions asking it to choose urgency |
| A new fact about one valve | A new registry snapshot supplied to the run | The preserved candidate package or general knowledge release |
| A selector or extraction behavior change | `triage_knowledge` retrieval/extraction code and controlled component evaluation | The source guidance itself |

This separation matters. Knowledge owns approved engineering interpretation;
application policy owns scoring anchors and deterministic routing. Calling every
change a "knowledge update" would hide code-owned policy changes from review.

Complete bounded source and registry context was chosen because the prototype
has only 21 findings and 18 equipment records; it avoids retrieval ranking and
omission failures at the cost of more input tokens. Immutable releases and
separate activation make each change reviewable, reconstructable and rejectable
without prompt surgery.

Document 05 defines the production architecture and commands. This document
shows what happened when that maintenance path was exercised.

The official-store full-batch exercise used `gpt-6.1-sol` and
`triage-policy-v11`; it predates the delivered `triage-policy-v16` behavior
calibration. The study therefore demonstrates the maintenance mechanism and
observed influence under its recorded run identity, not revalidation of the
delivered system.

## 2. Evidence at a glance

| Knowledge change or control | Actual observed result | What the result supports | Important limit | Evidence |
|---|---|---|---|---|
| Acceptance-aligned artificial instruction changed on the assessment-policy channel | Synthetic positive: L6/I3 -> L8/I3 | An isolated context instruction can influence the intended assessment while impact remains fixed | This is an evaluation overlay, not a released knowledge item or production maintenance-path test | [B02 semantic review](../eval/results/triage/v10-calibration/b02-execution/negative-control-semantic-review.json) |
| Same isolated instruction presented to a tag-only PSV finding | F-1016 remained an in-date tag defect; the passing/failure convention was not applied | Bounded applicability: the instruction was not blindly applied to every PSV | Model-level exclusion, not selector-level per-finding isolation | [B02 semantic review](../eval/results/triage/v10-calibration/b02-execution/negative-control-semantic-review.json) |
| Experimental PSV source traversed the official store and full production command | F-1002: two runs at L7/I8/U8 -> two runs at L9/I8/U9 | The real import/review/release/activation path can visibly affect generated tickets | The revised source hard-coded L9/I8 and the two repeats used a release that had lost structured scope | [Full-batch study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json) |
| Corrected release restored explicit `Pressure Safety Valve` scope and source evidence | One verification run retained F-1002 at L9/I8/U9 and F-1016 at L2/I8/U7 | The editor fix restored structured provenance without losing the target behavior | One run only; scoped guidance still entered the shared all-21 batch context | [Full-batch study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json) |
| Same full-batch edit evaluated against tag-only F-1016 | Likelihood remained L2 in both baseline and both revised runs | The target rule did not turn an unrelated tag defect into a functional failure | Impact varied across repeats, so this is not clean whole-ticket stability evidence | [Full-batch study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json) |
| Full-batch non-target comparison | F-1005 was L10 in both baselines and L9 in every run containing a PSV rule revision; the study records 5 baseline and 6 revised repeat score changes | The study exposed possible side effects and normal model variance instead of reporting only the target success | The retained summary does not define those counts as ticket tuples, and causality for F-1005 was not resolved | [Full-batch study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json) |
| Editor changed the source item but initially lost structured scope/evidence | Defect detected; editor fixed; verification release restored `Pressure Safety Valve` scope and one evidence span | Maintenance tooling can fail visibly and the release history supports correction without rewriting prior evidence | Batch-wide context still delivered scoped PSV guidance to every assessment in the all-21 batch | [Study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json), [release disposition](../eval/results/controlled-studies/knowledge-kb-edit-v1-release-disposition.json) |
| Promotion decision after the experiment | Experimental releases were not promoted; working candidate reset to the eight-item baseline; root `tickets.json` unchanged | Experimental evidence remained separate from production authority | No authenticated domain-owner approval was obtained | [Release disposition](../eval/results/controlled-studies/knowledge-kb-edit-v1-release-disposition.json) |

## 3. How a knowledge change reaches assessment

```text
approved source bytes
  -> source-faithful extraction with evidence spans
  -> explicit human review
  -> immutable replacement release
  -> separate activation approval
  -> provider-bound context with release identity
  -> regenerated assessment and ticket
  -> comparison, semantic review and promotion decision
```

Each boundary answers a different risk:

| Boundary | Question answered |
|---|---|
| Source and extraction | What exact approved text supports this guidance? |
| Review | Did a person approve the extracted meaning and scope? |
| Immutable release | Can the old and new states both be reconstructed? |
| Activation | Which reviewed release is allowed to affect this run? |
| Provider capture | Did the selected guidance actually reach the model request? |
| Before/after output | Did behavior change in the intended case? |
| Negative and non-target controls | Did the change leak into cases where it should not apply? |
| Promotion decision | Is the evidence strong enough to become runtime authority? |

Delivery is not the same as use, and use is not the same as correctness. The
study retains evidence for all three decisions instead of inferring one from
another.

## 4. Controlled context-influence evidence

### 4.1 Acceptance-aligned isolated comparison

The B02 probe held model, configuration, implementation and the synthetic input
fixed. Only an artificial instruction under
`context.assessment_policy.isolated_experiment` changed:

| Condition | Before | After |
|---|---:|---:|
| Synthetic positive likelihood | 6 | 8 |
| Synthetic positive impact | 3 | 3 |
| Tag-only F-1016 interpretation | In-date tag defect; passing rule excluded | In-date tag defect; passing rule excluded |

The acceptance contract describes this as an isolated knowledge input, but the
implemented diagnostic overlay is carried on the assessment-policy channel. It
tests context influence and applicability; it does not demonstrate the
source/release maintenance path.

The positive demonstrates intended influence. The negative control matters just
as much: it shows that a rule about observed PSV seat passing was not applied
merely because another finding also involved a PSV.

The calibrated reviewer marked this bounded four-condition comparison as a pass.
The reviewer was AI-only and not a domain expert. One result per condition does
not establish repeat stability, production correctness or the hidden
SDK-inclusive attempt bound.

### 4.2 What this comparison establishes

The retained runs include provider-bound context and exact overlay identities.
The evidence shows:

1. the before and after artificial policy overlays were different and
   hash-bound;
2. the intended overlay reached each request;
3. the positive output followed the changed convention; and
4. the negative output excluded the inapplicable convention.

That is the bounded B02 diagnostic claim. The release-path evidence comes from
the official-store exercise in section 5. Neither study proves that an
artificial score is correct for a real valve.

## 5. Official-store maintenance exercise

The second study tested the actual six-month maintenance path rather than an
isolated evaluation overlay.

### 5.1 What was changed

An experimental source defined a PSV seat-tightness interpretation for audible
tailpipe hissing and hydrocarbon odour below set pressure. It also prescribed
L9/I8 directly. That numeric prescription is an anti-pattern relative to the
authority split in section 1: a proper source should state source-backed
classification and evidence while the approved assessment rubric owns numeric
anchors.

The experimental change traversed:

1. source import;
2. source-faithful item extraction;
3. explicit review;
4. immutable release publication;
5. replacement history;
6. separately reviewed local activation; and
7. the production triage command across complete 21-finding batches.

No finding-ID branch was added and the final tickets were regenerated rather
than edited.

### 5.2 What changed in the output

| Finding | Baseline repeats | Revised-release repeats | Interpretation |
|---|---|---|---|
| F-1002, PSV seat-tightness observation | L7/I8/U8; L7/I8/U8 | L9/I8/U9; L9/I8/U9 | The revised source both reclassified the condition and declared L9/I8; the existing confirmed-function-failure minimum also enforces L9. U9 follows from the L9/I8 base calculation, not an urgency override |
| F-1016, tag-only defect | L2; L2 | L2; L2 | The functional-test rule did not change likelihood for the tag-only condition |
| F-1005, non-target protection case | L10 in both baselines | L9 in all rule-revision runs | Possible non-target effect remained unresolved |

These two revised repeats used release `a39d...`, whose pre-fix editor path had
lost structured scope and evidence and stored the item as general guidance. The
F-1002 result proves visible influence through the real lifecycle, but it is not
evidence from a correctly scoped release and not a clean "knowledge text changed
L by two" causal claim.

After the editor fix, release `63f1...` restored `Pressure Safety Valve` scope
and one source-evidence span. Its single retained full-batch verification run
produced F-1002 L9/I8/U9, F-1016 L2/I8/U7 and F-1005 L9/I6/U9. This confirms
the corrected release remained influential, but n=1 does not establish repeat
stability.

### 5.3 What the exercise exposed

The exercise found three issues that a simpler demo would have hidden:

1. **Authority wording leaked into guidance.** The first source called itself an
   evaluation-only proposal, so the model correctly declined to treat it as
   active engineering authority. Experiment status was moved to release metadata
   rather than left inside domain guidance.
2. **The editor lost structured scope and evidence.** The two revised repeats
   used the affected release, which stored the amended item as general guidance.
   The editor was fixed to re-extract scope, aliases and source evidence and to
   reject ambiguous edits; the corrected scoped release received one verification
   run.
3. **Restored scope did not provide per-finding isolation.** The batch contained
   PSV findings, so the scoped item entered one shared batch knowledge pool and
   appeared in every assessment request. Current behavior relies on model-level
   applicability, not selector-level isolation.

These are not side notes. They are the strongest evidence that the maintenance
path was tested as a system rather than demonstrated only on a happy path.

## 6. Promotion decision

The experimental releases were not promoted to production because:

- the rule was synthetic and test-informed;
- the source prescribed L9/I8 directly instead of leaving numeric anchoring to
  the assessment rubric;
- it closely followed test finding F-1002 and was revised after an observed
  output;
- it conflicted with the evaluation reference's distinction between suspected
  passing and proven inability to relieve;
- calibrated semantic review was not rerun for the full-batch outputs;
- non-target variance remained unresolved; and
- no authenticated domain owner approved the interpretation.

The working candidate was reset to the eight-item baseline release. After the
editor implementation hash changed, production activation was repinned to that
same baseline release; it had not been moved to an experimental release. Root
`tickets.json` remained unchanged.

This is the intended governance behavior: a release may prove that the mechanism
works and still be rejected as engineering authority.

## 7. Candidate-brief evidence map

| Candidate-brief question | Repository answer | Evidence status |
|---|---|---|
| How does `domain_knowledge.md` reach the model? | Preserved source bytes become reviewed release items, are selected into hash-bound context and are revalidated before provider dispatch | B01 delivery evidence exists; delivery alone does not prove use |
| How does `engineer_comment` reach the model? | The selected registry snapshot and comments are included as source-addressable context | Captured provider context and component checks |
| What does the engineer modify six months later? | An approved knowledge source and reviewed release for interpretation changes; policy code only when the rubric or deterministic routing changes | B03 lifecycle mechanics demonstrated |
| Can a released knowledge change affect output? | Yes, in the official-store full-batch exercise | Visible influence demonstrated; not domain correctness or clean score causality |
| Can an isolated context instruction affect output without leaking to the negative control? | Yes, in the B02 synthetic comparison | Bounded context influence/applicability evidence; not release-path evidence |
| Can an old release be recovered? | Releases are immutable and replacement history is preserved | Component/lifecycle tests and retained releases |
| Can a technically valid change be rejected? | Yes; publication and activation are separate, and no experimental PSV release was activated in production | Release disposition evidence |

The bounded corpus is small, so the prototype sends complete source and registry
context instead of introducing vector retrieval. This avoids ranking and
omission failure modes for 21 findings and 18 equipment records, while accepting
higher input-token cost. Provider-bound evidence that includes registry comments
is retained in the [final run record](../eval/results/triage/structured-planning-v31/final/evidence/run.json).

## 8. Claim boundaries

This study demonstrates:

- source import, extraction, review, immutable publication, replacement and
  activation mechanics;
- provider delivery of the selected release;
- bounded intended influence and negative-control applicability;
- visible full-batch influence through the official store; and
- working-candidate reset and non-promotion while production authority remained
  on the baseline release.

It does not demonstrate:

- independent correctness of the experimental PSV rule;
- stable non-target assessments;
- selector-level per-finding isolation;
- general causal use of every delivered knowledge item;
- authenticated domain-owner approval; or
- production promotion of the revised release.

The production architecture and maintenance commands remain in
[Document 05](05_KNOWLEDGE_LIFECYCLE.md). The detailed evidence index is
[`eval\results\README.md`](../eval/results/README.md).
