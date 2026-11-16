# Knowledge Module: Design Decision and Evaluation Contract

## 1. Status, scope and authority

This is the **single current design decision** for the replacement knowledge
module. It consolidates the owner's source-fidelity, editing, active-knowledge,
relevant-retrieval and evaluation requirements. Document 06 is a superseded-design
pointer, not another specification. Existing code remains legacy; this document
does not claim implementation, evaluation success, content approval or activation.
Root `DESIGN.md` remains reserved for the project owner.

Authority: the supplied candidate brief/domain, then documents 02/03 and frozen
reference 1.2. The owner additionally requires explicit evaluation of knowledge
extraction, whether performed by code or the existing LLM inference library.
The component checks below support B01-B03, A04/C04, D04 and X01/X02; they neither
replace those system scenarios nor certify engineering truth.

No outside engineering knowledge, autonomous web retrieval, evaluator answers or
per-finding answer tables enter the knowledge store. Initial content is only the
unchanged supplied `reference\domain_knowledge.md`. Later explicit user amendments
are separate, declared sources; user input is not permission to disguise outside
material or violate the exercise/frozen policies. Findings and registry comments
are factual query inputs, not general-rule extraction sources.

This is the replacement implementation's evaluation contract. The owner's later
implementation request authorizes an explicitly experimental Copilot comparison
through `llm_inference`, not a production release or a claim that every gate
passes. Fixture/reference and execution identities must be frozen before sends;
missing human review or unobservable accounting remains a qualification blocker.

## 2. Evaluate the responsibilities separately

| Stage | Question and observed artifact |
|---|---|
| Intake/extraction | Did source-exact units, conditions, exceptions, scope and context relationships survive? Retain source bytes, raw proposals and validation results |
| Editorial review/lifecycle | Can a user understand/correct/reject a proposal, publish a reviewed revision and withdraw it without leakage? Retain edits, review and release |
| Relevant retrieval | Does the actual tool return necessary active source passages and their qualifiers, not merely lexical matches? Retain query, selected atoms and omissions |
| Workflow handoff | Did those exact passages and the correct registry comments reach the provider? Retain actual request capture and independent hashes |
| Triage outcome | Does workflow interpret evidence into defensible L/I and code-derived U? Remains the separate system evaluation |

Passing schema, copying every byte or returning all active text is not proof of
good extraction structure, useful retrieval or correct triage. Evaluate raw
automation **before human correction** and reviewed output **after correction**
separately. Never present repaired proposals as unassisted model accuracy.

## 3. Evaluation data and independent expectations

Use the existing test runner and JSON evidence conventions, not a new evaluation
platform. Proposed component manifest: `eval\spec\knowledge_extraction.json`;
fixtures under `eval\data\knowledge_extraction`; observations under
`eval\results\knowledge\extraction\<run-id>`. These are planned files, not existing
commands/artifacts or amendments to the frozen triage reference.

### 3.1 Corpus and split

The original domain file is a shared, already-exposed, non-blind fidelity smoke,
not independent gold. In addition prepare **eight small, source-contained
synthetic documents**, four development and four evaluation, split by source
family rather than chunks. Do not put near-duplicate templates across the split.
Use artificial equipment/topic labels where necessary, not new real-world
engineering assertions; these fixtures never become shipping knowledge.

The eight-document roster must collectively cover explicit scopes, global rules,
negation/uncertainty, conditions/exceptions, cross-section qualifications, aliases
written in the source, contradictory/ambiguous passages and duplicate/repeated
clauses. Layout mutations additionally cover preambles, nested lists/headings,
UTF-8/BOM/CRLF, code-fence text and unsupported/corrupt input.
Before implementation comparison, the manifest assigns each source/family,
partition and covered requirement and pins its hash.
Family means shared template/authoring ancestry, including rewrites/mutations;
record that lineage and assign the four-plus-four split before either candidate's
outputs. Every named semantic phenomenon must occur in evaluation, not only
development. Record the per-source counts of labelled conditions, negations,
scopes, aliases, exceptions and context links; layout mutations are additional
deterministic tests outside the 24-query denominator.

