# Inference Boundary and Provider Control

The inference component sends requests to a model provider. It keeps that
communication separate from the rules for tickets. A successful model call
shows that communication worked. It does not show that the ticket is correct.

## Abstract

The component sends a complete assessment request through a provider route
selected in the run configuration. A route is the way the application reaches
the provider, such as Copilot CLI or direct Azure. A hash identifies the exact
request bytes. The component returns the response or reports failure.

Other code owns ticket rules, urgency, retries, publication and review of the
response's meaning. The brief allows provider SDKs (software libraries for
calling providers), but requires this repository to control the workflow.

Real calls returned invalid JSON, responses that broke the required structure,
responses that ran out of output tokens, and timeouts. Tokens are the units of
text a model reads and generates. Provider features for
structured output help prevent some errors. The application must still check
the result.

The component is also replaceable for cost reasons. An existing GitHub Copilot
CLI subscription gave development access to several models without a separately
visible charge for each call. This made it practical to try models and failure
cases. Copilot did not expose the run's share of the subscription cost in USD.
The evidence therefore shows a different funding route, not a measured saving.
Keeping provider calls in this module prevents that funding choice from
controlling the rest of the workflow.

## 1. Why this component exists

The workflow needs a model to interpret evidence. Providers differ in settings,
supported response structures, usage reports, retries and request records.
An **adapter** is the small piece of code that handles these provider-specific
differences. Without separate adapters, those differences could change ticket
rules and make runs harder to reproduce.

The separate module therefore serves two purposes:

1. **Separate responsibilities:** provider communication cannot control triage
   rules, workflow retries, urgency or publication.
2. **Allow a different funding route:** development can use an existing Copilot
   subscription. A stricter or separately billed route can be selected when the
   run needs better attempt records or different delivery controls.

The component answers four questions:

1. What exact request crossed the provider boundary?
2. Which route, model and settings were selected?
3. What did the provider report about the response, usage and elapsed time?
4. Which failures belong to transport, structure or application policy?

It does **not** decide whether evidence supports the likelihood and impact
scores, or whether a maintenance action is correct.

In this document:

- **L/I/U** mean likelihood, impact and urgency calculated by code;
- a **schema** defines the required response fields, types and limits;
- a **receipt** is a provider record of a request, response, usage and elapsed
  time, with secrets removed. It does not prove what happened inside the
  provider's communication layer;
- **request-cost units** and **AI units** are provider-exposed Copilot metering
  fields; neither has an exposed subscription USD conversion; and
- the **promoted artifact** is root
  [`tickets.json`](../tickets.json), which is byte-identical by SHA-256 to the
  final `structured-planning-v31` Copilot run output. SHA-256 is the hash used to
  check that the bytes match. The file was copied to root after review. A second
  workflow run did not generate it there.

## 2. Requirements mapped to inference design

| Brief expectation | Inference design response |
|---|---|
| Provider SDKs permitted; orchestration frameworks prohibited | Small adapters call model endpoints; repository code controls the workflow and rules |
| Malformed and structurally invalid output handled explicitly | Application code parses and checks the response again, and records the error type |
| One reproducible command and low cost | Run records include route, model, settings and reported usage. Declared API rates allow a cost estimate; hidden retries and Copilot's USD conversion remain unknown |
| Reproducible model instructions | The workflow supplies a packaged prompt identified by its exact hash; the adapter records the hash of the system message sent |
| Human deferral | Refusal, timeout or exhausted output budget returns failure; the adapter does not invent a replacement ticket |

The project requires strict records of attempts. The brief does not state that
stricter rule.

## 3. Design decisions

### 3.1 Keep the adapter smaller than the workflow

The adapter receives messages, a schema, and
provider settings. It makes one call visible to the application, then returns
the response and the metadata the provider exposes.

Application code checks ticket identity, repairs eligible assessment errors,
calculates urgency and publishes output. Keeping these tasks outside the adapter
makes responsibilities easy to inspect. Provider behavior cannot silently change
ticket policy.

We rejected a provider-specific agent that repeats calls, repairs responses and
publishes tickets. It would duplicate the workflow and make attempt counting
depend on the provider route.

### 3.2 Separate route economics from acceptance authority

The existing Copilot CLI subscription supports limited development and delivery
experiments. The same application contract can also use direct Azure or another
supported provider. Each observation names its route. A completed batch alone
does not show that the route meets acceptance requirements.

