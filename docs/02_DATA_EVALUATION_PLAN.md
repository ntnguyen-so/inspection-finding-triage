# Data, Context and Evaluation Boundaries

The evaluation design defines what the supplied data can support, how cases and
context are separated, and which evidence classes must remain distinct.
Executable membership and fingerprints remain authoritative in `eval\spec`.

## Abstract

The supplied dataset is too small, related and already exposed to support claims
of blind generalization. The evaluation design therefore uses it for a narrower
purpose: make engineering decisions, context boundaries and failure evidence
explicit without turning the 21 findings into a hidden answer key.

The central methodological problem is not how to calculate an accuracy
percentage. It is how to obtain useful evidence from a non-blind, relationship-
heavy case set while preserving the distinction between artifact integrity,
deterministic system behavior and semantic ticket quality. Passing one of these
classes does not imply the others.

## 1. Research questions

The evaluation design addresses four questions:

1. **Claim boundary:** what can 21 exposed findings establish without implying
   unseen-data performance or domain certification?
2. **Unit of independence:** which findings share evidence strongly enough that
   splitting them would create leakage or a false independence claim?
3. **Context boundary:** what may reach production assessment, and what must
   remain isolated as evaluator-only information?
4. **Evidence interpretation:** which observations establish software behavior,
   semantic quality, stability or maintainability, and with what limits?

## 2. Dataset and claim boundary

The supplied package contains 21 findings and 18 equipment records, plus domain
notes and one illustrative ticket. The evaluation split contains 13 development
cases in nine relationship groups and eight test cases in four groups. All source
rows and the example were available during development. The semantic reference
is AI-assisted and is not independent expert gold.

Consequently, the evaluation may support statements about:

- behavior on named scenarios;
- source and context delivery;
- deterministic contract enforcement;
- observed decision stability; and
- retained model and reviewer outcomes.

It may not support population accuracy, unseen-data performance, statistical
failure rates or domain certification. Raw outcomes and limitations are more
honest than percentages on this sample.

## 3. Data risks that shaped the evaluation

| Data characteristic | Evaluation implication |
|---|---|
| Reliability score runs opposite to likelihood | Include explicit direction checks and contradiction probes |
| Criticality and reliability are priors | Do not use registry values as exact expected scores |
| Related findings share equipment or protection state | Keep assessment-changing groups together |
| Redundancy labels do not establish partner health | Test actual delivered partner evidence |
| Missing deviation, personnel-on-board (POB) or restoration data | Preserve unknown state; do not infer confirmed absence |
| One example ticket is exposed | Treat it as format/detail guidance, not a scoring key |
| Only 21 findings exist | Report named outcomes; avoid accuracy and confidence claims |

The deluge observations illustrate why relationship grouping matters. One
finding records poor delivery above producing wellheads; a related finding
records a closed branch valve, reopening and missing impairment entry. Either
row can change the interpretation of the other, while neither proves restored
nozzle performance. Treating them as independent cases would erase
assessment-changing evidence.

Source profiling establishes these characteristics. It does not evaluate the
triage system.

## 4. Evaluation decisions

### 4.1 Group by shared assessment-changing evidence

Findings stay in the same partition when one can materially change the other’s
L/I, redundancy credit, fact state or planning decision.

Splitting linked observations could expose answer context during development
while presenting the paired test finding as independent.

Grouping every equipment or process adjacency together was rejected because it
would collapse the already small dataset without evidence that every
relationship changes assessment.

### 4.2 Label the split non-blind

Development and designated test partitions remain separate, but all source rows
are disclosed as exposed and the current system is informed by evaluation
evidence.

Partition discipline can reduce direct tuning on some cases. Calling the test
set “held out” or “unseen,” however, would overstate independence after source
exposure and AI-assisted reference construction.

The term “blind test” was rejected because it would turn a procedural separation
into a false generalization claim.

### 4.3 Keep test descriptions out of development provider context

Development inference may use the shared registry and approved domain material,
but not test finding descriptions, evidence cards, reviewer judgments or
expected probe answers.

Shared domain sources are part of the production problem. Case-specific test
answers are evaluation artifacts and would leak the target.

Enriching a shared knowledge store with test examples was rejected because it
could improve measured cases while destroying the meaning of the partition.

### 4.4 Use evidence cards instead of exact gold scores

Evidence cards identify contradictions, required distinctions and forbidden
claims for the semantic procedure in Document 03 §7. They constrain reviewer
judgment without prescribing one exact L/I tuple, so adjacent values may remain
defensible.

The source package does not provide calibrated numeric truth. Exact expected
scores would manufacture precision and encourage case-specific branches.

A single “correct” L/I/U tuple per finding was rejected because it would turn
engineering judgment into an invented oracle.

### 4.5 Keep observations outside specifications

Membership, scenarios and evidence rules live under `eval\spec`; executed
outcomes live under `eval\results`.

