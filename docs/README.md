# Project Development Chronology

This directory explains how the assignment progressed from an ambiguous
engineering brief to a generated, evidence-bound submission.

The numbered documents are now a contiguous **01-08 development narrative**.
They are not eight competing design authorities:

- root [`README.md`](../README.md) is the submission entry point, current status
  and run/verification guide;
- root [`DESIGN.md`](../DESIGN.md) is the concise answer to Candidate Brief
  sections A-D;
- numbered Documents 01-08 explain the reasoning, implementation sequence and
  controlled studies behind that design;
- [`eval\spec`](../eval/spec) defines what counts;
- [`eval\results\README.md`](../eval/results/README.md) indexes what actually
  happened, including failures and unresolved limits; and
- root [`tickets.json`](../tickets.json) is the generated draft deliverable.

## Panel review path

1. Read root [`README.md`](../README.md) for the submission contents, setup and
   run command; use [`eval\results\README.md`](../eval/results/README.md) for
   current evidence status and known limitations.
2. Read root [`DESIGN.md`](../DESIGN.md) for the model/code boundary, knowledge
   mechanism, urgency derivation, deferral policy and rejected alternatives.
3. Open root [`tickets.json`](../tickets.json) and the side-by-side baseline link
   at the top of
   [`08_BEHAVIOR_CALIBRATION_STUDY.md`](08_BEHAVIOR_CALIBRATION_STUDY.md).
4. Read
   [`07_KNOWLEDGE_CHANGE_STUDY.md`](07_KNOWLEDGE_CHANGE_STUDY.md) for the
   six-month PSV-maintenance answer and observed influence evidence.
5. Use [`eval\results\README.md`](../eval/results/README.md) only when detailed
   run, review, cost or failure evidence is needed.

## End-to-end development map

| Step | Engineering question | Main decision or result | Document |
|---:|---|---|---|
| 01 | What is the assignment actually asking, and where are the judgment traps? | Separate semantic assessment from deterministic control; identify unsupported assumptions before choosing components | [`01_INITIAL_INVESTIGATION.md`](01_INITIAL_INVESTIGATION.md) |
| 02 | What data, relationships and evidence boundaries make evaluation honest? | Profile 21 findings and 18 assets; define grouped, non-blind evaluation and production-context exclusions | [`02_DATA_EVALUATION_PLAN.md`](02_DATA_EVALUATION_PLAN.md) |
| 03 | What must count as success or failure before outputs are judged? | Define A-D/X scenarios, semantic review, fixed-identity reliability, accounting and controlled-change rules | [`03_EVALUATION_ACCEPTANCE.md`](03_EVALUATION_ACCEPTANCE.md) |
| 04 | How should model access be isolated and accounted for? | Introduce a provider-neutral inference boundary; distinguish measured Copilot usage from API-equivalent cost | [`04_INFERENCE_LIBRARY.md`](04_INFERENCE_LIBRARY.md) |
| 05 | How can domain guidance change without prompt surgery or workflow edits? | Build source-faithful extraction, review, immutable releases, separate activation and validated context delivery | [`05_KNOWLEDGE_LIFECYCLE.md`](05_KNOWLEDGE_LIFECYCLE.md) |
| 06 | How are the components integrated without hiding failure? | Implement bounded assessment, deterministic urgency/review policy, complete coverage and atomic publication | [`06_TRIAGE_WORKFLOW.md`](06_TRIAGE_WORKFLOW.md) |
| 07 | Does the six-month knowledge-maintenance path work in practice? | Demonstrate bounded influence and official-store traversal; expose hard-coded-score, scope and non-target risks; reject promotion | [`07_KNOWLEDGE_CHANGE_STUDY.md`](07_KNOWLEDGE_CHANGE_STUDY.md) |
| 08 | Did calibration make the ticket set more useful, and what caused the change? | Compare accessible baseline/current tickets, decompose review changes, retain failed interventions and state residual risks | [`08_BEHAVIOR_CALIBRATION_STUDY.md`](08_BEHAVIOR_CALIBRATION_STUDY.md) |
| Submit | What should the panel inspect and what remains unresolved? | Root README, DESIGN, tickets and evidence index form the submission; no separate readiness report competes with them | [`README.md`](../README.md), [`DESIGN.md`](../DESIGN.md), [`tickets.json`](../tickets.json), [`eval\results\README.md`](../eval/results/README.md) |

