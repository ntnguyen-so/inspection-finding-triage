# Inspection Finding Triage — System Design

## Five-minute status

This prototype turns 21 supplied inspection findings into draft maintenance
tickets. It has a tested implementation, controlled knowledge lifecycle,
code-derived urgency, retained real-model experiments and a generated root
`tickets.json` covering all 21 findings. The artifact passes the deterministic
output contract but is **not acceptance-eligible**: semantic assessment remains
`needs_review` at 54/63 with zero fail, human approval is outstanding, and clean-checkout
reproduction has not been run. Every draft still requires human approval.

| Panel question | Current answer |
|---|---|
| Can it generate the required structure? | Yes in offline tests and real experiments; malformed and schema-invalid responses were observed and regenerated once or failed closed. |
| Does it use the supplied engineering context? | The complete bounded source package, registry and maintained knowledge are hash-pinned and captured. Reference-1.3 B02 provides a bounded causal-influence and negative-control pass; general domain correctness remains unproven. |
| Is urgency model-authored? | No. The model proposes L/I and facts; code computes urgency and applies traceable rules. |
| Is the required file present? | Yes. Root `tickets.json` contains exactly 21 system-generated drafts and passes the deterministic contract. |
| Is it submission-ready? | The required draft file exists. V11 primary AI review is 54/63 with nine review-routed judgments and zero fail; the receipt remains non-eligible and human approval is mandatory. Actual Copilot USD allocation is unknown, while a disclosed equivalent OpenAI API estimate is about US$2.37. |

The ordered rationale from requirements through reliability measurement is in
[`docs/README.md`](docs/README.md); evidence status and limitations are indexed in
[`eval/results/README.md`](eval/results/README.md).

## The four judgment traps

1. **Missing evidence is not evidence of absence.** Unknown deviation, capacity,
   restoration or partner condition must remain unknown; it cannot activate a
   supplied override that requires a confirmed fact.
2. **Redundancy is not automatically creditable.** A stated 2oo3 arrangement
   proves a relationship, not that every partner is currently available and
   capable.
3. **Impact is not repair cost.** The assessment includes loss of required
   function, escalation, delayed or hidden consequences and the protected
   major-accident scenario where supported.
4. **Valid JSON is not a valid engineering answer.** The system must separate
   malformed output, structural errors, unsupported semantics and genuinely
   unassessable evidence.

These traps drive the architecture. Probabilistic interpretation is used where
language and evidence must be synthesized; predictable engineering controls stay
in code.

### Why knowledge and triage are separate modules

`triage_knowledge` owns source ingestion, extraction, review, immutable releases,
selection and context validation. `triage` owns assessment orchestration,
urgency policy, attempts, complete coverage and publication. Triage consumes a
pinned knowledge/context contract; it does not know how the store extracted or
selected the underlying items.

This one-way dependency separates content authority from execution authority. A
domain owner can update approved PSV guidance without editing workflow code, and
a workflow developer cannot silently turn evaluation cases into maintained
knowledge. The workflow is independent of store internals, not independent of
engineering context: missing or invalid required context remains a terminal
failure.

### Why inference is a separate module

The candidate already had a GitHub Copilot CLI subscription that included access
to the coding models used for development without a separately visible per-call
API charge. A provider-neutral `llm_inference` boundary allowed repeated probes
to use that lower-marginal-cost route instead of funding every iteration through
a separately billed OpenAI/Azure API, while keeping orchestration, validation and
policy independent of Copilot.

This was an economic development choice, not a claim that Copilot inference is
free or equivalent to a fully observable direct route. Subscription cost and
quotas are real, hidden HTTP attempts and per-run USD allocation are unavailable,
and another reviewer may not share the entitlement. The final draft uses the
explicit `copilot_delivery` mode: application sends are bounded and audited, but
strict transport accounting remains unestablished and acceptance remains false.

## Architecture and responsibility boundary

```text
validated findings + registry + pinned knowledge + fixed configuration
  -> complete source-first context and independent hash checks             [code]
  -> L/I, fact states, uncertainty, summary and proposed activity         [model]
  -> identity, schema, quotations, citations and fact consistency checks  [code]
  -> urgency arithmetic, floors, review routing and required checks       [code]
  -> exact 21-ticket coverage and atomic tickets.json replacement         [code]
  -> semantic evaluation and human approval                    [outside generation]
```

