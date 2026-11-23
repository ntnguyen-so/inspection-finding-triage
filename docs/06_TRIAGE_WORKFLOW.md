# Fail-Closed Triage Workflow

This document explains how one checked set of inputs becomes draft tickets.
It shows which decisions belong to the model and which belong to code.
It also explains how failures stop publication of a partial batch.
Code checks runtime rules; it cannot prove engineering correctness.

## Abstract

The workflow takes one validated snapshot of findings, registry data and
knowledge fixed by version and hash. It produces either a complete draft batch
or an explicit failure. The model, code and human have different responsibilities:

- the model interprets observations and proposes likelihood, impact, facts,
  uncertainty and planning text;
- code owns identity, schema, evidence checks, urgency, escalation, attempt
  accounting, coverage and publication; and
- a human owns approval.

This separation does not make model output correct or repeatable. It makes
failure visible. Invalid, partial or unsupported output cannot be presented as
a successful new delivery.

For this document:

- **L** is likelihood of failure, **I** is impact of failure and **U** is
  urgency calculated by code. Each uses the declared 1-10 ordinal scale:
  scores are ordered categories, not measured probabilities or amounts.
- **SCE** means Safety Critical Element.
- A **schema** defines required fields, types and limits. **Semantic review**
  checks meaning and evidence, not just response structure.
- An **activation** is a reviewed manifest, or record, fixing the exact knowledge
  release, selector, prompt and policy for a run. The selector is the code that
  chooses context. A **pin** is an exact version or content hash.
- Every generated batch requires ordinary human approval. The ticket field
  `review_required` marks an additional exceptional check before entry into the
  work queue. It does not replace approval of every draft.

Sections 1-3 explain the execution and failure path, section 4 defines urgency,
sections 5-7 cover context, publication and human review, and sections 8-10
state the observed evidence and remaining limits.

### Module boundary and dependency direction

The workflow does not extract or maintain engineering guidance.
`triage_knowledge` creates the versioned context bundle. `llm_inference` makes
one model call visible to the application at a time. `triage` controls the
sequence of calls and checks:

```text
triage_knowledge -> validated context bundle --+
                                               |
triage ----------------------------------------+-> llm_inference
  |                                                one model call
  +-> validation -> policy -> complete batch -> atomic publication
```

This separation allows source maintenance, extraction and context selection to
change without changing the batch workflow. Workflow tests can supply fixed
context without running the knowledge store. Knowledge tools must not depend
on the workflow in reverse: they do not publish tickets, choose urgency or read
evaluator answers.

We rejected placing retrieval inside the workflow. That would combine permission
to maintain sources with permission to run triage. Changing pressure safety
valve (PSV) guidance could then require a workflow edit. A workflow developer
could also silently change which knowledge is authoritative.

## 1. End-to-end execution

The brief requires more than 21 JSON objects. The system must explain what
happens when a response is not valid JSON, breaks the required structure,
breaks a meaning-related rule that code can check, or cannot support a score.
It must explain how knowledge reaches assessment, calculate urgency in code,
and defer to a human. Separate review of meaning and human approval are still
needed. Code cannot prove that every plausible score is correct.

The implemented lifecycle is:

```text
load and validate inputs
  -> fix exact configuration, policy, prompt and knowledge versions
  -> build size-limited context and check it independently
  -> request model assessment for one finding
  -> validate identity, schema, citations, quotations and fact consistency
  -> optionally repair one recoverable output error
  -> derive urgency, floors, review routing and required checks in code
  -> repeat within persistent attempt budget
  -> check complete coverage again (21 tickets for the delivery run)
  -> atomically replace the configured output
```

A terminal failure for any finding stops the batch before publication.
If a handled failure occurs after file replacement, the workflow restores the
previous bytes. If there was no previous output, it removes the new file.
If restoration fails, it reports that failure rather than claiming successful
publication.

The saved run published an experimental output and its own publication receipt.
Root `tickets.json` was copied separately after checking that every byte and the
hash matched. The workflow did not directly publish that root file.

The assessment system prompt is a packaged workflow file, not text inside Python
or editable run configuration. Activation fixes its exact bytes and the
contracts it must match in
[`config\triage-activation.json`](../config/triage-activation.json). Loading or
compatibility failure occurs before sending a request to the provider.

