# Triage workflow: design and eval-driven delivery

## 1. Status, scope and approval boundary

**Status: migrated to document 06's source-first schema 3 / native bundle 3.
The owner requested coordinated design, implementation and system evaluation.
Deterministic integration is implemented; this is not release acceptance.**
This increment designs one application workflow, not another inference adapter
or the separately owned knowledge/context module. The owner has agreed that
knowledge/context is a separate dependency. Section 3 now describes the actual
source-first handoff. Sections 10-12 are retained historical observations of the
legacy interface; section 13 records this migration and its evidence/gates.
The development method is **eval-driven, bottom-up**: existing acceptance
scenarios determine component contracts, implementation order and required
evidence. Neither a plausible design nor passing mocks establishes acceptance.

Authority: the supplied brief and domain notes, then documents 02/03 and frozen
reference 1.2 in `eval\spec\split.json` / `eval\spec\acceptance.json`.
No source package, reference, partition or expectation changes are proposed.
Root `DESIGN.md` remains reserved to the owner. This document supports the future
A-D system design; it does not replace that required owner-approved deliverable.

The new request authorizes system evaluation, not bypassing its prerequisites,
fabricating content approval, changing frozen expectations or autonomous
operations. The configuration, knowledge and development gates in section 8
still apply before paid baseline/test/final generation.

| Owner decision | Basis / affected scenarios | Status |
|---|---|---|
| Code-controlled lifecycle and bounded assessment interface | Brief A-D; A01-A03, B01, D02, X02 | Owner approved |
| Separate knowledge/context dependency; workflow consumes a pinned snapshot | Owner-agreed separation; B01-B03, X01 | Native bundle 3 via `build_source_context`; no v0 compatibility shim |
| Full selected-batch evidence, module-owned active knowledge selection | Document 06 sections 8-9; B01-B03 | Keep all selected finding/registry rows; retain one independently validated active-knowledge snapshot, without workflow ranking |
| L/I bands, with confirmed failed required function at the top end (9-10) | Prototype rubric within supplied scoring definitions; A04, C04, D03 | Owner approved |
| Consequence-weighted rounded urgency and exact floor 9 within allowed 9-10 | Prototype numerical choices; C01-C03 | Owner approved |
| All-SCE mandatory review, without an extra urgency floor | Additional declared prototype choice; D01/D03 | Owner approved |
| Bottom-up slices and bounded generation phase plan | Implementation approach; A-D, X01-X02 | Owner approved; live budget sign-off still separate |
| Exact provider snapshot, run controls, reviewer-call budget and pricing | Baseline configuration, not resolved by design approval; X01-X02 | Required before paid runs |

Confirmed overrides, precautionary immediate-attention conditions and the
other-material-safety-uncertainty floor of 7 are already acceptance-1.2 policy.
They are not new choices offered for silent removal here. Changing them requires
the controlled reference-change process, not merely approving this document.

### Current evidence, not assumed capabilities

| Artifact inspected | What it establishes | What it does not establish |
|---|---|---|
| `eval\results\readiness.json` | Recorded reference-integrity, evaluator self-tests and two disclosed known-fixture reviewer checks | Production context isolation, model quality or system acceptance |
| `eval\assess.py` | Executable output-contract checks and hash-bound semantic-review protocol | Production validation, orchestration, urgency calculation or publication |
| `eval\results\inference\verification.json` | Historical inference-component observations bound to its recorded hashes | Verification of later edits, a different provider or triage |
| Document 04 and `llm_inference\contracts.py` | Existing request/result protocol and separately developing provider implementations | An implemented triage workflow |
| `eval\results\inference\azure-comparison.json` | Separate synthetic provider-comparison observations in an actively changing increment | A completed comparison, final provider sign-off or candidate-finding evaluation |

Documents 02/03 describe the pre-system snapshot. Their historical absence-of-
provider statements are not current implementation inventories. Preserve those
frozen documents; do not rewrite history or attach old results to new hashes.
All 17 triage-system scenarios were unexecuted in that design-stage evidence.
Section 10 records the later implementation scope without relabelling that history.

## 2. Lifecycle and decision rights

The application owns the control flow. An LLM is a bounded assessment dependency,
not the workflow controller, validator, policy authority or output publisher.

```text
configuration + selected CSVs + maintained knowledge
  -> preflight and input validation                         [code]
  -> immutable ContextBundle from knowledge/context module [code dependency]
  -> proposed assessment or explicit inability              [LLM]
  -> assessment validation                                 [code]
  -> urgency and mandatory-review policy                    [code]
  -> ticket assembly and complete-batch validation           [code]
  -> atomic draft publication + run evidence                [code]
  -> semantic evaluation / human approval                   [outside generation]

Any blocking failure -> failed run + diagnostic; no new final tickets.
Only explicitly recoverable assessment failures -> one budgeted reattempt.
```

| Decision | Owner and boundary |
|---|---|
| Allowed findings and source versions | Workflow selects the allowed inputs and pins versions; the model cannot expand selection or consume eval annotations |
| Context construction and source indexing | Separate knowledge/context module; workflow verifies the returned bundle against its allowed inputs and versions |
| Identity, dates, numeric comparisons, schema and coverage | Code, operating on validated source data; never delegate arithmetic or joins unnecessarily |
| Meaning of free text and applicable relationships | Assessment layer proposes evidence-backed interpretations; adjacency alone is not causation |
| L/I, planning text and meaningful uncertainty | LLM proposes within the declared rubric; it may report inability instead |
| Urgency, escalation, mandatory review and retry | Code applies versioned policy; the model cannot lower a floor or allocate another attempt |
| Whether a citation supports a claim | Mechanical checks cover existence/quotes, not semantic entailment; evaluate separately |
| Whether a draft is acceptable for an eval baseline | Existing deterministic gates plus calibrated, evidence-bound semantic review |
| Whether maintenance proceeds | Human approval outside this prototype; `review_required=false` is not authorization |

There are three different outcomes: **draft generation succeeded**, **evaluated
baseline provisionally accepted**, and **human-approved work**. Generation exit 0
means only the first. Never encode the other two as an inference success flag.

## 3. Small application structure and stage contracts

Package: `triage`, initially `inputs.py` (input and consumer-boundary validation only),
`assessment.py`, `policy.py`, `workflow.py` (assembly/publication) and a thin
`__main__.py`. Keep typed contracts beside their owning stage; extract shared
types only when actually shared. The owned files now exist; section 10 distinguishes
the native consumer (`source_context.py`), separate workflow ordinal policy
(`assessment_policy.py`) and explicitly labelled legacy replay seam.
Use ordinary functions/dataclasses, the existing provider
protocol and permitted schema utilities; no framework, plugin platform, agent
loop or database. Context construction, knowledge loading/editing and source
index construction belong to the separate knowledge/context dependency, not a
second builder hidden inside `triage`.

| Stage | Contract and failure boundary |
|---|---|
| Preflight | Validate explicit configuration, output/evidence paths, assessment time, provider capabilities and budgets before inference |
| Input snapshot | Validate selected finding CSV and registry headers, IDs, dates, score directions/ranges, duplicate keys and primary FK/type joins; invalid primary mapping fails |
| Context handoff | Resolve/pin the release once; call public `build_source_context`, then public `validate_source_context` against trusted tables/store/pins; retain the independently regenerated native bundle 3 and local evidence |
| Assessment | One finding per request, same selected-batch context, fresh inference; return `assessed` or `unassessable` |
| Validation | Reject malformed/extra fields, wrong identity, invalid scores/facts, unsupported source references, blank required text and mechanically detectable inconsistencies |
| Policy | Pure function of validated assessment/source-attention extraction, source-derived gaps and policy version; return base/final urgency, rule trace and review requirements |
| Assembly | Code assigns `TKT-####` from the finding's four-digit suffix, identities and timezone-aware generation time; enforce the brief's exact ticket/wrapper fields |
| Publication | Validate complete selected coverage, then replace the output once; all evidence remains associated with this run, not an earlier output |

Production never imports `eval`. An evaluation driver reads only partition
membership from the manifest and materializes the selected input CSV before
calling production. Cards, group labels, expected answers and reviewer judgments
are not runtime inputs. Production accepts arbitrary valid selected inputs; it
must not encode the supplied 21 finding IDs or require their row counts.

### Separate knowledge/context dependency (B)

Document 06 supersedes the earlier full-domain/v0 proposal. Workflow calls the
existing module-owned `build_source_context`, then `validate_source_context`,
which independently rebuilds against trusted `TableSource` snapshots and pins.
No second extractor, selector, ranking algorithm, store or prompt-domain copy
is implemented in `triage`.

| Component | Owns | Must not own |
|---|---|---|
| Knowledge/context module | Source-faithful intake, reviewed releases, lifecycle, relevant active retrieval, canonical serialization and mechanical bundle assembly | L/I rubric, U, retries, publication or expanding finding membership |
| Workflow | Independent source validation/binding, activation, policy/rubric, handoff validation, gaps, attempts and publication | Extraction, scope matching, context closure, invented knowledge or fallback to an old release |
| Assessment layer | Grounded L/I, planning text, facts and uncertainty | Retrieval/tool control, urgency, knowledge edits or publishing |

Actual in-process handoff (normal production only):

```text
validate activation + independently retained finding/registry CSV bytes
release = SourceKnowledgeStore.resolve_release(exact_content_hash)
retain release in a read-only pinned SourceKnowledgeStore view
build_source_context(pinned_store, findings_table, registry_table,
    knowledge_version=exact_content_hash, assessment_time=fixed_cutoff,
    expected_strategy=activated_strategy,
    assessment_policy=workflow_assessment_policy, max_bytes=configured_limit)
  -> proposed SourceContext(native bundle 3, local evidence)
validate_source_context(proposed, findings_table, registry_table, pinned_store,
    knowledge_version=exact_content_hash, assessment_time=fixed_cutoff,
    expected_strategy=activated_strategy,
    expected_assessment_policy=workflow_assessment_policy, max_bytes=configured_limit)
  -> independently regenerated SourceContext and local evidence
retain this validated bundle for every finding and retry
```

The adapter retains the exact validated CSV bytes and hashes, constructs distinct
`finding_input` / `registry_input` tables, and compares their parsed rows with the
workflow's independently validated maps. It resolves the content-addressed release
once; the builder receives a read-only view returning that retained release,
not the mutable draft or an alias. The validator intentionally materializes a
second deterministic result at preflight to detect omissions as well as additions,
even if the incoming packet was rehashed. This is not a second assessment snapshot
or retrieval during retries. Incoming packet-owned local evidence is discarded;
the module regenerates provenance from trusted inputs. Immutable source validation
still belongs to the store. Unknown/invalid/draft-only versions fail; no old-release
substitution.

Activation is separate from editorial publication. `triage-activation-v1` binds
release, full selector implementation/parameter identity, reviewed retrieval-index
hash, `assessment_policy` hash and executable urgency-policy file hash.
Its explicit reviewer/reason/time and source-policy compatibility declaration
are local unauthenticated operator assertions, not proof of semantic correctness,
human identity, qualification or domain certification. `activation_candidate`
only prepares pins with `review=null`; it never approves or publishes knowledge.
Known source-policy conflicts require review/new compatible pins before activation;
hashes do not automatically detect semantic contradiction.

| Native bundle field | Consumer-visible contract |
|---|---|
| `contract_version` | Integer 3, with closed fields; never a counterfeit v0 export |
| `payload` | Exact selected finding maps, complete shared registry, selected active exact knowledge, and source-derived `triage-input-history-v1` |
| `source_index` | Exact CSV field values and `knowledge:<item>@<revision>:text` values; no review notes/history |
| `finding_ids`, `knowledge_version`, `assessment_time` | Exact selected membership and fixed run pins |
| `assessment_policy` | Separate workflow-owned ordinal policy, outside `payload.knowledge` |
| `knowledge_result_hash` | Hash of the retained `triage-knowledge-result-v1` result |
| `context_hash` | Module canonical UTF-8 compact serialization of every native field except this hash |

`SourceContext.evidence()` stays local: raw input manifests and the retrieval
result with release/query/strategy/index bindings, selected entries and source
lineage. Workflow independently verifies rows/comments, raw hashes, native hashes,
entry address/revision/text/eligibility and the exact provider projection.
It does not reproduce selection to decide what should have been included.
Omission/qualifier quality remains document 06's evaluation gate. Raw-file hashes
are excluded from semantic identity so CSV row-order reversal preserves the
bundle while changing independently retained manifests. No source bytes are
normalized. Full-context and full prepared-provider-request limits fail before
dispatch; there is no truncation or partial knowledge result.

Bundle 3 deliberately has no `gaps`, `purpose`, `rubric` or `source_manifest`
provider field. Workflow derives the existing closed
`tagged_partner_not_in_registry` gap from explicit N+1/Duplicated tags in its
validated registry; it records subject/partner, affected finding IDs and the
redundancy source reference outside the native bundle. The same source-known
gap still reaches policy/action composition even if the model omits uncertainty.
It does not assert partner failure, absence of deviation or a POB shortfall.
Missing primary equipment fails input validation; a missing partner can support
an explicitly uncertain draft. No per-finding branches are added.

`payload.history` is not maintained policy and does not ingest work-order records
that were not supplied. It deterministically orders selected findings by equipment
and date, and records only explicit redundancy tags or exact equipment-ID
references in registry text. Each relationship retains original source addresses
and is labelled context-only, not causation. The consumer rebuilds this projection
from trusted input bytes; target requests receive the relevant timeline/links and
unchanged related rows, while partition selection still occurs before context
construction.

Normal native input binding accepts ordinary finding/registry inputs only.
The explicit `IsolatedProbeContext` now supports the module-owned isolated-probe
contract: independently hash-bound evaluation inputs and one separately labelled
experimental assessment-policy overlay. It cannot change ordinary source
knowledge or the base assessment policy. Normal workflow rejects probe
purpose/overlay rather than relabelling F-9001 or injecting evaluation policy
into production knowledge. B02 uses only this explicit isolated path and its
own eight-send budget; software coverage is not actual behavioral evidence.
The old four-send failed legacy probe remains retained, not new-contract evidence.
Legacy `--context-export` is available only with explicit `--legacy-replay` and
a previously materialized or archived `triage-export-v0` file. No current module
produces new v0 exports; replay never activates native knowledge or qualifies
new-contract acceptance.

Production does not inspect partition IDs/cards. The evaluation driver selects
development rows before calling it; shared registry/domain are legitimate, test
finding descriptions and evaluator answers are not. Provenance validation cannot
detect disguised answers in falsely labelled caller inputs or incorrectly
reviewed sources. Actual B01 captures and omission-focused evaluation remain
required; fake-provider wiring is not evidence of model use.

For a PSV guidance change, the engineer imports/edits a declared source through
`triage_knowledge.source_editor` / `source_cli`, reviews exact source-backed
scopes/context/lifecycle and publishes a new immutable release. The operator
reviews source-policy compatibility and activates new pins; orchestration stays
unchanged. Prior domain source bytes are retained only for audit, never appended
to the active projection. A change to ordinal anchors edits the separate
`triage\assessment_policy.py`; a U/floor change edits `triage\policy.py` and its
tests. Neither is extraction. The local source-first path suits this small
package; all-active original-domain context may be legitimate but does not prove
useful selection, and vector/RAG infrastructure is not justified by this corpus.

