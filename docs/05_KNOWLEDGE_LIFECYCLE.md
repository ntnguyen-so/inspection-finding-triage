# Source-First Knowledge Lifecycle

The knowledge architecture separates source maintenance from runtime authority.
Extraction experiments and change-study results are evidence rather than
runtime authority; current observations remain in
[Document 07](07_KNOWLEDGE_CHANGE_STUDY.md) and
[`eval\results`](../eval/results/README.md).

## Abstract

The knowledge component turns approved source bytes into reviewable, immutable
and explicitly activated context. It is separate from ticket orchestration so a
knowledge steward can change engineering guidance without editing workflow code,
while a workflow developer cannot silently redefine knowledge authority.

The lifecycle is:

```text
approved source bytes
  -> extraction proposal with byte provenance
  -> working candidate (mutable and digest-guarded)
  -> explicit review
  -> immutable release
  -> separate activation approval
  -> deterministic selection and context assembly
  -> consumer-side re-validation
```

The supplied corpus is small: 21 findings and 18 equipment records. The system
therefore sends complete bounded source and registry context rather than adding a
vector-retrieval platform. This reduces omission risk for the prototype but
increases token cost. Captured context proves delivery, not causal model use or
domain correctness.

## 1. Responsibility and authority

`triage_knowledge` owns import, extraction, provenance, review state, immutable
release, selection and context validation. `triage` consumes a pinned context
contract and owns assessment, urgency, retries and publication. The dependency
points one way; knowledge tooling never runs triage or chooses ticket urgency.

| Information | Runtime authority | Owner |
|---|---|---|
| Supplied or approved general guidance | Preserved source bytes, reviewed item and immutable release | Knowledge steward/domain owner |
| Active release, selector, prompt and policy binding | Separately reviewed activation pinned by hash | Runtime approver |
| Asset fact or `engineer_comment` | Explicit registry snapshot supplied to the run | Asset-data owner |
| Finding and related observations | Selected input snapshot | Triage caller |
| L/I anchors and assessment rubric | `triage\assessment_policy.py` plus tests | Application-policy owner |
| Urgency and review floors | `triage\policy.py` plus tests | Application-policy owner |
| Evaluation cards and expected answers | Evaluator only; prohibited from production context | Evaluation owner |

Knowledge can provide source-backed evidence and interpretation within the
approved assessment rubric. It cannot override code-owned anchors, urgency
floors or review policy. A proposed guidance change that conflicts with those
controls is a policy change, not a knowledge-only edit.

## 2. Extraction and review gate

Imported sources retain their original bytes, digest and exact supporting spans.
Extraction creates a proposal in the mutable
`knowledge\source-first\working-candidate.json`; it never creates runtime
authority by itself. Each edit changes the candidate digest, so review and
publication commands must name the exact current digest rather than silently
overwriting another edit.

The implementation supports two proposal paths:

- deterministic C0 (rule-based, no-model) grouping and metadata extraction in
  `triage_knowledge\source.py`; and
- an optional schema-bound model extraction request for component experiments.

The active release contains eight reviewed items produced through the
source-only deterministic C0 path. Both proposal paths must pass source-span,
shape and review checks before publication. Runtime extraction behavior is
defined by `C0_POLICY` and extraction code in `triage_knowledge\source.py`, then
bound to runs by the activation's strategy hash.
[`eval\spec\knowledge_extraction.json`](../eval/spec/knowledge_extraction.json)
is the frozen component-evaluation
reference for thresholds, queries and limits; observed component results remain
under [`eval\results\knowledge`](../eval/results/knowledge).

This boundary rejects two shortcuts:

- generated summaries without exact provenance; and
- automatic publication or activation of extractor output.

## 3. Publication and activation

The mutable authoring surface is
`knowledge\source-first\working-candidate.json`. Runtime authority belongs to an
immutable `releases\sha256-*.json` artifact plus a separately reviewed
activation. Publication proves that a candidate passed the editorial/software
gate; activation decides whether that exact release, selector, prompt and policy
combination may feed a run.

Separating these decisions provides rollback and prevents a technically valid
edit from becoming active merely because it was saved. There is no dedicated
activation-approval CLI.

The current production activation is
[`config\triage-activation.json`](../config/triage-activation.json). Its
`knowledge_version` identifies the active immutable release; releases returned
by the knowledge-store `status` command are not active merely because they
exist. Runs either use this root activation through `run_triage.py` or pass an
explicit reviewed file with `--activation`.