### Prompt authority and controlled change

The prompt describes how to reason and what to return. It is not a second
knowledge base. Different information has different authority:

| Information | Authority |
|---|---|
| Finding observations and supplied registry fields | Selected input snapshot; missing current state is not inferred |
| Source-backed domain guidance | Reviewed, immutable and activated knowledge release |
| L/I anchors and declared assessment choices | Pinned assessment policy |
| Urgency, review floors and publication rules | Application policy and code |
| Reasoning sequence and response task | Packaged prompt artifact |
| Operational approval | Human reviewer |

The prompt's lasting rules include treating source text as data, not instructions;
keeping likelihood separate from impact; and distinguishing missing evidence from
confirmed absence. It also requires the model to label suspected causes and
report inability to assess instead of inventing a score. Related observations
alone do not prove a cause, a repair or current equipment state.

The active prompt tells the model to return `unassessable` if conflicting
authorities prevent it from justifying a required score. Code then fails the
batch. This depends on the model following the instruction. Code does not
detect every conflict. If the model resolves a conflict and still returns a
score, code does not catch that conflict as such.

Hashes and contract checks identify the exact prompt. They do not detect every
conflict of meaning between prompt, policy and knowledge. Some engineering
interpretation remains in the packaged prompt. This is a disclosed compatibility
risk; authority is not yet completely separated.

The Copilot route sends the packaged prompt as the system message. Saved evidence
records this requested separation, but cannot prove how the provider handles
messages internally. If new knowledge overlaps interpretation in the prompt,
maintainers must review compatibility before activation. New knowledge is not
assumed to override the prompt.

Prompt edits follow the controlled-change process. For each removed clause,
record where its responsibility moves, its source and focused tests showing
that required behavior remains. Remove duplicate code/schema instructions only
after code enforcement and preserved behavior are demonstrated. Do not promote
a shorter prompt just because it is easier to maintain or cheaper to send.
These checks apply to future changes. Because the current prompt still includes
engineering interpretation, overlapping knowledge changes need prompt review.

## 2. Responsibility boundary

| Model interprets or authors | Code owns |
|---|---|
| Meaning of free-text observations | Input structure, IDs, links between records and score direction |
| Near-term likelihood and consequence | Closed response schema and score ranges |
| Confirmed/false/suspected/unknown facts | Citation existence, exact quotations and fact-state consistency |
| Uncertainty and proposed verification | Urgency calculation, minimum values required by rules and review requirements |
| Summary and recommended activity | Attempt ledger, complete coverage and atomic publication |
| Explicit inability to support L/I | Nonzero failure; no default or placeholder score |

### Why this split

Free-text evidence and relationships between assets need interpretation.
Identity checks, arithmetic and publication rules can be enforced consistently
in code. Code gives them repeatable tests and clear failure records. It still
cannot prove the engineering truth of a plausible L/I assessment.

### Rejected alternatives

- **Model-authored urgency:** conflicts with the brief and hides the calculation
  and rules behind the result.
- **Rules-only L/I:** handles interacting observations poorly and risks encoding
  answers for particular findings.
- **Code rewriting the assessment's meaning:** can make an answer look plausible
  without adding evidence.
- **Fallback scores or placeholder tickets:** make inability to assess look like
  a complete answer.

## 3. Structured output and bounded recovery

The model returns an assessment object, not the final public ticket.
The application rejects extra fields, duplicate keys, wrong identity, scores
that are not integers or are outside the allowed range, and text that is too long.
It also rejects missing citations, quotations that do not match, contradictory
fact combinations and missing required activities.

For an error eligible for repair, the application may make one further attempt.
It sends the same pinned context, the rejected draft and limited feedback about
the error. Eligible errors include defined evidence, fact, planning and
policy-verification violations. The application does not silently change a score
to resolve unsupported uncertainty. If both attempts fail, it exits with a
nonzero status and publishes nothing.

Before sending a request, the application reserves the attempt in a persistent
ledger (a saved attempt record). If the process stops unexpectedly, that
reservation still counts against the run budget. The application allows at most
two sends per finding. It can count retries inside the provider only if the
route reports them. The Copilot delivery route did not expose hidden HTTP
communication attempts.

