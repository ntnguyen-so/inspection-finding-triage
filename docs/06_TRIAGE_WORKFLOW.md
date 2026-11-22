# Fail-Closed Triage Workflow

This document explains how a validated input snapshot becomes draft tickets,
where model judgment stops, and how the workflow fails without publishing a
partial batch. It describes runtime behavior; it does not claim that code can
prove engineering correctness.

## Abstract

The workflow converts one validated snapshot of findings, registry data and
pinned knowledge into either a complete draft batch or an explicit failure. Its
central design choice is asymmetric ownership:

- the model interprets observations and proposes likelihood, impact, facts,
  uncertainty and planning text;
- code owns identity, schema, evidence checks, urgency, escalation, attempt
  accounting, coverage and publication; and
- a human owns approval.

This boundary does not make model output correct or deterministic. It makes
failure visible and prevents invalid, partial or unsupported output from looking
like a successful current delivery.

For this document:

- **L** is likelihood of failure, **I** is impact of failure and **U** is
  code-derived urgency, all on the declared 1-10 ordinal scale.
- **SCE** means Safety Critical Element.
- An **activation** is the reviewed manifest that pins the knowledge release,
  selector, prompt and policy identities for a run.
- Every generated batch requires ordinary human approval. The ticket field
  `review_required` marks an additional exceptional check before work-queue
  entry; it does not replace that universal approval.

Sections 1-3 explain the execution and failure path, section 4 defines urgency,
sections 5-7 cover context, publication and human review, and sections 8-10
state the observed evidence and remaining limits.

### Module boundary and dependency direction

The workflow does not extract or maintain domain guidance.
`triage_knowledge` creates the pinned context bundle, `llm_inference` performs
one observable model call at a time, and `triage` owns the orchestration:

```text
triage_knowledge -> validated context bundle --+
                                               |
triage ----------------------------------------+-> llm_inference
  |                                                one model call
  +-> validation -> policy -> complete batch -> atomic publication
```

This separation allows knowledge sources, extraction and retrieval to evolve
without changing batch orchestration. It also lets workflow tests inject a fixed
context contract without exercising the knowledge store. The reverse dependency
is prohibited: knowledge tooling does not publish tickets, choose urgency or
consume evaluator answers.

Putting retrieval inside the workflow was rejected because it would make
source maintenance and operational execution one permission surface. A change to
PSV guidance could then require editing orchestration code, while a workflow
developer could silently alter the knowledge authority.

## 1. End-to-end execution

The brief requires more than generating 21 JSON objects. The system
must explain what happens when output is malformed, structurally invalid,
violates an enforceable semantic contract or cannot support a score. It must also
document how knowledge reaches assessment, derive urgency in code and defer to a
human. Separate semantic and human review remain necessary because code cannot
prove that every plausible score is correct.

The implemented lifecycle is:

```text
load and validate inputs
  -> pin configuration, policy, prompt and knowledge
  -> build and independently verify bounded context
  -> request model assessment for one finding
  -> validate identity, schema, citations, quotations and fact consistency
  -> optionally repair one recoverable output error
  -> derive urgency, floors, review routing and required checks in code
  -> repeat within persistent attempt budget
  -> revalidate exact selected-set coverage (21 tickets for the delivery run)
  -> atomically replace the configured output
```

Any terminal finding failure stops the batch before publication. Failures after
replacement that enter the workflow's handled failure path trigger rollback to
the previous bytes, or removal when no previous output existed; a rollback
failure remains visible rather than being reported as successful publication.
The retained run published an experimental output with its own receipt. Root
`tickets.json` was promoted separately by a byte-for-byte, hash-checked copy; the
workflow did not directly publish the root file.

The assessment system prompt is a packaged workflow artifact, not inline Python
or mutable runtime configuration. Activation pins its exact bytes and contract
bindings in
[`config\triage-activation.json`](../config/triage-activation.json). Loading or
compatibility failure occurs before provider dispatch.

### Prompt authority and controlled change

The prompt specifies the reasoning protocol and output task; it is not a second
knowledge base. Authority remains deliberately separated:

