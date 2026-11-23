# Source-First Knowledge Lifecycle

The knowledge component separates editing sources from approving what a run may
use. Extraction experiments and change studies provide evidence. Their results
do not automatically become approved guidance. Current observations remain in
[Document 07](07_KNOWLEDGE_CHANGE_STUDY.md) and
[`eval\results`](../eval/results/README.md).

## Abstract

The component turns approved source files into context that can be reviewed,
released and approved for use. A release is **immutable**: its contents cannot
be edited after publication. **Activation** is a separate approval of the exact
release and settings that a run may use.

The knowledge steward, the person responsible for guidance, can update sources
without editing the ticket workflow. A workflow developer cannot silently change
which guidance has authority.

The lifecycle is:

```text
approved source bytes
  -> extraction proposal linked to exact source bytes
  -> editable working candidate protected by a content hash
  -> explicit review
  -> immutable release
  -> separate activation approval
  -> deterministic selection and context assembly
  -> independent checks by the consuming workflow
```

The supplied material is small: 21 findings and 18 equipment records. The system
sends the complete source and registry context, within a size limit. It does not
add a vector-retrieval platform, which would search for related text using
numerical representations. Sending the complete context reduces the risk of
leaving out evidence, but costs more tokens. Saved request context shows what
was sent. It does not prove that the model used it or that the guidance is correct.

## 1. Responsibility and authority

`triage_knowledge` imports sources, extracts guidance, records where it came from,
tracks review, publishes releases, selects context and checks it. `triage` uses
that context through a fixed contract and controls assessment, urgency, retries
and ticket publication. Knowledge tools never run triage or choose ticket urgency.

**Pinned** means identified by an exact version or hash, not simply by a file
name. **L/I** below mean likelihood and impact. A **selector** is the code that
chooses context for a run.

| Information | Runtime authority | Owner |
|---|---|---|
| Supplied or approved general guidance | Original source bytes, reviewed item and immutable release | Knowledge steward/domain owner |
| Active release, selector, prompt and policy combination | Separately reviewed activation identified by hash | Runtime approver |
| Asset fact or `engineer_comment` | Explicit registry snapshot supplied to the run | Asset-data owner |
| Finding and related observations | Selected input snapshot | Triage caller |
| L/I anchors and assessment rubric | `triage\assessment_policy.py` plus tests | Application-policy owner |
| Urgency and review floors | `triage\policy.py` plus tests | Application-policy owner |
| Evaluation cards and expected answers | Evaluator only; prohibited from production context | Evaluation owner |

Knowledge provides evidence and interpretation supported by sources, within the
approved scoring rules. **Anchors** describe what different L/I scores mean.
An **urgency floor** is a minimum urgency required by a rule. Knowledge cannot
override those code-owned anchors, floors or review rules. Guidance that conflicts
with them requires a policy change, not just a knowledge edit.

## 2. Extraction and review gate

Imported sources keep their original bytes, digest (content hash) and exact
supporting text spans. Extraction proposes items in
`knowledge\source-first\working-candidate.json`, which can still be edited.
Extraction alone does not approve those items for runtime use.

Each edit changes the candidate digest. Review and publication commands must
name the current digest. This prevents a command from silently acting on a
candidate that someone has changed since it was checked.

The implementation supports two proposal paths:

- deterministic C0 grouping and metadata extraction, using rules and no model, in
  `triage_knowledge\source.py`; and
- an optional model extraction request with a required response structure, for
  component experiments.

The active release has eight reviewed items from the source-only C0 path.
Both paths must pass checks of supporting source spans, item structure and
review status before publication. `C0_POLICY` and the extraction code in
`triage_knowledge\source.py` define runtime extraction. The activation's
strategy hash fixes that behavior for a run.
[`eval\spec\knowledge_extraction.json`](../eval/spec/knowledge_extraction.json)
is the frozen evaluation reference for component thresholds, queries and limits.
Observed component results remain
under [`eval\results\knowledge`](../eval/results/knowledge).

This boundary rejects two shortcuts:

- generated summaries without exact source records; and
- automatic publication or activation of extractor output.

## 3. Publication and activation

Authors edit `knowledge\source-first\working-candidate.json`. A run may use only
an immutable `releases\sha256-*.json` file with a separately reviewed activation.
Publication shows that the candidate passed content-review and software checks.
Activation approves its exact combination of release, selector, prompt and
policy for use.

These separate decisions allow rollback to an earlier release. Saving a
technically valid edit does not make it active. There is no dedicated
activation-approval command-line interface (CLI).

The current production activation is
[`config\triage-activation.json`](../config/triage-activation.json). Its
`knowledge_version` identifies the active immutable release; releases returned
by the knowledge-store `status` command are not active just because they exist.
Runs either use this root activation through `run_triage.py` or pass an
explicit reviewed file with `--activation`.

