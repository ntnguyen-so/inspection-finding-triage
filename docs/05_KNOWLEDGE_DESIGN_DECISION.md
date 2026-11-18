# Source-Faithful Knowledge Design

> **Document status:** current knowledge architecture and maintenance decision.
> Context delivery is demonstrated. Reference-1.3 B02 provides a bounded causal
> influence and scope-isolation pass. Document 09 additionally demonstrates one
> end-to-end immutable release replacement after disclosing three failed design
> iterations; general domain correctness is not established.

## Abstract

The knowledge module exists to make engineering guidance reviewable,
source-faithful and maintainable without embedding case answers in prompts or
workflow code. Its lifecycle is:

```text
approved source bytes
  -> extracted candidate items with exact provenance
  -> explicit review
  -> immutable release
  -> separate activation approval
  -> deterministic selection and context assembly
  -> independent workflow validation
```

The supplied corpus is small, so the current assessment path favors complete
bounded context over vector retrieval. This is a scope decision, not a claim that
retrieval is generally unnecessary. Captured context proves what was sent to the
provider; it does not prove that the model used the knowledge correctly.

The source-first store is the official knowledge base. Its mutable authoring
file is `working-candidate.json`; runtime authority belongs to immutable
`releases\sha256-*.json` plus a separately reviewed activation. Legacy
`draft.json` stores remain readable and migrate on the next successful write.

## 1. Why knowledge is a separate module

Knowledge extraction and retrieval are first-class system responsibilities, not
prompt-construction details. They have a different lifecycle, authority and
change rate from ticket orchestration:

```text
approved sources
  -> triage_knowledge: import, extract, review, publish, select
  -> validated knowledge/context contract
  -> triage: assess, validate, derive urgency, publish drafts
```

`triage_knowledge` owns source provenance, extraction, review state, immutable
releases, selection and context validation. `triage` owns finding assessment,
policy, retries, complete-batch coverage and publication. The dependency points
one way: triage consumes a pinned context contract; knowledge tooling does not
call the triage workflow or decide ticket urgency.

**Rationale.** Extraction quality and relevant-context selection can change
independently from assessment orchestration. A separate module makes those
changes reviewable, testable and maintainable without editing workflow code. It
also creates a clear permission boundary:

| Role | Owned change |
|---|---|
| Knowledge steward/domain owner | Approved sources, extracted items, review and release |
| Runtime approver | Which immutable release/selector is activated |
| Triage application owner | Assessment rubric, urgency policy, attempts and publication |
| Evaluator | Scenarios and review evidence; never production knowledge |

**Rejected alternative.** Embedding extraction, retrieval and source editing
inside `triage.workflow` would combine content authority with execution control.
It would make a PSV guidance change require workflow review, obscure who approved
the knowledge, and increase the risk that evaluation examples become production
rules.

The workflow is independent of knowledge-store internals, not independent of
engineering context. It can consume any implementation that satisfies the pinned
validated context contract; it must still fail if required knowledge/context
cannot be established.

## 2. Candidate Brief question

Brief §6B asks:

1. how `domain_knowledge.md` and registry `engineer_comment` reach the model;
2. why that mechanism was chosen; and
3. what an integrity engineer changes when PSV scoring guidance changes.

The design must also preserve the brief’s model/code boundary and avoid evaluator
answers entering production context.

## 3. Knowledge categories and ownership

Not every text field is maintainable general knowledge.

| Information | Authority and lifecycle |
|---|---|
| Supplied domain guidance | Preserved source bytes, reviewed knowledge item, immutable release |
| General approved PSV guidance | New scoped source, review, release and activation |
| Asset-specific fact or engineer comment | Registry snapshot |
| Current finding or related observation | Selected input snapshot |
| Generic L/I anchor or urgency/review policy | Versioned application policy and tests |
| Evaluation card or expected answer | Evaluation only; prohibited from production context |

This separation prevents an asset fact from becoming a global rule and prevents a
policy change from requiring finding-ID branches.

## 4. Design decisions

### Decision 1 — Preserve source bytes and exact provenance

**Decision.** Imported guidance retains source identity, digest and exact
supporting text. Generated extraction is a proposal until reviewed.

**Rationale.** A reviewer must be able to trace consequential guidance back to
the supplied or approved source rather than trust a paraphrase.

**Rejected alternative.** Rewriting all knowledge into an optimized prompt would
erase where a rule came from and make later review dependent on generated prose.

### Decision 2 — Separate publication from activation