| Information | Authority |
|---|---|
| Finding observations and supplied registry fields | Selected input snapshot; missing current state is not inferred |
| Source-backed domain guidance | Reviewed, immutable and activated knowledge release |
| L/I anchors and declared assessment choices | Pinned assessment policy |
| Urgency, review floors and publication rules | Application policy and code |
| Reasoning sequence and response task | Packaged prompt artifact |
| Operational approval | Human reviewer |

Durable prompt protocol includes treating source text as data rather than
instructions, separating likelihood from impact, distinguishing missing
evidence from confirmed absence, qualifying suspected causes and returning
inability instead of inventing a fallback score. Related observations do not
establish causation, repair or present state.

The active prompt instructs the model to return `unassessable` when an authority
conflict prevents a required score from being justified; code then fails the
batch. This is a model-followed instruction, not a detected invariant: a
conflict the model resolves while still producing a score is not caught by
code. Hash and contract binding make prompt identity reproducible, but do not
detect every semantic conflict between prompt, policy and knowledge. Some domain
interpretation remains embedded in the packaged prompt; that is a disclosed
compatibility risk, not an achieved clean authority separation.

The Copilot route sends the packaged prompt as the system message. Retained
evidence records that requested separation but cannot prove how the provider
handles messages internally. A knowledge change that overlaps interpretation
in the active prompt therefore requires focused prompt-compatibility review
before activation; it is not assumed to override prompt wording.

Prompt changes therefore follow the controlled-change boundary. Each removed
clause needs a destination, provenance and focused regression evidence.
Code/schema duplication is removed only after deterministic enforcement and
behavioral preservation are demonstrated. A shorter prompt is not promoted
merely because it is easier to maintain or cheaper to send. This gate applies
to future changes. The current prompt still contains some domain interpretation,
so maintainers must review it when overlapping knowledge changes.

## 2. Responsibility boundary

| Model interprets or authors | Code owns |
|---|---|
| Meaning of free-text observations | Input schema, IDs, joins and score direction |
| Near-term likelihood and consequence | Closed response schema and score ranges |
| Confirmed/false/suspected/unknown facts | Citation existence, exact quotations and fact-state consistency |
| Uncertainty and proposed verification | Urgency arithmetic, rule floors and review requirements |
| Summary and recommended activity | Attempt ledger, complete coverage and atomic publication |
| Explicit inability to support L/I | Nonzero failure; no default or placeholder score |

### Why this split

Natural-language evidence and interacting asset context require interpretation.
Identity, arithmetic and publication are invariants. Moving the latter into code
provides deterministic tests and traceable failure without pretending that code
can prove the engineering truth of a coherent L/I assessment.

### Rejected alternatives

- **Model-authored urgency:** explicitly conflicts with the brief and hides
  arithmetic/rule provenance.
- **Rules-only L/I:** brittle against interacting observations and likely to
  encode finding-specific answers.
- **Code rewriting semantic output:** can manufacture plausibility without new
  evidence.
- **Fallback scores or placeholder tickets:** turn inability to assess into a
  complete-looking answer.

## 3. Structured output and bounded recovery

The model returns an assessment object, not the final public ticket. The
application rejects extra fields, duplicate keys, wrong identity, non-integer or
out-of-range scores, excessive text, missing citations, inexact quotations,
contradictory fact combinations and missing required activities.

Recoverable response or contract errors may receive one further application
attempt using the same pinned context, the rejected draft and bounded diagnostic
feedback. This includes named evidence, fact, planning and policy-verification
violations; unsupported semantic uncertainty is not repaired by silently
changing a score. When both attempts fail, the application exits nonzero and
publishes nothing.

Each send is reserved in a persistent ledger before provider dispatch. A process
interruption therefore consumes the reservation instead of resetting the
configured run budget. The application allows at most two sends for one finding,
but provider-internal retries can only be counted when the route exposes them;
the Copilot delivery route did not expose hidden HTTP attempts.

These validators catch defined semantic errors such as invented citations,
contradictory fact states and unsupported required activities. A schema-valid
but poorly judged adjacent score can still pass code validation. That case
requires the separate semantic-review and human-approval layers, and current A04
evidence remains partial.