Changes invalidate old context/model comparability and require B01-B03 plus
affected A04/C04/D01/D03 and stability checks. Tests retain the actual module
builder/store/retrieval, verify retired/future/expired exclusion, active-only
projection and one retained bundle. No legacy numeric-band/PSV starter is
automatically imported, reviewed or promoted.

## 4. Assessment is a proposal, not trusted application state (A/D)

An `assessed` result contains matching finding/equipment IDs, summary, recommended
action, L/I score+rationale+evidence, policy facts and material uncertainties.
It contains no ticket ID, urgency, publication status or final review flag.
An `unassessable` result contains identity, missing/contradictory evidence and
reason, but no invented scores. Treat it as visible batch failure, not a ticket.

Each policy fact has a named proposition, applicability
(`applicable`, `not_applicable`, `uncertain`), state
(`confirmed_true`, `confirmed_false`, `suspected`, `unknown`), explanation and
source references. Non-unknown observations require quoted evidence.
Unknown facts identify the missing information and the sources checked; an
empty evidence array is not permission to promote unknown to false. A negative
claim such as "no recorded deviation" requires an explicit source statement,
scoped to the relevant observation/time, or an authoritative complete record.
"Not found in these supplied sources" supports unknown, not confirmed absence.
The confirmed override can therefore be exercised on explicit evidence, including
synthetic C03 inputs, without pretending every actual finding supplies that fact.
Retain observation dates and distinguish historical observations from current
restoration. Assessment time is required configuration, not wall-clock ageing.
Treat the batch as recorded observations with no assumed repair or deterioration
beyond its evidence; `generated_at` is the actual run timestamp, not that cutoff.

Required propositions: assessed item's required-function failure, protection
impairment, recorded deviation, failed protection-function test, unavailable
evacuation craft, capacity below POB, discovered unlogged impairment and verified
restored protection. Applicable
unknowns cannot be omitted. Material uncertainty also records the affected
decision, specific reason, whether safety is involved and a verification activity.
Non-applicability cannot erase contradictory positive facts.

| Applicability / state | Mechanical treatment |
|---|---|
| `applicable` + any of the four states | Evaluate the named rule's state predicate; false is not unknown |
| `not_applicable` + `unknown` | No rule trigger from that proposition; require a source-backed explanation of non-applicability |
| `not_applicable` + any other state | Reject the conflicting representation; do not silently discard the asserted fact |
| `uncertain` + `unknown` or `suspected` | Mandatory review of policy applicability; material uncertainty about safety/protection applicability receives floor 7 |
| `uncertain` + a confirmed state | Reject inconsistent applicability; require the assessment to resolve its representation |

For applicable facts, unknown/suspected does not automatically mean material:
derive the specific immediate conditions first, then evaluate their effect on
the declared decision. Code-known gaps affecting safety redundancy independently
force review and floor 7; a known unavailable craft with unverified capacity
instead meets floor 9. Missing non-safety metadata does not. These bounded rules
cannot detect every model error about applicability, safety relevance or
materiality. A falsely justified `not_applicable` can still evade a semantic
condition; disclose and evaluate that risk rather than claim code proves truth.
The separately declared all-SCE review is one additional guard, not a solution.
The opposite error is also possible: model overstatement of materiality/safety
can unnecessarily raise urgency. Evaluate over-escalation and repeat drift, not
just missed floors. Registry SCE status alone cannot define all safety relevance:
non-SCE equipment can have major consequences. Do not solve that semantic problem
by suppressing the contract's floors for every non-SCE finding.

Code checks references against the allowed snapshot and exact quotes against
their referenced source fields. It compares numbers only when the operands,
units and applicable threshold are established, not by regex guessing meaning
from prose. Source existence, a quote and a model's confidence do not prove
entailment, correct materiality or score defensibility.

The validated bundle supplies known context gaps (for example an explicit missing
partner) independently of the model's uncertainty flag. Workflow's executable
policy determines their disposition; the context builder does not label their
materiality or assign urgency. Such gaps cannot be suppressed by `material=false`.
Semantic omissions beyond these bounded checks remain possible; C04/D01/D03 and
human review are required, not an invented universal truth checker.

### Owner-approved prototype L/I rubric

These are ordinal prototype anchors, not calibrated failure probabilities or
per-finding gold. The domain notes still govern their interpretation.
The assessment layer proposes L/I from the finding, registry, exact active domain
sources and the separate workflow-owned `assessment_policy`; code validates the
proposal and derives U. `triage\assessment_policy.py` implements the bands below;
they are not extracted knowledge or copied legacy-release bands. There is no registry-only
formula such as `L = 11 - reliability_score` or `I = criticality_score`.

| Score band | Likelihood: evidence about performing the required function | Impact: consequence if the assessed failure occurs |
|---|---|---|
| 1-2 | Little supported indication of near-term function loss; supported margin/service state matters | Appearance/housekeeping or similarly limited low-energy consequence |
| 3-4 | Credible limited degradation with supported margin, without strong progression evidence | Localized recoverable consequence with justified functional alternatives |
| 5-6 | Active degradation or meaningful precursor; near-term progression uncertain | Material operational consequence or moderate protection degradation with remaining capability |
| 7-8 | Strong progression, advanced damage or recurrent functional interruption | Severe operational, delayed integrity or major-accident exposure, accounting for actual protection |
| 9-10 | Direct evidence of imminent loss; a confirmed failed required function belongs at this top end | Extreme consequences supported by the actual scenario, not merely an SCE label or repair cost |

The model must justify its exact choice and countervailing evidence. Registry
reliability runs inversely to likelihood; criticality is only an impact prior.
Neither is an arithmetic lookup. A tag defect is not failed relief function;
a remaining 2oo3 arrangement is not automatically total defeat. These are generic
domain distinctions, not case-specific score branches.

The failed function is the assessed item's required function, not necessarily
the complete protection arrangement. A failed detector head can have top-end
likelihood while the remaining voted arrangement has moderate impact. Code
rejects an internally inconsistent assessment that simultaneously asserts confirmed
required-function failure and a likelihood below this top-end band; it never
silently rescores. A model can still misclassify that fact. Exact 9-versus-10
choices are not a mechanical truth oracle. Unresolved adjacent-score judgments
stay `needs_review` in semantic evaluation. Do not retry until reviewers agree.

## 5. Deterministic urgency and review policy (C/D)

Owner-approved policy `triage-policy-v1` adopts the previously deferred:

```text
base = ceil(0.7 * impact + 0.3 * likelihood)
     = (7 * impact + 3 * likelihood + 9) // 10
final = max(base, all applicable policy floors)
```

Integer-only L/I in 1-10; reject booleans and floats. Exact integer arithmetic
avoids rounding ambiguity. Monotonicity and range must hold over all 100 pairs.

| L / I | Proposed base | Plain mean | Plain maximum | Existing allowed band |
|---|---|---|---|---|
| 1 / 1 | 1 | 1 | 1 | 1-2 |
| 10 / 1 | 4 | 5.5 | 10 | 3-4 |
| 1 / 10 | 8 | 5.5 | 10 | 7-8 |
| 10 / 10 | 10 | 10 | 10 | 9-10 |

Consequence receives more weight so high consequence is not averaged away;
near-certain inconsequential failure need not demand today's intervention.
Weights, exact rounding and floors are prototype attention choices, not expert
calibration or statistical optimality. No acceptance anchors are changed.

### Authority and external context

Keep three sources of authority distinct:

- **Supplied requirements:** the candidate brief/domain notes define L/I, registry
  score directions, real redundancy, urgency time bands and the two confirmed
  override conditions. They require a documented urgency function but do not
  prescribe numerical weights.
- **Declared prototype choices:** the L/I bands, 0.7/0.3 weighting, ceiling and
  exact floor 9 are documented engineering choices. The additional precautionary
  floors come from the existing acceptance contract; all-SCE review is another
  declared prototype choice. None is an externally certified risk model.
