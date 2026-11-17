# Data, Context and Evaluation Boundaries

> **Document status:** panel summary of the evaluation design. The exact
> pre-rewrite working-contract bytes are preserved at
> `docs\original-decision-process\02_DATA_EVALUATION_PLAN.md`; current
> machine-checked membership and fingerprints are in `eval\spec\split.json`.

## Abstract

The supplied dataset is too small, related and already exposed to support claims
of blind generalization. The evaluation design therefore uses it for a narrower
purpose: make engineering decisions, context boundaries and failure evidence
explicit without turning the 21 findings into a hidden answer key.

The plan profiles the source data, groups findings that share
assessment-changing evidence, separates development from a non-blind test
partition, and defines what production context may contain. It also distinguishes
three evidence classes that are often confused:

1. artifact integrity;
2. deterministic system behavior; and
3. semantic ticket quality.

Passing one does not imply the others.

## 1. Dataset and claim boundary

The supplied package contains 21 findings and 18 equipment records plus domain
notes and one illustrative ticket. All findings and the example were available
during development. The reference material is AI-assisted and not independent
expert gold.

Consequently, the evaluation may support statements about:

- behavior on named scenarios;
- source/context delivery;
- deterministic contract enforcement;
- observed decision stability; and
- retained model/reviewer outcomes.

It may not support population accuracy, unseen-data performance, statistical
failure rates or domain certification.

## 2. Data risks that shaped the evaluation

| Data characteristic | Evaluation implication |
|---|---|
| Reliability score runs opposite to likelihood | Include explicit direction checks and contradiction probes |
| Criticality and reliability are priors | Do not use registry values as exact expected scores |
| Related findings share equipment or protection state | Keep assessment-changing groups together |
| Redundancy labels do not establish partner health | Test actual delivered partner evidence |
| Missing deviation, POB or restoration data | Preserve unknown state; do not infer confirmed absence |
| One example ticket is exposed | Treat it as format/detail guidance, not a scoring key |
| Only 21 findings exist | Report raw outcomes; avoid accuracy percentages and confidence claims |

Source profiling establishes these characteristics. It does not evaluate the
triage system.

## 3. Evaluation decisions

### Decision 1 — Group by shared assessment-changing evidence

**Decision.** Findings stay in the same partition when one can materially change
the other’s L/I, redundancy credit, fact state or planning decision.

**Rationale.** Splitting linked observations could expose the answer context in
development while presenting the paired test finding as independent.

**Rejected alternative.** Grouping every equipment/process adjacency together
would collapse the already small dataset without evidence that every relationship
changes assessment.

The exact groups and membership are versioned in `eval\spec\split.json`.

### Decision 2 — Label the split non-blind

**Decision.** Use a development partition for iteration and a test partition for
one declared test phase, while disclosing that all source rows were already read.

**Rationale.** Partition discipline still reduces direct tuning on some cases,
but “held out” would overstate independence after source exposure and
AI-assisted reference construction.

**Rejected alternative.** Calling the test set blind or unseen would turn a
procedural separation into a false generalization claim.

### Decision 3 — Keep test descriptions out of development provider context

**Decision.** Development inference may use the shared registry and approved
domain material, but not test finding descriptions, evidence cards, reviewer
judgments or expected probe answers.

**Rationale.** Shared domain sources are part of the production problem.
Case-specific test answers are evaluation artifacts and would leak the target.

**Rejected alternative.** Enriching a shared knowledge store with test examples
could improve the measured cases while destroying the meaning of the test
partition.

### Decision 4 — Use evidence cards as review aids, not exact gold scores

**Decision.** Cards identify evidence, contradictions, required distinctions and
forbidden claims. Adjacent L/I values may remain defensible.

**Rationale.** The source package does not provide calibrated numeric truth.
Exact expected scores would manufacture precision and encourage case-specific
branches.

**Rejected alternative.** A single “correct” L/I/U tuple per finding would turn
candidate judgment into an invented oracle.

### Decision 5 — Keep actual observations outside specifications

**Decision.** Split, scenarios and evidence rules live under `eval\spec`;
executed outcomes live under `eval\results`.

**Rationale.** A specification defines what would count. A result records what
happened. Mixing them makes failed evidence easy to overwrite with current
status.

**Rejected alternative.** Updating scenario definitions as a progress tracker
would allow the target to move after observing failures.

## 4. Context boundary

Production assessment may receive:

- the selected finding;
- the supplied registry and `engineer_comment` fields;
- deterministic related history and declared relationships;
- approved source-faithful domain knowledge; and
- versioned prompt, rubric and policy identifiers.

Production assessment must not receive:

- evidence cards or expected answers;
- semantic reviewer judgments;
- seeded contradictions and their expected labels;
- test-derived per-finding rules; or
- copied final/gold tickets.

Provider-bound context is captured where possible. That capture can establish
delivery of context, not causal model use.

## 5. Evidence model

| Evidence class | What it can establish | What it cannot establish |
|---|---|---|
| Source/profile validation | Counts, keys, joins, hashes and declared membership are internally consistent | Ticket quality or model behavior |
| Evaluator self-tests | The evaluator detects its seeded fixtures | Evaluator accuracy on real outputs |
| Deterministic production tests | Code follows tested schema, urgency, budget and publication rules | Correct L/I or action wording |
| Captured provider context | Named inputs reached the provider boundary | The model relied on them correctly |
| AI semantic review | Provisional judgment under one reviewer configuration | Independent expert certification |
| Human/domain review | Operational judgment within reviewer scope | General model reliability without a study |

`needs_review` and unexecuted checks are not passes. Unknown usage, retries or
cost remain unknown.

## 6. Freeze and controlled change

The archived working contract and executable specs form the current reference
record. A genuine source-backed correction, grader bug or authorized requirement
change must:

1. state the reason and affected scenarios;
2. preserve the prior bytes and results;
3. identify semantic versus layout-only impact;
4. version semantic changes explicitly;
5. update only intentional fingerprints; and
6. rerun affected validation/review before a new freeze.

Reference v1.3 is a disclosed semantic change: it corrects the synthetic B02
probe so impact is held fixed and only likelihood changes. Layout revision 2
then moves those unchanged v1.3 working-contract bytes into
`docs\original-decision-process`. The panel summary at this path is not a frozen
artifact. The prior committed v1.2 contract remains in Git at revision
`92734d6`; historical v1.2 results are not reinterpreted under v1.3.

## 7. Current status and limitations

| Item | Status |
|---|---|
| Source data/profile integrity | Validated for the current working reference |
| Split independence | Non-blind and AI-assisted by design |
| Runtime context isolation | Tested in bounded paths; not a universal proof |
| Semantic reference authority | Provisional; not expert gold |
| Acceptance scenarios | Mixed observed evidence; see `eval\results\README.md` |
| Final system acceptance | Not achieved; root `tickets.json` is absent |

The current working specs identify reference 1.3, while the archived Document 02
records the earlier design history. Validator consistency does not make an
uncommitted working-tree reference a durable freeze.

## 8. Reader path

- Exact pre-rewrite working design: `docs\original-decision-process\02_DATA_EVALUATION_PLAN.md`
- Current split and hashes: `eval\spec\split.json`
- Acceptance scenarios: `docs\03_EVALUATION_ACCEPTANCE.md`
- Observed outcomes: `eval\results\README.md`
- Frozen-version measurement: `docs\07_VERSION_RELIABILITY_PROTOCOL.md`
