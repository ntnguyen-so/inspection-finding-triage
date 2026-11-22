# Knowledge Change Study

This study answers a practical maintenance question: **if an integrity engineer
needs to change how pressure safety valve (PSV) evidence is interpreted six
months from now, what do they edit, how does that change reach the model, and
how can they decide whether to promote it?**

The short answer is:

- change an approved knowledge source when the engineering interpretation
  changes within the existing likelihood/impact rubric;
- change policy code when the rubric, urgency or review-routing rule changes;
- publish and activate knowledge as separate steps; and
- compare the resulting behavior before deciding whether the new release is
  safe to use.

The retained experiments show that this maintenance path can change model
behavior and can be rolled back. They do **not** establish that the experimental
PSV rule was correct. The rule was not promoted, and production remained on the
baseline knowledge release.

## 1. Choose the correct change surface

Not every future behavior change is a knowledge update.

| Requested change | Correct edit surface | Do not use |
|---|---|---|
| New approved PSV evidence or interpretation within the existing L/I rubric | Add or replace an approved knowledge source, review the extracted item, publish an immutable release and activate it separately | Prompt edits, orchestration changes or finding-ID branches |
| New generic likelihood or impact anchor | `triage\assessment_policy.py` and focused tests | Knowledge text that tries to override the scoring contract |
| New urgency floor or exceptional-review rule | `triage\policy.py` and focused tests | Model instructions that ask the model to choose urgency |
| New fact about one valve | A new registry snapshot supplied to the run | General knowledge or changes to the preserved source package |
| New selector or extraction behavior | `triage_knowledge` retrieval/extraction code and controlled component evaluation | Rewording the source guidance to compensate for code behavior |

This separation keeps approved engineering interpretation distinct from
code-owned scoring and routing policy. Document 05 defines the production
commands and release architecture; this document records what happened when
that architecture was exercised.

## 2. How a knowledge change reaches assessment

```text
approved source bytes
  -> source-faithful extraction with evidence spans
  -> explicit review
  -> immutable release
  -> separate activation approval
  -> provider-bound context with release identity
  -> regenerated assessment and ticket
  -> before/after review
  -> promotion or rejection
```

Each boundary answers a separate question:

| Boundary | Question |
|---|---|
| Source and extraction | What exact approved text supports the guidance? |
| Review | Was the extracted meaning and scope approved? |
| Immutable release | Can both the old and new states be reconstructed? |
| Activation | Which reviewed release may affect a run? |
| Provider capture | Did the selected release reach the model request? |
| Before/after comparison | Did behavior change in the intended case? |
| Negative and non-target controls | Did unrelated cases also change? |
| Promotion decision | Is the evidence strong enough to become runtime authority? |

The prototype sends complete bounded source and registry context because the
corpus contains only 21 findings and 18 equipment records. This avoids retrieval
ranking and omission failures, but it uses more input tokens and does not provide
selector-level per-finding isolation.

Delivery, influence and correctness are different claims. Captured context can
prove delivery. A before/after comparison can support influence. Neither proves
that the engineering rule itself is correct.

## 3. Why there are two experiments

The repository retains two related but different studies:

1. an **isolated context diagnostic**, which asks whether one artificial
   instruction can influence the intended case without changing a negative
   control; and
2. an **official maintenance-path exercise**, which asks whether a source can
   traverse import, review, release, activation and the production triage
   command.

The first provides a cleaner influence comparison but does not exercise the
knowledge release mechanism. The second exercises the real mechanism but uses a
test-informed synthetic rule and exposed several defects. They should not be
combined into one stronger claim.

## 4. Isolated context diagnostic

The B02 diagnostic (the acceptance scenario for knowledge influence and its
negative control) held the model, configuration, implementation and synthetic
input fixed. Only an artificial instruction under
`context.assessment_policy.isolated_experiment` changed.

| Condition | Before | After |
|---|---:|---:|
| Synthetic positive likelihood | 6 | 8 |
| Synthetic positive impact | 3 | 3 |
| Tag-only F-1016 interpretation | Identification-tag defect with no functional evidence; seat-leakage rule excluded | Identification-tag defect with no functional evidence; seat-leakage rule excluded |

The positive case followed the changed convention while impact remained fixed.
The F-1016 control did not apply that convention merely because it also involved
a PSV. The calibrated AI reviewer marked the four-condition comparison as a
pass.

This supports one bounded claim: an isolated context instruction influenced the
intended assessment and was not blindly applied to the tag-only control. It does
not demonstrate source import, release activation, repeat stability, production
correctness or domain approval. The instruction was carried on an
assessment-policy diagnostic channel, not as a released production knowledge
item.

Evidence:
[B02 semantic review](../eval/results/triage/v10-calibration/b02-execution/negative-control-semantic-review.json).

## 5. Official maintenance-path exercise

The second experiment used the actual knowledge store and full triage command.
An experimental source described audible tailpipe hissing and hydrocarbon odour
below set pressure as PSV seat-tightness evidence.

The source also prescribed L9/I8 directly. That was intentionally retained as a
visible anti-pattern: engineering sources should state the supported
interpretation, while the approved assessment rubric owns numeric anchors. This
alone would have blocked promotion.

The exercise passed through three states:

1. the first source described itself as an experiment, so the model declined to
   treat it as engineering authority;
2. a revised source was published as release `a39d...` and run twice, but an
   editor defect was later found to have removed its scope and evidence fields;
   and
3. after the editor fix, release `63f1...` restored those fields and received
   one verification run.

All three states remained experimental and were rejected in section 6.

The change traversed source import, extraction, review, immutable publication,
separate activation and complete 21-finding generation. No finding-ID branch was
added, and no ticket was hand-corrected.

