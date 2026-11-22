# Inference Boundary and Provider Control

The inference boundary isolates provider transport from ticket policy. A
successful provider call establishes transport behavior, not ticket quality.

## Abstract

The inference component has one narrow responsibility: send a fully constructed,
hash-identified assessment request to an explicitly selected provider route and
return an observable response or failure. It does not own ticket policy, urgency,
workflow retries, publication or semantic acceptance.

The brief permits provider SDKs but requires repository-owned orchestration. The
boundary also responds to an empirical
constraint: real providers returned malformed JSON, schema violations, token
exhaustion and timeouts. Provider structured output is therefore a useful first
line, not a trust boundary.

There was also a practical economic reason to make inference replaceable. An
existing GitHub Copilot CLI subscription exposed the coding models used during
development without a separately visible per-call API charge. Using that
entitlement made repeated probes materially cheaper than funding every iteration
through a separately billed OpenAI or Azure route. The module prevents that
cost choice from becoming workflow architecture.

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

## 2. Requirements mapped to inference design

| Brief expectation | Inference design response |
|---|---|
| Provider SDKs permitted; orchestration frameworks prohibited | Thin adapters call inference endpoints; workflow and policy remain repository-owned |
| Malformed and structurally invalid output handled explicitly | Provider response is parsed and locally revalidated; error class remains visible |
| One reproducible command and low cost | Route/model/settings and exposed usage are captured; API-equivalent cost is calculable while hidden retries and Copilot billing conversion remain unknown |
| Reproducible model instructions | The workflow supplies an exact, hash-pinned packaged prompt artifact; the adapter records the transmitted system hash |
| Human deferral | Refusal, timeout or exhausted output budget returns failure; the adapter does not invent a fallback ticket |

The strict interpretation of observable attempts is a project-defined policy,
not a requirement stated by the brief.

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

### Decision 2 — Separate route economics from acceptance authority

**Decision.** Use the existing Copilot CLI entitlement for bounded development
and delivery experiments, while keeping the same application contract portable
to direct Azure or another supported provider. Route identity is part of every
observation; no provider is accepted merely because it completes a batch.

**Rationale.** The subscription reduced marginal development cost and made it
practical to probe multiple models and failure modes. A dedicated
inference module preserved direct Azure as a comparison route with disabled SDK
retries, explicit ledgers and provider usage fields. Azure observations exposed
useful transport/accounting differences, but their retained semantic and
completion results did not justify replacing the promoted Copilot artifact.

**Rejected alternative.** Coding directly against one separately billed
provider would couple experimentation cost and vendor behavior to the workflow.
Coding directly against Copilot would make the included subscription route look
like a universal deployment assumption.

**Cost boundary.** “Included in an existing subscription” does not mean zero
economic cost or measured API spend. Copilot receipts expose request-cost units,
AI-unit metering and token/cache counts. They do not expose the subscription's
AI-unit-to-USD conversion, hidden transport attempts or an actual per-run USD
charge. Token counts can support a declared API-equivalent estimate, but not a
claim about Copilot billing.

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

## 5. Current assessment of the inference design

The evidence below assesses whether the design decisions expose the intended
failure modes. It does not establish a provider benchmark. Detailed artifacts
and current status remain in
`eval\results\README.md`.

| Design hypothesis | Current evidence | Assessment and remaining limit |
|---|---|---|
| Native structured output still requires local validation and bounded repair | Real calls produced malformed JSON and schema faults; bounded repair recovered some responses, while an exhausted fault failed the batch without publication. | **Supported.** The boundary exposed recoverable and terminal failures, but hidden provider attempts remain unknown. |
| Route completion must remain separate from semantic acceptance | Both provider routes produced structurally valid batches, while one completed Azure batch failed semantic review and the promoted Copilot delivery required a separate review. | **Supported.** Transport success is not evidence of ticket quality. |
| Provider choice must not become workflow policy | Current retained observations cover Copilot and direct Azure routes under the same application contract. | **Supported.** Urgency and publication policy remain outside both adapters; route completion does not establish equivalent behavior. |
| Cross-setup comparison must not be presented as fixed-identity reproduction | The all-21 comparison used current code with a different activation and execution-policy identity from the retained delivery. It preserved review routing for every ticket and L/I/U for 19 tickets, but changed every ticket's text. | **Bounded observation only.** It is neither X01 evidence nor clean reproduction, and the differences mix model variability with setup changes. |

