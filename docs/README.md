# Development argument and documentation map

The numbered documents are not seven independent essays or a literal chronology.
They present the **logical dependency order** of the engineering argument:

```text
understand the problem
  -> define honest evidence boundaries
  -> decide what would count before observing results
  -> isolate model transport
  -> isolate knowledge authority
  -> integrate a fail-closed workflow
  -> measure one frozen version without tuning it
```

This order matters as a review structure. Reversing the dependencies would
encourage implementation before the failure policy is explicit, evaluation
after results are visible, or knowledge rules hidden inside orchestration. The
actual development chronology included iterations and test-informed corrections,
disclosed below.

## Five-minute panel path

| Need | Read |
|---|---|
| Current architecture and brief A-D | [`DESIGN.md`](../DESIGN.md) |
| Why each step depends on the previous one | This page |
| Current delivery/evidence status | [`eval\results\README.md`](../eval/results/README.md) |
| How one frozen version is measured | [`07_VERSION_RELIABILITY_PROTOCOL.md`](07_VERSION_RELIABILITY_PROTOCOL.md) |
| How behavior, knowledge, prompt authority and semantic review are controlled | [`08_BEHAVIOR_CALIBRATION_STUDY.md`](08_BEHAVIOR_CALIBRATION_STUDY.md), [`09_KNOWLEDGE_CHANGE_STUDY.md`](09_KNOWLEDGE_CHANGE_STUDY.md), [`10_PROMPT_AUTHORITY_AUDIT.md`](10_PROMPT_AUTHORITY_AUDIT.md), [`11_SEMANTIC_REVIEW_PROTOCOL.md`](11_SEMANTIC_REVIEW_PROTOCOL.md) |
| Final submission-readiness decision, issue closure and limitations | [`12_SUBMISSION_READINESS_REPORT.md`](12_SUBMISSION_READINESS_REPORT.md) |

## Why the logical process is ordered 01 to 07

### 01 — Frame the engineering problem before choosing components

[`01_INITIAL_INVESTIGATION.md`](01_INITIAL_INVESTIGATION.md) separates explicit
Candidate Brief requirements from candidate interpretations and domain traps.
It establishes the core boundary: semantic interpretation may be probabilistic,
but urgency, contracts, attempts and publication require predictable control.

**Why first:** without a source-derived problem statement, later architecture
could optimize for attractive tickets rather than the assignment.

**Output/gate:** requirement map, unresolved assumptions and rejected shortcuts.
This unlocks a defensible evaluation design.

### 02 — Define data and evidence boundaries before writing acceptance tests

[`02_DATA_EVALUATION_PLAN.md`](02_DATA_EVALUATION_PLAN.md) profiles the 21
findings/18 assets, identifies related evidence, declares the split non-blind and
specifies what production context may not contain.

**Why second:** acceptance scenarios are only meaningful after leakage,
relationship groups, reference limitations and claim boundaries are known.

**Output/gate:** split/context contract and evidence classes. This unlocks
preregistration without pretending the dataset is independent gold.

### 03 — State what counts before running the system

[`03_EVALUATION_ACCEPTANCE.md`](03_EVALUATION_ACCEPTANCE.md) maps Brief A-D plus
X01/X02 to observable evidence and explicit failure conditions.

**Why third:** building or reviewing outputs first would allow the success
criteria to move after failures are observed.

**Output/gate:** preregistered executable expectations, attempt/accounting rules
and claim limits. Reference v1.3 is tracked, but remains a disclosed
test-informed, non-blind revision rather than independent gold. This unlocks
component implementation and controlled experiments.

### 04 — Isolate model transport and development economics

[`04_INFERENCE_LIBRARY.md`](04_INFERENCE_LIBRARY.md) defines a small provider
boundary. The existing Copilot CLI subscription enabled economical development
probes; direct Azure remains the strict route when attempts and usage must be
observable.

**Why before workflow:** provider retries, schemas and accounting must not own
ticket policy. The workflow should be able to change routes without being
rewritten.

**Output/gate:** explicit inference request/response/failure contract. This
unlocks provider-independent orchestration.

### 05 — Isolate knowledge authority before consuming knowledge

[`05_KNOWLEDGE_DESIGN_DECISION.md`](05_KNOWLEDGE_DESIGN_DECISION.md) assigns
source import, extraction, provenance, review, immutable release, selection and
context validation to `triage_knowledge`.

**Why before workflow:** embedding knowledge extraction inside orchestration
would combine content approval with execution authority and make PSV maintenance
require workflow changes.

**Output/gate:** pinned validated knowledge/context contract and explicit edit
surfaces. This unlocks triage without coupling it to store internals.

### 06 — Integrate the contracts into one fail-closed workflow

[`06_TRIAGE_WORKFLOW.md`](06_TRIAGE_WORKFLOW.md) consumes inference and knowledge
contracts, validates assessment evidence, derives urgency in code, enforces the
attempt ledger and publishes only a complete atomic batch.

**Why after 04/05:** orchestration can remain small only when provider behavior
and knowledge authority already have stable boundaries.

