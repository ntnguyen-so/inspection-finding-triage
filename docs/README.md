# Engineering Development Record

These documents explain how the submitted design developed and why decisions
were made. They support root `README.md` and `DESIGN.md`; they do not replace
or duplicate them.

Documents 01-08 explain decisions and study results. Each file has a different
role:

- root [`README.md`](../README.md) contains setup, current status and verified
  run commands;
- root [`DESIGN.md`](../DESIGN.md) is the direct answer to Candidate Brief
  sections A-D;
- numbered Documents 01-08 explain the decisions, build sequence and controlled
  studies behind that design;
- [`eval\spec`](../eval/spec) defines what counts as acceptance evidence;
- [`eval\results\README.md`](../eval/results/README.md) indexes what actually
  happened, including failures and unresolved limits; and
- root [`tickets.json`](../tickets.json) is the generated draft deliverable.

## Reading guide

For a first review, use this shorter path:

1. root [`README.md`](../README.md) for setup, run commands and delivery status;
2. root [`DESIGN.md`](../DESIGN.md) for the direct Candidate Brief A-D answers;
3. root [`tickets.json`](../tickets.json) for the generated deliverable; and
4. [`eval\results\acceptance-status.md`](../eval/results/acceptance-status.md)
   for scenario-by-scenario evidence and limits.

Use Documents 01-06 to understand why a design decision was made. Documents 07-08
show worked studies. Document 07 follows a pressure safety valve (PSV) knowledge
change of the kind an engineer might make six months later. Document 08 compares
the available earlier result (the **baseline**) with current tickets.

## Development topics

The numbers give a reading order, not an exact timeline. We revisited components
when tests exposed problems.

| Document | Engineering question | Main decision or result | File |
|---:|---|---|---|
| 01 | What does the assignment require? Where can judgment go wrong? | Separate model interpretation from fixed code rules. Identify unsupported assumptions before choosing components | [`01_INITIAL_INVESTIGATION.md`](01_INITIAL_INVESTIGATION.md) |
| 02 | What can the data show? How should related cases and model context be separated? | Inspect 21 findings and 18 assets. Group related cases, disclose prior exposure and exclude evaluator material from production context | [`02_DATA_EVALUATION_PLAN.md`](02_DATA_EVALUATION_PLAN.md) |
| 03 | What counts as success or failure? | Define A-D/X scenarios, review of ticket meaning, fixed-version repeat checks, usage accounting and contract-change rules | [`03_EVALUATION_ACCEPTANCE.md`](03_EVALUATION_ACCEPTANCE.md) |
| 04 | How do we isolate model access and record usage? | Use an inference boundary that supports different providers. Separate measured Copilot usage from estimated API-equivalent cost | [`04_INFERENCE_LIBRARY.md`](04_INFERENCE_LIBRARY.md) |
| 05 | How can guidance change without editing workflow code? | Preserve source meaning during extraction and review. Create releases that cannot be changed. Approve runtime use separately and check delivered context | [`05_KNOWLEDGE_LIFECYCLE.md`](05_KNOWLEDGE_LIFECYCLE.md) |
| 06 | How do the components work together without hiding failure? | Limit assessment attempts. Keep urgency and review rules in code. Require complete coverage and replace output in one step | [`06_TRIAGE_WORKFLOW.md`](06_TRIAGE_WORKFLOW.md) |
| 07 | Does the six-month knowledge-change process work? | Show limited influence and exercise the official store. Expose fixed-score, scope and non-target risks. Do not promote the experimental rule | [`07_KNOWLEDGE_CHANGE_STUDY.md`](07_KNOWLEDGE_CHANGE_STUDY.md) |
| 08 | Did calibration make tickets more useful? What caused the changes? | Compare baseline and current tickets. Separate causes of review changes. Keep failed experiments and explain remaining risks | [`08_BEHAVIOR_CALIBRATION_STUDY.md`](08_BEHAVIOR_CALIBRATION_STUDY.md) |