A specification defines what would count, while a result records what happened.
Mixing them makes failed evidence easy to overwrite with current status.

Using scenario definitions as a progress tracker was rejected because it would
allow the target to move after observing failures.

## 5. Context boundary

Production assessment may receive:

- the selected finding;
- the supplied registry and `engineer_comment` fields;
- deterministic related history and declared relationships;
- approved source-faithful domain knowledge; and
- prompt, rubric and policy identities required to explain one run.

Production assessment must not receive:

- evidence cards or expected answers;
- semantic reviewer judgments;
- seeded contradictions and their expected labels;
- test-derived per-finding rules; or
- copied final or gold tickets.

Provider-bound context is captured where possible. Capture can establish delivery
of named context, not that the model used it causally or correctly.

## 6. Evidence model

| Evidence class | What it can establish | What it cannot establish |
|---|---|---|
| Source/profile validation | Counts, keys, joins, hashes and declared membership are internally consistent | Ticket quality or model behavior |
| Evaluator self-tests | The evaluator detects its seeded fixtures | Evaluator accuracy on real outputs |
| Deterministic production tests | Code follows tested schema, urgency, budget and publication rules | Correct L/I or action wording |
| Captured provider context | Named inputs reached the provider boundary | Correct causal use |
| Token-based cost calculation | A reproducible API-equivalent estimate under declared public rates | The Copilot subscription's actual per-run USD allocation |
| Bounded intervention | One isolated input change produced the preregistered effect while controls remained semantically excluded | General knowledge correctness |
| AI semantic review | Provisional judgment under one reviewer configuration | Independent expert certification |
| Human/domain review | Operational judgment within reviewer scope | General model reliability without a study |

`needs_review`, unexecuted checks and unknown accounting are not passes.

## 7. Current assessment of the evaluation design

The table assesses the evaluation design against current evidence without
turning observations into new specifications.

| Evaluation decision | Current evidence | Interpretation and remaining limit |
|---|---|---|
| Group related findings | Current split membership keeps assessment-changing equipment and protection evidence together. | **Supported as leakage control.** It does not prove that every operational dependency is known. |
| Label the split non-blind | All findings are exposed and the current configuration is informed by exposed evaluation evidence. | **Honest but non-independent.** Current test evidence supports regression claims, not blind generalization. |
| Isolate test descriptions and answers | Boundary tests show that production did not import evaluator cards or expected answers, but the retained `structured-planning-v31` development provider context contained all eight test finding records. | **Not met for the retained development runs.** The failure is test-description leakage, not evidence-card or expected-answer leakage; the 13/8 split therefore supports regression workflow, not case-isolated generalization. |
| Use cards rather than exact scores | The current semantic procedure evaluates grounding, planning and uncertainty while allowing unresolved adjacent-score judgment. | **Supported provisionally.** Reviewer calibration is narrow and AI-assisted. |
| Separate specifications from results | Executable specifications remain under `eval\spec`; current observations remain under `eval\results`. | **Supported structurally.** Current status must be read from root `README.md` and the evidence index. |

## 8. Threats to validity and claim limits

- **Small, exposed sample.** All findings were read during development; no
  population or unseen-data claim is available.
- **Development-context leakage.** The retained `structured-planning-v31`
  development runs selected 13 DEV findings but sent all eight TEST finding
  records in provider context.
  Later TEST results are test-informed regression evidence, not isolated
  held-out evidence.
- **Relationship-heavy cases.** Grouping reduces obvious leakage but cannot prove
  independence between all operationally connected equipment.
- **AI-assisted reference and review.** Cards and semantic judgments are useful
  structured evidence, not domain-expert gold.
- **Evaluation-conditioned configuration.** Current behavior and policy reflect
  exposed evaluation evidence, so the resulting observations support regression
  claims rather than blind evaluation.
- **Provider opacity.** Token and cache metering are exposed, and declared public
  rates support a reproducible API-equivalent estimate. Hidden HTTP attempts and
  the actual Copilot billing allocation remain unknown.
- **Source provenance.** Exact producer bytes are retained and hash-bound, but
  clean-checkout reproduction is not established.

These limitations do not make the prototype evidence useless. They bound the
claims it can support.

## 9. Controlled-change boundary

This design document does not define a second change procedure. Executable
specifications remain the machine-checked authority, results remain separate,
and replaced contract bytes or failed observations must not be silently
reinterpreted.
Document 03 §9 defines the current controlled-change procedure.

## 10. Reader path

- Source package: `docs\candidate-pack\candidate-pack`
- Current split and hashes: `eval\spec\split.json`
- Acceptance scenarios and semantic reviewer protocol:
  `docs\03_EVALUATION_ACCEPTANCE.md`
- Observed outcomes, evidence and limitations: `eval\results\README.md`
- Current delivery status and run instructions: root `README.md`