The approver generates a draft with
`triage.source_context.activation_candidate(...)`. They check the pinned
release, selector, prompt and policy, fill the `review` record, and save a new
activation file. [Document 07 section 1.1](07_KNOWLEDGE_CHANGE_STUDY.md#11-change-general-psv-evidence-or-interpretation)
contains the complete approval and comparison procedure.

Rollback means creating and reviewing a new activation that points to an earlier
immutable release, then updating the run configuration to match. Old releases
are not edited or deleted. Approval still needs this manual handoff; the lack
of a dedicated approval CLI is a known gap, not automatic promotion.

An experimental pressure safety valve (PSV) source is saved outside the active
release. It is not approved for runtime use. A file's presence on disk never
gives it authority.

## 4. Selection and provider delivery

For each assessment, the knowledge/context boundary supplies:

- the selected finding and input metadata;
- complete registry rows and `engineer_comment` values;
- same-equipment evidence selected by code and explicitly declared related evidence;
- active knowledge items that preserve their source meaning;
- policy, prompt and release identities; and
- hashes that the consuming workflow uses to check the context.

Selection uses each item's declared scope, alternate names, source relationships
and rules for safely including broader context. Before sending a request, the
workflow independently rebuilds the expected identities and hashes.
Production code does not import evaluator evidence cards or expected answers.

The current selector is `source-selector-v1`. It includes general items and
matches scoped items to registry equipment types without regard to letter case.
It follows declared source relationships. If context exceeds the size limit,
selection fails instead of silently cutting off text. The activation's
`strategy` hash identifies the selector's parameters and implementation files.

The current batch includes PSVs, so PSV guidance can enter context shared by the
whole batch. The selector does not isolate knowledge for each finding.
A **negative control** is a case where the changed rule should not apply.
Its result can show that the model declined to apply an irrelevant rule. It
cannot show that the selector kept that rule out of the request.

We rejected vector RAG (retrieval-augmented generation using vector search),
automatic web retrieval and unrestricted model selection of context. They would
add risks from ranking, missing evidence and unapproved sources. There is no
evidence that this small, size-limited collection needs them.

## 5. Six-month maintenance change

Choose the file or component to edit based on what changed:

| Requested change | Where to make it |
|---|---|
| New general PSV evidence or interpretation within existing scoring rules | Add a separately approved source. Import, review and publish a new knowledge release. If guidance overlaps interpretation in the prompt, complete the [Document 06 prompt-compatibility review](06_TRIAGE_WORKFLOW.md#prompt-authority-and-controlled-change) before activation |
| New fact about one asset | Create a new registry snapshot outside the supplied package and pass it with `--registry`; do not edit the preserved source package |
| New generic L/I anchor or scoring rule | Update `triage\assessment_policy.py` and focused tests |
| New urgency threshold or review floor | Update `triage\policy.py` and focused tests |
| New extraction rules or selector behavior | Update `triage_knowledge\source.py` or `triage_knowledge\retrieval.py` and rerun the controlled component evaluation |

Changes to knowledge, policy, prompt, selector or extraction code change the
hashes used to check activation compatibility. After focused review and tests,
each needs a new reviewed activation and fresh run configuration, as described
in section 3. A new registry snapshot changes run input, not activation.
It still needs fresh evidence tied to its exact bytes.

For a general knowledge update, use the repository's source lifecycle rather
than inserting guidance into the prompt. The complete procedure is in
[Document 07 section 1.1](07_KNOWLEDGE_CHANGE_STUDY.md#11-change-general-psv-evidence-or-interpretation):
import the source; run `check` for item IDs and the current digest; review every
pending item using the latest digest; publish to obtain a `knowledge_version`;
create and approve an activation; then generate comparison tickets in a new
run directory.

The new release is not active until the separate approval and configuration
update in section 3 is complete. Document 07 sections 2-7 record the limited
lifecycle evidence. Its synthetic PSV material is not approved for runtime use.
Record experiment status in publication metadata, not engineering guidance.
Knowledge cannot silently override production scoring rules.

## 6. Evidence and limits

| Claim | Evidence | Interpretation |
|---|---|---|
| Source bytes, spans and eight reviewed baseline items are preserved | [`source-owner-promotion-1`](../eval/results/knowledge/source-owner-promotion-1) | Source history and software/content-review steps demonstrated; not domain certification |
| Reviewed content can become an immutable release and activation candidate | [`tests\test_source_workflow.py`](../tests/test_source_workflow.py) and promotion evidence | Lifecycle steps demonstrated; activation approval is still manual |
| Expected context reached the provider boundary | [Final run evidence](../eval/results/triage/structured-planning-v31/final/evidence/run.json) | Shows delivery, not proof that the model used it |
| A limited knowledge change can affect one declared comparison | [B02 negative-control review](../eval/results/triage/v10-calibration/b02-execution/negative-control-semantic-review.json) | The model changed the target case and excluded the rule in the control. This is not selector isolation or calibrated engineering truth |
| A source addition or edit can pass through the real lifecycle | [Document 07](07_KNOWLEDGE_CHANGE_STUDY.md) and [retained study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json) | Limited lifecycle evidence; experimental releases are still inactive |

Current evidence does not establish independent engineering correctness,
reliability across a wider population, knowledge isolation for each finding, or
automatic approval for operational work. Full context also costs many input
tokens. In the saved delivery, input tokens account for about 82.8% of the simple
estimate at equivalent API rates. Safe context reuse or trimming remains future
work. Document 04 explains the calculation and why it is not a Copilot bill.

## 7. Reader path

- Architecture and authority boundaries: sections 1-4 above.
- Which component to edit: section 5 above.
- Step-by-step maintenance runbook and validation study:
  [Document 07](07_KNOWLEDGE_CHANGE_STUDY.md).
- Observed evidence: [`eval\results\README.md`](../eval/results/README.md) and
  [`eval\results\knowledge`](../eval/results/knowledge).