## Phase 1 - Understand the problem and define evidence

### 01 - Investigate before designing

The work started by reading the Candidate Brief, source data and outgoing
engineer's notes as authority rather than treating the example ticket as a gold
answer. The investigation identified the recurring traps:

- reliability runs in the opposite direction to likelihood;
- redundancy is a claim that needs partner evidence;
- SCE impact concerns the protected major-accident scenario, not repair cost;
- missing evidence is unknown, not confirmed absence; and
- valid JSON can still contain an invalid engineering judgment.

This produced the first architecture boundary: use the model where evidence must
be interpreted, but keep urgency, schema, attempts, coverage and publication in
code.

**Gate unlocked:** an evaluation plan could now test the actual brief rather than
an attractive implementation.

### 02 - Define data, context and leakage boundaries

The next step profiled the complete supplied corpus and mapped relationships that
can change an assessment. The split was deliberately labelled non-blind and
AI-assisted; it was never presented as independent gold.

Production context was separated from evaluator cards, expected answers and
reviewer judgments. Related equipment evidence was grouped to reduce obvious
leakage, while the documents retained the limitation that not every operational
dependency can be known from 21 rows.

**Gate unlocked:** acceptance scenarios could be frozen without silently using
test answers as production knowledge.

### 03 - Decide what counts before judging outputs

The evaluation contract mapped Candidate Brief A-D plus cross-cutting stability
and reproducibility requirements to observable evidence:

- A: structure, coverage, repair and semantic failure;
- B: context delivery, bounded influence and maintenance path;
- C: code-derived urgency, corners, overrides and fact assessment;
- D: deferral, inability to assess, exclusions and provenance;
- X: fixed-identity stability, delivery, accounting and cost.

This phase also separated deterministic self-tests from semantic model quality.
A passing validator was not allowed to become a claim that the scores were
correct.

**Gate unlocked:** implementation and paid experiments had explicit stop/fail
conditions.

## Phase 2 - Build the system boundaries

### 04 - Isolate inference transport

The inference layer was kept smaller than the triage system. It records provider
identity, request boundaries, usage, latency and failures without owning
engineering policy.

Copilot enabled low-marginal-cost development under an existing subscription.
Direct Azure remained useful where strict provider accounting was needed. The
documents distinguish measured tokens and AI units, reproducible
API-equivalent estimates and unknown actual Copilot billing allocation.

**Gate unlocked:** triage could change provider routes without moving urgency or
knowledge authority into a provider adapter.

### 05 - Separate knowledge authority from orchestration

The supplied notes and future approved guidance were moved behind a source-first
lifecycle:

```text
approved source
  -> source-faithful extraction
  -> review
  -> immutable release
  -> separate activation
  -> validated provider context
```

This answered the brief's maintainability question: an integrity engineer can
change approved PSV interpretation through a reviewed source/release rather than
editing the prompt or adding a finding-specific branch. Generic score anchors
and urgency rules remain application-policy changes.

**Gate unlocked:** the workflow could consume knowledge without owning how it
was authored or approved.

### 06 - Integrate one fail-closed workflow

The workflow joins validated findings, registry data and pinned context; requests
model-proposed L/I, facts, uncertainty and planning text; validates the result;
derives urgency and review routing in code; enforces the total attempt ledger;
and publishes only a complete atomic batch.

Malformed output, structural violations, unsupported evidence and inability to
justify scores remain distinct failure classes. A failed finding cannot publish
a partial new batch or make an old output look current.

**Gate unlocked:** real-model observations could test the integrated system
rather than isolated components.

## Phase 3 - Exercise change paths and calibrate behavior

### 07 - Validate the knowledge-maintenance path

The knowledge study first used an isolated artificial context intervention, then
exercised the official source store and complete 21-ticket command.

