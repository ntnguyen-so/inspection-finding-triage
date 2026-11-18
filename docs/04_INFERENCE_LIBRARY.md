# Inference Boundary and Provider Control

> **Document status:** current component design with historical observations.
> Provider transport success is not ticket-quality acceptance.

## Abstract

The inference component has one narrow responsibility: send a fully constructed,
hash-identified assessment request to an explicitly selected provider route and
return an observable response or failure. It does not own ticket policy, urgency,
workflow retries, publication or semantic acceptance.

This boundary follows the Candidate Brief’s permission to use provider SDKs while
requiring candidate-owned orchestration. It also responds to an empirical
constraint: real providers returned malformed JSON, schema violations, token
exhaustion and timeouts. Provider structured output is therefore a useful first
line, not a trust boundary.

There was also a practical economic reason to make inference replaceable. The
candidate already had a GitHub Copilot CLI subscription that exposed the coding
models used during development without a separately visible per-call API charge.
Using that entitlement made repeated development probes materially cheaper than
funding every iteration through a separately billed OpenAI or Azure route. The
module prevents that cost choice from becoming workflow architecture.

## 1. Why this component exists

The workflow needs probabilistic interpretation, but provider APIs differ in
configuration, schema support, usage reporting, retry behavior and receipt
visibility. Without an explicit adapter boundary, these differences leak into
ticket policy and make one run difficult to reproduce.

The separate module therefore serves two purposes:

1. **Engineering isolation:** provider transport cannot own triage policy,
   retries, urgency or publication.
2. **Economic portability:** development can use an already-paid Copilot
   entitlement, while a stricter or separately billed route can be selected when
   attempt visibility, reproducibility or delivery policy requires it.

The component answers four questions:

1. What exact request crossed the provider boundary?
2. Which route, model and settings were selected?
3. What did the provider expose about response, usage and latency?
4. Which failures belong to transport, structure or application policy?

It does **not** answer whether L/I are defensible or whether a maintenance action
is operationally correct.

## 2. Candidate Brief trace

| Brief expectation | Inference design response |
|---|---|
| Provider SDKs permitted; orchestration frameworks prohibited | Thin adapters call inference endpoints; workflow and policy remain repository-owned |
| Malformed and structurally invalid output handled explicitly | Provider response is parsed and locally revalidated; error class remains visible |
| One reproducible command and low cost | Route/model/settings and exposed usage are captured; unknown retries or price remain unknown |
| Reproducible model instructions | The workflow supplies a versioned, hash-pinned packaged prompt artifact; the adapter records the transmitted system hash |
| Human deferral | Refusal, timeout or exhausted output budget returns failure; the adapter does not invent a fallback ticket |

The strict interpretation of observable attempts is a candidate-owned policy,
not wording supplied by Falkor.

## 3. Design decisions

### Decision 1 — Keep the adapter smaller than the workflow

**Decision.** The adapter accepts explicit messages, schema and provider
configuration, performs one observable inference call, and returns response
content plus exposed metadata.

**Rationale.** Ticket identity, assessment repair, urgency and publication are
application concerns. Keeping them outside the adapter makes the model/code
boundary reviewable and prevents provider behavior from silently changing
business policy.

**Rejected alternative.** A provider-specific agent that loops, repairs and
publishes would duplicate orchestration and make attempt accounting route
dependent.

### Decision 2 — Separate the economical development route from the strict route

**Decision.** Use the existing Copilot CLI entitlement for bounded development
experiments, but keep the same application contract portable to direct Azure or
another supported provider. Route identity is part of every observation.

**Rationale.** The subscription reduced the candidate's marginal cash cost and
made it practical to probe multiple models and failure modes. A dedicated
inference module preserved the option to move to direct Azure when the study
needed disabled SDK retries, explicit ledgers and provider usage fields.

**Rejected alternative.** Coding directly against one separately billed
provider would couple experimentation cost and vendor behavior to the workflow.
Coding directly against Copilot would make the included subscription route look
like a universal deployment assumption.

**Cost boundary.** “Included in an existing subscription” does not mean zero
economic cost or reproducible USD cost. Subscription price, quotas, hidden
transport attempts and provider allocation are not exposed per run. Another
reviewer may not have the same entitlement. Copilot observations therefore
remain development evidence unless the route is explicitly frozen and its
accounting limitations accepted.

### Decision 3 — Require explicit route and model configuration

**Decision.** Provider route, model/deployment and settings are pinned in run
configuration. There is no automatic model fallback inside a run.

**Rationale.** Model name alone does not identify behavior. Copilot and direct
Azure expose different controls, retries, receipts and cost information.
Switching routes after failure would create a different experiment while
presenting it as one run.

**Rejected alternative.** Environment-driven implicit defaults and automatic
fallback optimize for completion but weaken provenance and comparability.

