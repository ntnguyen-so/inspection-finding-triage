# Fail-Closed Triage Workflow

> **Document status:** current workflow rationale. Deterministic controls are
> implemented and tested; semantic quality and final delivery remain unresolved.

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
  -> revalidate exact 21-ticket coverage
  -> atomically replace tickets.json
```

Any terminal finding failure stops the batch. The previous output remains
unchanged.

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

Recoverable malformed or structural errors may receive one further application
attempt using the same pinned context, the rejected draft and bounded diagnostic
feedback. Semantic uncertainty is not repaired by silently changing a score.
When both attempts fail, the application exits nonzero and publishes nothing.

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
The B02 influence experiment remains failed/inconclusive.

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

The current retained Copilot artifact sets `review_required` on all 21 tickets
and places 19 at urgency 7-9. That is honest evidence of weak discrimination,
not a success metric. `R-SCE` guarantees targeted review for every SCE, so the
flag currently adds little beyond global human approval. F-1016 (an illegible
tag on a recently recertified PSV) and F-1019 (loose cladding with no process
concern) are the concrete weekly-routing cases to challenge. The next experiment
should retain global approval but reserve `review_required` for a specific
additional check and recalibrate impact anchors on those lower-consequence cases.

## 8. Evidence status

| Area | Retained observation | Status |
|---|---|---|
| Schema, identity, bounded repair, exhaustion and atomic publication | Deterministic fault and behavior demonstrations | **D-pass** for stated control behavior |
| Urgency range, monotonicity, corners and fact-state rules | Regression and 100-cell grid checks | **D-pass** for implemented policy; not calibrated truth |
| Knowledge/context delivery | Captured provider-bound context and source integration checks | **D-pass** for delivery; influence unproven |
| Pre-v8 policy-v5 Copilot all-21 at `235bdd1` | One gpt-6 batch reviewed 63/63 | **Provisional**, selected and non-eligible |
| Later pre-v8 gpt-6 X01 pair at `4debeba` | Both generations completed; semantic reviews were 38/39 and 37/39 | **Fail**; matching-model stability gate not closed |
| Later gpt-6.1 all-21 | First run failed; retry failed two AI-only reviews at 60/63 | **Fail**, contradicting stable-quality claims |
| Strict Azure delivery | Latest applicable route failed closed | **Fail/pending**; no accepted root output |
| Human/domain certification | Not performed | **Not run** |

The evidence authority is `eval\results\README.md`. Test counts, evaluator
self-tests and AI review are never presented as equivalent to system acceptance.

## 9. Material evolution and disclosure

The workflow evolved through multiple policies after observed failures. Some
changes were generic reliability controls; others were test-informed. The
current v8 direction retains bounded attempts, code-owned urgency and
fail-closed publication while withdrawing case-shaped planning rules.

The high-impact SCE urgency floor remains explicitly test-informed: an observed
development repeat changed one finding from weekly to monthly routing, and the
floor was added to protect the supplied low-L/high-I corner. This provenance is
why the policy is labelled candidate-owned and uncalibrated.

Pre-freeze `v8verify-*` and `v8r1` observations cannot become measured v8
reliability evidence after the fact. The prospective measurement authority is
`docs\07_VERSION_RELIABILITY_PROTOCOL.md`.

## 10. Assumptions and limitations

- Inputs represent one selected snapshot; later field state is not invented.
- Redundancy labels do not establish current partner health.
- L/I/U are ordinal scales.
- The explicit asymmetric examples take precedence over the domain note's more
  general “closer to maximum” wording where they conflict.
- One trusted local writer and same-volume replacement are assumed.
- Provider labels expose configuration, not hidden weights or expertise.
- AI reviewers are provisional and may share model-family failure modes.
- Cost and transport attempts remain unknown where the route does not expose
  them.
- A successful draft still requires human approval.

The exact development chronology, policy versions, failed runs, withdrawn
proposals and handoffs are preserved in
`docs\original-decision-process\05_TRIAGE_WORKFLOW.md`. They explain how the
design evolved but do not override current code, configuration or evidence.