Each synthetic source has **three frozen query contexts**: scoped match,
qualifier/cross-topic context, and unknown/ambiguous scope requiring conservative
handling: 24 nominal retrieval cases, 12 per partition. Every scoped query has
at least one declared irrelevant scoped passage so usefulness can be measured.
Keep the original smoke and deterministic lifecycle/failure mutations separate
from those denominators.
The evaluation efficiency denominator is exactly eight queries: the scoped-match
and qualifier query for each of the four evaluation sources; the four unknown/
ambiguous queries are separate conservative-handling cases. Pin their actual IDs.
Development uses its four-source index plus the common original domain; evaluation
uses only its four-source index plus that same common source. Never combine both
synthetic partitions into an index during development.

The evaluation sources and labels are unavailable for development tuning. They
are exposed only after code, extraction prompt/model/configuration and selector
are frozen. Since an AI-assisted fixture author may already know the material,
record actual exposure; do not claim independent or statistically blind gold.
Any post-evaluation fix is disclosed and subsequent work is regression, not a
fresh blind test.

### 3.2 Source-anchored reference, not extractor-generated gold

Before running either candidate, a source reviewer defines canonical **source
atoms**: exact byte spans with source hash, whole rule/condition/exception roles,
required context relationships and ambiguity notes. These evaluation-only atoms
need not match either extractor's item boundaries.

For each query label required, permitted-context and irrelevant source atoms,
plus required failure/broadening behavior. A selected passage covers an atom only
if it contains the atom's full text and necessary associated conditions; overlap
with a fragment is insufficient. Duplicate passages earn no extra recall.
This prevents an extractor from grading its own item IDs or exploiting chunk size.
Coverage is computed from the union of returned source-byte intervals, keyed by
source identity: an atom may cross code-unit/item boundaries but its full spans
and required contextual atoms must be covered. Do not require the reference to
copy either extractor's partition. Equivalent valid groupings/context graphs are
allowed; cross-group qualifications use links rather than duplicated source units.
Freeze the common byte-preserving unitizer before fixture/reference finalization.

The extractor receives the submitted source and extraction schema/instructions
only, never atom labels, expected scopes/links, query answers, triage cards or
test findings. Editorial reviewers see source and proposal without the evaluation
answer sheet. Evaluators compare retained raw/reviewed artifacts with the frozen
reference, not the extractor's explanations.

Ambiguous reference judgments stay `needs_review` with cited spans; they cannot
count as passes or be dropped from denominators. An optional semantic reviewer
must first detect seeded missing-negation, detached-exception, reversed-direction
and unsupported-alias errors, while accepting supported and unresolved controls.
Calibrate the actual reviewer/configuration; a previous triage-review file or the
extractor's self-grading does not qualify it. No paid LLM judge is assumed here.
On the finite calibration controls require zero false accepts of the seeded
critical errors, correct supported controls and unresolved cases left unresolved.
Report all control counts; calibration is not proof of general reviewer quality
and the semantic judge is not the sole pass authority.

## 4. Metrics, failure conditions and prototype acceptance

These are declared prototype gates on the fixed suite, not panel-prescribed
percentages or future-world guarantees. Report per-source and per-query results
alongside totals; no weighted composite may hide a critical failure.

| Gate | Required evidence/threshold |
|---|---|
| Source fidelity | 100% original bytes accounted for exactly once in accepted extraction coverage; all materialized knowledge text comes from the cited source units, zero invented/altered text |
| Semantic preservation | All labelled critical negations, uncertainty, qualifications, prior directions and required context retained; zero unsupported restrictive scope/alias or critical detached exception in validated automatic output, for both C0 and C1 |
| Retrieval completeness | Required-atom recall 1.0 on every answerable frozen case, including all critical atoms; ambiguous/missing-input cases produce the declared broadening or explicit inability |
| Lifecycle/isolation | Zero retired/future/expired/replaced text, rejected suggestions, evaluator answers or unauthorized finding descriptions in result/index/provider payload |
| Fail-closed behavior | Malformed/invented references, bad bindings, known dangling dependencies, unsupported versions and size overflow stop activation/assessment; no partial success, stale-release substitution or silent source loss |
| Reproducibility | Code-only output and fixed released-index retrieval are byte-deterministic under fixed pins and row reordering; LLM variation is measured, not declared deterministic |
| Human publication boundary | Every actual publication binds review to the exact candidate; edited content has new user-source lineage, never falsely cited as original |