The comparison encountered preflight failures before provider dispatch and its
successful artifact received no semantic review. It therefore cannot replace or
strengthen the retained ticket-quality result. Its evidence is indexed in
`eval\results\README.md`.

## 6. Reproducibility and cost limits

Direct Azure was evaluated as the stricter accounting route because the
application can disable SDK/transport retries and retain an explicit ledger. It
did not produce the promoted root artifact: both that artifact and the
cross-setup comparison used Copilot. This establishes route provenance, not a
strict attempt contract; provider-hidden attempts remain unknown.

Cost is reported in three distinct layers:

| Cost view | Retained delivery | Defensible claim |
|---|---:|---|
| Measured usage | 973,468 input; 40,335 output tokens | Receipt-backed usage |
| Simple API-equivalent repricing | US$2.350286 | Reproducible estimate under declared rates |
| Copilot metering | 21 request-cost units; 249.31861 AI units | Receipt-backed units without an exposed USD conversion |
| Actual Copilot USD allocation | Unknown | Not exposed by the subscription route |

The retained totals, source-run SHA-256, assumptions and calculations are
available in the compact
[delivery cost evidence](..\eval\results\delivery-cost-summary.json), which is
derived only from per-send receipt usage rather than duplicated accounting
checkpoints.

The equivalent calculation is
`input_tokens * US$2 / 1,000,000 + output_tokens * US$10 / 1,000,000`,
using the configured model's OpenAI Standard short-context rates published at
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) and checked
on 2026-11-18.
The production workflow records raw usage and leaves `usd_cost` null; it does not
calculate this proxy. The repository's controlled-experiment helper implements
the same rate formula, which is applied transparently to the retained run
receipts. The simple estimate deliberately ignores cache adjustments so that
it depends only on the measured input/output totals named in the formula.

The retained receipt also exposes 143,251 cache-read tokens, 830,154 cache-write
tokens and a model-catalog schedule whose unit ratios match the public
short-context rates for ordinary input, cached input, 30-minute cache writes and
output. Applying that schedule gives a cache-aware OpenAI-equivalent scenario of
US$2.493186 and reproduces the reported 249.31861 AI units after the documented
unit scaling. This stronger scenario is still not an invoice: Copilot does not
expose an AI-unit-to-USD conversion or establish that subscription allocation
equals public API billing.

The retained delivery estimate consists of US$1.946936 input and US$0.403350
output, approximately US$0.111918 per ticket. Input accounts for about 82.8% of
this proxy, making bounded-context size the clearest cost-optimization surface.

These estimates should be reported, not hidden under “unknown cost.” They remain
API-equivalent planning values rather than Copilot invoices. Copilot does not
expose hidden transport attempts. Direct Azure exposes attempts and tokens, but
the retained observations do not include a deployment tariff. Metering and
pricing assumptions are indexed in `eval\results\README.md`.

## 7. Assumptions and limitations

- Provider SDK behavior is observable only to the extent exposed by the route.
- The existing Copilot entitlement is a development constraint, not a general
  availability or pricing assumption.
- Account isolation, caches and hidden transport retries are not inferred from a
  model label.
- A response hash proves byte identity of the retained response, not how hidden
  model weights produced it.
- Strict schema reduces formatting risk but cannot certify engineering judgment.
- Restricted-session or CLI-mediated experiments are development routes unless
  explicitly accepted and frozen as delivery configuration.

Current system-level responsibility remains in `DESIGN.md`; measured run
outcomes remain in `eval\results`.