| Model interprets or authors | Deterministic code owns |
|---|---|
| Meaning of observations and comments | Input shape, IDs, joins, dates and score directions |
| Near-term likelihood and consequence | Closed schemas, ranges and text limits |
| Confirmed/false/suspected/unknown facts | Exact citations, quotations and state consistency |
| Uncertainty and proposed verification | Urgency, floors, override conditions and review rules |
| Summary and recommended activity | Attempt budget, complete coverage and atomic publication |
| Explicit inability to support L/I | Nonzero failure; never a guessed fallback score |

The boundary does not make model judgment deterministic or correct. It makes the
consequences observable and bounded. Real runs produced malformed JSON and schema
violations; model repair attempts guided by code-generated feedback validated four
responses in one batch, while another batch failed after both attempts. A later
fixed-configuration gpt-6 X01 pair completed both generations but reviewed
38/39 then 37/39, so the showcased all-21 63/63 result did not close the
stability gate. No
counterfactual experiment has compared this design with model-authored urgency,
so that alternative is rejected on predictability and brief compliance, not
claimed empirical superiority.

### Worked example: F-1005

The detector head failed two gas tests; the other two heads in the 2oo3 group
responded. The model assessed `L=9`: failure of this head's required function was
confirmed. It assessed `I=6`: detection was degraded, but the observation still
showed two responsive heads and therefore did not justify treating group
protection as lost.

Code calculated a base urgency of 7. A separately labelled candidate policy for a
confirmed failed protection-function test raised the final urgency to 9 and
required checks of the impairment/deviation record and current group condition.
The supplied confirmed override was **not** claimed because absence of a recorded
deviation was unknown, not confirmed. This example shows the intended separation:
semantic assessment may vary; arithmetic, fact-state requirements and provenance
do not.

## A. Structured output and failure behavior

Each model response must satisfy a closed assessment schema. Code rejects extra
fields, duplicate keys, wrong identity, non-integer or out-of-range scores,
unsupported citations, inexact quotations, invalid fact combinations and missing
required activities. A repair receives the same pinned context, the rejected
draft and a bounded error message. Only explicitly recoverable output errors get
one further application attempt.

The L/I rubric defines ordinal bands. A confirmed required-function failure must
be in the 9-10 likelihood band; a lower but otherwise valid score is an
`assessment_contradiction` and gets one repair. Code can similarly detect
citation and fact-state contradictions. A coherent, in-range but engineering-wrong
score cannot be proven wrong by schema code: it remains subject to offline
semantic review and human approval, as the Azure v5 failures demonstrate.
Model-authored fact states can also activate code-owned floors—for example, a
confirmed failed protection-function test triggers a floor of 9. Code validates
the fact state's form, citations and internal consistency, not its engineering
truth. Independent fact-state calibration remains future work.

The batch has a persistent 42-attempt budget. Provider retries are disabled on
the strict Azure route. Any failed finding exits nonzero and publishes nothing;
an existing output remains byte-identical. Only a complete, revalidated
21-ticket wrapper is flushed and atomically substituted for `tickets.json`.

### Observed control behavior

The retained
[`behavior demonstration`](eval/results/design-behavior-demonstration.json)
binds a 195,917-byte raw verifier report by SHA-256. It ran 125 component tests
with zero failures, plus 63 inference/provider tests, 81 knowledge/context tests,
126 evaluator tests and frozen-reference validation. It predates the current v8
production changes and is historical control evidence, not current-v8
certification.

| Adversarial behavior exercised | Observed result | What it establishes |
|---|---|---|
| Malformed JSON versus structural schema failure | Classified separately; each received only its allowed repair | Errors are not collapsed into a success-shaped fallback |
| Both attempts invalid | Nonzero failure; previous output preserved | Exhaustion cannot masquerade as current success |
| One finding fails within a batch | No partial batch published | Completeness is enforced at publication |
| Atomic replace fails | Old bytes preserved; temporary file removed | Publication failure is fail-closed |
| New process tries to reset budget | Persistent budget still enforced | Restarting cannot create unbounded retries |
| Evidence cannot support L/I | No midpoint or placeholder score | Review does not legitimize fabrication |
| Timeout, refusal or context mutation | No publication | Transport and provenance failures are terminal |