### Why one repair

One repair is sufficient to test whether explicit feedback corrects an output
fault while keeping the maximum batch budget finite. More retries would increase
cost and create optional stopping; zero repair would discard observed cases where
the same model corrected malformed JSON or a schema violation.

The two-attempt limit is a project policy, not a requirement stated by the
brief.

## 4. Urgency and fact-state policy

For model-proposed ordinal likelihood `L` and impact `I`, code computes:

```text
base  = ceil(0.7 * I + 0.3 * L)
      = (7 * I + 3 * L + 9) // 10
final = max(base, every applicable rule floor)
```

Impact receives more weight because the supplied domain notes say a
low-likelihood, high-impact **SCE** still requires attention this week, while the
brief requires both asymmetric corners to be documented. The same notes also say
urgency is generally closer to the maximum; that statement conflicts with the
explicit high-likelihood/low-impact example that may wait for shutdown. The
prototype resolves the ambiguity by weighting impact: it is closer to the
maximum when `I >= L`, but deliberately follows the explicit shutdown example
when `L > I`. The 0.7 weight is a project-defined interpretation, not
calibrated risk mathematics.

| L / I | Chosen base | Interpretation |
|---|---:|---|
| 1 / 1 | 1 | Low/low remains low |
| 10 / 1 | 4 | Frequent low-consequence issue does not become maximum urgency |
| 1 / 10 | 8 | Rare catastrophic consequence still receives prompt attention |
| 10 / 10 | 10 | High/high reaches the ceiling |

Supplied overrides require confirmed facts. Project-defined precautions and
review rules are separately labelled. Unknown deviation, personnel-on-board,
restoration or partner state cannot be converted into a confirmed trigger.

### Rejected alternatives

- A plain mean understates the low-L/high-I corner.
- A plain maximum overstates the high-L/low-I corner.
- Treating every SCE issue as maximum L/I discards the actual finding evidence.
- Treating unknown as confirmed would inflate urgency while obscuring why.

All 100 L/I pairs are checked for range and monotonicity. Those checks establish
formula behavior, not domain calibration.

## 5. Context and knowledge safeguards

Each per-finding model call identifies one target finding, but its shared context
payload contains **every finding in that run's input CSV**, the complete bounded
registry and engineer comments, derived history, and the active source-faithful
knowledge release. Production code rebuilds and hash-checks that payload before
dispatch. Evaluation cards, expected answers and reviewer judgments are
excluded.

Full bounded context was chosen because the supplied corpus is small and
relationship-heavy. This avoids unsupported top-k assumptions, but it has a
measured token cost and does not prove that the model used every relevant item.
The bounded knowledge-influence experiment supports one declared synthetic
positive and negative-control scope; it is not production domain certification.

This design is valid for the final delivery because its input is all 21
findings. It violated B01 when the development run selected 13 output findings
but supplied the all-21 CSV: every development provider request also contained
the eight test finding records. That is an evaluation-isolation failure, not a
failure of the final all-21 generation.

## 6. Complete-batch publication

The output JSON must contain exactly one ticket for every input finding.
Publication occurs only after batch-level identity and coverage validation. A
temporary file is flushed and atomically substituted on the same volume; if
replacement fails, old bytes remain.

A partial file could be mistaken for the complete planning package and hide
which findings failed.

Publishing valid tickets while dropping one failed finding was rejected because
it optimizes availability at the cost of silent incompleteness.

This choice has a real trade-off: whole-batch generation is fragile and can
waste completed work. Hash-pinned per-finding resume is future work, but it must
not weaken final all-or-nothing publication.

## 7. Deferral and human authority

There are three valid outcomes:

1. a draft ticket with no exceptional prequeue check;
2. a draft ticket with a specific additional check; or
3. terminal inability to produce the batch.

`review_required` does not mean “the score may be unsupported.” It identifies a
specific check beyond the global approval required for every draft. No output
authorizes maintenance, shutdown or work-order creation.