Invalid raw LLM outputs are retained and rejected, not accepted as knowledge.
Report first-attempt failures, semantic errors, recovery and final inability
separately. A recoverable format error is not concealed by a later valid response.
Any validated critical semantic error blocks qualification of that extraction
profile even if a human later repairs it.
Here "validated critical error" means structurally accepted automatic output
that the evaluator finds wrong, not an invalid output correctly rejected by a
validator. Apply the distinction and gates symmetrically to C0/C1. Report scope,
alias and context-link precision/recall against the labelled source inventory
as separate diagnostics, including over-inclusion and unsafe exclusion.
The exposed original-source smoke must also pass fidelity/critical-semantic gates
for either usable profile; it is excluded from paired effort/selection averages,
not exempt from correctness.

### 4.1 Useful selection, not an all-active loophole

For the scoped-query subset fixed in the manifest, report required-atom recall,
non-required/non-permitted scoped bytes returned, total provider bytes, expansion
frequency and the complete active-corpus baseline. General/context-required
passages are not falsely penalized as irrelevant.

Let `B(q)` be unioned active scoped source bytes labelled neither required nor
permitted-context for query q, and `R(q)` the subset of those bytes returned.
Reduction is `1 - R(q)/B(q)`, not a score based on item counts or repeated copies.
The eight preregistered scoped evaluation queries must each have `B(q)>0`.
To claim **selective retrieval qualified**, all hard gates and per-query recall
1.0 must pass, and reduction must be at least **20% on each of those eight
queries**. Report median, individual fractions and absolute bytes; no median may
hide a zero-reduction case and no post-hoc case selection is allowed.
A safe all-active implementation
may establish fidelity/delivery but fails this usefulness claim. It cannot be
marketed as proven relevant selection.

The mostly general original document may legitimately return in full. Synthetic
selection success does not establish selective recall on field knowledge.

### 4.2 Review effort, reliability and cost

Measure normalized corrective operations, not UI clicks or extractor self-reports.
Freeze this unit-weight taxonomy: add/remove an atom-level scope assignment;
add/remove an alias assignment anchored to source atoms; add/remove a required
context relation; and a necessary group split/merge/reassignment, logged once
with its affected atoms. Normalize shared group metadata to source-atom facts,
deduplicate repeated edit events and do not charge stylistic edits between
equivalent source-faithful groupings or equivalent context closures.
Sum operations across the four paired evaluation sources; report source-level
counts too, not the mean of per-source percentage improvements.

Strategy labels are hidden from editorial reviewers; record any recognizability.
A reviewer must not review both candidates on the same source. Use different
reviewers for that pair and cross their candidate assignments across sources,
with a fixed order/assignment schedule before outputs. Record identity, exposure,
actual corrections and any unblinding/learning limitation. The editor sees no
answer sheet; a later evaluator checks the resulting state against the frozen
source-backed constraints, not a mandatory unique gold partition.
The target end state is source-faithful, appropriately scoped reviewed knowledge,
not merely clicking Approve on a coarse document. Actual review time is optional
observed evidence; do not invent productivity savings from correction counts.
If suitable independent source review is unavailable, the review-benefit gate
is unexecuted and C1 remains unqualified, not automatically approved by an AI
self-review. One reviewer repeating a source is exploratory evidence only.

Report raw first-attempt validity, per-input success within budget, refusals,
broadenings, critical errors and repair counts. For LLM extraction repeat the two
evaluation sources selected by sorted source hash **twice additionally** after
their primary run, with unchanged configuration. All three outputs must satisfy
critical fidelity/semantic gates; report atom/relationship agreement and drift.
Do not demand identical item IDs or claim statistical stability from two sources.
Pin the chosen two IDs after hashing/freeze, before any output; do not edit
fixtures to manipulate that selection.

Record source/prompt/schema/code/model/parameter hashes, raw requests/responses
when available, SDK/runtime, attempts/errors, exposed tokens/cache, latency and
usage/cost. Unknown USD or hidden HTTP counts remain unknown. Code runtime,
review effort and LLM inference are separate cost categories.

### 4.3 Deterministic evaluator and handoff controls

Before grading production output, exercise the grader with independently worked
perfect and adversarial controls: fragment-only coverage, duplicate atoms,
missing negation, detached exceptions, reversed directions and unsupported
aliases. Check manually worked interval-union/irrelevant-byte arithmetic,
equivalent partitions/context closures, unresolved judgments retained in the
denominator, semantic identity under row reordering and changed source hashes
after a one-byte mutation. These establish grader behavior, not module success.