- **External background, not runtime authority:** the public overview of
  [DNV-RP-G101](https://www.dnv.com/energy/standards-guidelines/dnv-rp-g101-risk-based-inspection-of-offshore-topsides-static-mechanical-equipment/)
  describes risk-based inspection planning for offshore pressure systems.
  [Havtil Management Regulations section 5](https://www.havtil.no/en/regulations/all-acts/the-management-regulations3/II/5/)
  addresses barrier independence, awareness of impairment and compensating
  measures. These support the engineering context, not this scoring formula or
  a compliance claim. The DNV reference is to its public overview, not a review
  of the full recommended practice.

Arithmetic on ordinal L/I bands is an explicit ranking convention: equal numeric
steps do not establish equal changes in probability or consequence. U is not
expected loss or quantitatively calibrated risk. Boundary/monotonicity checks
demonstrate policy consistency, not operational validity. External references
do not establish that the weights are optimal or justify an extra criticality/SCE
uplift beyond assessed consequences and named rules. This clarification adds no
runtime knowledge, changes no frozen expectation and does not replace domain
review or human approval.

| Rule ID | Qualifying evidence-backed condition | Floor / disposition |
|---|---|---|
| `O-PROTECTION` | Confirmed protection impairment AND confirmed absence of recorded deviation | 9; label confirmed override |
| `O-EVACUATION` | Confirmed capacity below POB | 9; label confirmed override |
| `P-FAILED-TEST` | Confirmed failed test of an assessed protection component's required function | 9; precautionary attention, not invented absence of deviation or total layer defeat |
| `P-EVACUATION` | Known unavailable craft with unverified remaining capacity/POB comparison | 9; precautionary attention, not proven capacity shortfall |
| `P-RESTORATION` | Explicit discovered unlogged impairment with unverified restored protection | 9; precautionary attention, not a claim of continuing total defeat |
| `P-SAFETY-UNKNOWN` | Other material safety uncertainty | 7 and mandatory review/verification |
| `R-MATERIAL` | Material uncertainty affecting justified assessment/disposition | Mandatory review, specific reason and verification; no extra floor unless safety policy applies |
| `R-SCE` | Registry identifies an SCE | Mandatory integrity review as a separately declared prototype choice; no automatic urgency floor |

State predicates below resolve the rule table before implementation. `T`, `F`,
`S` and `U` mean confirmed true, confirmed false, suspected and unknown. Apply
these only after the section 4 applicability checks; no omitted fact is defaulted
to `F`. Each named condition is scoped to the assessment cutoff and evidence.

| Rule | Required proposition states |
|---|---|
| `O-PROTECTION` | protection impairment `T` AND recorded deviation `F` |
| `O-EVACUATION` | capacity below POB `T` |
| `P-FAILED-TEST` | failed protection-function test `T` |
| `P-EVACUATION` | unavailable craft `T` AND capacity below POB in `{U, S}`, with unverified remaining capacity/POB comparison |
| `P-RESTORATION` | discovered unlogged impairment `T` AND verified restored protection in `{F, U, S}` |
| `P-SAFETY-UNKNOWN` | a source-derived safety gap or an evidence-backed material safety uncertainty, including unresolved safety-policy applicability; no stronger immediate condition is required |
| `R-MATERIAL` | source-derived material gap or assessed material uncertainty; verification activity required |
| `R-SCE` | primary registry SCE flag is `Yes`, independent of model applicability |

For capacity below POB, `F` means the comparison is verified non-shortfall, not
that a partner tag exists. Restored protection `F` means verified non-restoration;
`U`/`S` mean restoration is not verified, not confirmed continuing total defeat.
Protection impairment `T` with deviation `U`/`S` does not meet `O-PROTECTION`:
require review and at least floor 7 for that material safety uncertainty, or floor
9 if a separate failed-test/restoration/evacuation precaution qualifies.
Two simultaneous overrides retain both rule IDs. A lower floor never reduces
an already higher base or floor.

Record every qualifying rule even when the base or another rule is already
higher. Trace includes base, floors, final score, labels, source references and
policy version; assemble the urgency rationale from this trace in code.
Facts remain four-state: suspected/unknown cannot satisfy a confirmed override.
The confirmed versus precautionary conditions and floor bands come from document
03 section 3D; selecting 9 within the 9-10 band is this proposal's exact-value
choice. Remaining voting/redundancy moderates consequences where supported but
does not cancel that contract's failed-protection-test attention rule.
Uncertain safety applicability is reviewable material uncertainty, not a proven
trigger. Unknown fields on genuinely unrelated equipment do not escalate every
ticket. All-SCE review is explicit defense in depth, not a substitute for assessing
facts, nor a claim that non-SCE findings cannot have major consequences.

Never alter L/I to achieve a floor. Require the associated structured verification
activity to be present in the recommended action when uncertainty requires it;
absence is validation failure, not silent text truncation. Mechanical presence
does not certify that the activity is meaningful or evidence-appropriate; that
remains part of planning/uncertainty review.

## 6. Recovery, publication and evidence

Use sequential finding requests initially: predictable accounting and failure
handling matter more than concurrency for 21 rows. Reserve each attempt before
dispatch. Two total provider attempts per finding include SDK/HTTP retries;
counting Python `generate()` calls alone is insufficient.

Allow one fresh reattempt for malformed JSON, structural/identity/evidence
validation failure or a named mechanically detected contradiction. Supply only
the same allowed context and sanitized validation diagnostics; never eval answers.
Both attempts remain in the trace. An explicit `unassessable` assessment fails
without forcing another answer. Authentication/configuration, unknown dispatch
accounting, refusal, boundary failure, timeout/transport ambiguity and cleanup
failure stop the run; no hidden failover or open-ended repair.

Fail with nonzero exit and stderr JSON containing `run_status`, `finding_id`,
`error_class`, `attempts`, `published_output=false`; use `finding_id=null` for
preflight/batch-level failures. Keep attempt reservations distinct from observed
dispatches; unknown usage is null, never zero.

Validate all tickets and coverage before writing a same-directory temporary file,
flush/close it, then use atomic replacement on the local filesystem. Persist
required evidence and the intended output hash before replacement; replacement
is the final fallible application operation in the success path. The old output
stays byte-identical on any pre-publication failure. Reject a pre-existing evidence
directory so an old run cannot appear current. Assume one CLI writer per output;
concurrent writers, crash recovery and network-filesystem transactions are outside
this prototype. If interruption leaves publication uncertain, report it as
uncertain instead of inventing a transactional success/failure guarantee.

Proposed evidence location: `eval\results\triage\<run-id>` for evaluation runs;
ordinary runs accept a separate explicit evidence directory. Production writes
evidence but never reads evaluation results. Preserve attempts, failed responses,
validated assessments, context membership, rule traces and before/after hashes.
Capture actual provider-bound inputs, not merely prompt templates; retain
source/config/prompt/knowledge/policy/reference hashes, Git revision/dirty state,
fixed assessment time, actual execution time, provider/deployment/reported model,
controls, cache mode, tokens, attempts, latency and sourced cost/qualified estimate.
Redact credentials/headers and keep sensitive source/request bodies local unless
explicitly approved for publication. Receipt hashes alone cannot establish B01.

## 7. Requirement -> implementation -> test -> eval

Do not build another evaluator or expand the benchmark. The existing 17 scenarios
are the contract. New production tests belong under `tests`; frozen `eval\tests`
remain evaluator self-tests. Production must not import their helpers.

| Existing scenarios | Planned production slice | Required evidence, beyond merely having tests |
|---|---|---|
| A01 | Input/assessment/final-ticket validation and coverage | Named invalid mutations, valid control, diagnostics and input/output hashes; valid is not semantically passed |
| A02-A03 | Bounded workflow recovery and publication | Fake-provider invalid->valid / invalid->invalid traces, both output-presence conditions, nonzero stderr JSON and old-file hashes |
| A04 | Independent semantic-review protocol | Current reviewer's seeded-contradiction calibration, grounded real-output judgments and unresolved score review |
| B01 | Separate module's bundle tests plus workflow handoff/request-capture integration | Correct comments/partner evidence, reversed-row semantic context equality with separate raw-file hashes, rejection of foreign membership/version drift/invalid bundles, actual provider capture with no cards/test descriptions |
| B02-B03 | Separate module's maintenance/release path plus isolated workflow experiment | Frozen four-condition real probe, versioned knowledge-only diff, negative control, actual engineer edit path and later owner DESIGN section B; no second rule store |
| C01-C02 | Pure base urgency function | All 100 pairs, independent worked values, integer/range/monotonic checks and mean/max corner comparison |
| C03 | Pure escalation/review function | True/false/unknown/suspected and applicability matrix, both overrides, precaution-only cases, complete rationale trace |
| C04, D01, D03 | Actual assessment/fact supply and routing | Development case reviews including F-1010/F-1012 and the tag/crack/coating contrast; test chronology only after freeze |
| D02 | Invalid input versus inability versus context gap | Synthetic primary-FK failure, unassessable result, missing-partner uncertain draft; no placeholder or skipped finding |
| D04 | Implemented limits and approval boundaries | Code/design comparison, exclusions, assistance/rejected proposals and separate unresolved gates |
| X01 | Repeated real development generation | Two fixed-config 13-finding outputs, per-finding L/I/U/band/review/claim adjudication, cache disclosure and distribution diagnostic |
| X02 | CLI, automatic publication, provenance and budgets | Fresh-environment single-command all-21 run, usage/cost and dependency/history inspection, required final owner DESIGN |

The real-model development portion of C04 does not establish restored-protection
chronology extraction: that portion is reserved to the test group. Synthetic C03
fact-state tests establish policy behavior, not extraction quality; the B02 policy
probe is not restoration evidence either. Keep this explicit gap until the
scheduled test observation, rather than invent a new case or claim full C04 from
development. Pure-policy branches can pass while their real fact extraction is
still unverified.

Bottom-up implementation order after approval:

1. Agree the typed ContextBundle handoff with the knowledge/context module; define
   focused A01/D02 fixtures and implement workflow's input and handoff validation.
   Use fake bundles to test wrong membership, source/hash/version/time mismatch,
   probe-purpose and disguised evaluation-input/overlay rejection, unknown/foreign
   gap records, size limits and unchanged output on context failure. Include a
   valid isolated-probe bundle with exact declared input/overlay hashes and a
   mismatched-hash rejection: rejecting every probe must not pass the contract.
   A known missing-partner gap must reach the policy rather than be dropped.
   No provider calls; workflow does not implement a replacement context builder.
2. Freeze independent worked policy expectations; implement pure C01-C03 and
   routing, without an LLM. Property checks alone do not prove exact formula
   conformance: include independently calculated interior/boundary examples.
3. Implement assessment adapter, orchestration and publication against fake
   context and inference dependencies; exercise A02/A03/D02 including
   existing-output preservation. In parallel, the knowledge module implements
   bundle construction/maintenance against the same interface, not workflow code.
4. Integrate the real context module first: verify B01 source delivery through
   request serialization, missing-partner gaps and frozen-snapshot behavior when
   a new knowledge release is edited mid-run. Offline capture proves wiring only.
   Then integrate the separately owned direct provider and capture its actual
   requests. Run development assessment, calibrated semantic review, B02 and X01
   under section 8; mocks prove neither model quality nor knowledge influence.
5. Freeze applicable versions/configuration, run test once, disclose failures;
   final all-21 generation/delivery follows the contract, never hand-edited tickets.

Each slice records changed requirements, focused command, actual result and
remaining gaps. Two bounded reviews challenge substantive implementation changes,
with the second cross-critiquing the first; adjudicate, do not vote.

## 8. Evaluation execution gates and budgets

**This implementation increment executes zero live triage provider sends.** Existing synthetic
inference budgets are not transferable to triage. Design approval permits offline
implementation only until an owner-approved system-design/baseline configuration
exists and the following prerequisites are met.

Proposed integration: the direct Azure provider being developed in document 04,
through `InferenceProvider.generate`. Do not assume its in-progress evidence
qualifies final code. Before baseline, record the exact deployment and reported
model/version, freeze its adapter/configuration, verify zero hidden SDK/transport
retries and permitted raw-endpoint usage, and resolve capability gaps. Copilot
with unknown internal attempts is not eligible for the strict production budget.
No inference changes or Azure resource operations belong to this increment.

Proposed run controls: sequential execution, fresh requests, 90-second inference
deadline, reasoning effort `low` only if supported, Azure-native JSON only after
the assessment schema is verified compatible, 4,096 completion-token cap and no
application result cache. Token truncation fails visibly; no partial JSON repair.
These settings and the section 4 rubric/section 5 formula require approval and
must be preregistered for each development observation. Development findings may
justify a versioned correction and a newly authorized bounded run, never an
overwrite of failed evidence. X01's paired runs must use the same fixed version;
the accepted development snapshot is frozen before opening test.

| Phase | Nominal requests | Maximum including two-attempt allowance | Entry / exit gate |
|---|---|---|---|
| Offline component/integration checks | 0 | 0 | Deterministic slices pass; no model-quality claim |
| Development + X01's one repeat | 26 | 52 | 13 findings twice with fixed context/time/config; review drift and all 39 dimensions per output |
| B02 isolated probe | 4 | 8 | Frozen positive/negative inputs under both policies; retain failed/unresponsive behavior, no silent retuning |
| Frozen test once | 8 | 16 | Applicable development gates accepted, no blocker; assess 24 dimensions, no blind-test claim |
| Final all-21 generation | 21 | 42 | Disclosed non-blind regeneration/regression including test findings; automatic coverage plus 63 review dimensions and delivery evidence |

The prospective ceiling is 118 generation attempts across these phases, not an
authorization to spend it, not a target and not a promise of inexpensive operation.
Stop before dispatch if either per-finding or phase budget is exhausted. Additional
development experiments need a recorded reason and new bounded authorization,
not a reset ledger. Test-informed changes/reruns must be disclosed. Do not add a
default tuning pass just to spend a budget; make a concrete development finding
the reason for another observation.

AI semantic review/calibration calls are separate from these generation counts.
Before using a model reviewer, declare its configuration, scope, nominal calls,
retry ceiling and token/cost budget in a separate review ledger. No such calls
are authorized by the table; their cost must be included in total evaluation
cost, not hidden under "offline assessment". Human review has no provider-call
count. Architecture-review agents used for this document are disclosed below;
their runtime billing is not exposed and is not reported as zero.

Before any paid baseline, source current pricing/account terms and preregister
the request/token ceiling, input-size bound, pricing assumptions and expected cost.
No USD estimate is invented here. Missing pricing/billing stays unverified and
blocks a low-cost delivery claim even if the request count is within budget.

Calibrate the actual semantic reviewer/configuration using the existing seeded
controls before relying on its judgments. Old reviewer-a/b files do not qualify a
new reviewer. Record provenance and output-field exact quotes; `needs_review`
blocks baseline acceptance. AI-only reviews remain provisional, not independent
domain certification. A04 calibration does not prove general reviewer competence.

Existing commands, executable now from the repository root:

```powershell
python -B -m eval.validate
python -B -m eval.assess --partition development --checklist
python -B -m eval.assess --help
```

The production entry point is `python -B -m triage`. Its native store/activation
command is documented in README; the v0 bridge in sections 10-12 is historical
and now requires explicit `--legacy-replay`. Native activation does not imply
knowledge qualification or a real system baseline.
The live command shape is not claimed as executed reproduction evidence.

Then use the existing assessor with `--partition development --tickets <path>`
and an output-hash-bound review file via `--reviews <path>`. Exit 2 means pending
review, exit 1 failed, and exit 0 only provisional ticket-output acceptance.
The scenario evidence above is additionally required; the assessor is not a
complete system acceptance runner.

Freeze code/dirty-state snapshot, provider/model, settings, prompt, knowledge,
policy, reference, sources and assessment time before the single test run.
The split is 13 development/8 test, 9/4 groups, already exposed/non-blind and
AI-assisted. Do not tune against test descriptions/cards/outputs or enrich shared
knowledge with test answers. After any test-informed correction, label the next
observation as regression, never newly blind.

## 9. Alternatives, limits and review record

Rejected: LLM-controlled workflows/retries/publication; an LLM-authored urgency
score; keyword-based semantic truth checks; finding-ID score tables; plain mean
or maximum urgency; silent defaults/JSON repair; automatic model fallback; using
an LLM judge as certification; retrieval infrastructure without a measured need.

The earlier urgency-only recommendation was too narrow for the requested
lifecycle design. Conversely, one giant deterministic module would mix policy,
I/O and recovery. Keep one small workflow with independently testable components.
Faster parallel dispatch and caching are deferred because they complicate attempt
accounting/stability evidence without a demonstrated requirement.

Not built: live maintenance actions, approval UI/service, training/calibrated
probabilities, a complete plant-state graph, universal contradiction detection,
operational risk certification or a new evaluation platform.

The owner-agreed revision separates context/knowledge from workflow. This
document defines consumer needs, not the parallel module's unapproved editor,
storage or concrete API. Resolve any interface mismatch together before
integration; do not make competing builders and reconcile their behavior later.

Copilot authored this proposal using repository contracts and current component
boundaries. It has not generated tickets or used test outputs to tune a model.
Owner approval and domain review are not implied by AI reviewer agreement.

### Bounded design review and verification

Two actual read-only `rubber-duck` agents reviewed the proposal. Reviewer A
(`workflow-design-review-a`) challenged the first draft; reviewer B
(`workflow-design-review-b`) cross-critiqued its findings against the revised
draft. Both are AI-only engineering feedback, not independent domain validation.
They made no edits or provider calls for triage. Their agent billing/model
configuration was not exposed; no zero-cost claim is made.

| Finding / suggestion | Disposition and reason |
|---|---|
| A: applicability x fact-state mapping was ambiguous | Accepted; explicit valid/invalid combinations and routing were added, followed by B's requested per-rule state predicates |
| A: no deviation found in supplied sources could establish absence | Rejected; missing evidence remains unknown. Explicit source-scoped negatives can support a confirmed absence; the override need not trigger on every actual finding |
| A: failed component likelihood and immediate attention conflict with remaining 2oo3 capability | Rejected as stated; item failure, arrangement consequence and attention policy differ. Document 03 section 3D already requires failed-protection-test precaution, so dropping it would weaken frozen policy |
| B: exact likelihood 10 is overprecise and the floor may appear to force L/I | Partly accepted; remove exact-10 enforcement, retain the supplied top-end principle (9-10) as an internal consistency check. Floors never alter L/I; semantic classification still needs review |
| A/B: reviewer calls and generation calls need separate budgets; final all-21 is non-blind | Accepted; separate review ledger/cost gate, versioned development observations and final-regression disclosure added |
| A: add an automatic extra 13-finding tuning pass | Rejected; additional development observations need an actual finding, explicit bounded budget and retained provenance, not another default benchmark |
| A: locks/crash reconciliation and rigid module split are excessive here | Accepted; single-writer CLI assumption, simple atomic replacement and a smaller initial module layout |
| A: approval bundled new choices with existing contract policies | Accepted; owner checklist distinguishes prototype choices, fixed requirements and separate paid-baseline prerequisites |
| B: use only registry SCE status to establish safety-floor relevance | Rejected as exclusive rule; non-SCE hazards also matter. Accepted its over-escalation concern and explicitly disclosed both semantic error directions |
| B: development cannot establish the test-only chronology part of C04 | Accepted; policy tests, real development extraction and still-unobserved test extraction are separately identified |

A read the full initial proposal, domain notes and selected brief/acceptance
sections, but not documents 02/03 in full or actual evidence/code. B read the
revised proposal and document 03's policy sections and selected split/scenario
references, but not the full supplied brief/domain or actual evidence/code.
Neither opened test cards/outputs or ran tests. The author adjudicated against
the source contracts; review agreement is not an acceptance result. Final
clarifications received direct consistency checks, not a claimed third review.

Initial-snapshot documentation verification: frozen reference validation passed; the assessor
help interface remained compatible; development checklist generation returned
39 dimensions. Direct checks found all 17 scenario IDs represented, balanced code
fences, ASCII text, no trailing whitespace, valid README navigation and existing
contract paths; reserved root `DESIGN.md` remained absent. These are consistency
checks, not execution of any production scenario.

The command/provenance record is
`eval\results\triage\design-verification.json`. No paid inference, production
implementation, full test suite or frozen-test assessment was performed for this
documentation task. No scenario is promoted to pass by this design review.

### Knowledge/context boundary revision

The owner approved separating knowledge/context after the initial design review.
This revision changes ownership, the proposed ContextBundle handoff and B01-B03/
X01 integration tests; it does not approve the remaining policy/rubric proposals
or assert compatibility with an implementation that has not been handed off.
The initial verification record retains its original document hash and results.
Revision-specific review dispositions and new observations are appended, not
silently attached to the older snapshot.

Two further read-only `rubber-duck` reviews examined only this boundary revision:
`context-boundary-review-a` challenged the handoff; `context-boundary-review-b`
cross-critiqued the revised interface and B02 isolation. Both are AI-only; neither
inspected or changed the parallel knowledge implementation, ran tests or called
triage inference. Agent billing/settings are not exposed.

| Revision finding | Disposition |
|---|---|
| A: a mutable version label cannot pin/verify a run snapshot | Accepted; explicit one-time release resolution, immutable snapshot content/handle and manifest agreement |
| A: canonical hash verification and size-limit ownership were unclear | Accepted; module-owned versioned serializer, consumer digest check, workflow byte limit and full-request limit; shared serialization is not an independent oracle |
| A: B02 had no explicit purpose/overlay construction path | Accepted; explicit isolated parameters and source-kind/hash checks, including a normal-labelled overlay rejection |
| A: factual gaps lacked a consumable closed shape | Accepted; one initial typed missing-partner gap, source/membership checks, unknown-kind failure and downstream D02 tests |
| B: synthetic probe input also needs provenance/isolation | Accepted via `evaluation_input` kind and experiment-declared hashes; rejected a partition/fixture-ID blacklist in production because normal callers accept arbitrary valid findings |
| B: rejecting all probes could pass the proposed tests | Accepted; add a valid isolated-bundle control alongside rejection cases before real provider integration |

A read the revised sections 3/7, but not the full reference contracts or parallel
module. B additionally read document 03's knowledge-policy section and the revision
note, but not frozen probe contents or the other lifecycle sections. These bounded
reviews do not establish end-to-end B01/B02 behavior. Final clarifications receive
direct consistency checks; no additional independent review is claimed.

## 10. Implemented offline increment and explicit integration boundary

The owner subsequently approved this design and requested implementation,
testing and eval. `triage` implements source validation, strict assessment
validation, pure urgency/review policy, two-attempt recovery, persistent
phase reservations, complete output validation and atomic draft publication.
`tests\test_triage.py` exercises production functions using arbitrary synthetic
F-800x inputs; it is not a table of supplied finding answers. Production imports
neither the evaluator nor any test helper. The package adds no dependency.

Document 06 appeared concurrently and proposes concrete `TableSource` types,
integer context version 1, richer snapshot/payload/index fields and module-owned
compact UTF-8 serializers. These differ from the earlier abstract handoff.
Initially no knowledge implementation was available; it subsequently appeared
from the parallel session with its own `WorkflowExport.from_bundle()` adapter.
Do not invent a competing builder, call an unagreed positional API, or claim B03.
The temporary `ContextExport.read_export()` seam consumes an already materialized
artifact only. Its deliberately distinct `triage-export-v0` contract is **not**
the version-1 headless knowledge API. Before schema-1/2 removal, a focused
integration test exercised the module-owned release/snapshot/TableSource/builder/
export path using unchanged supplied domain notes and synthetic finding/inference
dependencies. It preserved domain bytes and pinned the same delivered knowledge
over a retry; `offline-implementation-7` retains that historical evidence. The
producer and test were retired after native migration. Test-local review metadata
was explicitly synthetic, not actual human approval or a production release.

### Provisional export, not a knowledge release implementation

The export is exactly `{snapshot, bundle}`. Snapshot fields are
`knowledge_version`, `content` (source-ID to exact text), `content_hash`,
`source_manifest`, `approved`. Approval is a producer's unauthenticated claim;
the consumer cannot certify source authority, rubric compatibility, truthful
approval or absence of covert answers. Snapshot content digest uses inference
`canonical(content)`: sorted JSON keys, ASCII escaping, standard separators.

Bundle fields are the section-3 names, with `contract_version="triage-export-v0"`,
payload maps `findings`, `registry`, `knowledge`, and an exact string-valued source
index. Source-manifest entries are exactly `source_id`, `kind`, `sha256`.
The consumer recomputes source/hash/membership/index equality and preserves source
strings. Semantic serialization is `canonical()` of all bundle fields except
`context_hash` and `source_manifest`; its UTF-8 SHA-256 is `context_hash`.
These provisional bytes also form the assessment context; this is intentionally
different from document 06, which serializes full provenance separately.
External export bytes get their own raw SHA-256. A literal independent tiny
wire fixture and source-row reorder tests cover this local codec, not the
separate module's future serializer.

Normal generation rejects evaluation kinds and overlays. A distinct
`isolated_probe` path checks a declared overlay's ID/text/hash/input kind and
the selected input's raw hash. The current seam is not the frozen B02 experiment:
there are no live positive/negative policy-influence results. Only explicit
`N+1 (TAG)` / `Duplicated (TAG)` declarations generate mechanically checkable
missing-partner gaps; free-text parentheses do not become a guessed plant graph.

Every missing-partner gap forces a concrete verification/review independently
of model materiality. Registry SCE is sufficient, **not necessary**, for the
independent safety floor 7: assessed material safety uncertainty also imposes
7 on non-SCE equipment. For an otherwise unclassified non-SCE gap, code requires
review but cannot infer safety consequence from the missing tag alone. Semantic
review must check omitted safety relevance; this limitation is not solved by
calling every absent partner a safety hazard or treating every SCE as high impact.
Non-applicable facts do not become unknown operands of immediate rules. Once a
confirmed trigger establishes a dependency (impaired protection -> deviation
status; unavailable craft -> capacity comparison; discovered unlogged impairment
-> restoration), declaring that dependent fact non-applicable is a recoverable
`fact_contract` contradiction, not permission to suppress all review/floors.
Verified non-restoration still meets floor 9 but does not require an invented
uncertainty-verification activity.

### Reproduction and evidence semantics

README gives the exact offline command:
`python -B -m tools.verify_triage --output <new-evidence-directory>`.
It runs existing unittest runners, inference/evaluator regressions, reference
integrity, the development checklist and an isolated installed-package import.
It records actual results and hashes under `eval\results\triage`, including
synthetic workflow inputs/captures, failures, budgets, policy grid/state matrix,
output hashes, Git revision/dirty state and still-unexecuted gates.
No frozen expectations, partition or source bytes are changed.
This is a collector of focused component evidence, not a new evaluation rubric.

The CLI requires `--allow-inference`; it is not paid-baseline authorization.
`RunConfig` pins explicit model/release/time, context and timeout limits,
reasoning effort, phase ceiling and a persistent `attempt_ledger` path.
Reservations survive failures/new runs and precede dispatch; a failed/ambiguous
dispatch is never refunded. Reuse one ledger/ceiling for all observations in a
phase. Single writer per output and ledger is required; no locking, authenticated
authorization, cross-process CAS or crash reconciliation is claimed.
Do not delete/reset evidence or ledgers to evade a budget.

The provider closes before publication. `run.json` persists
`ready_to_publish` and the intended output hash before the final atomic replace;
stdout is the success receipt. The record is deliberately not rewritten after
publication, since a later write error must not report failure after changing
the final output. Retain stdout/output with this record; interruption can leave
publication uncertain. Synthetic receipt accounting is not measured network usage.
Failed runs retain the attempt list separately from their JSON diagnostic.

### Bounded implementation review, round A

One read-only `rubber-duck` reviewer (`triage-implementation-review`) reviewed
production/tests against the component/frozen contracts. It ran no tests,
triage inference or nested agents and read no test finding cards/answers.
AI-only feedback is not domain certification; reviewer billing is not exposed.

| Finding | Disposition |
|---|---|
| Bridge can be mistaken for document 06's real interface/serializer/approval | Accepted: distinct version, export-only port, raw export hash and explicit unauthenticated-provenance record; real integration remains blocked |
| Invalid provider response can escape the JSON failure contract | Accepted: explicit response/configuration guards and bounded malformed-contract error handling; rejected indiscriminate catch-all handling that would hide arbitrary programming defects |
| Non-applicable facts were converted to unknown rule operands | Accepted: predicates only consume applicable states; regression tests cover three affected rules |
| Verified non-restoration unnecessarily demanded uncertainty verification | Accepted: retain floor 9, require verification only for unknown/suspected restoration |
| Use floor 7 for every missing-partner gap | Rejected as blanket policy: it invents safety relevance for non-safety gaps; retain mandatory gap review, independent SCE floor and non-SCE material-safety floor, disclose semantic omissions |
| Missing receipt masked original fatal provider cause | Accepted: fatal errors stay terminal with their cause; recoverable errors require verified accounting before retry, preserving the original error in attempt evidence |
| Write a best-effort success file after replacing output | Rejected: conflicts with final-fallible-operation boundary; document prepublication evidence and stdout receipt instead |

### Round B cross-critique and disposition

A second read-only `rubber-duck` reviewer (`triage-cross-critique`) read the
revised implementation/tests, collector and relevant contracts, cross-critiquing
round A. It ran no tests, nested agents or triage inference and opened no test
finding cards/answers. It agreed with the export separation, bounded response
validation, verified-restoration change, non-blanket gap policy, cause/accounting
separation and final-fallible-operation boundary. It found an important defect in
A's suggested NA fix: simply excluding a dependent NA fact could suppress every
rule. This was accepted and corrected using the explicit dependency contradictions
above; pure-policy and full recovery tests check actual urgency/review outcomes.
Reviewer agreement is neither independent domain review nor an acceptance gate.

| Other B finding | Disposition |
|---|---|
| Every suspected/unknown safety fact should independently force review | Rejected as blanket policy: sections 4/5 explicitly separate state from materiality, and unrelated unknowns must not escalate every finding. Named immediate conditions, dependency contradictions, uncertainty applicability, source gaps and assessed material safety still route in code. Missing/false materiality remains an explicit semantic-eval risk, not mechanically certified truth |
| Required verification text may not fit the 300-character action limit | Accepted as an explicit failure-path test and documented decision: bounded retry, then visible failure with old output intact; no truncation, omitted verification or extra final fields to evade the brief |
| Very short exact quotes can pass existence checks | Acknowledged limitation: quote presence/length does not prove entailment at any arbitrary cutoff. Semantic review must check support; no fabricated semantic validator is added |

The initial offline observation (`offline-implementation-1`) passed 37 production-
component tests plus the recorded inference/evaluator/reference/import checks.
Round-B fixes are not retroactively attached to its hashes. The subsequent
`offline-implementation-2` observation passed 39 component tests.
`offline-implementation-3` additionally exercised the exact A02
structural-recovery branch and A03 subprocess nonzero/stderr contract with both
absent and old outputs: all 41 tests and command checks passed, but the collector
correctly returned failure because it also hashed unexecuted knowledge tests
being added concurrently. That failed observation is preserved unchanged.
The collector now fingerprints executed production/regression dependencies
(including the real knowledge producer), not unrelated unexecuted test files;
this is explicitly not a whole-repository/system freeze or weakened acceptance.
`offline-implementation-4` added the actual knowledge-export handoff test, but
failed copying its long release filename into the fully named evidence directory
on Windows. That failed observation is retained, not counted as qualified.
The collector now uses short deterministic artifact-directory hashes plus
`test-id.json` mappings and always cleans up its own temporary test directories.
`offline-implementation-5` retained a subsequent failure: the parallel producer
changed its default domain locator and edited headless code during capture.
The test then pinned its configured source locator explicitly instead of depending
on that default. `offline-implementation-6` exposed the now-required distinction
between an absolute physical path and a repository-relative logical locator.
The fixture now uses the same explicit repository-relative locator for candidate
and store; a focused real-handoff rerun passes. Both failed observations remain
unchanged. The final `offline-implementation-7` observation binds these fixes and the actual
knowledge-export handoff test. Its command logs and `verification.json` are the
authoritative executed counts and source hashes.
No live triage provider was called. Architecture-review agents have separate,
unexposed billing; the collector's no-live-generation statement does not claim
this entire AI-assisted development task was free.

This increment does not establish real B01/B02/B03,
model fact/score/planning quality, X01 stability, frozen-test acceptance or final
all-21 delivery. Root `DESIGN.md` remains owner-reserved and no tickets are
hand-authored.

## 11. Owner-requested Copilot integration experiment

The owner subsequently confirmed inference completion and requested Copilot
integration/testing to limit development cost. Git commits `acd978a` and
`69117c1` establish the reusable adapters and their documented limitations.
The Copilot SDK still cannot control/observe internal HTTP retries, output-token
caps or USD billing. Its agent-runtime transport does not establish the brief's
raw-inference-endpoint compliance. This request permits a bounded development
integration experiment, not silent weakening of acceptance 1.2 or a paid baseline.

Add explicit `RunConfig.execution_mode="copilot_experiment"` and
`triage --provider copilot`. Default `strict` retains the direct-provider HTTP
checks; neither provider fallback nor fabricated HTTP counts is allowed.
Copilot requires a dedicated `.experimental-ledger.json`, mode-bound ledger
format and `.experimental.json` output; ordinary final output is rejected before
inference. Experiment results report `acceptance_eligible=false` and a distinct
success status. Unknown HTTP attempts/USD/token caps remain null. Application
sends are recorded separately from strict provider-attempt evidence.

Preflight checks actual restricted capabilities, chosen enabled catalog model,
Copilot routing and supported requested effort. Each successful/recoverable
response must establish one audited inference event, matching requested model,
matching actual system/user event hashes, zero observed tools, completed session
deletion and no boundary/cleanup errors. Missing/ambiguous evidence stops the run.
This proves only the exposed runtime boundary, never hidden network-attempt bounds.

For the completed historical experiment, the now-retired `tools.probe_triage`
collector recorded the unchanged reference check,
selected source hashes, explicit model/settings, code/Git state, command, knowledge
release and phase ceiling. Selection is fixed to F-1005, F-1010 and F-1012: three
singleton development groups, avoiding partial bound groups. Only those finding
descriptions, shared registry/domain and maintained rubric reach the provider.
No cards, expected scores, published example answer or test descriptions are
context. This small integration subset is not the full B01 development baseline.

One initial experiment: three nominal application sends, **maximum six**, at most
two per finding, 90-second inference deadlines, no requested reasoning effort,
fresh tool-disabled sessions and no application result cache. Backend caching and
internal HTTP retries remain uncontrolled. Select one explicit lower-catalog-price
account-visible model from the catalog; do not assume subscription access is free
or convert exposed billing units to USD. No fallback or automatic rerun. Any
diagnostic repeat needs a concrete recorded failure, preserved old observation,
unchanged phase ceiling/remaining ledger budget and disclosure; no extra budget
is inferred. No semantic-review model sends are included.

Knowledge is built by the separate module under the experiment evidence folder,
with an explicitly AI-assisted experiment-only local review declaration, not a
human/expert-approved production release. The producer owns its rubric/context/
export; workflow does not rebuild or edit it. A code-known gap's mandatory action
text is now supplied to assessment before inference through the same shared
policy helper used at validation: requiring an undisclosed exact sentence only
after generation was an avoidable deterministic interface defect. No per-finding
answer or urgency is added to the model request.

Review A (`copilot-triage-plan-review`, read-only AI engineering critique) required
separate capability/receipt checks, strict-path regression tests, mode-bound
experimental outputs/ledgers, complete message/deletion audits, catalog validation,
test isolation and explicit unverified billing. These safeguards are accepted.
Its suggested blanket renaming of mandatory failure-diagnostic `attempts` is not
adopted: preserve that required field, add experiment-specific accounting units,
and use `application_sends` for the experimental run trace.
Actual command outcomes, second cross-critique and limitations follow after testing.

The zero-generation catalog observation is
`eval\results\triage\copilot-catalog-1\catalog.json`. Select `gpt-6-luna`: its exposed
base input/output token-price values (10/50 per catalog batch of 1,000,000) are
among the lowest listed, matching Haiku 5.5 and MAI Code 2 Flash. These units are
not labelled USD; backend caching/context length can change billed usage. This
is a reasoned economical development choice, not measured triage-quality or
monetary-savings evidence. No second model or fallback is authorized.

Second read-only review (`copilot-triage-cross-review`) found no blocking issue
in the implemented mode/ledger/CLI/receipt separation. It inspected the workflow,
collector, error contracts and tests, but did not directly read the policy/
assessment helper or this section; no domain review is implied. Accepted:
missing captures cannot prove isolation, collector errors must persist failed
observations, valid drafts with invalid provenance are not integration passes,
and singleton group sizes must be verified from the manifest. A bounded cleanup
margin now surrounds Copilot's own inference timeout; exhausted outer deadlines
record a failed send with unknown dispatch outcome instead of a bare reservation.
Focused regressions cover these paths.

The suggestion to hard-kill the child at 900 seconds is rejected for this local
prototype: killing only the wrapper can orphan its owned Copilot runtime. Use
the adapter's bounded inference/startup/session/runtime cleanup and report any
failure instead; no new process supervisor/OS tree-killing implementation is
introduced. The existing mandatory JSON failure fields are retained with
explicit experiment accounting labels.

The first live-command invocation (`copilot-integration-1`) stopped during offline
preparation, before creating any Copilot send or phase ledger. The concurrently
developed knowledge adapter required original TableSource values and cutoff to
verify its export, not just snapshot/bundle. Owned callers supplied those original
inputs; the retired collector's preparation/consumer regression checked the
contract without calling a model. The failed observation remains unchanged. This
consumed zero generation sends; the subsequent invocation retained the same
six-send authorization, not a reset of spent budget.

The first actual-model observation (`copilot-integration-2`) used two application
sends on F-1005, then stopped without output. Both calls passed the exposed
Copilot boundary audits. Assessment validation rejected the first proposal's
evidence and the second proposal's non-applicable/confirmed-false combination.
These are retained development failures, not model or system passes. Inspection
found that the prompt/schema exposed applicability enums but did not state their
cross-field restrictions or the exclusion-evidence requirement; retries received
only a generic error code and no rejected draft.

The generic assessment instructions now state the already-enforced combinations,
require verbatim quotations and quote-backed exclusions, without changing any
validator or score expectation. A recovery receives the named local validation
message and its own untrusted rejected draft, not an expected answer. Evidence
is still checked only against original context. This is a disclosed
development-output-informed interface fix, not an untouched baseline.

One historical diagnostic repeat used the same gpt-6-luna model, source bytes,
release, settings and **original spent phase ledger** (two of six sends already
reserved). The retired collector's `--repeat-from` mode validated the original
config against captured config, source hashes and unchanged ceiling; it built a
fixed CLI command rather than executing an arbitrary stored command. The new
observation had at most four remaining sends, never a new six-send budget. The
collector and its focused tests were removed after the phase closed.

### Actual diagnostic outcome and stopping decision

The diagnostic observation `copilot-integration-3` also failed, consuming two
more sends on F-1005. Its first response quoted Markdown with different
formatting/line breaks; its second passed schema, fact-state and exact-evidence
validation but failed `policy_verification`. The proposed action changed a
required period to a semicolon and lowercased another required sentence. The
activities remained semantically similar, but the approved implementation
requires exact inclusion; no automatic punctuation repair, validation weakening
or hand-corrected ticket was used. This is a brittle interface finding, not proof
that the domain assessment was incorrect or correct.

Both observations have stable execution-time source hashes and matching actual
Copilot system/user audits, one observed inference event per send, zero observed
tools, completed session deletion and no observed boundary violation. Actual
provider-bound context excludes test descriptions. This is limited integration
evidence for A03/B01/X02, not scenario acceptance. The recovery itself was
exercised (A02), but neither observation recovered to a publishable batch.

| Observation | Application sends | Final error | Published output | CLI wall time |
|---|---|---|---|---|
| `copilot-integration-1` | 0 | Preparation `TypeError` | None | Not model timing |
| `copilot-integration-2` | 2 | `fact_contract` | None | 68.234 seconds |
| `copilot-integration-3` | 2 | `policy_verification` | None | 61.546 seconds |

Across the four receipts, exposed usage totals are 66,801 input tokens, 11,352
output tokens, 4,948 reasoning tokens, 6,114 cache-read tokens and 60,675
cache-write tokens. These counters may overlap and are not additive billing
categories. Summed `usage.cost` is 4.0 and `copilotUsage.totalNanoAiu` is
1,332,271,500; neither is reported as USD. Requested reasoning effort was unset;
all four receipts exposed `medium`. No comparison run establishes savings.

The phase ledger now contains **four of six reservations**. Stop here rather than
spending the last two slots on an unchanged three-finding experiment that cannot
complete nominal coverage. F-1010/F-1012 were not targeted for assessment; their
descriptions were present in the shared three-finding context on each send.
Do not claim three successful cases, model quality, calibrated semantic acceptance, X01 stability, frozen-test
success or final tickets. A next development decision should explicitly address
the action-rendering boundary (code-owned composition versus model verbatim
copying), with bounded review before changing the approved contract. This task
does not silently redesign that boundary or authorize another model/budget.

The diagnostic-guidance changes were author-adjudicated against existing
validation and focused regressions; no additional independent/domain review is
claimed. The final offline observation is
`eval\results\triage\offline-copilot-1\verification.json`; its executed counts,
command logs, source and artifact hashes are authoritative. It tests control
flow and failure handling, not the failed smoke's semantic quality.

A post-run source comparison found parallel knowledge edits after the stable
live observation (`__init__.py`, `__main__.py`, `context.py`, `editor.py`,
`knowledge.py`). The offline run exercised later headless dependencies, but
`knowledge.py` changed again after that capture. Its 58 workflow tests, 48
inference tests and 20 evaluator self-tests passed on the recorded snapshot,
not an implied freeze of the concurrently changing worktree. No live replay of
newer knowledge code is claimed. Workflow/inference code still matches the last
live snapshot. `postrun-provenance.json` records these distinctions, observed
hashes and persisted-artifact checks. Reverify the producer after it stabilizes
before a full integration baseline; old results are not rebound to new hashes.

## 12. Owner-directed corrective smoke phase

The owner explicitly requested continued fixes until the actual live smoke passes.
The prior stopping decision is historical, not completion of this new request.
Address the measured interface defect rather than sampling unchanged prompts
until one happens to satisfy punctuation constraints.

Proposed boundary correction (A01/A02/A03, D02, X02): the model proposes concise
core action text and structured verification activities; code appends every
policy-required activity not already present verbatim. It does not paraphrase,
truncate or drop the model's core action or mandatory activity. The composed
action must still be at most 300 characters; overflow remains a recoverable
contract failure, then a terminal no-publication failure after two attempts.
Evidence, applicability, L/I, urgency, coverage and human-review rules are unchanged.
This changes the component's rendering responsibility, not frozen evaluation.
Prompts will describe that interface and direct quotations to original indexed
source values instead of reconstructed Markdown paragraphs.

The new owner-directed corrective phase authorizes at most **12 additional
application sends** on gpt-6-luna, with a persistent dedicated phase ledger,
maximum two per target per observation, the same three development targets,
90-second inference deadline and no requested reasoning effort. All diagnostic
observations in this phase reuse its spent ledger, source-input/export bytes and
configuration; code/prompt fixes have new recorded hashes and must remain stable
during each observation. Each rerun needs a concrete failure and recorded fix. The prior
six-send phase is closed with four consumed/two unused, not reset or reused to
evade its ceiling. Total generation sends across both phases cannot exceed 16
under this authorization. No new model, semantic-review model, test partition
or final all-input generation is authorized; USD and hidden HTTP bounds remain
unverified. Copilot remains experimental, not strict acceptance.

An experimental live-smoke pass requires CLI exit 0, exactly three automatically
published tickets with valid identities/schema/lengths, output hash matching the
publication receipt, all captured Copilot receipts passing model/message/tool/
cleanup audits, no test descriptions, stable execution-time source hashes and
the phase ledger within its authorized ceiling. It does not imply semantic or
strict system acceptance. Preserve the model core, appended activity spans and
composed action in each attempt trace, including overflow failures.

Reviewer A (`smoke-render-review-a`, read-only AI) read the implementation and
section 12, but did not inspect the supplied brief or document 03 and ran no
tests/models. Accepted: replace the old copying instructions, preserve the
post-composition exact-coverage invariant, record composition provenance, provide
bounded actionable overflow feedback and compare repeats against the recorded
ceiling plus actual ledger. The model still sees code-known requirements to
coordinate concise activity text, explicitly as code-owned action text rather
than facts. Rejected: arbitrarily shrink the core's schema limit below the brief's
300; instead guide brevity and validate the composed limit. Also rejected an
immediate terminal overflow: model-authored activities may be shortened legitimately
within the existing two-attempt recovery contract.

Composition uses case-sensitive literal substring presence, a single space
separator and policy's deterministic activity order. Nothing is normalized or
silently removed. A new phase is explicitly invoked with `--phase-budget 12`;
default remains six, values above 12 are rejected, and repeats cannot override
their original budget. These local ledgers are not a tamper-proof authorization
service; the operator must not create another ledger to evade this phase's cap.

Reviewer B (`smoke-render-review-b`, read-only AI) cross-critiqued the implemented
boundary against the supplied output constraints and selected document 03
requirements; it did not read sections A/D or section 12 in full, and ran no
tests/models. No implementation blocker was reported. Accepted focused gaps:
CLI budget rejection before preparation, separately inconsistent manifest/ledger
ceilings, exhaustion, redirected ledgers and code-known gap overflow recovery.
Existing composition tests already pin literal inclusion and preserved core;
no redundant language-behavior tests were added. Both reviews are bounded AI
engineering feedback, not independent domain certification; billing is unexposed.

The initial corrective observation is `copilot-correction-1`, explicitly launched
with `--phase-budget 12`. This created the sole corrective-phase ledger; the phase
is now closed and the collector was retired, so no further observation is
authorized. The prior closed phase remains at four sends. The nominal successful
batch needed three sends, at most six with per-target recovery; twelve permitted
at most two worst-case complete batches, not unbounded sampling.

The first corrective observation validated F-1005 and F-1010 with code-composed
actions, then stopped on an explicit F-1012 `unassessable` response (three sends,
stable execution hashes, no output). The model treated missing partner/plant
totals as necessarily preventing any supported impact assessment. This is
preserved as a failed observation, not overridden or coerced into a ticket.
The next generic prompt clarification distinguishes missing plant-state facts
from inability to score the observed loss under the supplied rubric. Qualified
scores still need original evidence; missing redundancy is neither credited nor
asserted failed, unknown capacity stays unknown, and policy floors cannot justify
L/I. Genuine inability remains terminal with no scored fallback. No band, target
score, finding-ID branch or new knowledge content is introduced. This follows
the supplied item/consequence distinction and document 03's uncertainty versus
inability policy, not an evaluation answer.

The second corrective observation validated F-1005, then used both attempts on
F-1010: independent paraphrases of the same checks overflowed the composed action;
the shortened retry then omitted a required fact-slot activity even though a
similar uncertainty activity existed. Six of twelve phase sends are now reserved.
The next contract clarification lists the existing conditional fact-slot
requirements and instructs exact reuse of concise activity strings across facts,
uncertainties and code-known requirements. This makes the already-enforced
protocol visible, without semantic deduplication, removing required checks,
normalizing wording, changing the 300-character limit or altering policy.
The same phase/input/export/config is retained for the next diagnostic observation.

### Passing live observation

`copilot-correction-3` returned CLI exit 0 and
`experimental_draft_generated`: three automatically generated tickets covering
F-1005, F-1010 and F-1012. Its first F-1005 attempt still had an inexact domain
quotation; the bounded recovery corrected it. All three final assessments and
composed actions validated without manual edits. Four actual sends were used,
with stable execution hashes, matching message/model audits, no tools, completed
session cleanup and no test descriptions in context.

| Corrective observation | Sends | Outcome |
|---|---|---|
| `copilot-correction-1` | 3 | Two targets validated; third explicitly unassessable; no publication |
| `copilot-correction-2` | 3 | Action overflow then missing fact-slot activity; no publication |
| `copilot-correction-3` | 4 | Three experimental tickets published; one evidence retry |

The corrective ledger contains **10/12 reservations**; the prior closed phase
contains 4, for **14/16 total authorized sends**. Stop inference after this pass.
Do not spend the remaining two corrective slots on an unnecessary repeat.
Across the ten corrective receipts, exposed totals are 167,412 input, 33,745
output, 17,132 reasoning, 23,128 cache-read and 144,254 cache-write tokens.
Counters may overlap. Summed `usage.cost` is 10.0 and `totalNanoAiu` is
3,513,853,000, not reported as USD; hidden HTTP attempts remain unknown.

The output SHA-256 is
`fc6faa1868aca8e941cb3bc6482ef769298a12f580982091c5cedda82b8d209c`.
The separate `copilot-correction-3\verification.json` checks the persisted
publication receipt/hash, schema/coverage, all actual phase receipts, deterministic
action composition and urgency derivation. Final offline regressions are recorded
under `offline-fix-2`, not attached retroactively to prior snapshots.

An uncalibrated AI-authored output inspection observed the failed head versus
remaining 2oo3 distinction, the 27/50 Pa refuge shortfall, and explicit unknown
partner/capacity-versus-POB status in the lifeboat draft. All require human review;
urgency is code-derived. This inspection is not a calibrated semantic review,
score certification, X01 stability result or full development baseline. No frozen
test or all-21 final generation was run; Copilot strict/raw-endpoint limitations
remain. The successful retry does not establish that quotation failures are
eliminated generally.

The first final offline capture (`offline-fix-1`) passed all 63 workflow tests,
48 inference tests, 20 evaluator self-tests and every command check, but correctly
reported an unstable observation because another session changed README during
capture. No runtime source changed in that window. That failed capture is retained;
`offline-fix-2` repeats the same checks against the settled documentation snapshot.
No additional model calls are needed or made for this documentation drift.

## 13. Source-first coordinated migration and system-evaluation boundary

The owner's new request replaces the workflow's legacy knowledge assumptions
with document 06 sections 8-9. Section 3 is the current design decision; sections
10-12 remain observations of earlier source/configuration identities. No source
package, frozen triage reference, split, expectation or fingerprint is changed.
`triage_knowledge` is separately owned and is not modified in this migration.
Root `DESIGN.md` remains reserved; this component document cannot pass that
delivery gate on its behalf.

| Requirement / scenarios | Migration and expected evidence |
|---|---|
| Brief B, B01/B03/D04 | Actual source-first store/release/tool/builder; active exact texts, full selected evidence and unchanged comments; independently bound raw inputs and local lineage; concrete source-edit and activation path |
| Brief A/D, A01-A03/D02 | Native failures remain pre-dispatch, no partial/stale publication; exact terminal knowledge errors; invalid pins, unsupported contracts and size/input mismatches tested |
| Brief A/C, A04/C04/D01/D03 | Separate approved ordinal policy delivered as `assessment_policy`; source facts are not rubric/urgency; no middle-score fallback or source-policy conflict laundering |
| Brief C, C01-C03 | Existing urgency arithmetic, confirmed overrides, precautions, materiality and all-SCE review unchanged; missing-partner gaps cannot be suppressed by model output |
| B02 | Current native module rejects evaluation-input binding and exposes no isolated overlay contract; record blocked rather than contaminate shipping knowledge or claim legacy influence evidence |
| X01/X02 | One immutable release and one retained bundle per run; row-order determinism with changed raw hashes; actual repeat/model/budget/final-delivery evidence still separately required |

`tests\test_source_workflow.py` exercises production workflow/CLI with the actual
source-first store, release, selector and native builder. Its synthetic
publication/activation declarations and fake inference are explicitly software
fixtures. It additionally passes the unchanged supplied domain and the 13
selected development rows through the actual prepared-request seam, checking
source-byte coverage/comments/partner membership and test-description exclusion.
That is delivery wiring, not a real provider call, knowledge use, semantic
quality or content approval. No test cards/outputs are used to tune the workflow.

The primary command requires `--knowledge-store` and `--activation`. Activation
candidates are inert until explicitly reviewed. Legacy command helpers now name
`--legacy-replay`; existing historical ledgers and paid observations are not
reset, reclassified as native, or automatically replayed. A matching local hash
does not convert a reviewer assertion into human/domain approval.

### Bounded AI review and adjudication

Reviewer A (`workflow-contract-review`, read-only AI architecture review) challenged
the proposed native migration against candidate requirements and document 06.
All six substantive adjustments were accepted: use a retained read-only release
view rather than pretend the builder takes a snapshot; distinguish both native
indexes and canonical hash bodies; remove knowledge-owned rubric authority;
explicitly block unsupported native B02; derive known partner gaps outside the
bundle and preserve terminal `KnowledgeError.code`; fingerprint actual native
dependencies and do not claim readiness from legacy checks. The review ran
reference integrity only, not a model or system evaluation. No services, caches
or automatic legacy conversion were added.

Reviewer B (`workflow-cross-review`, read-only AI) cross-critiqued those findings,
the native implementation, tests and documented boundaries. It ran 92 targeted
offline tests successfully and found one required correction: release-resolution
`KnowledgeError` was still collapsed into a generic invalid-release diagnostic.
Accepted/fixed: retain the original terminal knowledge code; only filesystem
resolution failures map generically. A focused native regression verifies
`unsupported_contract` / `invalid_dependency`, zero attempts, no publication and
the missing-file diagnostic. Its other findings accepted the single-retrieval
boundary and explicit B02/release blockers; no domain certification or paid model
evaluation was performed. The concurrently added module
`validate_source_context` deliberately rebuilds context for external validation;
the initial in-process workflow did not use it to perform a second retrieval.
**Superseded by section 14:** the committed public consumer validator is now
required, including its independent deterministic rebuild at preflight.

### Gates not waived by the release request

The latest retained upstream observation
`eval\results\knowledge\extraction\source-first-verification-1\readiness.json`
reports no promoted release, eight failed selective-efficiency cases, unqualified
C1, unavailable strict HTTP/USD accounting for Copilot and pending downstream
B01/B02. This is a hash-bound historical observation, not an assertion about
unmeasured parallel edits. Initial inspection found only the legacy draft.
A parallel session later created a source-first draft; draft existence is not
a reviewed immutable release. Workflow must not silently publish either draft or
fabricate new content approval.
Re-read actual upstream status before activating a separately delivered release.

Consequently, a green offline integration is necessary but insufficient for the
requested system release. Before real development/test/final work: obtain a
reviewed compatible source-first release and activation; settle native B02's
isolated module contract; declare strict provider/model/pricing and bounded phase/
review budgets; calibrate the actual semantic reviewer. Then run all 13
development findings twice at fixed pins, review all dimensions and the knowledge
probe; freeze before the one eight-finding test; automatically generate/review
all 21 only after those gates. Required final owner `DESIGN.md`, fresh-environment
reproduction, low-cost evidence and genuine Git history remain delivery checks.
Do not label pending/failed gates green or retry a fixed probe until it agrees.

### Observed migration checks

The final stable software observation is
`eval\results\triage\source-first-snapshot-verification-2\verification.json`:
84 workflow/native-and-legacy integration tests, 48 inference regressions,
63 source-first component tests and 105 evaluator self-tests passed (**300 tests**,
no failures/errors/skips), with reference validation, checklist generation and
isolated installed-package imports passing. All runtime source fingerprints were
stable during that observation. These are software results, not a 300-case
domain/model evaluation.

Two earlier shared-checkout captures (`source-first-migration-1` and `-2`) passed
their test commands but correctly failed the stability gate: the parallel session
changed `eval\run_knowledge_completion.py`, then its test, during execution.
Both observations remain intact. Rather than ignore those files or change the
gate, a byte-hashed source snapshot was copied and verified against the source
at capture time. It is local under ignored `.artifacts\s1`, with
`snapshot-manifest.json`; it is not a promoted release or durable shared backup.
The first isolated run used a longer snapshot path and hit a Windows path-length
failure in an upstream evaluator test. Moving the identical bytes to the short
path resolved that environment failure; the failed
`source-first-snapshot-verification-1` remains preserved. No evaluator expectation
or production behavior was changed to obtain the subsequent pass.

A wheel built from that snapshot installed with declared runtime dependencies
in a fresh local virtual environment. All 30 installed runtime Python modules
match the captured source hashes and `pip check` passes. The initial
no-build-isolation attempt lacked `bdist_wheel`; rebuilding with the declared
isolated setuptools backend succeeded. This establishes packaging/import
reproducibility, not a live all-21 reproduction, affordability or final submission.
The wheel is local in `.artifacts\triage-source-first-wheel-1`; it does not contain
final tickets or the reserved owner design.

The current author separately reviewed the two disclosed A04 contradiction
controls against actual development source rows. The existing assessor reports
`known_fixture_conformance: pass` in
`source-first-calibration-1\report.json`, with AI-only, same-author, non-independent
provenance and visible expected verdicts. There was no separate model-judge send;
conversation/reviewer billing is unavailable, not zero. This narrow calibration
does not pass A04's real-output/uncertain-score requirement or certify a semantic
reviewer for arbitrary findings.

`source-first-migration-summary.json` links the observed checks and current
release blockers. Its final checkout preflight found eight pending source-first
items and no immutable release; all 30 current runtime modules still matched
the verified snapshot. No live triage provider call, X01 model repeat, frozen test or
all-21 generation was executed by this migration. Test prerequisites remain
unmet; no final root `tickets.json`, fabricated review, reserved `DESIGN.md`, commit or push
is produced to disguise that fact. This final observation text was added after
the software snapshot; code evidence remains bound to its recorded source hashes,
not retroactively to a later documentation or parallel-module revision.

## 14. Committed native handoff and bounded system integration

The renewed owner request and knowledge-session handoff identify `8b83639`
(native consumer validation) and `db49683` (completion-experiment freeze).
The workflow now uses the public module facade for both construction and
validation. It no longer duplicates the module's bundle/index/entry validator.
Workflow-owned activation, immutable release resolution, raw table bindings,
assessment policy, missing-partner gaps and terminal diagnostics remain local.
No knowledge-module, extraction experiment, default-store or frozen triage
evaluation file is changed by this correction.

This supersedes section 13's decision to avoid the public validator. Merely
checking included entries cannot establish that the selector's required entries
were not omitted. Module-owned reconstruction closes that gap without a workflow
selector or per-finding answers. Integration regressions cover rehashed omission,
discarded forged local evidence, exactly one consumer validation before inference,
one retained snapshot across retries, and replacement expiry without resurrection.
This maps to B01/B03/D04 and the A03/D02 no-publication boundary.

### Preregistered experimental development execution

`tools.integrate_triage` prepares an isolated source-first C0 store from the exact
unchanged supplied domain, selects only the 13 development rows, preserves the
entire shared registry, and records explicitly SOFTWARE-only publication and
activation assertions. These declarations are test fixtures, not the real pending
KB's editorial review or approval of this policy for operations.

The initial observation and at most one fixed-configuration repeat share one
`native-e2e.experimental-ledger.json`: 13 nominal / at most 26 application sends
each, **52 total**, two application attempts per finding. This is the renewed
request's bounded development-integration experiment, not permission to reset old
knowledge ledgers, fund extraction, rerun a failed fixed probe, or execute test/
final. HTTP attempts, exact USD and a USD-enforced budget are unavailable in
Copilot; the experiment remains `acceptance_eligible=false`.

Prepare first, review the written plan, then explicitly execute it:

```powershell
.\.venv\Scripts\python.exe -B -m tools.integrate_triage --model gpt-6-luna --output eval\results\triage\native-e2e-plan-1
.\.venv\Scripts\python.exe -B -m tools.integrate_triage --plan eval\results\triage\native-e2e-plan-1\plan.json --output eval\results\triage\native-e2e-development-1 --allow-inference
.\.venv\Scripts\python.exe -B -m tools.integrate_triage --repeat-from eval\results\triage\native-e2e-development-1 --output eval\results\triage\native-e2e-repeat-1 --allow-inference
```

The driver calls the actual native workflow CLI. Frozen code/input/config hashes,
single-use observation reservations, the shared persistent send ledger, captured
provider inputs/receipts, publication receipt and persisted ticket hashes are
retained. A changed pin fails; it is never refreshed automatically. Output files
are `.experimental.json`, never final `tickets.json`. Structural/delivery success
is separate from semantic review and X01 decision adjudication. Actual current
reviewer calibration and output-bound judgments must use the existing assessor.
Any failed observation remains evidence; no outcome is presumed here.

Native B02 still needs an agreed isolated `evaluation_input`/overlay API. The
handoff forbids disguising those fixtures as ordinary source knowledge.
Development success cannot waive that gate, genuine KB activation, strict
accounting or the owner-reserved final system design. Test/final remain unopened
until the applicable development gates pass.

### Bounded handoff review dispositions

Two actual read-only AI reviewers (`native-handoff-review-a` and then
`native-handoff-review-b`) challenged this increment. A read the adapter, driver,
workflow and module validator but not the candidate/evaluation documents or tests.
B cross-critiqued those findings, exercised the 24 then-current targeted tests with
the repository virtual environment, and checked a constructed native request.
Neither performed domain certification or live triage inference.

| Finding | Adjudication |
|---|---|
| A: preparation can reserve a doomed observation before full context preflight | Accepted: prepare performs the real native preflight, freezes context hash/bytes, and execution checks every captured context against it |
| A: shallow executable fingerprints could miss nested modules | Accepted recursive Python-module hashing; no current non-Python runtime prompt/schema assets were found |
| A: post-dispatch verification can lose accounting in its summary | Accepted: failure observations retain CLI status, sends, phase reservations, output hash and named audit failure; regression exercises that path |
| A: kill the outer CLI on a wall-clock timeout | Not added: provider startup, send, session cleanup and shutdown already have explicit deadlines; externally killing the parent risks orphaning SDK children in the shared environment. Both reviewers found no experiment blocker here |
| A: a public validator using the same builder is not an independent implementation | Agreed limitation, rejected as reason to skip it: independence is of trusted input/release/policy bindings, not a second algorithm or semantic oracle |
| A: add a separate store README for fixture status | Not needed: immutable review/release metadata plus plan/observation explicitly state SOFTWARE TEST ONLY; no production approval is claimed |
| B: successful collector execution needs a fake-CLI regression before paid sends | Accepted: full native capture, audited synthetic receipts, complete selected coverage and publication hash are checked in a focused software fixture |
| B: check receipts for recoverable failed sends too | Accepted: collector audits every available receipt, not only validated sends; missing/unauditable receipt conservatively fails delivery qualification |
| B: an operator could hand-forge a prior observation | Disclosed single-writer/local-assertion boundary, not authenticated evidence; original pins, single-use repeat marker and persistent phase ceiling remain enforced |

System Python lacked the SDK in B's check; all documented/run commands use the
repository `.venv` interpreter, and the subprocess retains `sys.executable`.
No extra reviewer, independent approval or zero-cost agent claim is made.

### First real observation and bounded corrective development

`native-e2e-development-1` made **three** application sends at the planned pins:
F-1001 validated; F-1003 failed both allowed attempts on exact-quote validation.
The first invalid quote joined a hard-wrapped source line; the repair then
attributed a real firewater comment to the other pump's reference. Captured
native context and receipts audited successfully and executable hashes stayed
stable. CLI exited 1, preserved diagnostics and published no tickets. This is
an actual failed system-integration observation, not an accepted baseline.

The generic corrective change is confined to `triage.assessment`: recommend
short single-line quotations and same-source attribution; report the exact
assessment field/citation index, offending quote and **complete** native address.
Previously the error truncated the native address at 120 characters and did
not identify the rejected citation. Exact-substring validation is unchanged;
code does not normalize quotes, switch sources, insert answers or repair scores.
Focused regressions cover wrapped-line and related-source quote failures.

One explicitly versioned corrective development observation is allowed for this
diagnosed defect, followed only on success by the already-budgeted fixed-config
repeat. It uses the original selected bytes, fixture release, activation, model,
settings and **same 52-send ledger**; three spent sends leave at most 49, not a
fresh 52. The old plan/failure remain immutable. A new corrective plan records the
old plan hash, failure path/reason, deliberate changed executable hashes and
remaining ceiling before dispatch. It is not X01 relative to the changed prompt,
an untouched baseline, an automatic pin refresh, or authorization for further
sampling. The existing driver's `execute(plan, new_directory)` is used explicitly
for this corrective observation after reserving a single-use corrective marker;
normal `--plan` will correctly refuse to replay the old frozen plan.

### Observed corrective outcome: release remains blocked

The corrective dispatch first failed **before any send** because the knowledge
session changed `source.py` after the correction freeze. No activation/strategy
was silently refreshed. `native-e2e-correction-preflight-1` records the drift.
The exact already-planned bytes were then isolated under `.artifacts\i1`;
34 frozen runtime/config/reference files match the correction plan. The source
file's frozen bytes were recovered exactly from commit `6736fc2`, not reconstructed
or written over the shared working copy. Its manifest records that origin.
This local runtime snapshot is not a durable shared release or qualification of
subsequent knowledge changes.

`native-e2e-correction-1` made **nine** further sends (12 cumulative / 52 cap).
Six findings validated: F-1001, F-1003, F-1004, F-1005, F-1006 and F-1007.
F-1004 required its permitted second attempt to repair another wrapped quote.
F-1008 failed both attempts because composed actions were 420 and 398 characters.
Its assessment marked multiple unrelated protection/evacuation applicability
questions uncertain and proposed eight distinct mandatory checks; shortening the
core alone could not satisfy 300 characters. This remains a real assessment/
action-planning defect, not permission to drop checks, truncate actions, invent
exclusions or weaken the brief. Exact native context/message/model/zero-tool
audits passed and the isolated runtime was stable.

CLI again exited 1 and published no batch. The unused 40 send slots are **not**
permission for unplanned additional sampling. The declared corrective observation
is exhausted; a fixed-config repeat cannot establish X01 without a successful
baseline. No complete development batch exists to submit to semantic assessment.
The first failed observation is not compared with the changed prompt as X01.
The frozen eight-finding test and final all-21 generation remain unopened.
The actual failures, spent ledger and exact inputs/receipts are retained; no
root `tickets.json`, fabricated human approval or owner-reserved `DESIGN.md`
is produced to turn this result green.

The final current-checkout software observation is
`native-handoff-verification-2\verification.json`: **337 passing tests**
(94 workflow/integration, 48 inference, 69 source-first component and 126 evaluator
self-tests), reference integrity, checklist and isolated installed import checks,
with stable measured fingerprints during that observation. Current knowledge
work is concurrent: this does not retroactively bind those changed bytes to the
earlier live experiment. The live snapshot remains pinned to its own hashes.
`native-e2e-repeat-blocked-1` verifies `repeat_contract` rejection without a send.

`native-handoff-system-summary.json` links commands, hashes, exposed usage and all
17 scenario states, separating software passes, failed real E2E and unexecuted
acceptance gates. Final default-store inspection still found eight pending items,
zero reviewed, no release/activation and unchanged candidate digest
`fc7c8553b13614d0416a3cb8ca500280d5cfde01a5d1043ffa410b68799bc013`.
These final observations are added after the verification's recorded document
hash; no old measurement is rebound to this explanatory text.

## 15. Owner-renewed correction and native probe completion

The owner explicitly renewed corrective work after section 14's failed system
observations. The old stop declaration is superseded prospectively, not erased:
the same development ledger retains **12 spent / 52 maximum**, leaving 40 for
corrective development and a successful fixed-configuration repeat. Each finding
still has at most two attempts per observation; no old run or ledger is reset.
A continuation must bind the actual prior plan path/hash, prior ledger hash and
observed reservation count. New knowledge executable identities require deliberate
fresh fixture publication/activation, not silent refresh of the old plan.

### Action-planning root cause

The assessment prompt distinguishes a relevant fact with unknown status
(`applicable`/`unknown`) from uncertainty about whether the question concerns this
function. Missing mention does not make every policy question uncertain.
Equipment type/service may justify an unrelated question's exclusion with quoted
evidence; actual dependencies and material uncertainty must remain explicit.
Evacuation questions are about craft or evidenced capacity dependencies, not
speculative remote consequences of every SCE defect. This does not make source
type a universal semantic oracle; review every `not_applicable` judgment in actual
outputs. Code's existing dependency guards and all policy floors are unchanged.

Action-overflow feedback budgets **all distinct appended checks**, rather than
encouraging a shorter core while leaving >300 characters of checks. It reports
the number of checks and available average characters, while requiring retention
of each genuine obligation. The overall 300-character validator is unchanged.

### Native B02 contract repair

A bounded implementation in the knowledge module adds optional trusted
`input_purpose="isolated_probe"` to binding/retrieval/builder and matching
`expected_input_purpose` to validation. Only that explicit path permits honest
`evaluation_input`; probe bindings/results/contexts carry a hash-covered purpose.
At that increment the default normal bundle-2 layout remained unchanged, and default consumers rejected
probe declarations. No extractor, store schema, source text or frozen evaluation
expectation is changed. New executable strategy hashes require explicit repinning.

Workflow's separate `IsolatedProbeContext` binds independent raw table hashes,
declared input kinds, unchanged shipping policy plus a labelled experimental
section and its complete hash. It uses both public native APIs. It requires
`purpose="isolated_probe"` and `.experimental.json` output even with a strict
provider. The normal CLI cannot construct this variant; probe policy never
enters `payload.knowledge`.

`tools.probe_native_knowledge` runs the exact frozen four conditions through the
actual workflow, one selected finding per condition with the full shared registry
plus the disclosed synthetic bench device. The negative row is unchanged original
development F-1016, not a test finding. Before/after native packets differ only in
the declared artificial policy and resulting context hash. The existing frozen
6-to-8 convention is copied verbatim into separate assessment policy; expected
outputs/reviewer answers are not provider inputs. Confirmed-function-failure
minimum 9, all fact checks, urgency and output constraints remain unchanged.

B02 has its own new `native-b02.experimental-ledger.json`, four nominal/eight
maximum sends, at most two per condition and no automatic repeats. Old legacy B02
spending remains historical, not refunded. Current calibrated negative-control
review and actual outputs are required; completing four calls is not a pass.
Copilot HTTP/USD/raw-endpoint limitations and real KB approval remain disclosed,
not waived by a software-fixture experiment.

### Renewed bounded reviews

Two read-only AI critics (`renewed-triage-review-a`, then
`renewed-triage-review-b`) found no experiment blocker. A could not import the
SDK through system Python; B ran nine native-probe tests with `.venv`. The author
ran 85 targeted tests. None of these is a semantic/model-quality result.
Accepted: explicit applicability adjudication in actual review, exact frozen
policy re-derivation during B02 execution, prior-plan/ledger hash checks on
continuation and a separate eight-send B02 ledger. Arbitrary experimental policy
is a trusted isolated configuration surface, not a shipping CLI input.

B's assertion that the retry loop allows three attempts was rejected by the
actual control flow: `while attempts < 2`, pre-dispatch increment, terminal
`attempts == 2`. The shared eight-send cap therefore covers four conditions at
their maximum two attempts. Failed/unexecuted conditions retain their diagnostic
status and observed score null, not an invented wrong numeric answer. Extra
unreferenced files cannot enter packets because construction consumes explicit
trusted tables/release/policy, not directory discovery. No expectation was changed.

### Direct inference route discovered and compatibility-checked

Read-only metadata confirmed an already-existing Azure deployment
`gpt-5.1-chat`. A single separately ledgered native-schema acknowledgement
request succeeded using the existing credential environment (no secret recorded).
Its actual response identifies `gpt-chat-latest`, not an invented dated snapshot.
The deployment/response alias and sanitized metadata are retained; backend weight
immutability is not claimed. No resource was created or reconfigured.

The renewed system baseline therefore switches explicitly to the permitted direct
Azure inference adapter instead of spending more Copilot experimental calls.
This is a new provider/configuration identity, not X01 against Copilot and not
reclassification of its 12 historical sends. `tools.integrate_triage --provider
azure` uses a separate strict development ledger: 26 nominal / at most 52 actual
retry-free HTTP sends for development plus its one fixed-configuration repeat.
All requests use native JSON Schema, no tools/redirects/SDK or transport retries,
4096 completion tokens, timeout 90 seconds, no reasoning-effort parameter,
128000 context bytes, and exact original-domain fixture pins.

Conditional phase ceilings are strict B02 eight, frozen test sixteen and final
all-21 generation forty-two; they execute only after prerequisite acceptance.
The compatibility phase has its own ceiling two, with one observed send so far.
The old Copilot ledger remains 12/52 and is not reset or mixed into strict counts.
Actual provider receipts establish HTTP counts and tokens. USD estimates must
name their tariff assumptions and are not Azure invoices: the public OpenAI
GPT-5.1 Chat page lists $1.25/$0.125/$10 per million input/cached/output tokens,
but marks that OpenAI alias shut down, whereas this existing Azure deployment is
observably responsive and exposes the generic response alias. Do not equate that
historical public tariff with this resource's actual bill. Retain conservative
published chat-latest estimates separately where appropriate.

Two bounded direct-route reviewers found no blocking provider-selection/retry
defect. Accepted their accounting suggestions: count known receipt dispatches
even when verification fails; mark absent receipts or ledger-only reservations
unknown rather than zero; record observed aliases; revalidate B02 configuration
and its dedicated ledger; reject an explicitly conflicting CLI provider.
The B02 four-condition experiment intentionally continues its other independent
controls after one condition fails (within eight total sends); these controls
still diagnose collateral policy leakage. Reporting both aliases is not a
claim that a mutable backend is immutable. Stronger driver diagnostic formatting
remains separate from the already enforced production JSON/nonpublication
contract; no acceptance requirement or reference was weakened.

The first strict development dispatch failed HTTP 400 before inference: Azure
rejects the JSON Schema `uniqueItems` keyword. The last of the two declared
compatibility slots reproduced that exact provider diagnostic using the actual
assessment schema without findings. The adapter now projects only this
unsupported keyword out of its wire schema; the original unchanged schema still
validates every response locally, and a duplicate-array regression must fail.
No triage schema, evidence requirement or evaluator expectation was relaxed.
This correction continues the strict development 52-send ledger with its first
failed dispatch retained. Compatibility is now spent 2/2; no automatic health
resampling is authorized.

The corrected schema reached real inference: the next strict run validated
F-1001/F-1003/F-1004, then hit HTTP 429 on its sixth dispatch (five responses had
roughly 18-20k prompt tokens each). Preserve all six receipts and seven cumulative
strict development reservations. Add explicit configurable minimum dispatch
spacing, default zero/backward-compatible; this strict phase pins 30 seconds.
Spacing applies across findings and validation retries before reservation/dispatch,
does not add attempts or extend a model's 90-second deadline, and cannot guarantee
an externally shared resource quota. HTTP 429 still fails closed, not a hidden
SDK retry. Generic quotation instructions additionally prohibit JSON field-label
decoration and added outer quotation marks; exact-source validation is unchanged.

The paced run `native-strict-development-3` automatically published all thirteen
development tickets: fourteen actual HTTP dispatches, 411.828 seconds, stable
runtime/native packet and matching observed alias; cumulative strict reservations
21/52. This establishes transport/structure, **not semantic acceptance**.
The actual calibrated parent reviewer rejected it in `native-strict-review-1`:
wrong component-versus-voted-group failure scope, conditional impact confused
with current tag-defect severity, omitted specialist/retest/extent activities,
and insufficient dropped-object exposure treatment. The review deliberately
stopped at blockers (other dimensions remain pending), retained an unresolved
adjacent impact judgment rather than inventing numeric gold, and did not open test.

The next same-provider correction states existing source requirements more
explicitly: assess the affected component's function separately from remaining
arrangement capability; keep conditional impact separate from failure likelihood;
do not equate missing evidence with confirmed false; retain actual comment timing,
specialists, measurements/location, conditional diagnosis and functional retests.
Aim for readable summaries below 240 characters and allow core actions up to a
140-character aim while the unchanged complete-action maximum remains 300.
Material injury exposure matters even without process loss. These are generic
requirements, not per-finding answers, numeric lookup tables, or new knowledge.
This correction continues the same 52-send ledger with all 21 reservations kept;
the one X01 repeat has not yet been used.

Current offline collector passes 355 tests (104 workflow/integration, 49 inference,
76 source/probe, 126 evaluator). A broader 287-test component discovery also
exposed three legacy-probe failures referencing the renamed document 06; the
one-path mechanical repair uses its actual current name, with focused tests
passing. No old observation's hashes were refreshed. An isolated wheel build,
fresh dependency installation and evaluator-free installed imports passed; real
final generation in that environment is still a later gate.

The second paced output (`native-strict-development-4`) also completed all thirteen
with fifteen actual HTTP dispatches (448.609 seconds); cumulative strict spend is
36/52. Semantic review 2 still rejects it: source timing is omitted, UT/MPI
diagnostic condition findings are incorrectly promoted to failed operational
protection tests, and an exposure hazard is reduced to a paperwork check. Do not
perform X01 on this failed baseline. The generic prompt now explicitly separates
material-condition inspection from functional testing and requires concrete
checks of decision-changing exposure unknowns.

**Prospective bounded replacement phase:** use the already-existing deployment
`gpt-5.3-chat` with otherwise identical strict Azure controls in a separately
named directory `eval\results\triage\native-strict-model53`. This is a justified
replacement after observed instruction/fact-assessment failures, not an
unreported same-configuration resample or a claim that the nominal version is
better. Preregister a new development-plus-one-repeat ceiling 52 (26 nominal);
the old ledger remains 36/52 and its unspent sixteen are not transferred. Thus
both direct development phases together authorize at most 104 and have spent
36 before this new phase. Separate B02/test/final ceilings remain eight/sixteen/
forty-two, gated on actual acceptance; compatibility is exhausted 2/2.

Before this replacement's first paid dispatch, the official public
`https://developers.openai.com/api/docs/models/gpt-5.3-chat-latest` lists assumed
input/cached/output rates $1.75/$0.175/$14 per million tokens, but also marks its
OpenAI alias shut down. These are explicitly historical public-rate estimates,
not identification or pricing of this responsive Azure resource's generic
backend. Preserve requested deployment, actual exposed model and tokens; exact
Azure billing and backend-weight identity remain unknown. No source was changed,
no test was opened, and neither failed semantic review is attached to new hashes.

The replacement chat run completed thirteen tickets with sixteen actual HTTP
dispatches, but its actual review still fails unverified lifeboat redundancy
credit and omission of dropped-object exposure checks. Preserve
`native-strict-model53\review-1` and its pending dimensions. No X01 was sampled.
The source requirements are already explicit; more per-case prompt patching is
not the next action.

**Prospective reasoning replacement:** select the existing `o4-mini` deployment
with explicit `reasoning_effort=low`, native schema, 8192 completion tokens
(including reasoning), 90-second timeout and 30-second pacing, under
`native-strict-o4`. Its development-plus-one-repeat ceiling is52, B02eight,
test16 and final42, with the same prerequisite gates. The two closed chat phases
retain36+16=52 actual sends; their unused16+36 slots are not transferred. Thus
the new development scope can bring actual direct development sends to at most104,
plus the separately spent two compatibility sends. All earlier Copilot twelve
sends and model limitations remain disclosed separately.

The cap is now an explicit `azure_max_completion_tokens` RunConfig field, default
4096/backward-compatible, validated before dispatch and passed to the actual
Azure constructor; it does not pretend to constrain Copilot. The driver accepts
explicit reasoning effort and Azure cap rather than guessing by model name.
Before paid reasoning inference, official
`https://developers.openai.com/api/docs/models/o4-mini` lists historical assumed
input/cached/output rates $1.10/$0.275/$4.40 per million tokens, including billed
reasoning in completion usage. That public alias is also marked shut down; this
is a qualified tariff estimate, not the existing Azure deployment's invoice or
an availability guarantee. Actual requested/observed identity is retained.
The reviewer/protocol remains the already calibrated general protocol in
`native-strict-model53\calibration`, with generator identity recorded separately.

The actual low-effort o4 run failed closed after two sends on F-1001:
`not_applicable/confirmed_false`, missing exclusion evidence, then incomplete
correction and fabricated key-prefixed quotations. No output was published.
Actual backend identity was `o4-mini-2025-04-16`; native schema and low reasoning
were accepted, with observed reasoning usage. Before another send, raise only
effort to `medium` within the **same52** phase and preserve explicit continuation
lineage at2/52. This is development diagnosis, not a fixed-configuration repeat.
Do not waive citation/applicability checks or repair the model's content in code.

Medium effort then produced a structurally valid F-1001, but F-1003 exhausted all
8192 completion tokens in reasoning with no visible answer (`finish_reason=length`).
Retain this failed run and its actual usage; the phase is4/52. Before the next
continuation, explicitly increase the completion cap to16384 and timeout to180
seconds, preserving medium effort and the same52 ceiling. Both drivers expose
the timeout rather than mutating a prepared plan. Local original-schema checking,
fail-closed incomplete-response handling and the two-attempt ceiling are unchanged.

The expanded run still failed its first finding after two sends: exact text was
cited against nonexistent aggregate `finding:F-1001` rather than the supplied
field address. The diagnostic also misleadingly described an unknown address as
a quotation mismatch. Preserve6/52 sends. This reveals a mechanical conformance
gap, not grounds for relaxing citation integrity.

The request schema now binds citation/check addresses to the trusted native
source index, and identities to the current validated input. A shared `$defs`
address enum avoids duplicating the full index in each citation. Shared policy
fact branches encode the already-required applicability/state combinations;
neither scoring bands nor case answers are added. The original independent
assessment validator and exact quote checks remain unchanged. This moves
checkable syntax into supported native constraints instead of endlessly adding
prompt instructions. Focused regression covers nonexistent aggregate addresses,
wrong identity, contradictory applicability, original-schema immutability and
Azure schema projection. Next development continuation retains medium/16384/180,
the same52 ceiling and all six failures; it is not X01 or untouched test.

The full offline regression exposed one old experimental-probe harness failure:
it unnecessarily changed the overlay source ID between policies, so the new
address-bound schema correctly changed too. Keep its failure observation. The
legacy harness now retains one `probe-policy-overlay` identity while content/version/hash
change; this preserves the intended fixed-system paired comparison. No frozen
expectation or source package was edited, and the active native driver is
unaffected. Local definitions are restricted to existing acyclic root `$defs`,
with remote/missing/dynamic/cyclic references and identifier rebinding rejected
before validator construction. Native projection also traverses definitions.

The source-bound o4 run dispatched thirteen times, corrected three invalid drafts,
then stopped honestly at F-1012: it declined impact because alternate-craft status
was unknown. Publication remained blocked; the o4 phase closes at19/52, with33
unused slots not transferred. This demonstrates a bounded inability path, not
successful all-finding assessment. Some accepted intermediate drafts still
credited only nominal firewater redundancy, so no semantic baseline is claimed.

**Prospective final deployment-family replacement:** read-only resource metadata
shows `gpt-5.1-codex-max` succeeded. The official model page
`https://developers.openai.com/api/docs/models/gpt-5.1-codex-max` documents
structured outputs and Responses-only inference, not Chat Completions.
Extend the existing low-level Azure adapter with an explicit Responses API option;
do not use Codex agent orchestration, tools, stored/background responses or a
structured-generation harness. Keep original-schema local validation and exact
source checks. Default Chat Completions stays backward-compatible; no fallback.

Before any dispatch, declare `native-strict-codex` as a separate development/
one-repeat phase of52, with medium effort,16384 output tokens including reasoning,
180-second timeout,30-second pacing, native source-bound schema and the same
source/assessment policy/reference. The previous chat52 and reasoning19 sends
remain71 direct development sends; this phase can bring that ceiling to123,
plus the two compatibility sends and separately retained twelve Copilot sends.
B02eight, test16 and final42 remain prerequisite-gated, not automatic resampling.
No more compatibility/health slots are created.

The public historical tariff is input/cached/output $1.25/$0.125/$10 per million;
it is not a verified Azure invoice, and public alias retirement is disclosed
separately from existing resource metadata. Generality/quality on triage is
unproven: a coding-specialized model gets no semantic waiver. This is a bounded
stronger instruction/reasoning alternative after concrete small-model failures,
not per-case answer repair. The adapter/API switch requires focused HTTP mocks,
full regressions and critical review before real inference.

Closed-phase accounting is persisted in
`eval\results\triage\native-live-accounting-1\report.json`:71 observed direct
development dispatches plus two compatibility dispatches, with all ledger
reservations reconciled. The qualified historical-tariff estimate for **known
development usage only** is $1.80343985; two old failed development calls have
unknown usage, and actual Azure USD, Copilot/parent/reviewer billing and the
knowledge session's usage are not inferred or counted as zero. Reasoning tokens
are already included in completion totals. This is failure/usage evidence, not
acceptance or a claimed full-project bill.

The first bounded Responses/native-boundary review found a real preflight defect:
memoized local definitions bypassed the intended depth32 guard when declarations
were ordered leaf-first, permitting recursion failure after a paid dispatch.
Accepted: cache maximum remaining reference depth and check the whole path, with
both root-first and leaf-first32/33 boundary regressions. This strengthens the new
local-reference capability without changing any evaluation expectation. The
unused i11 plan is not executed against changed hashes; refreeze before paid use.

The second review first examined only the depth correction, then completed the
requested Azure/triage/driver boundary read on follow-up; its limited test-name/
forwarding-site inspection is not portrayed as full test review. No blocking
Responses bug remained. Accepted two hardening suggestions before paid use:
Azure-specific workflow preflight checks the actual configured API/token cap,
and successful/recoverable receipts must match API, cap, requested model and
workflow-computed actual message hashes; a miswired factory cannot silently
qualify another API. Also preserve our own wire-guard `boundary_violation` through
SDK connection-error wrapping instead of misclassifying it as transport.
Generic synthetic-provider fixtures remain explicitly synthetic, not Azure
proof. Speculative compiler-depth/malformed-definitions risks were not additional
blockers: existing `RecursionError`/`TypeError` conversion already fails before
dispatch; IDs without references do not trigger external resolution and retain
the prior unsupported-feature behavior. Tests, not reviewer agreement, establish
the limited software evidence; real inference remains a separate gate.

The actual Responses route works: observed `gpt-5.1-codex-max`, four retry-free
dispatches, matching native/wire audits, no tools, then no publication. F-1003's
first draft had **both** a prefixed/nonliteral quotation and confirmed-function/
likelihood7 contradiction; first-error-only feedback corrected the quote but
left the independent contradiction on the final allowed attempt. Preserve4/52.
This motivates a bounded recovery correction, not extra attempts: collect
independent post-schema evidence/score errors and put the score contradiction
plus citation locations in the same500-character correction message. Every
violation still rejects the draft; the original schema, exact quotes and ceiling
remain unchanged. A regression requires both defects in one feedback message.

For native packets only, the wrapper additionally repeats the current target's
**unchanged** finding and registry row as `target_query_facts`, next to the target
request. Full validated native context/shared registry and partner findings remain
present, with no alternate KB, source selection or new answer material. This is
query-focus/transport redundancy, not retrieval or a case-specific rule. The
captured-wire test checks these copies against the actual packet. Continuation
retains the same model/medium/16384/180 settings and52 ceiling with four spent.

The second Codex observation consumed another four dispatches without publication.
Its F-1003 retry corrected the quotation but changed the function state from
suspected to confirmed true while retaining likelihood7. Batched feedback alone
cannot prevent a newly introduced cross-field contradiction. Preserve8/52;
neither failure is an accepted baseline.

For native bundle2 only, the next model-wire contract is
`joint_function_likelihood_v1`: the function-failure fact is nested inside the
likelihood object. Native `anyOf` branches permit confirmed-true/applicable with
likelihood9/10, or the other valid fact states with likelihood1..10. Workflow
losslessly relocates this model-authored fact into the original assessment shape
before the unchanged independent validator. Duplicate/missing placement fails.
It never clamps scores, changes truth states, repairs text or supplies a scored
fallback. Raw provider output and the projected assessment are retained.
Unassessable remains an explicit no-publication failure. Legacy replay retains
its original shape. This enforces the existing supplied top-end principle and
declared9-10 consistency policy; it does not establish that a claimed failure
is grounded.

The native schema also binds every citation to an exact source address and its
complete literal field/passage value. Shared definitions avoid repeating address
enums. This narrows generation, not frozen evaluation; the independent original
substring/provenance checks still run, and semantic review must establish that
the chosen source supports the claim. It prevents prefixed, stitched and
cross-address quotations without repairing generated evidence. Source values
are therefore present as quoted schema data as well as native context; they
remain untrusted source data, not executable instructions or evaluator answers.

Offline mechanical capacity checks, with zero inference, observed development
269 addresses/581 enum values/162282 prepared input bytes and full-package
341 addresses/725 enum values/196781 bytes, below the256000-byte request bound.
Native schemas were103671/128336 bytes. The all-21 check measures serialization
capacity only; it is not test generation or semantic evaluation. Larger
source-enumerated schemas can increase latency, input usage and quota pressure.
Continue the existing Codex phase, not a reset, with medium/16384/180 and explicit
90-second pacing prospectively; the attempt ceiling remains52 with eight spent.
The first bounded reviewer found no blocking issue in the native contract and
ran five focused offline tests; it did not establish Azure schema acceptance.
The second cross-critique and actual provider behavior remain separate checks.

The second bounded reviewer found no blocking projection/constraint bug after
reading the affected runtime paths; it inspected test names but did not run
tests. Accepted: check documented native character/depth limits offline, and
explicitly label quoted schema source enums as untrusted data in SYSTEM.
Its suggestion to prefer short clauses was already addressed by the new
schema-permitted-full-value instruction; exact full-field evidence is not
treated as proof of relevance. Accepted its remaining semantic risk: the model
could weaken a true function-failure fact instead of raising L. Actual
development review must inspect fact grounding, not merely count fewer
contradiction errors. Reject its factual phrase that this new schema had
already passed live: at review time only offline checks existed. No Azure
acceptance, all-21 model result or owner approval follows from either review.
Avoid a broader inference-message protocol change in this increment; retain
explicit data labeling, wire capture, input bounds and actual semantic review.

Actual Azure rejected the first source-enumerated schema with HTTP400 before
model generation. Two explicitly declared one-dispatch diagnostics were charged
to the same phase ledger, not the exhausted compatibility budget. The first
word-only diagnostic omitted the relevant rule; the second retained only a
recognized schema-error message with environment credentials redacted:
newline is not allowed in string literals for `strict=true`. It pointed to
source-citation branch261, the first multiline knowledge passage. Preserve all
three failed HTTP observations and11/52 reservations; unknown error usage is
not reported as zero cost.

Correct the native quotation choices to complete **nonblank source lines**,
preserving each line's bytes/characters and its original source address.
Single-line finding/registry values remain whole; multiline passages offer their
individual literal lines, never joined or rewritten. This both respects actual
provider constraints and retains the original no-stitched-quotation rule.
Independent substring validation and semantic relevance review remain required.
It is a generation-schema correction, not a knowledge/evaluator change or
post-generation quote repair. The joint fact/likelihood contract is unchanged.
The first capacity reporter incorrectly measured the API wrapper's nesting as0;
`capacity-correction.json` preserves that error and establishes actual nesting5
for development and all21. Character totals31047/37712 were below120000.
Put the function fact first in each native likelihood object's property order,
before the numeric score. Native output follows wire-schema order; canonical
system-schema text alone does not establish that order. This avoids forcing a
fact-state choice after the model has already emitted a low score. It still
does not prove correct fact interpretation; inspect actual model evidence.

### Native assessment v2: semantic recovery, not an accepted baseline

The i16 observation `native-strict-codex\development-4` automatically published
all 13 development drafts after 15 actual HTTP dispatches, with native context,
matching message audits and no tools. The observed deployment was
`gpt-5.1-codex-max`. The unchanged assessor accepted the output contract, but
the calibrated, hash-bound AI review in `review-1` returned **24 pass, 14 fail,
one needs_review** across 39 dimensions. This is a failed development baseline,
not system acceptance. Failures concern source-required timing/cadence and
approving authority, unsupported operating clearance or causal assertions,
unexamined interruption/exposure consequences, and evacuation capacity versus
current POB. Preserve these outputs and judgments. Do not repeat this failed
configuration for X01 or open test/final generation.

Two responses also mixed `status=assessed` with `facts=null`; recovery used the
second permitted attempt. The earlier property-order note describes the
authored schema, not the actual wire: `InferenceRequest.prepared()` canonicalizes
the schema, and Azure uses `validator.schema`. The actual fact still preceded
the score, but was not the first property. No ordering claim establishes grounding.

Native-only `native-assessment-v2` supersedes the earlier wire layout:

- A closed envelope correlates complete assessed/non-null and
  unassessable/null frames. The original independent eight-fact assessment
  validator and joint confirmed-function/L9-10 constraint remain in force.
- A deterministic source-line catalog, sorted by trusted source address and
  retaining each nonblank literal line unchanged, is supplied as user data.
  The model selects catalog IDs, not generated quotations. Code independently
  rebuilds the catalog, verifies the echoed SHA-256, resolves selections and
  runs the original address/substring checks. A rehashed or stale foreign
  catalog cannot remap a response. Repeated text at different addresses keeps
  separate identities. This is deterministic rendering of model selections,
  not repair of model-authored quotations or a new knowledge source.
- Shared selector/uncertainty definitions avoid hundreds of source-text
  objects and keep source text out of the system-role schema. Measure the
  actual prepared wire schema against Azure's documented 100-property,
  five-level limits before dispatch, as well as input/enum limits. Previous
  live acceptance of a larger schema does not waive those documented limits.
- Separate `same_day_attention` carries a reason, directive evidence and
  current-trigger evidence. Both lists must be nonempty and quote only the
  target finding description or its own engineer comment. Unknown selectors,
  foreign assets, knowledge legends, blank reasons and nonliteral evidence
  fail closed. An unconditional directive may use the same source line twice.
  Mechanical provenance does **not** prove directive applicability or detect
  an omitted directive; actual semantic review remains necessary.

Execution policy `triage-policy-v2` leaves the base formula and L/I unchanged.
`S-SOURCE-TODAY`, explicitly labelled `source_directed_attention`, floors U at9
and requires review plus `Obtain source-required attention today.` It schedules
an evidenced existing source instruction; it is not a fabricated confirmed
regulatory override. The general prompt preserves source cadence and approving
authority, qualifies suspected causes, and requires material exposure and
interruption uncertainties. There are no finding-ID answer branches.

The unavailable-craft precaution now appends the code-owned minimum
`Verify current POB against certified available evacuation capacity.`, retaining
other model-proposed obligations. Confirmed evacuation unavailability or
discovered unlogged impairment cannot evade their immediate precaution merely
because the dependent comparison/restoration fact has uncertain applicability.
That correction is scoped to those two dependencies; confirmed overrides still
require confirmed applicable facts. Every distinct activity remains subject
to the complete 300-character action bound, with no truncation or semantic
deduplication.

Bounded review disposition: both reviewers supported the selector/timing design
without treating it as implementation or live evidence. The first actual-code
review found that adapter-local schema rejection lost already screened visible
draft text before workflow capture. Accepted: retain bounded visible text on
local malformed/schema errors, outside generic serialized diagnostics; after
receipt validation, preserve it and use it only as untrusted retry data.
Refusal, filtering, reasoning and operational output are not retained this way.
Projected assessments remain available on failures after projection completes;
the raw response remains the evidence when projection itself fails. Keep the
existing model capacity-verification requirement alongside the code minimum:
it preserves additional item-specific checks and the established failure
contract rather than treating a generic check as a substitute.

All changes address A01-A04, B01/B03, C03/C04 and D01-D04; frozen evaluation
expectations and the supplied package are unchanged. The Codex phase has
**26/52** dispatch reservations before any v2 inference, leaving26, not a reset.
The prepared i16 B02 plan and wheel remain bound to i16 and must not be used as
current-code evidence. Real default knowledge still needs genuine content
review/publication and explicit activation; software-fixture publications do
not satisfy that gate. Root `DESIGN.md` remains owner-reserved.

The second actual-code cross-review found no blocking defect in its bounded
read; it did not rerun tests or reread the adapter, receipt checker or routing
schema declarations. Accepted limitations: the timing floor trusts model
interpretation of directive/trigger evidence, including applicability of a
shared equipment comment to this particular finding; source membership alone
cannot establish that. The catalog hash is snapshot/replay consistency, not a
separate provenance authority. Shared uncertainty definitions remove seven
duplicate wire properties before final capacity measurement. The first
reviewer's visible-draft fix has focused adapter/workflow regressions; no
reasoning or raw HTTP body is copied into retry data.

Prospective continuation retains `gpt-5.1-codex-max`, Responses/native strict,
16384 output tokens, 180 seconds, 90-second pacing and the same52 ceiling,
but raises reasoning effort from medium to **high** after the actual semantic
failure. Observed i16 output use was1043-3568 tokens, maximum2112 reasoning;
the existing cap therefore has measured headroom, not a guarantee of success.
Freeze this changed configuration explicitly; any accepted X01 repeat must use
exactly that new configuration. No compatibility or extra development budget
is created.

Later read-only inspection found the knowledge session had already acted on the
owner's explicit promotion instruction: all eight original C0 items are reviewed
and release `sha256-b215857575e443ba5fd9cb56a19f3079003cd68acb03fdf0e33ca7fbed59e097`
exists. `source-owner-promotion-1\approval.json` records that instruction; local
knowledge-session history independently confirms it. Earlier pending-KB notes
are historical, not the current gate. Preserve the knowledge session's files.
The old integration activation correctly fails after the execution-policy
change; `native-owner-activation-v2` records a deliberate technical compatibility
review and new pins, not fabricated new owner/expert approval. Current native
consumer validation passes for13 development and21 serialization-only inputs.
Payload, source index, assessment policy, membership and time match the software
development fixture; release/hash provenance differs and remains explicit.
No real-release live generation or system acceptance follows from that equality.