The approver generates a draft with
`triage.source_context.activation_candidate(...)`, verifies the release,
selector, prompt and policy pins, fills the `review` record and saves a new
activation artifact. [Document 07 section 1.1](07_KNOWLEDGE_CHANGE_STUDY.md#11-change-general-psv-evidence-or-interpretation)
contains the complete approval and comparison procedure.

Rollback means generating and reviewing a new activation that points to a prior
immutable release, then repinning the run configuration. Old releases are not
edited or deleted. This manual handoff is a known runbook gap, not an automatic
promotion.

An experimental PSV source is retained outside the active release. It has no
runtime authority; existence on disk never confers authority.

## 4. Selection and provider delivery

For each assessment, the knowledge/context boundary supplies:

- the selected finding and input metadata;
- complete registry rows and `engineer_comment` values;
- deterministic same-equipment and declared related evidence;
- active source-faithful knowledge items;
- policy, prompt and release identities; and
- hashes needed for consumer-side verification.

Selection uses declared scope, aliases, source relationships and safe broadening
rules. The workflow rebuilds expected identities and hashes before provider
dispatch. Production code does not import evaluator cards or expected answers.

The current selector is `source-selector-v1`. It includes general items, matches
scoped items case-insensitively against registry equipment types, follows
declared source relationships and fails rather than silently truncating when the
context exceeds its limit. Its parameters and implementation files are hashed
into the activation's `strategy` pin.

The current selected batch contains PSVs, so scoped PSV guidance can be included
in the shared batch context. Per-finding knowledge isolation is not implemented.
A negative-control result can show that the model declined to apply an
inapplicable rule; it does not prove selector-level isolation.

Vector RAG, autonomous web retrieval and model-selected arbitrary context were
rejected for this prototype. They would add ranking, omission and authority
failure modes without evidence that the bounded corpus needs them.

## 5. Six-month maintenance change

The edit surface depends on what changed:

| Requested change | Correct change surface |
|---|---|
| New general PSV evidence or interpretation inside the existing rubric | Add a separately approved source; import, review and publish a new knowledge release; if guidance overlaps prompt-embedded interpretation, complete the [Document 06 prompt-compatibility review](06_TRIAGE_WORKFLOW.md#prompt-authority-and-controlled-change) before activation |
| New fact about one asset | Create a new registry snapshot outside the supplied package and pass it with `--registry`; do not edit the preserved source package |
| New generic L/I anchor or scoring rule | Update `triage\assessment_policy.py` and focused tests |
| New urgency threshold or review floor | Update `triage\policy.py` and focused tests |
| New extraction grammar or selector behavior | Update `triage_knowledge\source.py` or `triage_knowledge\retrieval.py` and rerun the controlled component evaluation |

Knowledge, policy, prompt, selector and extraction-code changes also change
activation compatibility hashes. After their focused review/tests, each requires
a new reviewed activation and fresh run configuration as described in section 3.
A new registry snapshot is a run input rather than an activation change, but it
still requires fresh evidence bound to its exact bytes.

A general knowledge update uses the repository-owned lifecycle rather than
prompt surgery. The complete runbook is
[Document 07 section 1.1](07_KNOWLEDGE_CHANGE_STUDY.md#11-change-general-psv-evidence-or-interpretation):
import the source, run `check` to obtain item IDs and the current digest, review
every pending item using the latest digest, publish to obtain a
`knowledge_version`, create and approve an activation, then generate comparison
tickets in a new run directory.

The new release is not active until section 3's separate approval and repinning
step is complete. Document 07 sections 2-8 record bounded lifecycle evidence;
its synthetic PSV material remains outside runtime authority. Experiment
metadata belongs in publication records rather than engineering source text,
and knowledge cannot silently override the production rubric.

## 6. Evidence and limits

| Claim | Evidence | Interpretation |
|---|---|---|
| Source bytes, spans and eight reviewed baseline items are preserved | [`source-owner-promotion-1`](../eval/results/knowledge/source-owner-promotion-1) | Software/editorial provenance demonstrated; not domain certification |
| Reviewed content can become an immutable release and activation candidate | [`tests\test_source_workflow.py`](../tests/test_source_workflow.py) and promotion evidence | Lifecycle mechanics demonstrated; activation approval remains manual |
| Expected context reached the provider boundary | [Final run evidence](../eval/results/triage/structured-planning-v31/final/evidence/run.json) | Delivery demonstrated; causal use is not implied |
| A bounded knowledge change can influence one declared comparison | [B02 negative-control review](../eval/results/triage/v10-calibration/b02-execution/negative-control-semantic-review.json) | Model-level positive change and rule exclusion; not selector isolation or calibrated engineering truth |
| A source addition or edit can traverse the real lifecycle | [Document 07](07_KNOWLEDGE_CHANGE_STUDY.md) and [retained study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json) | Bounded lifecycle evidence; experimental releases remain inactive |

The current evidence does not establish independent domain correctness,
population-level model reliability, per-finding knowledge isolation or automatic
operational approval. Full context also creates a material token-cost trade-off;
the retained delivery's simple API-equivalent estimate attributes about 82.8% of
its cost proxy to input tokens. Safe context reuse or trimming remains future
work; Document 04 records the calculation and billing boundary.

## 7. Reader path

- Architecture and authority boundaries: sections 1-4 above.
- Change-surface map: section 5 above.
- Step-by-step maintenance runbook and validation study:
  [Document 07](07_KNOWLEDGE_CHANGE_STUDY.md).
- Observed evidence: [`eval\results\README.md`](../eval/results/README.md) and
  [`eval\results\knowledge`](../eval/results/knowledge).