These are deterministic self-tests, not evidence that the proposed L/I values are
correct.

### Observed model behavior

| Experiment | Observation | Interpretation |
|---|---|---|
| Pre-v8 policy-v5 Copilot at `235bdd1`, 21 findings | 25 sends; four first attempts failed: two malformed JSON and two schema violations; all four repairs succeeded | Bounded repair solved observed output faults on that route/version, but the run is not acceptance-eligible |
| Pre-v8 Copilot X01 first run | F-1017 returned malformed JSON twice; batch failed and no repeat was run | The same controls also rejected a real exhausted response |
| Later pre-v8 gpt-6 X01 pair at `4debeba` | Both 13-ticket generations completed; semantic reviews were 38/39 `needs_review` and 37/39 `fail` on F-1003/F-1005 planning | Recorded X01 **fail**; the separate 63/63 all-21 result did not establish stability |
| Later pre-v8 gpt-6.1 first all-21 run | Failed at F-1015 after 15 sends because the response crossed the output boundary | A newer model did not reproduce complete generation on its first attempt |
| Later pre-v8 gpt-6.1 retry | 21 contract-valid tickets in 23 sends; two separate calibrated AI-only reviews each failed at 60/63 | The earlier gpt-6 63/63 result is best-of-several evidence, not stable quality |
| Direct Azure v5, 21 findings | 24 requests produced 21 contract-valid tickets; semantic gate still failed despite 60/63 reviewed dimensions | Structural success is insufficient |

The historical Azure experiment used 1,289,873 prompt tokens, 45,878 completion tokens and
16,474 reasoning tokens. Reported cache reuse was small relative to cache writes;
its USD cost remains unknown because no deployment tariff was captured.

The current Copilot delivery provides a simpler reproducibility estimate. It
completed 21 application sends in 635.64 seconds (about 10m36s), with median
send latency 29.45 seconds and maximum 37.36 seconds. Receipts report 983,821
input tokens and 40,200 output tokens. Pricing all input at $2/M and output at
$10/M using OpenAI's 2026-11-17 standard short-context `gpt-6.1-sol` table gives
an illustrative **US$2.37**. This intentionally ignores cache discounts and is
not the actual Copilot subscription charge. Exact assumptions and the pricing
URL are retained in
`eval\results\triage\v8-reliability\delivery-cost-latency.json`.

## B. Knowledge, context and maintenance

The corpus is small and relationship-heavy, so every assessment receives the
complete bounded registry, all selected findings and engineer comments, exact
source-faithful domain items, deterministic same-equipment history and explicit
relationships. This avoids lossy summaries, vector infrastructure and unsupported
top-k retrieval assumptions. The supplied package is preserved byte-for-byte.

A run pins input, knowledge release, selector, prompt, assessment policy and
execution policy by hash. Code independently reconstructs and validates context
before provider dispatch. Evaluation cards, expected answers and reviewer
judgments are excluded from production context.

An engineer changing PSV behavior uses one of three explicit surfaces:

| Intended change | Correct surface |
|---|---|
| General PSV guidance or exception | Import an approved PSV-scoped source, review it, publish an immutable knowledge release, then approve and repin activation |
| Fact about one PSV | Update the registry snapshot and revalidate it |
| Generic L/I anchor or urgency/review policy | Change versioned application policy and focused tests |

This avoids prompt surgery and finding-ID branches. It also exposes a limitation:
captured context proves delivery, not causal use. The retained B02 influence probe
was failed/inconclusive, and no PSV-specific behavior change has yet been
demonstrated.

The concrete general-guidance path is:

```powershell
python -B -m triage_knowledge --store knowledge\source-first import-source `
  --source "path\to\approved-psv-guidance.md" --name "approved-psv-source"
python -B -m triage_knowledge --store knowledge\source-first review `
  --item "item-id" --expected-digest "digest" --reviewer "reviewer" --reason "scope checked"
python -B -m triage_knowledge --store knowledge\source-first publish `
  --expected-digest "digest" --author "author" --reviewer "reviewer" --reason "approved"