Lifecycle fixtures separately include retired, future, expired and replaced
items whose text would otherwise match the query, cutoff boundaries, successor
expiry without ancestor resurrection and broken required context. Add malformed
unit IDs, unsupported versions, wrong row-content bindings and result overflow.
Verify failures leave existing publication unchanged and supply no usable partial
knowledge. Counts are separate from the 24 semantic retrieval cases.

B01 handoff evidence compares actual provider-bound passages and the correct
`engineer_comment` bytes with independently read/hash-bound authorized inputs;
repeating the producer's own manifest is insufficient. Also check provider-bound
exclusion of inactive/evaluator/test content under B01/D04 isolation checks.
B03 remains the concrete engineer-edit path, maintenance trade-off and change
impact, as specified by unchanged reference 1.2. B02 still needs the actual downstream
knowledge-change experiment and semantic assessment; extraction/selection metrics
do not establish changed triage decisions or repair the historical B02 result.

## 5. Fair code-versus-LLM comparison and decision rule

| Candidate | Extraction behavior | Reason to evaluate |
|---|---|---|
| C0: code baseline | Code-fence-aware Markdown-heading groups over common source units; extract explicit `Scope: <literal>` / `Equipment: <literal>` labels and source-written `Aliases:` declarations by a fixed grammar, cite their source units; other scope is general | Credible reproducible baseline, not deliberately empty metadata; may still miss scope expressed in prose |
| C1: source-grounded LLM extraction | Existing `llm_inference` proposes groups/scopes/context links over code-assigned source-unit IDs; code validates and users review | May recognize dispersed conditions and scope in less structured input; can hallucinate metadata or detach conditions |
| Unrestricted generative rewrite | Generates new rule prose/engineering advice | Rejected: conflicts with source adherence; not a candidate to legitimize by scoring |

Freeze C0 grammar, unitization and matching before seeing C1 output or finalizing
the fixture set; no fixture-specific parser patches. Both use identical selector
parameters. Labels with plurals/hyphens or source-written aliases must appear in
the evaluation roster; count conservative expansion honestly rather than fitting
fixtures only to convenient exact-label matching.

Use identical source bytes, code validators, lifecycle, selector, query cases and
reference for C0/C1. Change only extraction strategy. Separate **raw proposal
quality**, **review corrections** and **retrieval from genuinely reviewed releases**.
Never mark an unreviewed index reviewed merely to make production retrieval narrow.
Raw metadata can be assessed against reference without publishing it; any
diagnostic bypass must be isolated and cannot establish the production gate.

The frozen evaluation comparison uses the four held-out sources, not development
averages. Original-source smoke and repeats are separate rows. Same model/prompt/
settings apply to all C1 primary evaluation/repeat slots. No best-of-N selection,
semantic retry-to-improve-scores, cherry-picked runs or unreported manual fixes.

**Decision now:** implement C0 as the mandatory baseline and support C1 as an
explicit, evaluated extraction strategy through the inference library, not a
different product or implicit fallback. No evidence currently selects C1.

**C1 eligibility:** all hard gates and reliability checks pass, and on the paired
evaluation sources it requires at least **25% fewer normalized corrective
operations** than C0 **and at least four fewer operations**, on a C0 baseline
of **at least eight operations** summed across the four sources, with zero
accepted-wrong critical errors. If that baseline is smaller or suitable blinded
review is unavailable, benefit is not demonstrated. Both reviewed-index outputs
must meet the selective-retrieval gate; the original smoke and repeats must pass
their correctness gates. These are conservative prototype criteria on a tiny
suite, not measured population rates or a claim that code/LLMs are intrinsically
superior. Actual paid cost/latency must fit
the preapproved run budget and be disclosed; passing the edit threshold is not
automatic cost-benefit approval. Choose code on a tie, inconclusive reviewer
judgment, failed gate or unproven benefit. C1 is enabled for user intake only
after an explicit profile/model/configuration qualification and owner decision.
Never claim the actual source is extracted better solely because it used an LLM.

## 6. Bounded execution plan and evidence freeze