The subscription avoided separately visible charges for development calls.
The separate inference module also kept direct Azure available for comparison.
On that route, SDK retries were disabled and the application retained an explicit
attempt ledger and provider usage fields. The Azure runs showed useful
communication and accounting differences. The completed Azure batch did not
receive a review of its meaning and did not replace the Copilot delivery.

The promoted file came from the Copilot `copilot_experiment` route. Its SHA-256
matched the reviewed output. That proves which retained file was delivered; it
does not reveal Copilot's hidden communication attempts or establish compliance
with the strict attempt limit.

We rejected tying workflow code directly to one separately billed provider.
That would tie both experiment cost and workflow behavior to a vendor. Tying it
directly to Copilot would instead assume that every deployment has the same
subscription access.

“Included in an existing subscription” does not mean zero cost or measured API
spend. Copilot receipts report request-cost units, AI units and token/cache
counts. They do not report a USD conversion, hidden attempts or a USD charge for
the run. Token counts support an estimate at declared API rates, not a claim
about the Copilot bill.

### 3.3 Require explicit route and model configuration

Run configuration fixes the route, model or deployment, and settings. A run
does not automatically switch to another model after failure.

A model name alone does not describe run behavior. Copilot and direct Azure
expose different controls, retries, receipts and cost information. Switching
routes after failure would mix two experiments while calling them one run.

We rejected unrecorded defaults taken from the environment and automatic
fallback. They might help finish a batch, but would make its history and
comparisons less reliable.

### 3.4 Revalidate locally even when native schema is available

Where supported, the provider is asked to enforce the response structure.
Application code still parses and checks the returned bytes.

The provider can reduce formatting errors. It cannot enforce this repository's
rules for identity, quotations, coverage or meaning. Local checks give both
routes the same application contract.

We rejected trusting a provider's “structured output” success flag alone.
A provider accepting a response does not make that response correct for triage.

### 3.5 Do not hide application retries in the adapter

One adapter call represents one application send. The workflow identifies the
error type and decides whether it may use the single allowed repair.

To inspect failures, we need to know which component owns retries and what
attempt limit applies.

We rejected hidden repair and unlimited provider retries. They could hide
repeated failures behind a successful response and make cost records incomplete.

### 3.6 Sanitize evidence without claiming wire-level proof

Run evidence keeps hashes, timing, reported usage, response status and receipts
with secrets removed. It never keeps credentials.

These fields identify runs and support comparison. Provider receipts help trace
a run's history, but do not prove hidden SDK or communication behavior.

We rejected capturing whole environments or authorization headers. That would
expose secrets without showing whether an assessment was correct.

## 4. Failure classification

| Failure | Adapter responsibility | Workflow consequence |
|---|---|---|
| Authentication/configuration | Report an explicit terminal error | No ticket, no publication |
| Timeout/refusal/communication failure | Report the provider failure | Follow declared run policy; never guess a draft |
| Malformed JSON | Keep the response and parsing error | May receive one application repair within the attempt budget |
| Schema violation | Keep errors from checking response structure | May receive one application repair within the attempt budget |
| Valid structure but unsupported assessment | Adapter does not decide this | Application contradiction checks, offline review and human approval |
| Hidden provider retry count | Record as unknown | Cannot establish a limit that includes SDK retries |

Several failures can all result in “no ticket”. Recording the cause tells a
reviewer what failed and what the observation can support.

## 5. Current assessment of the inference design

The evidence below checks whether the design makes failures visible as intended.
It is not a benchmark of provider quality. Detailed records and current status
remain in
[`eval\results\README.md`](../eval/results/README.md).