```

The returned `knowledge_version` must be reviewed and pinned in a **new**
activation identity and fresh run configuration; activation remains separate
from knowledge publication. `config\triage-activation-v11.json` records the
post-experiment policy decision and two bounded critical reviews. The prototype
still does not provide a dedicated activation-approval CLI.

The current root `tickets.json` was generated with that activation and the
prospectively pinned v11 delivery configuration. This closes the earlier
activation-provenance gap for the recorded run, but not the separate
clean-checkout reproduction or human-approval gates.

## C. Urgency derivation and observed stability

The model never outputs urgency. For ordinal likelihood `L` and impact `I`:

```text
base  = ceil(0.7 * I + 0.3 * L)
      = (7 * I + 3 * L + 9) // 10
final = max(base, every applicable rule floor)
```

This is a candidate-owned attention policy, not probability, expected loss or a
calibrated risk model. Its source is the supplied asymmetric corner requirement,
not an external formula. If `w` is the impact weight, requiring `(L=10,I=1)` to
remain at most 4 gives `w >= 2/3`; requiring `(L=1,I=10)` to remain at most 8
gives `w <= 7/9`. `0.7` is a simple interior rational with exact integer
arithmetic.

| L / I | Plain mean | Plain maximum | Chosen formula |
|---|---:|---:|---:|
| 1 / 1 | 1 | 1 | 1 |
| 10 / 1 | 5.5 | 10 | 4 |
| 1 / 10 | 5.5 | 10 | 8 |
| 10 / 10 | 10 | 10 | 10 |

All 100 input pairs were range-checked and monotone. A 16-state fact experiment
also showed that the supplied protection override fires only for confirmed
impairment plus confirmed absence of a recorded deviation; suspected or unknown
states receive separately labelled precaution/review treatment.

The base formula alone gives `L=1,I=8 -> U=6`, so it does not satisfy the supplied
statement that a low-likelihood, high-impact SCE still needs attention this week.
`P-SCE-HIGH-IMPACT` closes that specific gap with a floor of 7. It was added after
an observed development-repeat band failure, but its design authority is the
supplied SCE rule; the threshold remains candidate-owned and uncalibrated.

| Rule | Trigger and effect | Authority |
|---|---|---|
| `O-PROTECTION` | Confirmed impairment and confirmed no recorded deviation; floor 9 | Supplied override |
| `O-EVACUATION` | Confirmed evacuation capacity below POB; floor 9 | Supplied override |
| `S-SOURCE-TODAY` | Cited active source explicitly requires same-day attention; floor 9 | Source directive composed by code |
| `P-FAILED-TEST` | Confirmed failed protection-function test; floor 9 | Candidate precaution |
| `P-EVACUATION` | Craft unavailable but capacity/POB comparison unresolved; floor 9 plus verification | Candidate precaution |
| `P-RESTORATION` | Unlogged impairment and restoration false/unverified; floor 9 plus closure checks | Candidate precaution |
| `P-SAFETY-UNKNOWN` | Material safety uncertainty, including unknown deviation; floor 7 plus verification | Candidate precaution |
| `P-SCE-HIGH-IMPACT` | SCE with assessed impact at least 8; floor 7 | Supplied SCE intent, candidate threshold |
| `R-MATERIAL` / `R-SCE` | Targeted review; no urgency floor | Candidate review policy |

F-1020 demonstrates `O-PROTECTION`: impairment and absence of a deviation record
were both confirmed. F-1012 demonstrates the opposite boundary: unavailable craft
with unknown POB comparison activates `P-EVACUATION`, not the supplied
`O-EVACUATION` override.

### What the outputs reveal

| Observation | Result |
|---|---|
| Pre-v8 policy-v5 Copilot urgency | 7 today, 12 this week, 1 this month, 1 next shutdown |
| Model impact scores | 13 at I=8, 5 at I=7, 1 at I=6, 2 at I=4 |
| Floors changed the base result | Only F-1001 and F-1005 |
| Targeted review flag | 21/21 true |
| Azure v5 versus pre-v8 policy-v5 Copilot urgency band | 19/21 the same; F-1007 and F-1014 differed |
| Current v11 root urgency | 19/21 at 7-10; distribution is U4=1, U5=1, U7=6, U8=6, U9=7 |
| Current v11 root review flag | 20/21 true |

The concentration is driven mainly by high model impact assessments rather than
floors. V9 attempted to make review selective and v10 attempted an interaction
formula; both were rejected after semantic failures and no demonstrated
prioritisation benefit. V11 deliberately accepts a saturated conservative review
gate because material uncertainty must remain visible. The flag is therefore a
safety gate, not a workload-ranking mechanism.

The current root artifact confirms rather than resolves this calibration risk.
Code sets `review_required` whenever any policy rule exists; 62 generic
`P-SAFETY-UNKNOWN` rule instances therefore help saturate the flag. F-1016
(in-date PSV with an illegible tag, U7) and F-1019 (unquantified dropped-object
exposure, U8) are explicit challenge cases. The candidate did not tune policy
after seeing the final artifact. The retained adjudication accepts the file as a
review-routed draft, not as proof that 19 findings objectively require
week-or-faster handling.

Controlled repeats show the remaining semantic variance. Before policy v4,
F-1016 changed from U7 to U6 and crossed from this-week to this-month. A later
gpt-6.1 repeat changed three of 39 impact values but no final urgency band; one
threshold rule trace changed. The high-impact SCE floor that absorbed the earlier
corner is explicitly test-informed, not independently calibrated.

## D. Limits, alternatives and human authority

The system has only three valid outcomes: supported draft; supported but
materially uncertain draft with a specific check; or unassessable batch failure.
Human approval is always outside generation. No output authorizes maintenance,
shutdown or work-order creation.

The main rejected alternatives are model-authored urgency, rules-only L/I, plain
mean/maximum urgency, automatic credit for redundancy, using the SCE label alone
to force high L/I or immediate urgency, placeholder scores, semantic rewriting in
code, vector RAG for this corpus, unbounded retries and partial publication. Each
either conflicts with the brief, hides uncertainty or adds infrastructure without
demonstrated need.

The production-essential core is smaller than the evidence apparatus: validated
context, one bounded repair, schema/fact checks, urgency policy and atomic
publication. The calibrated reviewers, frozen cards, archives and experiment
ledgers are prototype evaluation scaffolding. They explain failures and prevent
success-shaped claims, but they would not belong in the runtime service. The
current balance is still too evaluation-heavy for the brief because it has not
yet produced the required final artifact.

### High-impact assumptions

| Assumption | Safeguard or consequence |
|---|---|
| Supplied files are the complete selected snapshot | No unprovided state is invented |
| Assessment cutoff is `2026-07-01T00:00:00+00:00` | Later deterioration or repair is not assumed |
| Registry comments are evidence, not conclusions | They require grounded interpretation |
| Redundancy relationships do not prove partner health | Availability and capability require evidence |
| Missing deviation, POB or restoration data remains unknown | Confirmed overrides cannot be inferred |
| L/I/U are ordinal scales | Numerical gaps are not treated as equal quantities |
| One trusted local writer and same-volume replacement are available | No distributed-concurrency claim |
| Model/reviewer labels expose configuration, not hidden weights or expertise | Results are evidence, not certification |

### AI assistance and candidate overrides

AI assisted code, tests, documentation, review and experiments. Candidate-owned
decisions overrode AI suggestions by keeping urgency in code, rejecting
per-finding answer tables and placeholder scores, retaining failed/inconclusive
results, and preserving frozen evaluation fingerprints. Restoration sequencing,
the high-impact SCE floor and some guidance are disclosed test-informed changes;
they are not presented as untouched blind-test findings.

## Submission gap and ordered next work

1. Perform semantic and human review of the generated root `tickets.json`; either
   restore and commit the exact generating workflow or regenerate from a clean,
   approved frozen identity so the result is reproducible.
2. Calibrate impact anchors, precaution thresholds and targeted review with a
   domain owner, especially the low-consequence weekly cases.
3. Demonstrate a PSV knowledge change with a controlled ablation.
4. Add hash-pinned per-finding resume without weakening atomic final publication.
5. Reduce repeated context cost and, if available, capture actual Copilot billing
   rather than relying on the disclosed US$2.37 equivalent-API estimate.
6. Repeat controlled stability experiments on held-out or independently
   reviewed cases.

The strongest demonstrated claim is narrow: **model behavior varied, including
real malformed and schema-invalid output; deterministic controls made those
failures traceable, bounded and fail-closed.** The prototype is technically
substantial, and the required file now exists. Final semantic acceptance and
reproducible delivery provenance remain open.