Planned C1 slots: eight synthetic sources plus one original-source smoke, then
four extractions for the two repeated evaluation sources: **13 nominal sends**,
at most **26 total provider attempts**, maximum two per slot including SDK
retries. Only transport/structural-validation recovery is eligible; semantic
failure is recorded without retry. Code-only extraction/retrieval tests consume
no model slots; their computation and review are not claimed free.
Freeze the recoverable transport/error-code and structural-error allowlist before
dispatch. A retry reuses the same source, prompt, schema and settings; no semantic
feedback or edited source is smuggled into recovery. First-attempt failures remain
visible even after recovery. C0 failures/recovery are recorded symmetrically.

Before any send, freeze sources/labels/splits, candidates, prompts/schema,
tokenization/selector, model/deployment/provider, parameters, token/time/size
limits, retry classification, prices/monetary ceiling, reviewer and fixed slots.
Reserve a single persistent phase ledger before dispatch; interrupted/failed
slots are not silently reset. Stop if the budget or a required development gate
fails. Tuning after a run requires disclosed new approval/budget and must not
relabel evaluation-informed work as untouched evaluation.
The four development C1 slots are fixed-profile measurements, not a free tuning
round inside these 13 slots. Report planned, attempted, failed and unexecuted
slots separately; budget exhaustion aborts qualification rather than silently
skipping a failed input. An interrupted reserved send remains accounted for.

Use the existing direct inference adapter for a strict accounting run, with
hidden SDK retries disabled. An explicit Copilot experiment may supply
development observations, but hidden HTTP/token/cost controls remain limited and
must not be claimed equivalent to strict acceptance. A strict deployment and
monetary ceiling are **not chosen/authorized by this design**; strict execution
and qualification are blocked until they are recorded and approved.

The owner's implementation instruction selects **Copilot** for this increment's
experimental observations. Pin catalog-enabled `gpt-6-luna`, reasoning `low`,
90-second timeout and a fresh extraction-specific ledger: 13 nominal slots,
maximum 26 reserved application sends, at most two per slot. This does not impose
an enforceable USD or hidden-HTTP ceiling: both remain unknown and strict-cost/
attempt qualification cannot pass. It does not reuse the spent B02 ledger.

Fixtures/manifests are frozen before either candidate's evaluation outputs are
seen. The proposed component manifest is separate from unchanged triage reference
1.2. If a genuine source/reference semantic change is needed, follow AGENTS
section 6 with bounded review/versioning; never weaken old expectations to pass.

## 7. Extraction, storage and user review decisions

### 7.1 Source units and LLM boundary

Accept UTF-8 Markdown/plain text upload or exact submitted UI text, retaining
original bytes/BOM/line endings. Reject unsupported encodings/formats/oversize;
no automatic PDF/OCR/web conversion. Code assigns stable source-unit IDs and exact
byte ranges on UTF-8/line boundaries, preserving preambles, lists and code fences.
Splitting never cuts CRLF or drops formatting/source bytes.

C0 groups those units mechanically. C1 receives those units and only the
submitted source, through `llm_inference` with a closed output schema. It returns
unit-ID groups and source-grounded metadata/context-link proposals, not new rule
text, scores or model-chosen urgency. Materialize all knowledge text from source
bytes in code. Reject unknown/duplicate/omitted units, extra fields, fabricated
references and unsupported metadata. Coverage requires the complete source
partition; complete byte coverage does not prove correct grouping/links.
Empty or ambiguous metadata is explicit, never filled with LLM-recalled policy.
Scope/alias proposals carry source-unit IDs and exact evidence spans; labels
must be source literals, not invented synonyms. Context links cite both endpoints
and their supporting source spans. The same requirements apply to C0 metadata.
Code checks references, literal presence and structural consistency, not semantic
entailment. An unsupported restrictive suggestion cannot be silently rewritten as
general to hide an error; retain the raw failure and require explicit correction.

LLM grouping/label suggestions are interpretations, not source-certified truth.
Exact quotes prove location only; user content review checks entailment,
qualifications and safe scope. Retain the raw response and validation failure,
not only the eventual approved state. An extraction failure leaves a visible
pending/failed intake and any existing release unchanged. Switching to C0 is an
explicit new strategy attempt with separate evidence, not concealed C1 success.
Editing/review does not silently rerun paid extraction. An explicit re-extraction
creates a separately recorded, budgeted attempt and cannot reset the phase ledger.

### 7.2 Records, lifecycle and UI