Global human approval remains universal. The exceptional flag is reserved for
specific unresolved protection, evacuation, restoration or an SCE finding's
unregistered redundancy-partner decision; SCE adjacency, general uncertainty or
redundancy wording alone does not trigger it. Each flagged ticket projects a
concrete `Why:` explanation and verification check.

## 8. Current assessment of the workflow design

| Question | Evidence | Current conclusion |
|---|---|---|
| Are deterministic controls outside the model? | [Production tests](../tests/test_triage.py) and [fault evidence](../eval/results/triage/native-v2-fault-evidence-1/report.json) cover schema, identity, bounded repair, exhaustion, urgency and publication. | Supported for tested control behavior; formula behavior is not calibrated risk truth. |
| Does knowledge reach assessment without becoming policy? | [Final provider-bound context](../eval/results/triage/structured-planning-v31/final/evidence/run.json) shows delivery; the [B01 audit](../eval/results/triage/structured-planning-v31/b01-development-context-audit.json) shows TEST findings in DEV context. | B01 is not met for the retained development runs. Broad causal use remains inconclusive, and the evidence is not domain certification. |
| Does fixed-identity comparison expose decision drift? | The [X01 adjudication](../eval/results/triage/structured-planning-v31/x01-development-adjudication.json) preserves operational routing while disclosing numeric and rule-trace drift. | Inconclusive for full X01 acceptance because the semantic procedure was supplementary and reviewer identity was incomplete. |
| Is complete-batch publication observable? | The experimental output has a [publication receipt](../eval/results/triage/structured-planning-v31/final/evidence/publication.json); root `tickets.json` is byte-identical by SHA-256 but was promoted outside the workflow. | Supported for the observed publication and hash-checked promotion. The root file has no separate workflow receipt; human approval and clean-checkout reproduction remain unresolved. |
| Was semantic quality reviewed separately? | The [all-finding review](../eval/results/triage/structured-planning-v31/final/reviewer-observation.json) reports no failed dimensions. | Inconclusive for protocol-conformant acceptance because required reviewer identity fields were not exposed. |
| Are accounting limits visible? | [Delivery cost evidence](../eval/results/delivery-cost-summary.json) records application sends and provider metering. Measured tokens produce a US$2.350286 API-equivalent estimate under declared public rates. | Partial: the estimate is reproducible; actual Copilot billing allocation and hidden HTTP attempts remain unknown. |

The evidence authority is
[`eval\results\README.md`](../eval/results/README.md). Test counts, evaluator
self-tests and AI review are not equivalent to system acceptance.

### Cost interpretation

The retained 21-ticket delivery used 973,468 input and 40,335 output tokens
(US$2.350286 API-equivalent under the declared public rates, not a Copilot
invoice). [Document 04 section 6](04_INFERENCE_LIBRARY.md#6-reproducibility-and-cost-limits)
owns the calculation, cache-aware scenario and billing limits; the underlying
totals and assumptions are retained in the
[delivery cost evidence](../eval/results/delivery-cost-summary.json).

## 9. Current provenance and disclosure

The current policy and configuration are informed by exposed evaluation
evidence, so the retained observations are not independent confirmation of
stable quality. The high-impact SCE urgency floor protects the supplied
low-L/high-I corner and remains project-defined and uncalibrated.
[Document 03 section 6](03_EVALUATION_ACCEPTANCE.md#6-cross-cutting-evidence)
defines the fixed-identity reliability protocol; current evidence does not
establish a clean checkout reproduction or independent reviewer authority.

## 10. Assumptions and limitations

- Inputs represent one selected snapshot; state outside that snapshot is not
  invented.
- Redundancy labels do not establish current partner health.
- L/I/U are ordinal scales.
- The explicit asymmetric examples take precedence over the domain note's more
  general “closer to maximum” wording where they conflict.
- One trusted local writer and same-volume replacement are assumed.
- Provider labels expose configuration, not hidden weights or expertise.
- AI reviewers are provisional and may share model-family failure modes.
- API-equivalent cost is calculable from measured tokens; actual provider
  billing and hidden transport attempts remain unknown where the route does not
  expose them.
- A successful draft still requires human approval.