These checks catch defined errors of meaning, such as invented citations,
contradictory fact states and unsupported required activities. A response can
still have valid structure and pass code checks with a poorly judged score,
including a score one point away from a defensible anchor. Separate review of
meaning and human approval must address that risk. Current A04 evidence remains
partial.

### Why one repair

One repair tests whether clear feedback can correct a response error, while
keeping the maximum batch budget finite. More retries would cost more and risk
stopping only when a desirable answer appears. No repair would discard observed
cases where the same model corrected invalid JSON or a structural error.

The two-attempt limit is a project policy, not a requirement stated by the
brief.

## 4. Urgency and fact-state policy

For model-proposed ordinal likelihood `L` and impact `I`, code computes:

```text
base  = ceil(0.7 * I + 0.3 * L)
      = (7 * I + 3 * L + 9) // 10
final = max(base, every applicable rule floor)
```

Impact has more weight because the supplied notes say a low-likelihood,
high-impact **SCE** still needs attention this week. The brief requires the design
to explain both cases where one score is high and the other low.

The notes also say urgency is generally closer to the maximum. That conflicts
with their specific example of a high-likelihood, low-impact issue that may wait
for shutdown. The prototype gives more weight to impact to resolve this
ambiguity. The result is closer to the maximum when `I >= L`. When `L > I`,
it deliberately follows the specific shutdown example. The 0.7 weight is a
project choice, not a risk formula calibrated by experts.

| L / I | Chosen base | Interpretation |
|---|---:|---|
| 1 / 1 | 1 | Low/low remains low |
| 10 / 1 | 4 | Frequent low-consequence issue does not become maximum urgency |
| 1 / 10 | 8 | Rare catastrophic consequence still receives prompt attention |
| 10 / 10 | 10 | High/high reaches the ceiling |

Overrides from the supplied notes require confirmed facts. Project precautions
and review rules are labelled separately. Unknown deviation, personnel-on-board
(POB), restoration or partner state cannot be treated as a confirmed trigger.

### Rejected alternatives

- A plain mean understates the low-L/high-I corner.
- A plain maximum overstates the high-L/low-I corner.
- Giving every SCE issue maximum L/I ignores the finding's actual evidence.
- Treating unknown as confirmed raises urgency without honestly explaining why.

All 100 L/I pairs are checked for range and monotonicity: increasing either
score must not lower urgency. These checks establish how the formula behaves,
not whether its scores are correct for engineering decisions.

## 5. Context and knowledge safeguards

Each model call names one target finding. However, its shared request context
contains **every finding in that run's input CSV**, the complete size-limited
registry and engineer comments, history derived from the inputs, and the active
knowledge release preserving source meaning. Production code rebuilds this
context and checks its hash before sending it. Evaluation cards, expected
answers and reviewer judgments are excluded.

Complete context was chosen because the supplied material is small and contains
many relationships. This avoids assuming that a search's top-ranked results
contain all needed evidence. It costs tokens, and does not prove that the model
used every relevant item. The knowledge-influence experiment supports one
declared synthetic case where a change should apply, and a negative control
where it should not. It does not certify production engineering correctness.

This context design is valid for final delivery, which uses all 21 findings.
It violated B01 in development: the run selected 13 output findings but supplied
the all-21 CSV. Every development provider request therefore also contained
the eight test finding records. This failed evaluation isolation. It was not
a failure of final generation for all 21 findings.

## 6. Complete-batch publication

The output JSON must contain exactly one ticket per input finding.
The application checks identity and complete coverage before publication.
It writes and flushes a temporary file, then replaces the output atomically on
the same volume. Atomic replacement means readers see the old file or the new
file, not a partly written file. If replacement fails, the old bytes remain.

A partial file could be mistaken for the complete planning package and hide
which findings failed.

We rejected publishing valid tickets while dropping failed findings. That would
provide some output, but silently leave the batch incomplete.

This choice has a cost: one failure can stop the whole batch and waste completed
work. Resuming saved work for individual findings with matching hashes remains
future work. It must not weaken final all-or-nothing publication.

## 7. Deferral and human authority

There are three valid outcomes:

1. a draft ticket with no exceptional prequeue check;
2. a draft ticket with a specific additional check; or
3. terminal inability to produce the batch.

`review_required` does not mean “the score may be unsupported.” It identifies a
specific check in addition to approval of every draft. No output authorizes
maintenance, shutdown or creation of a work order.