The target result moved as intended, while the negative tag-only PSV remained
bounded. The exercise also revealed that:

- the experimental source hard-coded scores that should belong to the rubric;
- an editor path lost structured scope and evidence;
- scoped PSV guidance still entered a shared batch knowledge pool;
- non-target scores varied; and
- the rule lacked authenticated domain-owner approval.

The editor defect was fixed and verified, but the experimental releases were not
promoted. The working candidate returned to the baseline authority.

**Gate unlocked:** maintainability was demonstrated as a controlled,
rejectable process rather than assumed from code structure.

### 08 - Calibrate the integrated ticket behavior

The retained baseline was structurally valid but operationally weak: 19/21
tickets were U7-U9 and all 21 carried the earlier broad review flag.

Calibration changed several system surfaces, so the final comparison is
explicitly not a single-variable A/B test. The study exposes both full ticket
files at its top, records the model/policy identities and decomposes the review
reduction with deterministic replay.

The current result has 15/21 tickets at U7-U9 and six exceptional prequeue review
routes. That is improved discrimination, not calibrated risk truth. Six
protection cases still depend on changed assessment inputs as well as routing
policy, and the study keeps that as a named regression risk.

**Gate unlocked:** the generated ticket set could be submitted with a clear
before/after explanation and explicit causal limits.

## Phase 4 - Assemble the submission

The final submission has four primary entry points:

| Artifact | Purpose |
|---|---|
| Root [`README.md`](../README.md) | What is included, current status, run command and fastest panel path |
| Root [`DESIGN.md`](../DESIGN.md) | Concise answer to Candidate Brief A-D and architectural trade-offs |
| Root [`tickets.json`](../tickets.json) | System-generated 21-ticket draft output |
| [`eval\results\README.md`](../eval/results/README.md) | Evidence index, actual observations, cost/accounting and unresolved gates |

There is no separate submission-readiness report. A second status document would
duplicate these authorities and create drift risk.

The final artifact is contract-valid and has a provisional AI-only semantic
observation. It is not human-approved, independently domain-certified or
clean-checkout reproduced. Hidden provider attempts and actual Copilot USD
allocation remain unknown.

## Where development was iterative

The project did not occur once in a perfect waterfall:

- early workflow work preceded the final knowledge-lifecycle boundary;
- Document 08 includes early calibration interventions that preceded the
  Document 07 knowledge exercise; the numbering places Document 07 before the
  **final** behavior calibration rather than claiming a strict file-by-file
  execution order;
- failed B02 attempts exposed a confounded synthetic probe before the corrected
  isolated comparison;
- the official knowledge-change exercise exposed a real editor scope defect;
- prompt-only chronology repair was rejected after it changed development
  urgency/review behavior;
- calibration used exposed findings and is disclosed as test-informed; and
- the final producing workflow was retained by hash after the run rather than
  established by clean-checkout reproduction.

These are not rewritten as planned successes. Failed observations remain under
`eval\results` or in its lossless archive, and Git preserves the implementation
history.

## Authority and evidence hierarchy

| Question | Authority |
|---|---|
| What did Falkor require? | Unchanged Candidate Brief and supplied domain notes |
| What is the current design? | Root `DESIGN.md` |
| What does the system currently do? | Production code and pinned configuration |
| What was supposed to count? | `eval\spec`; Documents 02-03 explain that contract and its rationale |
| Why were component/workflow decisions made? | Documents 01, 04-06 |
| What happened during controlled changes? | Documents 07-08 and linked evidence |
| What actually passed, failed or remains unknown? | `eval\results` |
| What should the panel run or read first? | Root `README.md` |

Specifications define what would count; results record what happened. Integrity
checks, evaluator self-tests and AI review are not operational approval.

## Original decision process

[`original-decision-process\README.md`](original-decision-process/README.md)
indexes the exact pre-rewrite working snapshot of Documents 01-06, bound by
`manifest.json`. It preserves the detailed historical order and earlier
terminology without competing with the current panel-facing narrative.

Root `DESIGN.md` links to the current numbered documents for decision detail;
the numbered files remain supporting rationale rather than competing design
authorities.