**Output/gate:** one end-to-end implementation with deterministic failure paths.
This unlocks real-model observation, while not itself proving semantic quality.

### 07 — Measure a frozen version rather than select a favorable run

[`07_VERSION_RELIABILITY_PROTOCOL.md`](07_VERSION_RELIABILITY_PROTOCOL.md)
defines how to freeze identity, retain failures, separate reliability dimensions
and report decision/reviewer variance without a composite score.

**Why last:** reliability cannot be interpreted until the requirements,
evaluation contract, component identities and workflow are fixed. Historical
development runs cannot be promoted retrospectively.

**Output/gate:** a prospective measurement protocol plus a completed,
hash-pinned dirty-worktree observation. The clean-freeze/reproduction result is
**inconclusive**, not all-green.

### 08-11 — Record controlled changes without rewriting failed observations

[`08_BEHAVIOR_CALIBRATION_STUDY.md`](08_BEHAVIOR_CALIBRATION_STUDY.md) records
the rejected v9/v10 policy calibrations and the retained v11 decision.
[`09_KNOWLEDGE_CHANGE_STUDY.md`](09_KNOWLEDGE_CHANGE_STUDY.md) records how a
future PSV source change traverses the official source-first lifecycle,
including three failed protocol iterations before the bounded v4 observation,
while [`10_PROMPT_AUTHORITY_AUDIT.md`](10_PROMPT_AUTHORITY_AUDIT.md) separates
prompt protocol from code, source evidence, equipment registry and reviewed
knowledge authority. [`11_SEMANTIC_REVIEW_PROTOCOL.md`](11_SEMANTIC_REVIEW_PROTOCOL.md)
freezes reviewer scope, checklist dimensions and verdict boundaries so ad hoc
reviewer variation cannot be used as a delivery gate.

**Why after 07:** Documents 08-10 are observed change studies, not prerequisites
that can be presented as prospectively frozen acceptance. Document 11 is a
retrospective reviewer protocol for future reviews; it does not rescore earlier
observations.

## Where the actual chronology deviated

The clean dependency chain is a retrospective explanation, not a claim that
development occurred once in seven perfect phases:

- workflow work historically preceded the knowledge redesign; the archive keeps
  the original `05 Workflow -> 06 Knowledge` order;
- retained v1.2 B02 failures motivated the disclosed reference-v1.3 fixture
  correction;
- the `P-SCE-HIGH-IMPACT` floor was added after a development stability failure
  crossed the weekly/monthly urgency boundary; and
- the detailed reliability protocol prose was finalized after the local
  `v8r1`-`v8r3` series, while the machine-readable run order, hashes, budget and
  no-tuning rule were recorded before sends; the result is therefore useful
  controlled evidence but not a committed clean-freeze study; and
- the knowledge-change study was redesigned after v1-v3 failures. V4 is useful
  exploratory lifecycle evidence, not the original prospective B02 protocol.

These deviations are evidence of iteration, not erased history. The numbered
order shows how a reviewer should reason about the final design and which
dependency should govern future changes.

The panel-facing tree retains current evidence and the material v29/v30 failures,
not every generated transcript. Superseded raw experiments remain recoverable in
Git commit `071d29e62be419bb7443a6e18bf55d2763d46e69`; see
`eval\results\README.md` for the retained evidence map.

## Authority and evidence

| Question | Authority |
|---|---|
| Supplied requirement/domain rule | Candidate package |
| Current system behavior | Production code and pinned configuration |
| Current system design | `DESIGN.md` |
| Evaluation membership/scenarios | `eval\spec\split.json` and `eval\spec\acceptance.json` |
| Current working evaluation contract | `eval\spec`; archived v1.3 Documents 02/03 provide fingerprinted prose |
| Component rationale, controlled change studies and reviewer protocol | Documents 01-11, subordinate to `DESIGN.md`, code/config, `eval\spec` and `eval\assess.py` on conflict |
| Runtime string `Document 05 section 4` | Historical pointer to `docs\original-decision-process\05_TRIAGE_WORKFLOW.md` §4; it does not mean current panel Document 05 |
| Observed outcome | `eval\results` |
| Chronological development narrative | Archived Documents 01-06 and Git history |

Specifications define what would count; results record what happened. Integrity
checks, evaluator self-tests and AI review are not system acceptance.

## Original Decision Process

[`original-decision-process\README.md`](original-decision-process/README.md)
explains the exact pre-rewrite working-tree snapshot of Documents 01-06.
`manifest.json` binds each file by byte length and SHA-256 digest.

The archive preserves detailed chronology, failed approaches and handoffs. It is
not a second current design. Historical result files retain the code,
configuration, paths and hashes recorded at execution time; Git remains the
authority for earlier revisions.

An uncommitted draft decision summary was folded into `DESIGN.md`, Documents
04-07 and the evidence index. Keeping another summary layer would duplicate
authority and invite status drift.

Adversarial-review suggestions to present the provisional Copilot batch as
accepted or to weaken the freeze gate were rejected because they would change
labels rather than create evidence. Suggestions that exposed missing failures,
stale status or unclear provenance were accepted and incorporated.