**Decision.** Review and publish an immutable knowledge release, then approve
activation separately and pin the selected release/configuration by hash.

**Rationale.** “Technically valid knowledge artifact” and “approved for this
triage run” are different decisions. Separating them allows rollback and makes
the exact active surface visible.

**Rejected alternative.** Automatically activating every imported or published
item would let an extraction or editorial error change production behavior.

### Decision 3 — Use complete bounded context for this corpus

**Decision.** Provide the complete registry, engineer comments, selected
findings, deterministic related history and active knowledge to each assessment.

**Rationale.** The source package has only 21 findings and 18 equipment records,
with important cross-record relationships. Full bounded context avoids lossy
summaries and unsupported retrieval thresholds.

**Rejected alternative.** Vector RAG would add chunking, ranking and omission
failure modes without evidence that the bounded corpus exceeds the model context.

**Trade-off.** Repeated full context is expensive. The Azure v5 observation used
about 1.29 million prompt tokens, and reported cache reuse was limited relative
to cache writes. Context reuse or safe trimming is future work.

### Decision 4 — Keep selection deterministic and independently checked

**Decision.** Context assembly uses explicit scope, source and relationship rules.
The workflow independently reconstructs and validates selected IDs and hashes
before provider dispatch.

**Rationale.** Knowledge tooling should not be able to smuggle evaluation data or
silently omit required registry/finding context.

**Rejected alternative.** Letting the model retrieve arbitrary context during
generation would make production inputs difficult to enumerate and reproduce.

### Decision 5 — Keep findings out of general rule extraction

**Decision.** Findings and registry comments are assessment evidence. They are
not mined into general engineering rules or per-finding answer tables.

**Rationale.** Turning evaluation cases into reusable policy would leak answers,
overfit the 21 supplied examples and make future behavior case-shaped.

**Rejected alternative.** A lookup table keyed by finding or equipment could
appear accurate on the supplied data while failing the maintainability question.

## 5. How context reaches assessment

For each finding, code assembles a canonical bundle containing:

- the exact finding and input metadata;
- complete registry rows and all `engineer_comment` values;
- deterministic same-equipment and declared relationship context;
- active source-faithful knowledge items;
- policy/rubric identifiers and provenance; and
- hashes needed to verify the bundle before dispatch.

The provider receives this bundle through the assessment prompt. Production code
does not import the evaluator or evidence cards. Captured provider-bound context
supports a delivery claim only: it shows what was sent, not which item caused a
model decision.

## 6. Six-month PSV change

The correct edit depends on the nature of the change:

| Requested change | Engineer action |
|---|---|
| New general PSV guidance or exception | Add an approved PSV-scoped source, review extracted items, publish a release, approve activation and repin configuration |
| New fact about one PSV | Update the registry snapshot and validate the run inputs |
| New generic L/I anchor or urgency threshold | Change versioned application policy and focused tests |

A general knowledge update does not require prompt surgery:

```powershell
python -B -m triage_knowledge --store knowledge\source-first import-source `
  --source "path\to\approved-psv-guidance.md" --name "approved-psv-source"
python -B -m triage_knowledge --store knowledge\source-first review `
  --item "item-id" --expected-digest "digest" --reviewer "reviewer" `
  --reason "scope and source checked"
python -B -m triage_knowledge --store knowledge\source-first publish `
  --expected-digest "digest" --author "author" --reviewer "reviewer" `
  --reason "approved"