| Design question | Current evidence | Assessment and remaining limit |
|---|---|---|
| Does provider-structured output still need local checks and limited repair? | Real calls returned invalid JSON and structural errors. Repair recovered some responses. An error that exhausted the budget stopped the batch without publication. | **Supported.** Recoverable and terminal failures were visible. Hidden provider attempts remain unknown. |
| Must route completion remain separate from acceptance of ticket meaning? | Both routes produced valid batch structures. The completed Azure batch had no review of meaning. The promoted Copilot file had a separate AI-only review: 63/63 applicable dimensions and six exceptional-review routes. That review deviated from the required procedure. | **Supported.** Successful communication does not prove ticket quality. The Copilot result remains provisional, not domain-certified. |
| Can provider choice stay separate from workflow rules? | Saved observations cover Copilot and direct Azure under the same application contract. | **Supported.** Both adapters leave urgency and publication to application code. Completing both routes does not prove equivalent behavior. |
| Can a comparison with a different setup count as exact reproduction? | The all-21 comparison used current code, but different prompt/knowledge activation and run-policy settings from the saved delivery. Every ticket kept its review routing; 19 kept L/I/U. Every ticket's text changed. | **Limited observation only.** This is neither X01 decision-stability evidence nor clean reproduction. Model variation and setup changes are mixed. |

The comparison first failed checks before any request reached the provider.
Its later successful output received no review of meaning. It therefore cannot
replace or strengthen the retained ticket-quality result. Its evidence is listed in
[`eval\results\README.md`](../eval/results/README.md).

The promoted Copilot review is retained in
[`reviewer-observation.json`](../eval/results/triage/structured-planning-v31/final/reviewer-observation.json).

### 5.1 Models tried during development

The Candidate Brief allows any model/provider. It does not require a multi-model
benchmark. We tried alternatives as an additional development step, to exercise
structured output, recovery and ticket generation.

The table shows representative recorded attempts, not every run or a ranking.
The model names come from saved observations, not folder names or catalog
availability. In particular, `gpt-chat-latest` is a reported alias, not a pinned
backend version. The folder named `native-strict-model53` does not establish
that its backend was a specific GPT-5.3 version.