## Phase 1 - Understand the problem and define evidence

### 01 - Investigate before designing

We started with the Candidate Brief, source data and outgoing engineer's notes.
These are the source authority. The example ticket is not an answer key. The
investigation identified these recurring traps:

- reliability runs in the opposite direction to likelihood;
- redundancy (backup equipment) needs evidence that the partner can perform;
- Safety Critical Element (SCE) impact concerns the protected major-accident
  scenario, not repair cost;
- missing evidence is unknown, not confirmed absence; and
- valid JSON can still contain an invalid engineering judgment.

This led to the first responsibility boundary. The model interprets evidence.
Code controls urgency, schema (allowed fields and types), attempts, coverage and
publication.

### 02 - Define data, context and leakage boundaries

We then inspected all supplied data and mapped relationships that can change an
assessment. We labelled the split **non-blind** because all cases had been
exposed, and disclosed AI assistance. We did not claim independent expert truth.

Production context excluded evaluator cards, expected answers and reviewer
judgments. Related equipment evidence was grouped to reduce obvious information
leakage. We also noted that 21 rows cannot reveal every operational dependency.

The saved development runs nevertheless sent all eight TEST finding records to
the provider. B01 is not met. The split supports **regression evidence** (checks
on already exposed cases), not inference on cases isolated from development
context
([Document 02 section 7](02_DATA_EVALUATION_PLAN.md#7-current-assessment-of-the-evaluation-design)).

### 03 - Decide what counts before judging outputs

The contract linked Candidate Brief A-D and stability/reproduction requirements
to checks we could observe:

- A: structure, coverage, repair and incorrect ticket meaning;
- B: context delivery, limited knowledge influence and maintenance;
- C: code-derived urgency, corners, overrides and fact assessment;
- D: requests for human help, inability to assess, exclusions and source records;
- X: stability with fixed versions, delivery, accounting and cost.

This phase separated software self-tests from review of actual model output.
A passing validator does not prove that scores are correct.

## Phase 2 - Build the system boundaries

### 04 - Isolate inference transport

The inference layer handles model requests, not triage decisions. It records
provider identity, request boundaries, usage, request duration and failures. It
does not own engineering policy.

An existing subscription provided Copilot access. Copilot did not expose billing
allocation for each run. Direct Azure remained useful for stricter provider
accounting.

The documents separate measured tokens and Copilot AI units from API-equivalent
cost estimates. These estimates apply declared API prices to measured usage;
they are not actual Copilot charges. Actual Copilot billing allocation remains
unknown.

### 05 - Separate knowledge authority from orchestration

We created a **source-first lifecycle** for supplied notes and future approved
guidance. The process preserves the source before preparing model context:

```text
approved source
  -> source-faithful extraction
  -> mutable, digest-guarded working candidate
  -> review
  -> immutable release
  -> separate activation
  -> validated provider context
```

In this process, extraction preserves source meaning. The working candidate can
be edited, but its digest (hash) guards against unexpected changes. A reviewed
release cannot be changed. Separate activation approves it for runtime use.

This answers the brief's maintenance question. An integrity engineer can change
approved PSV interpretation through a reviewed source and release, instead of
editing the prompt or adding code for one finding. General score anchors and
urgency rules still require an application-policy change. If new guidance
overlaps domain interpretation in the prompt, check prompt compatibility before
activation.

### 06 - Integrate one fail-closed workflow

The workflow links validated findings, registry data and version-fixed context.
It asks the model for likelihood/impact (L/I), facts, uncertainty and planning
text. Code validates the response, calculates urgency and review routing, and
enforces the total attempt record. It publishes only a complete batch, replacing
the output file in one step (**atomic publication**).

Each model call targets one finding but receives every finding in that run's
input CSV. This is correct for final all-21 generation. The saved development run
generated 13 tickets but included all 21 finding records in its input context.
That is why it failed B01, as described in section 02 above.

Unreadable JSON, schema violations, unsupported evidence and inability to justify
scores remain different failure types. If one finding fails, the system cannot
publish a partial batch or present an old output as the current result.

## Phase 3 - Exercise change paths and calibrate behavior

### 07 - Validate the knowledge-maintenance path

The knowledge study first changed one isolated artificial context input. It then
tested the official source store and the complete 21-ticket command.

The target result changed as intended. The negative control, a PSV identified
only by its tag, remained outside the rule's scope. The exercise also showed that:

- the experimental source fixed scores that should belong to the scoring guide;
- one editor path lost structured scope and evidence;
- PSV guidance with a limited scope still entered the knowledge shared across
  the batch;
- non-target scores varied; and
- the rule lacked authenticated domain-owner approval.

The editor defect was fixed and checked. The experimental releases were not
approved for promotion. The working candidate returned to the baseline authority.

### 08 - Calibrate the integrated ticket behavior

The saved baseline had valid structure but gave planners little separation:
19/21 tickets were U7-U9, and all 21 had the earlier broad review flag.

Calibration changed several parts of the system. The final comparison is not a
single-variable A/B test. The study links both complete ticket files at the top,
records model and policy identities, and uses code replay to separate causes of
the review reduction.

The current result has 15/21 tickets at U7-U9 and six extra-review routes before
normal queuing. The tickets are less uniform; that does not prove calibrated
risk. Six protection cases changed because of assessment inputs as well as
routing policy. The study records this as a specific regression risk.

## Phase 4 - Delivery artifacts

Current delivery status is available through four primary artifacts:

| Artifact | Purpose |
|---|---|
| Root [`README.md`](../README.md) | Included artifacts, current status and run commands |
| Root [`DESIGN.md`](../DESIGN.md) | Direct answers to Candidate Brief A-D and reasons for design choices |
| Root [`tickets.json`](../tickets.json) | System-generated 21-ticket draft output |
| [`eval\results\README.md`](../eval/results/README.md) | Evidence index, observations, cost/accounting and unresolved acceptance checks |

The final file meets the structural contract and has a provisional AI-only
review of its meaning. It is not human-approved or independently
domain-certified. Reproduction from a clean checkout is not established.
Hidden provider attempts and actual Copilot USD allocation remain unknown.

## Authority and evidence hierarchy

| Question | Authority |
|---|---|
| What are the source requirements? | Unchanged Candidate Brief and supplied domain notes |
| What is the current design? | Root `DESIGN.md` |
| What does the system currently do? | Production code and pinned configuration |
| What was supposed to count? | `eval\spec`; Documents 02-03 explain the contract and its reasons |
| Why were component/workflow decisions made? | Documents 01, 04-06 |
| What happened during controlled changes? | Documents 07-08 and linked evidence |
| What actually passed, failed or remains unknown? | `eval\results` |
| Where are setup and run commands? | Root `README.md` |

Specifications define what counts as success. Results record what happened.
File integrity checks, evaluator self-tests and AI review are not approval for
operational use.

## Original decision process

[`original-decision-process\README.md`](original-decision-process/README.md)
indexes the exact working snapshot of Documents 01-06 before the rewrite.
`manifest.json` records its file identities. This snapshot preserves the detailed
historical order and earlier terminology.

Root `DESIGN.md` links to the current numbered documents for more detail. These
files explain decisions and report studies.

## Plain-English documentation review

The current documents, root `README.md` and root `DESIGN.md` were rewritten for
readers who use English as a second language. The supplied candidate package and
historical snapshots remain unchanged.

Two AI agents reviewed the rewrite in sequence. The first found no remaining
issue. The second found one misleading explanation: a prompt change corrected
event ordering, not records of origin. That correction was accepted. No review
suggestion was rejected. These were documentation reviews, not new evidence that
the system passes acceptance or that its engineering judgments are correct.