Keep the existing package and strict local JSON/Streamlit, one trusted writer;
no database/service/vector store. Record immutable source blobs, logical item IDs,
content-hashed revisions, reviewed scope/alias/context links, per-span coverage
decisions and immutable releases. Hash canonical complete records, excluding only
their own IDs; review/publication metadata is bound to the release. Code defines
one versioned canonical serialization and deterministic address ordering.
Scope and alias fields belong to the content-hashed revision. Store context
edges separately in the complete hashed release, with exact item/revision
endpoints and evidence. This avoids mutually dependent revision hashes while
allowing cyclic context groups. Validate edges at publish and query; an endpoint
edit invalidates the old binding and needs explicit reviewed rebinding, never an
automatic move to a newer revision.

Text edits create a new user-authored source/revision, with explicit ancestry;
they never modify the original citation or supplied package. Review all original,
proposed and neighbouring/context-linked text. An unresolved intake/conflict/
scope case blocks that draft's publication. Reject-with-reason at intake differs
from withdrawing previously active content. Initial unamended release covers the
entire original domain; later reviewed edits/retirements carry an explicit diff.

An eligible revision belongs to the reviewed pinned release, is active, satisfies
inclusive-from/exclusive-until bounds and is not replaced at the cutoff.
Replacement edges are immutable release-bound decisions with explicit start:
before it, predecessor may qualify; at/after it, ancestors are suppressed even
if the successor later expires or is retired. Retiring a scheduled successor
does not cancel its edge; show any future gap. Cancellation before start or
restoration afterwards requires an explicit reviewed change/new revision.
No automatic resurrection, latest-alias reload or global revocation of old pins.

Withdrawal is explicit item retirement. A source-withdrawal request lists direct
items/known edited descendants for user decision; no hidden ancestry cascade.
Context links bind exact revisions and are checked at publish and query time,
including known windows. A changed linked revision requires reviewed rebinding,
not following a logical ID to arbitrary newer words.

Streamlit supports import, candidate inspection (C0/C1 identified), per-item
accept/edit/reject/pending, scope/context review, lifecycle, exact active preview,
diff and candidate-bound publish. Show model failures/cost where exposed.
Every edit invalidates review. Publish does not alter workflow configuration;
the workflow operator separately pins a release after compatibility approval.
Show deployment status as unknown if the configured pin is unavailable.
Local author/reviewer declarations are unauthenticated, not enterprise approval
or engineering certification.

## 8. Module-owned relevant retrieval and callable contract

The module owns extraction/indexing, lifecycle filtering, relevant selection and
packaging; workflow must not duplicate ranking/chunking/selection. It owns
neither L/I assessment nor U calculation. Explicit numeric rules in an authorized
source are preserved as text; editable text cannot execute workflow policy.

```text
get_triage_knowledge(
    query_context, *,
    knowledge_version, assessment_time, expected_strategy,
    allowed_input_binding, max_bytes
) -> KnowledgeResult
```

All keyword arguments are required trusted run bindings. Start with an ordinary
in-process function/JSON tool wrapper, not a server or model-controlled loop.
Optional future model function-calling invokes the same API with bindings hidden
from model selection; existing provider tools remain disabled.

`query_context` is exactly the unchanged selected finding rows and shared registry
under their original column contracts. Workflow supplies independent validated
snapshots; wrapper/module check row content, IDs, manifests and joins, rejecting
unknown fields or unauthorized data. IDs join/trace only, never choose answers.
Mechanically derive subjects from selected findings/primary equipment; other
registry rows provide relationships, not additional target subjects. Query prose
is data, never permission to fetch extra sources or change bindings.

Retrieve once for the selected batch, union relevant items and retain one bundle
for every assessment/retry. The module's initial deterministic selector:

1. Filter the release at the cutoff; inactive revisions are never candidates.
2. Include all general/unclassified active context, definitions and qualifications.
3. Include all reviewed equipment-type/alias scope matches for every subject.
   Unicode case-folded exact labels determine scope; source lexical whole-word
   matches may add items, never remove a matching scope or infer an actual fault.
4. Close `required_with` context groups in both directions, including exceptions
   to an included general rule. Missing/inactive required context fails; do not
   revive it. Review uncertain/unlinked qualifications as general.