### Decision 4 — Revalidate locally even when native schema is available

**Decision.** Use provider-native strict structure where available, then parse
and validate the returned bytes again in application code.

**Rationale.** The provider can reduce formatting errors but cannot enforce
repository-specific identity, quotation, coverage or semantic rules. Local
validation provides one route-independent contract.

**Rejected alternative.** Trusting a provider “structured output” success flag
would confuse transport acceptance with application correctness.

### Decision 5 — Do not hide application retries in the adapter

**Decision.** One adapter invocation represents one application send. The
workflow decides whether a classified error receives its single permitted
repair.

**Rationale.** The brief asks for failure behavior. That behavior is auditable
only when attempt ownership and budget are explicit.

**Rejected alternative.** Silent repair or unbounded retry in the provider layer
could turn repeated failures into a success-shaped response and invalidate cost
accounting.

### Decision 6 — Sanitize evidence without claiming wire-level proof

**Decision.** Retain hashes, timing, exposed usage, response state and sanitized
receipts; never persist credentials.

**Rationale.** Reviewers need enough information to identify and compare runs,
but logs must not leak secrets. Provider receipts are supporting provenance, not
proof of hidden SDK or transport behavior.

**Rejected alternative.** Capturing entire environments or authorization
headers would create security risk without establishing semantic correctness.

## 4. Failure classification

| Failure | Adapter responsibility | Workflow consequence |
|---|---|---|
| Authentication/configuration | Return explicit terminal diagnostic | No ticket, no publication |
| Timeout/refusal/transport failure | Return visible provider failure | Governed by declared run policy; never a guessed draft |
| Malformed JSON | Preserve response and parse error | May receive one budgeted application repair |
| Schema violation | Preserve structured validation errors | May receive one budgeted application repair |
| Valid but unsupported assessment | Not decided by adapter | Application contradiction checks, offline review and human approval |
| Hidden provider retry count | Record as unknown | SDK-inclusive attempt claim is inconclusive |

This separation matters because the same outward “no ticket” can have different
causes and different evidence value.

## 5. Evidence and observed behavior

The retained evidence index is `eval\results\README.md`. Relevant observations
include:

| Observation | Result | Highest defensible claim |
|---|---|---|
| Inference/provider component tests | Deterministic paths passed in retained runs | Adapter behavior passed its tested fixtures |
| Pre-v8 policy-v5 Copilot all-21 run at `235bdd1` | Four first-attempt output faults were repaired; 21 contract-valid drafts produced | Bounded repair handled observed faults on that route/version |
| Pre-v8 Copilot X01 run | One finding returned malformed JSON twice; batch failed closed | Exhausted malformed output did not masquerade as success |
| Later pre-v8 gpt-6 X01 pair at `4debeba` | Both 13-ticket outputs were contract-valid; semantic reviews were 38/39 `needs_review` and 37/39 `fail` | Matching-model X01 failed; the all-21 63/63 artifact did not establish stability |
| Direct Azure v5 | 21 contract-valid drafts in 24 requests; semantic review failed 60/63 | Structural completion did not establish ticket quality |
| Azure v6 | Failed after 19 validated findings; no publication | Timeout/failure remained visible |

These are route- and version-specific observations. They are not a provider
benchmark, proof of model quality or evidence that Copilot satisfies the strict
Azure delivery policy.

## 6. Reproducibility and cost limits

Direct Azure was selected for the strict delivery route because the application
can disable SDK/transport retries and retain an explicit ledger. Copilot was
selected for much of development because its models were already included in the
candidate's CLI subscription and did not create a separately visible API bill.
That made iteration economical, but Copilot does not expose all HTTP attempts,
per-run subscription allocation or a verified USD tariff in the retained
records.

The Azure v5 observation records 1,289,873 prompt tokens, 45,878 completion
tokens and 16,474 reasoning tokens. USD cost is unknown because the deployment
tariff was not captured. Unknown is not reported as zero, and this observation
does not yet prove the brief’s low-cost reproducibility expectation.

## 7. Assumptions and limitations

- Provider SDK behavior is observable only to the extent exposed by the route.
- The candidate's existing Copilot entitlement is a personal development
  constraint, not an availability or pricing assumption for reviewers.
- Account isolation, caches and hidden transport retries are not inferred from a
  model label.
- A response hash proves byte identity of the retained response, not how hidden
  model weights produced it.
- Strict schema reduces formatting risk but cannot certify engineering judgment.
- Restricted-session or CLI-mediated experiments are development routes unless
  explicitly accepted and frozen as delivery configuration.

The chronological adapter experiments, superseded proposals and probe diaries
are preserved in
`docs\original-decision-process\04_INFERENCE_LIBRARY.md`. Current system-level
responsibility remains in `DESIGN.md`; measured run outcomes remain in
`eval\results`.