```

The returned release identity is then pinned by activation/run configuration.
There is not yet a dedicated activation-approval CLI. The owner must review the
output of `triage.source_context.activation_candidate`, record approval
provenance, create a new activation identity, and repin a fresh run
configuration. The existing `config\triage-activation-v8.json` cannot be reused
as freeze provenance. This manual approval step is a documented runbook gap, not
an automatic promotion.

Document 09 exercises this path in an evaluation-only store. Its retained v4
observation published old/new PSV releases, recorded a replacement and effective
date, activated each release and observed L4→L8 for the applicable synthetic
likelihood case while the unchanged tag-only control stayed L2 and explicitly
excluded the rule. V1-v3 failures are retained: the system first rejected a
harness boundary and then two knowledge rules that conflicted with the
production assessment policy. This is exploratory lifecycle evidence, not a
domain-owner-approved production change or a prospective B02 pass.

The subsequent official-store follow-up used the existing Streamlit-equivalent
CLI operations against `knowledge\source-first`, then ran the production triage
CLI on all 21 findings twice per arm. The test-informed F-1002 case repeated
L7/I8/U8 under the baseline release and L9/I8/U9 under the revised release;
F-1016 remained L2, with explicit exclusion in one revised run. The first source revision failed because experiment-status prose in
the domain text caused the model to reject its authority. This demonstrates why
workflow metadata belongs in publication/activation records, not engineering
guidance. The source rule was written and revised against test finding F-1002,
was sent in the shared all-21 context and conflicts with the reference's
suspected-passing framing. The synthetic releases remain unpromoted, and the
working candidate was reset to the eight-item baseline pending authenticated
domain and semantic review.

The experiment also found a source-editor defect: a text amendment cleared
structured scope and evidence. The editor now re-runs deterministic extraction
for one-item amendments, preserving source-derived scope/aliases/evidence and
rejecting structural edits that would create multiple items. A scoped immutable
verification release and full 21-ticket run confirmed the stored-metadata fix;
it did not narrow delivery because selection is batch-wide and the batch
contains PSVs. Per-finding knowledge isolation is not implemented. Production
knowledge remains the unchanged baseline release. Activation v12 recorded the
editor fix; activation v13 supersedes it only to add the byte-identical,
independently pinned assessment prompt.

## 7. Evidence status

| Question | Evidence | Status |
|---|---|---|
| Are supplied bytes and provenance preserved? | Source integration/readiness checks | **D-pass** for checked artifacts |
| Can reviewed content be released and promoted? | Source-owner promotion evidence and lifecycle tests | **D-pass** for software workflow |
| Does the provider receive expected context? | Captured provider-bound context and history verification | **D-pass** for delivery |
| Does knowledge causally change the intended decisions? | Reference-1.3 B02 controlled probe | **Bounded pass**: positive L6/I3→L8/I3 and both tag-only negative controls excluded the synthetic rule |
| Can a later source replacement traverse import, review, immutable release and activation? | Document 09 v1-v4 retained study | **Exploratory bounded pass** for v4 lifecycle and likelihood L4→L8; protocol was tuned after disclosed failures |
| Can the existing official editor/store change a complete 21-ticket run? | Document 09 official-store follow-up and `knowledge-kb-edit-v1-study.json` | **Test-informed delivery/influence observation**: repeat-stable F-1002 L7→L9 and F-1016 L2, with non-target variance, reference conflict and semantic review still open |
| Is selection independently domain-correct? | AI-assisted references and software checks only | **Not certified** |
| Is the current release a production-qualified default? | No accepted final run or domain approval | **No** |

The earlier result was intentionally not converted into a pass. Under reference
v1.2, the likelihood-only overlay left impact unsupported, so both positive
cases were unassessable; the negative controls remained unchanged. Reference
v1.3 is a disclosed, test-informed repair that supplies the same synthetic
impact 3 to both policies and varies only likelihood. It was executed under the
frozen v10 runtime: all four conditions completed in one send, the positive
changed L6/I3 to L8/I3, and calibrated semantic review confirmed both unchanged
F-1016 controls excluded the passing rule. This is a bounded causal and
isolation result, not engineering validation of the synthetic scores or
certification of the production knowledge base.

## 8. Rejected broader architectures

- **Autonomous web retrieval:** introduces changing, unapproved authority and
  weakens reproducibility.
- **Unrestricted generated engineering advice:** source provenance would be
  unclear.
- **Per-finding answer registry:** leaks evaluation answers and fails the PSV
  maintenance requirement.
- **Workflow-owned duplicate knowledge logic:** creates two selection authorities.
- **Automatic activation:** conflates editorial validity with operational
  approval.
- **Large retrieval platform:** unnecessary infrastructure for the bounded
  prototype and its 4–6 hour brief.

These are scope judgments for this exercise, not universal architecture claims.

## 9. Assumptions and limitations

- The supplied source package is the initial written authority.
- User amendments must be explicit, separately identified sources.
- Scope vocabulary and relationship rules bound deterministic selection.
- Source review is software/editorial evidence, not independent domain approval.
- Model and AI reviewer labels do not imply engineering expertise.
- Full context can reduce omission risk but may increase cost and distraction.
- Delivery of knowledge does not prove causal use.
- Current experiments are non-blind and test-informed.

The chronological extraction prompts, schema revisions, failed usefulness
checks, reviewer discussions and migration history remain in
`docs\original-decision-process\06_KNOWLEDGE_DESIGN_DECISION.md`. They are
valuable process evidence but are not the current maintenance interface.