This exercise used `gpt-6.1-sol` and `triage-policy-v11`; it predates the
delivered `triage-policy-v16` calibration. It therefore demonstrates the
maintenance mechanism under its recorded run identity, not revalidation of the
delivered system.

### 5.1 Observed output

| Finding | Baseline | Experimental release | Interpretation |
|---|---|---|---|
| F-1002, PSV seat-tightness observation | Two runs at L7/I8/U8 | Two runs at L9/I8/U9 | The source declared L9/I8; the existing confirmed-function-failure minimum also enforces L9. U9 follows from the L9/I8 calculation, not an urgency override |
| F-1016, tag-only defect | L2 in both runs | L2 in both runs | The seat-tightness rule did not change likelihood for the tag-only condition |
| F-1005, non-target protection case | L10 in both runs | L9 in all three experimental runs | A possible non-target effect remained unresolved |

The two experimental repeats used release `a39d...`. A defect in the editor had
removed its structured scope and source-evidence fields, so the item was stored
as general guidance. The F-1002 change proves visible influence through the real
lifecycle, but it is not evidence from a correctly scoped release and cannot be
described as clean causal proof that knowledge text changed likelihood by two.

After the editor was fixed, release `63f1...` restored explicit
`Pressure Safety Valve` scope and one source-evidence span. Its one retained
verification run produced:

- F-1002: L9/I8/U9;
- F-1016: L2/I8/U7; and
- F-1005: L9/I6/U9.

The target behavior remained visible after scope was restored, but one run does
not establish repeat stability. F-1016 likelihood stayed at L2 across the
baseline and experimental repeats, while its impact varied. Other non-target
scores also varied within the retained repeats; those changes were not resolved
as causal effects of the source update.

Evidence:
[full-batch study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json).

### 5.2 What the exercise revealed

The exercise found problems that a happy-path demonstration would have hidden:

1. **Experiment wording entered engineering guidance.** The first source called
   itself an evaluation-only proposal, so the model correctly declined to treat
   it as active authority. Experiment status was moved to release metadata.
2. **The editor lost scope and evidence.** The editor was fixed to re-extract
   scope, aliases and source evidence and to reject ambiguous edits. Prior
   release evidence was preserved rather than rewritten.
3. **Restored scope did not create per-finding isolation.** The scoped PSV item
   entered the shared batch knowledge pool and appeared in every request.
   Applicability still depended on model interpretation.
4. **Non-target behavior was not stable.** F-1005 changed, and F-1016 impact
   varied even though its likelihood control remained intact.
5. **The proposed rule conflicted with the evaluation reference.** It treated
   suspected passing too much like proven inability to relieve and hard-coded
   numeric scores.

These findings are evidence that the maintenance mechanism was exercised under
failure, not evidence that the proposed rule should be accepted.

## 6. Promotion decision

The experimental releases were rejected because:

- the rule was synthetic and test-informed;
- it prescribed L9/I8 instead of leaving numeric anchoring to the assessment
  rubric;
- it closely followed test finding F-1002 and was revised after observed output;
- it conflicted with the reference distinction between suspected seat passing
  and proven inability to relieve;
- the full-batch outputs did not receive the calibrated semantic review required
  for promotion;
- non-target variance remained unresolved; and
- no authenticated domain owner approved the interpretation.

The working candidate was reset to the eight-item baseline release. Activation
approval is bound to the editor implementation hash, so fixing the editor
invalidated the existing approval; production was re-approved for the same
eight-item baseline release. Root `tickets.json` remained unchanged.

This is the intended governance result: an experiment can prove that the
maintenance mechanism works while its engineering content is still rejected.

Evidence:
[release disposition](../eval/results/controlled-studies/knowledge-kb-edit-v1-release-disposition.json).

## 7. Answers to the maintenance requirements

| Question | Repository answer | Evidence status |
|---|---|---|
| How does `domain_knowledge.md` reach the model? | Preserved source bytes become reviewed release items, are selected into hash-bound context and are revalidated before dispatch | Delivery is observable. B01, the context-isolation scenario, remains not met for the retained development runs |
| How does `engineer_comment` reach the model? | The selected registry snapshot and comments are included as source-addressable context | Captured provider context and component checks |
| What does the engineer modify six months later? | An approved knowledge source and reviewed release for interpretation changes; policy code for rubric or deterministic-routing changes | B03, the maintainable-knowledge lifecycle scenario, is demonstrated mechanically |
| Can a released change affect output? | Yes, in the official maintenance-path exercise | Visible influence demonstrated; not domain correctness or clean score causality |
| Can an isolated instruction affect its target without changing the negative control? | Yes, in the B02 diagnostic | Bounded influence and applicability; not release-path evidence |
| Can an old release be recovered? | Releases are immutable and replacement history is retained | Component tests and retained releases |
| Can a technically valid release be rejected? | Yes; publication and activation are separate, and no experimental PSV release became production authority | Release disposition evidence |

Provider-bound evidence that includes registry comments is retained in the
[final run record](../eval/results/triage/structured-planning-v31/final/evidence/run.json).

## 8. What this study supports

The evidence supports:

- source import, extraction, review, immutable publication and separate
  activation;
- provider delivery of the selected release;
- one bounded intended-influence and negative-control comparison;
- visible full-batch influence through the official knowledge store; and
- rejection and rollback while production remained on the baseline release.

It does not support:

- independent correctness of the experimental PSV rule;
- stable non-target assessments;
- selector-level per-finding isolation;
- general causal use of every delivered knowledge item;
- authenticated domain-owner approval; or
- production promotion of the experimental release.

The production architecture and maintenance commands are in
[Document 05](05_KNOWLEDGE_LIFECYCLE.md). The complete evidence index is
[`eval\results\README.md`](../eval/results/README.md).