5. Narrow only if every scoped item has completed scope/context review with
   explicit type scope and every query subject type is recognized by that index.
   Missing/unknown types, incomplete review, mechanism-only scope or no scoped
   matches returns all eligible items with disclosed conservative expansion.

No top-k truncation, semantic score-as-certainty or invented synonyms. The module
defines/version-controls tokenization (maximal Unicode letter/digit tokens after
case-folding), ordering and narrowing policy. Scope review/LLM metadata can still
be wrong: omission-focused evaluation, not this predicate, qualifies retrieval.
An empty active view is valid storage state but blocks required-knowledge triage.
Known invalid context groups fail even when a larger result might hide the issue.

Result `triage-knowledge-result-v1` contains release/time, semantic query hash,
strategy implementation/parameter digests, reviewed retrieval-index hash, status,
fixed error code, selected exact entries/index and semantic content hash.
Use `knowledge:<item-id>@<revision-id>:text` addresses. Include raw authorized-input
manifest hash and selection/exclusion diagnostics in separate local evidence.
Code/parameter identity differs from corpus scope/alias identity: both are pinned.
Alias-only edits change revision/release/index identity, not necessarily algorithm.

Canonical semantic hashes include release/time/query, strategies/index, status/
selection mode and exact entries/index sorted by address. Input rows are maps
keyed by ID; raw CSV ordering/hashes and operational timestamps are excluded from
semantic identity but independently retained/verified. No hidden cross-batch
cache/state; any future cache keys must bind the same full identities.

Provider projection contains active exact source texts/references only, not
archived originals, retired text in errors, review notes, raw source blobs,
selection explanations or evaluator data. Keep source-byte lineage locally.
Code checks the completed serialized projection against failure-only `max_bytes`;
never trim or return partial usable entries. Workflow checks full request size.

Usable `status=ok` distinguishes scoped selection and conservative expansion;
`status=unavailable` has no usable partial entries. Closed failure codes:
`invalid_query`, `input_binding_mismatch`, `unsupported_contract`,
`unknown_or_invalid_release`, `strategy_binding_mismatch`, `knowledge_gap`,
`invalid_dependency`, `result_too_large`. These stop assessment/publication,
not trigger a provider retry or substitution of an old release.
Runtime retrieval uses the reviewed index without an LLM call. Extraction-time
LLM expense does not disappear merely because runtime retrieval is deterministic.

## 9. Workflow ownership and coordinated migration

Workflow owns L/I definitions/rubric and any approved ordinal anchors in a
separate versioned `assessment_policy` request-envelope field; they are explicit
design choices, not extracted domain facts or a knowledge-bundle rubric slot.
Do not silently migrate the old unapproved bands into that configuration.
Code derives U, overrides/floors, review routing, attempts and publication.
Known conflicting source-policy amendments block activation pending review;
metadata cannot automatically prove semantic compatibility.

Workflow activation approval binds knowledge release, extraction/selector/index,
assessment configuration and executable policy. Pins freeze once per run.
Provider retries reuse the retained result/bundle; changed pins/strategies/hashes
fail rather than retrieving a different answer. Registry comments and batch
evidence still reach assessment unchanged. Retrieval inclusion does not assert
the rule's factual condition has occurred.

Agree the breaking handoff **before implementation**: proposed knowledge schema
3, active-view contract `active-knowledge-v1`, result above and native bundle 2;
if a file bridge remains, use `triage-export-v1`, never counterfeit v0 fields.
No knowledge `rubric`, failure-band compatibility shim or auto-created PSV advice.
One mechanical context adapter assembles selected evidence and tool output.

Preserve legacy sources/dependencies/artifacts before code migration; old schema
1/2 replay uses their old implementation, not a promise that new workflow accepts
old pins. Build the new initial draft from source, not AI-authored legacy text.
Remove old exporter behavior that re-appends the full historical domain when
some of it has been withdrawn; archive access is local audit, not model context.
Changing extraction/index/prompt/provider context invalidates automatic
comparability with old observations, even if raw domain bytes do not change.

## 10. Decision summary and implementation gates

