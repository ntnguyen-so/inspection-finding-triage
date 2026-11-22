# Fail-Closed Triage Workflow

This document explains the workflow and its deterministic controls. The root
artifact is a hash-checked, byte-identical promotion of a published experimental
output. Semantic review remains provisional, and human approval is required.

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

## Module boundary and dependency direction

The workflow does not extract or maintain domain guidance. It asks
`triage_knowledge` for a pinned, validated context bundle and then treats that
bundle as an input contract:

```text
llm_inference  -> one observable model call
triage_knowledge -> one validated knowledge/context bundle
                         |
                         v
triage -> assessment orchestration, policy, attempts and atomic publication
```

This separation allows knowledge sources, extraction and retrieval to evolve
without changing batch orchestration. It also lets workflow tests inject a fixed
context contract without exercising the knowledge store. The reverse dependency
is prohibited: knowledge tooling does not publish tickets, choose urgency or
consume evaluator answers.

**Rejected alternative.** Putting retrieval inside the workflow would make
source maintenance and operational execution one permission surface. A change to
PSV guidance could then require editing orchestration code, while a workflow
developer could silently alter the knowledge authority.

## 1. Workflow question

The Candidate Brief requires more than generating 21 JSON objects. The system
must explain what happens when output is malformed, structurally invalid,
semantically wrong or impossible to support. It must also document how knowledge
reaches assessment, derive urgency in code and defer to a human.

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
bindings. Loading or compatibility failure occurs before provider dispatch.

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

The prompt instructs the model to treat supplied observations as evidence rather
than instructions. The route places that prompt as a replace-mode system message
and records the separation as requested rather than proving raw provider
equivalence. A knowledge change that overlaps interpretation embedded in the
active prompt therefore requires focused prompt-compatibility review before
activation; it is not assumed to override prompt wording.

Prompt changes therefore follow the controlled-change boundary. Each removed
clause needs a destination, provenance and focused regression evidence.
Code/schema duplication is removed only after deterministic enforcement and
behavioral preservation are demonstrated. A shorter prompt is not promoted
merely because it is easier to maintain or cheaper to send. This gate applies
to future changes; the current prompt remains a disclosed compatibility surface.

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

### Why one repair

One repair is sufficient to test whether explicit feedback corrects an output
fault while keeping the maximum batch budget finite. More retries would increase
cost and create optional stopping; zero repair would discard observed cases where
the same model corrected malformed JSON or a schema violation.

The two-attempt limit is a project policy, not a Falkor requirement.

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
when `L > I`. The 0.7 weight is a candidate interpretation, not calibrated risk
mathematics.

| L / I | Chosen base | Interpretation |
|---|---:|---|
| 1 / 1 | 1 | Low/low remains low |
| 10 / 1 | 4 | Frequent low-consequence issue does not become maximum urgency |
| 1 / 10 | 8 | Rare catastrophic consequence still receives prompt attention |
| 10 / 10 | 10 | High/high reaches the ceiling |

Supplied overrides require confirmed facts. Candidate-owned precautions and
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

Every assessment receives the selected finding, complete bounded registry,
engineer comments, related evidence and the active source-faithful knowledge
release. Production code independently rebuilds and hash-checks the context
before dispatch. Evaluation cards, expected answers and reviewer judgments are
excluded.

Full bounded context was chosen because the supplied corpus is small and
relationship-heavy. This avoids unsupported top-k assumptions, but it has a
measured token cost and does not prove that the model used every relevant item.
The bounded knowledge-influence experiment supports one declared synthetic
positive and negative-control scope; it is not production domain certification.

## 6. Complete-batch publication

The public wrapper must contain exactly one ticket for every input finding.
Publication occurs only after batch-level identity and coverage validation. A
temporary file is flushed and atomically substituted on the same volume; if
replacement fails, old bytes remain.

**Rationale.** A partial file could be mistaken for the complete planning
package and hide which findings failed.

**Rejected alternative.** Publishing valid tickets while dropping one failed
finding optimizes availability at the cost of silent incompleteness.

This choice has a real trade-off: whole-batch generation is fragile and can
waste completed work. Hash-pinned per-finding resume is future work, but it must
not weaken final all-or-nothing publication.

## 7. Deferral and human authority

There are three valid outcomes:

1. a supported draft;
2. a supported draft with a specific additional check; or
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

| Design hypothesis | Current evidence | Interpretation and remaining limit |
|---|---|---|
| Deterministic controls remain outside the model | Fault and behavior tests cover schema, identity, bounded repair, exhaustion, urgency and atomic publication. | **Pass for tested control behavior.** Formula behavior is not calibrated risk truth. |
| Knowledge reaches assessment without becoming policy | Captured provider-bound context and a bounded positive/negative comparison exercise the boundary. | **Pass for inspected delivery paths; inconclusive for broad causal use.** The evidence is not domain certification. |
| Fixed-identity comparison exposes decision drift | The current X01 comparison preserves operational routing while disclosing numeric and rule-trace drift. | **Inconclusive for full X01 acceptance.** Its semantic observations use a supplementary procedure and lack complete reviewer identity. |
| Complete-batch publication is observable | The experimental 21-ticket output has a verified publication receipt; root `tickets.json` is byte-identical by SHA-256 but was promoted outside the workflow. | **Pass for the observed experimental publication and hash-checked promotion.** The root file has no separate workflow receipt; human approval remains required and clean-checkout reproduction is unresolved. |
| Semantic quality is reviewed separately | The retained all-finding review reports no failed dimensions. | **Inconclusive for protocol-conformant acceptance.** Required reviewer identity fields were not exposed. |
| Accounting limits remain visible | Retained evidence exposes application sends, latency and provider metering. Measured input/output tokens produce a US$2.350286 API-equivalent estimate for the retained delivery under declared public rates. | **Partial.** The estimate is reproducible; actual Copilot billing allocation and hidden HTTP attempts remain unknown. |

The evidence authority is `eval\results\README.md`. Test counts, evaluator
self-tests and AI review are never presented as equivalent to system acceptance.

### Cost interpretation

The retained 21-ticket delivery used 973,468 input and 40,335 output tokens in
21 application sends. Applying the declared OpenAI Standard short-context rates
of US$2 per million input tokens and US$10 per million output tokens gives:

```text
(973,468 * 2 + 40,335 * 10) / 1,000,000 = US$2.350286
```

This is a measured, reproducible API-equivalent cost proxy, approximately
US$0.111918 per generated ticket. It is not the Copilot subscription's billed
cost: the route does not expose its AI-unit-to-USD conversion or hidden HTTP
attempts. The receipt separately reports 21 request-cost units and 249.31861 AI
units. Its cache fields and catalog schedule also support a cache-aware
OpenAI-equivalent scenario of US$2.493186, but that remains a pricing scenario,
not a Copilot invoice. The workflow retains raw usage with `usd_cost=null`; the
equivalent figures are explicit calculations over that evidence rather than
runtime billing fields. The
[delivery cost evidence](..\eval\results\delivery-cost-summary.json) records the
source-run hash, measured totals, formula assumptions and the official
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) source.
Document 04 owns the detailed provider/accounting rationale.

## 9. Current provenance and disclosure

The current policy and configuration are informed by exposed evaluation
evidence, so the retained observations are not independent confirmation of
stable quality. The high-impact SCE urgency floor protects the supplied
low-L/high-I corner and remains candidate-owned and uncalibrated. Document 03
§6 defines the fixed-identity reliability protocol; current evidence does not
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