| Recorded generation model | Route and trial | Application sends | Observed outcome | Evidence |
|---|---|---:|---|---|
| `o4-mini-2025-04-16` | Azure native structured output; an early development attempt | 2 | Failed with a nonzero exit and no validated output. No semantic review. | [S1](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/native-strict-o4/development-1/observation.json) |
| `gpt-chat-latest` | Azure native structured output; development batch | 16 | Output structure passed. The subsequent AI semantic review failed under reference 1.2. | [S2](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/native-strict-model53/development-1/observation.json), [review](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/native-strict-model53/review-1/report.json) |
| `gpt-5.1-codex-max` | Azure native structured output; a later development attempt | 15 | Output structure passed. The subsequent AI semantic review failed under reference 1.2. | [S3](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/native-strict-codex/development-4/observation.json), [review](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/native-strict-codex/review-1/report.json) |
| `gpt-6-sol` | Copilot; all 21 findings, medium reasoning | 25 | 21 structurally valid tickets. Four sends failed. AI review recorded a provisional 63/63 result for this artifact. | [S4](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/copilot-gpt6-current-all21/observation.json) |
| `gpt-6.1-sol` | Copilot; earlier policy-v5 all-21 trial, medium reasoning | 21 | 21 tickets. AI review recorded 62/63 passing dimensions; one planning dimension failed. | [S5](https://github.com/ntnguyen-so/inspection-finding-triage/blob/071d29e62be419bb7443a6e18bf55d2763d46e69/eval/results/triage/copilot-gpt61-policy-v5-all21/observation.json) |
| `gpt-6.1-sol` | Copilot; later retained delivery, medium reasoning | 21 | 21 published tickets. The exact artifact received a provisional 63/63 AI review, with the disclosed reviewer-protocol limits. | [Delivery](../eval/results/triage/structured-planning-v31/final/reviewer-observation.json) |
| `gpt-6.1-sol-2026-09-29` | Azure; later same-family route check, medium reasoning | 22 | 21 structurally valid tickets after one repair. No semantic review or promotion. | [Azure](../eval/results/inference/azure-gpt61-parity-20261118-summary.json) |

S1-S5 and the two earlier review reports link to the preserved Git snapshot
`071d29e62be419bb7443a6e18bf55d2763d46e69`. Their exact bytes are also retained
in the archive indexed by
[`artifacts-manifest.json`](../eval/results/artifacts-manifest.json).
Application sends are counts for each listed attempt, not total development
spend or hidden provider retries. All of these runs are experimental;
successful structure or a provisional review is not full system acceptance.

**Why retain `gpt-6.1-sol`?** The later delivery provides a complete saved
batch, a review bound to that exact output and the cost evidence in section 6.
That makes it a usable prototype baseline. It does not prove superiority over
`gpt-6-sol` or the other alternatives. In particular, the earlier
`gpt-6.1-sol` failure remains part of the record.

Code, prompts, policies, reference versions and reviewer configurations changed
during development. The findings were already exposed. Differences between
these outcomes therefore cannot be attributed to the model alone or reported
as accuracy on unseen findings. The same-family Copilot/Azure runs are route
checks, not two distinct models. Catalog listings, provider smoke tests and
models used by coding/review agents are not additional triage-quality trials.

## 6. Reproducibility and cost limits

Direct Azure was tested as the route with stricter accounting. The application
can disable SDK/communication retries and keep an explicit attempt ledger there.
It did not produce the promoted root file. Both that file and the comparison
with a different setup used Copilot. These records identify the route; they do
not establish the strict attempt limit. Hidden provider attempts remain unknown.

Cost is reported in four distinct views:

| Cost view | Retained delivery | Defensible claim |
|---|---:|---|
| Measured usage | 973,468 input; 40,335 output tokens | Usage reported in receipts |
| Simple API-equivalent repricing | US$2.350286 | Reproducible estimate under declared rates |
| Copilot metering | 21 request-cost units; 249.31861 AI units | Units reported in receipts; USD conversion not exposed |
| Actual Copilot USD allocation | Unknown | Not exposed by the subscription route |

The saved totals, source-run SHA-256, assumptions and calculations are in the
[delivery cost evidence](../eval/results/delivery-cost-summary.json), which is
calculated from each send's receipt. Repeated accounting checkpoints are not
counted again.

The equivalent calculation is
`input_tokens * US$2 / 1,000,000 + output_tokens * US$10 / 1,000,000`,
using the configured model's OpenAI Standard short-context rates published at
[OpenAI API pricing](https://developers.openai.com/api/docs/pricing) and checked
on 2026-11-18. The configured model was `gpt-6.1-sol`; the retained pricing
assumption records US$2.00 per million ordinary input tokens, US$0.10 per
million cache-read tokens, US$2.50 per million 30-minute cache-write tokens and
US$10.00 per million output tokens.
The production workflow records raw usage and leaves `usd_cost` null. It does not
calculate this estimate. The repository's controlled-experiment helper uses the
same formula on saved run receipts. The simple estimate deliberately ignores
cache adjustments. It uses only the measured input and output totals in the
formula.

The saved receipt also reports 143,251 cache-read tokens and 830,154 cache-write
tokens. Cache tokens represent input reused from, or stored in, a provider
cache. The model catalog reports a unit schedule with ratios matching public
short-context rates for ordinary input, cached input, 30-minute cache writes and
output. Applying that schedule gives a cache-aware OpenAI-equivalent estimate of
US$2.493186.

The reported 249.31861 AI units are numerically 100 times that estimate.
This observed ratio is not a published billing rule or USD conversion.
The cache-aware estimate is not an invoice either. Copilot does not establish
that its subscription allocation equals public API billing.

The retained delivery estimate consists of US$1.946936 input and US$0.403350
output, approximately US$0.111918 per ticket. Input accounts for about 82.8% of
this estimate. Reducing context size safely is therefore the clearest place to
investigate lower cost.

Report these estimates rather than writing “unknown cost.” They are
planning estimates at API rates, not Copilot invoices. Copilot does not expose
hidden communication attempts. Direct Azure exposes attempts and tokens, but the
saved observations do not include the deployment's prices. Usage records and
pricing assumptions are listed in
[`eval\results\README.md`](../eval/results/README.md).

## 7. Assumptions and limitations

- We can observe SDK behavior only where the route reports it.
- Development used an existing Copilot subscription. This does not assume that
  others have the same access or prices.
- A model label does not prove account isolation, cache behavior or hidden
  communication retries.
- A response hash identifies the saved bytes. It does not explain how the
  model's internal parameters produced them.
- A strict response structure reduces formatting risk. It cannot certify
  engineering judgment.
- The current root artifact came from the Copilot `copilot_experiment` route and
  was promoted after checking its hash. The saved delivery used a limited
  experimental route with unknown hidden attempts. It did not use a production
  route proven to meet the strict attempt limit.

The full system design is in [root `DESIGN.md`](../DESIGN.md).
Measured run outcomes remain in
[`eval\results\README.md`](../eval/results/README.md).