| Decision | Rationale / rejected alternative |
|---|---|
| Evaluate extraction before adoption; C0 baseline, C1 explicitly qualified | Neither "always LLM" nor "code is enough" is an observed conclusion |
| Source-unit references, code materialization and human review | Quote location/schema alone cannot certify semantic scope; generative advice is out |
| Module owns relevant retrieval and its tool | Not a passive store or workflow-owned keyword engine |
| Conservative selector plus usefulness gate | All-active is a safe disclosed mode, not proof of relevant selection |
| Immutable releases, cutoff, active-only projection | No stale original-text leakage or hot reload |
| Separate workflow scoring/policy | No knowledge-invented U/L/I or laundering of old assumptions |
| Local JSON/Streamlit and existing inference/testing utilities | No PostgreSQL, vector service, AI orchestration framework or new eval platform |

Execution order: agree handoff and freeze component fixtures/reference/metrics;
implement code materialization/validators and independent evaluator self-tests;
implement C0 and guarded C1 through existing inference; UI/release/index and
tool integration; deterministic lifecycle/isolation checks; explicitly authorized
paired extraction comparison; choose/qualify strategy; source content review,
release/pin and actual request capture. Deterministic bugs and paid failures stay
recorded. Frozen triage test/final tickets require their separate phase gates.

The subsequent owner request authorizes implementing the evaluator first, then
the module and corresponding tests/experimental comparison. This updates task
authorization, not the semantic gates above. Synthetic fixture-review declarations
exercise software only; they are not independent human editorial evidence.

## 11. Existing evidence and current limitations

Legacy evidence remains under `eval\results\knowledge`, including
`lifecycle-verification.json`, `lifecycle-regression-1\verification.json` and
`live-probe-driver-verification.json`. Passing legacy software checks are not
acceptance of the replacement architecture or extraction quality.

The legacy four-send `gpt-6-luna` B02 observation at
`copilot-b02-1\observation.json` is **failed_or_inconclusive**: both synthetic
positives were unassessable; controls passed mechanical validation, not calibrated
semantic acceptance. Its spent `copilot-b02.experimental-ledger.json` is unchanged.
Do not rerun or repurpose that phase to fund this extraction evaluation.

The unapproved root draft originated from code-authored numeric bands/PSV prose,
not a pure domain extraction; its hash was
`6ab008aceb1851e5da9936ce2f6bf0a257c7e8efca7a0c734d7b2af1ade00147`.
The original domain hash is
`5bdc39e19ca7e885234c391fe24e0ea2e9585af57be456948c2b1506bf8ac066`.
Those old additions do not qualify as newly supplied user knowledge.
No replacement-model quality, selective recall, human-review savings, new
calibration or promotion is established by this document.

## 12. Bounded review and adjudication

Two read-only AI critics reviewed this candidate's extraction/comparison design
and evaluation method; a third sequential critic cross-critiqued their findings.
Their scopes were AGENTS and the candidate decision, not an independent inspection
of source-domain correctness, production code, executed tests or paid outputs.
They did not edit artifacts or certify domain expertise. The implementing author
checked the supplied brief/domain separately; agreement is not acceptance.

Accepted: explicit credible C0 grammar, source-evidenced metadata, fixed source
families/phenomenon inventory and query denominators, byte-union coverage,
symmetrical critical-error accounting, original-source fidelity as a separate
mandatory smoke, per-case usefulness rather than a median loophole, fixed retry/
repeat accounting, grader controls and independent request-comment comparison.
The reviewed effort gate now specifies blinded different reviewers for the same
source, normalized operation counts and both relative/absolute minimum benefit.
If that review cannot be obtained, C1 remains unqualified; no fictional result
or expanded automatic-model benchmark substitutes for it.

Rejected: forcing reference atoms onto extractor chunk boundaries or requiring
one gold partition, because valid alternative groupings must not lose credit;
excluding the exposed original from correctness gates, because it is the actual
initial source; replacing the owner-evidence effort gate with a metadata-recall
lift threshold, because extra tagging alone does not demonstrate useful savings.
Precision/recall remain diagnostics. No complex edit-distance platform, extra paid
judge or further review workflow is introduced.

Consolidation removes obsolete schema-1/2/rubric-first design prescriptions from
document 06; legacy runtime and historical observations remain unchanged.
This decision is ready to guide the next implementation, not evidence that its
unmaterialized evaluation has passed.

Implementation-contract review accepted separate release-bound context edges to
avoid circular revision hashes, independent byte-span grading, isolated legacy
replay and explicit Copilot accounting limits. It also requires distinguishing
software fixture review from genuine editorial review: a passing deterministic
selector fixture cannot certify editorial quality or all system goals.