Every draft needs human approval. The exceptional flag is reserved for a
specific unresolved decision about protection, evacuation or restoration, or
about an unregistered redundancy partner in an SCE finding. A relationship to an
SCE, general uncertainty or mention of redundancy alone does not trigger it.
Code gives each flagged ticket a concrete `Why:` explanation and verification
check.

## 8. Current assessment of the workflow design

| Question | Evidence | Current conclusion |
|---|---|---|
| Does code enforce repeatable controls outside the model? | [Production tests](../tests/test_triage.py) and [fault evidence](../eval/results/triage/native-v2-fault-evidence-1/report.json) cover structure, identity, limited repair, exhaustion, urgency and publication. | Supported for tested controls. Formula behavior is not calibrated engineering risk. |
| Does knowledge reach assessment without becoming policy? | [Final provider-bound context](../eval/results/triage/structured-planning-v31/final/evidence/run.json) shows delivery. The [B01 audit](../eval/results/triage/structured-planning-v31/b01-development-context-audit.json) shows TEST findings in DEV context. | Saved development runs do not meet B01. Evidence does not establish broad model use of knowledge or certify engineering correctness. |
| Does comparison with a fixed setup reveal changed decisions? | The [X01 adjudication](../eval/results/triage/structured-planning-v31/x01-development-adjudication.json) records unchanged operational routing but changed numbers and applied-rule traces. | Full X01 acceptance remains inconclusive. The review of meaning was supplementary, and reviewer identity was incomplete. |
| Can publication of the complete batch be observed? | The experimental output has a [publication receipt](../eval/results/triage/structured-planning-v31/final/evidence/publication.json). Root `tickets.json` matches its bytes by SHA-256, but was copied outside the workflow. | The observed publication and checked copy are supported. The root file has no separate workflow receipt. Human approval and reproduction from a clean checkout remain unresolved. |
| Was ticket meaning reviewed separately? | The [all-finding review](../eval/results/triage/structured-planning-v31/final/reviewer-observation.json) reports no failed dimensions. | Acceptance under the required procedure remains inconclusive because required reviewer identity fields were not exposed. |
| Are accounting limits visible? | [Delivery cost evidence](../eval/results/delivery-cost-summary.json) records application sends and provider usage units. Measured tokens give a US$2.350286 estimate at declared public API rates. | Partial: the estimate is reproducible. Actual Copilot billing allocation and hidden HTTP attempts remain unknown. |

The current evidence record is
[`eval\results\README.md`](../eval/results/README.md). Test counts, evaluator
self-tests and AI review do not establish system acceptance.

### Cost interpretation

The retained 21-ticket delivery used 973,468 input and 40,335 output tokens
(US$2.350286 API-equivalent under the declared public rates, not a Copilot
invoice). [Document 04 section 6](04_INFERENCE_LIBRARY.md#6-reproducibility-and-cost-limits)
owns the calculation, cache-aware scenario and billing limits; the underlying
totals and assumptions are retained in the
[delivery cost evidence](../eval/results/delivery-cost-summary.json).

## 9. Current provenance and disclosure

The current policy and configuration were chosen with access to evaluation
evidence. The saved observations therefore do not independently confirm stable
quality. The minimum urgency for high-impact SCE findings protects the supplied
low-L/high-I example. That floor remains a project choice without domain
calibration.
[Document 03 section 6](03_EVALUATION_ACCEPTANCE.md#6-cross-cutting-evidence)
defines the fixed-identity reliability protocol; current evidence does not
establish a clean checkout reproduction or independent reviewer authority.

## 10. Assumptions and limitations

- Inputs represent one selected snapshot; state outside that snapshot is not
  invented.
- A redundancy label does not show that the partner is currently healthy.
- L/I/U are ordinal scales.
- The explicit asymmetric examples take precedence over the domain note's more
  general “closer to maximum” wording where they conflict.
- One trusted local writer and same-volume replacement are assumed.
- Provider labels describe configuration, not hidden model parameters or expertise.
- AI reviews are provisional. Models in the same family may make similar errors.
- API-equivalent cost is calculable from measured tokens; actual provider
  billing and hidden transport attempts remain unknown where the route does not
  expose them.
- A successfully generated draft still requires human approval.
