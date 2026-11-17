# Inspection Finding Triage — System Design

## Overview

The system converts the supplied findings CSV and equipment registry into draft
maintenance tickets. An LLM performs evidence-grounded assessment and concise
planning; deterministic Python code owns input identity, context construction,
schema validation, retry accounting, urgency derivation, coverage and atomic
publication. Every ticket remains subject to human approval.

The final delivery uses:

- the unchanged 21-row findings file and 18-row registry;
- the owner-promoted, source-faithful knowledge release derived from
  `reference/domain_knowledge.md`;
- equipment comments plus deterministic same-equipment history and explicit
  registry/redundancy links;
- the direct Azure deployment `triage-final-sol-20260709` with native JSON
  Schema; and
- `triage-policy-v5`, with a fixed assessment time and bounded attempt ledger.

## A. Structured output

### Boundary

The model proposes:

- likelihood and impact scores with evidence-based rationales;
- a planning summary and specific recommended action;
- explicit policy fact states (`confirmed_true`, `confirmed_false`, `suspected`,
  `unknown`) and material uncertainties.

Code decides and enforces:

- finding/equipment identity and one-ticket-per-input coverage;
- the closed assessment and ticket schemas;
- exact source references and quotations;
- score types/ranges and summary/action length;
- policy consistency and required verification activities;
- urgency calculation and escalation;
- the total attempt budget; and
- final all-or-nothing publication.

### Validation and recovery

Provider responses use native strict JSON Schema and are independently validated
locally. A response is rejected for malformed JSON, unknown fields, wrong
identity, missing coverage, invalid score types/ranges, unsupported citations,
policy contradictions or incomplete required activities.

One repair retry is allowed for a recoverable structural or validation failure.
It receives the same approved context, the code-generated validation message
(bounded to 500 characters) and the rejected draft, never evaluation answers.
Authentication, configuration, refusal, transport ambiguity, explicit inability
to assess, or exhausted attempts stop the run.

A structurally valid but semantically questionable score is not silently
rewritten. It remains visible for evidence-bound semantic and human review.
If any ticket cannot be produced, the CLI exits nonzero, emits a JSON diagnostic
and does not replace the previous output. On success, all 21 tickets are
validated before `tickets.json` is atomically replaced.

## B. Domain knowledge

The source-first knowledge module stores the exact supplied domain document,
reviewed item revisions and immutable releases separately from orchestration.
The final run pins one release and retrieval implementation by hash.

For each finding, code constructs a bounded context containing:

- the complete target finding and registry row, including `engineer_comment`;
- applicable source lines from `domain_knowledge.md`;
- a deterministic same-equipment timeline;
- related findings only through explicit redundancy or registry references; and
- provenance, limitations and the workflow-owned assessment policy.

This mechanism was chosen because the source is small enough to include without
lossy summarization, exact citations are auditable, and no vector index or
retrieval-quality assumption is needed. Relationships are context, not inferred
causation. Test references, expected
answers, reviewer judgments and evaluator code are excluded from production
context.

The supplied domain document currently contains no PSV-specific rule. To add one,
an integrity engineer imports an approved PSV guidance source, creates a
`Pressure Safety Valve`-scoped item in the editor/CLI, cites its basis, obtains
review, publishes a new immutable release and regenerates the activation.
`knowledge_version` is then updated in both the activation and final config.
Equipment-specific facts may instead be maintained in the registry
`engineer_comment`. Changing generic L/I anchors or code-owned urgency requires a
separately versioned code-policy change; prompts, finding-ID branches and
evaluation cards are not the maintenance surface.

## C. Urgency derivation

The model does not choose urgency. Code computes:

```text
base = ceil(0.7 * impact + 0.3 * likelihood)
final = max(base, every applicable policy floor)
```

Impact is weighted more heavily so severe consequences are not averaged away.
The corners behave as follows:

| Likelihood | Impact | Base urgency | Interpretation |
|---:|---:|---:|---|
| 10 | 1 | 4 | highly likely but limited consequence |
| 1 | 10 | 8 | unlikely but extreme consequence |

This is neither a plain average nor a maximum. It is an ordinal attention
ranking, not calibrated expected loss.

| Rule | Evidence-backed trigger | Floor/disposition |
|---|---|---|
| `O-PROTECTION` | Confirmed protection impairment and confirmed absence of a recorded deviation | 9 |
| `O-EVACUATION` | Confirmed evacuation capacity below personnel on board | 9 |
| `P-FAILED-TEST` | Confirmed failed protection-function test | 9 |
| `P-EVACUATION` | Unavailable craft with capacity comparison unresolved | 9 |
| `P-RESTORATION` | Discovered unlogged impairment with restoration unresolved/false | 9 |
| `S-SOURCE-TODAY` | Applicable source explicitly requires same-day attention | 9 |
| `P-SAFETY-UNKNOWN` | Material safety uncertainty | 7 |
| `P-SCE-HIGH-IMPACT` | Registry SCE and assessed impact at least 8 | 7 |
| `R-MATERIAL` / `R-SCE` | Material uncertainty or SCE integrity review | Review; no extra floor |

The model assesses SCE consequences against the protected major-accident
scenario. Code does not mechanically alter L/I from the SCE flag; it applies the
documented floor/review rules after assessment. All applied rules and evidence
appear in the urgency rationale.

I rejected a plain mean because it suppresses low-likelihood/high-impact cases,
and a plain maximum because it over-prioritizes high-likelihood cosmetic defects.
I also rejected asking the model for urgency because that would make policy
inconsistent and difficult to test.

## D. Limits and human deferral

The system fails rather than publishing a scored placeholder when required
identity, context, evidence or score justification cannot be established.
Material uncertainty that can be bounded produces a draft with
`review_required=true`, a specific reason and a verification action. Missing
evidence is never converted into confirmed absence.

Human approval is always required before the batch enters a work queue.
`review_required=false` only means no additional case-specific targeted check
was identified. Additional review is explicitly flagged for SCEs, policy floors,
material uncertainties and context gaps.

Deliberate exclusions:

- no live work-order creation or autonomous operational action;
- no high-level orchestration framework;
- no vector database or probabilistic relationship inference for 21 rows;
- no learned/calibrated probability model from this small, non-gold dataset;
- no automatic repair of semantically unsupported scores;
- no hidden provider fallback or unbounded retry; and
- no claim that AI-only evaluation is domain-expert certification.

These choices keep the prototype reviewable and inexpensive while preserving
the safety boundary.

The direct Azure path uses the provider SDK only. The optional GitHub Copilot SDK
was used for development experiments with tools disabled; it is not an
orchestration framework and is not selected by the final command.

## Assumptions

- The supplied files are the complete assessment snapshot at the configured
  assessment time.
- Registry links and comments are authoritative inputs but still require
  evidence-aware interpretation.
- Likelihood, impact and urgency are ordinal 1–10 rankings, not probabilities.
- The final Azure deployment `triage-final-sol-20260709` is available to the
  reproducing reviewer and is explicitly bound to account-visible model
  `gpt-5.6-sol`, version `2026-07-09`. Secrets
  are supplied through the environment and never committed.
- The local filesystem supports atomic replacement and one writer per output.

## AI assistance and evaluation disclosure

GitHub Copilot assisted with implementation, tests, documentation, review and
experimental inference. I retained control of policy choices, rejected
finding-ID answer branches, initially rejected an unapproved SCE floor, later
versioned it only after owner authorization, and retained the failed frozen
observation rather than relabelling a corrected rerun. Evaluation answers never
enter production inference.

The following results used Copilot `gpt-5.6-sol-fast` in explicitly
non-acceptance-eligible experimental mode on a non-blind, AI-assisted split:

- initial frozen eight-ticket observation: 22/24;
- an intermediate test-informed regression remained non-green;
- disclosed corrected test-informed regression: 24/24;
- development and fixed-config repeat: 39/39 each; and
- a fresh all-21 run: 59/63, while the separately reviewed partition composite
  reached 63/63 but was not a single inference.

The failed v3 development repeat exposed F-1016 policy drift and preceded the
owner-authorized policy-v4 change. Numeric variation in the later v4 repeat was
reported rather than called deterministic; all urgency bands and review gates
were stable. These AI-only observations are regression evidence, not independent
engineering truth and not evidence for the final Azure model. The final direct
Azure output is reviewed separately after generation.

Earlier direct-Azure development experiments were also retained. `o4-mini` and
`gpt-5.1-codex-max` had structural/semantic failures; `gpt-5.1-chat` runs failed
semantic review. An earlier `gpt-5.3-chat` development run needed evidence-repair
retries for F-1001/F-1005/F-1019 and then failed review on F-1012 grounding and
F-1019 uncertainty. That run used an older knowledge release and pre-v4 policy,
so it is not reused as final evidence. The first final attempt used that
deployment but its 50k-token/minute limit was lower than the full-batch request
and failed closed before producing a ticket. I therefore created the dedicated
version-bound `triage-final-chat-20261007` deployment at 250k tokens/minute,
without changing model family or application logic. It supports the required
native schema, has no agent/tool layer, and offers a lower-complexity reproducible
path than the earlier failed configurations. The committed config also enforces
20-second request pacing.

The first run on the dedicated deployment progressed through 11 findings and
then failed closed on F-1012 because the composed action was 301 characters
after its single repair attempt. No output was published. The generic recovery
guidance was corrected to budget model-authored text around fixed code-supplied
checks; the hard 300-character limit and required activities were not weakened.
That code change starts a new bounded phase ledger, while the failed observation
remains retained.

The next bounded phase failed closed on F-1007 because the model repeated
inspection/retest content in both the core and five appended verification
activities. No output was published. The composition contract was then clarified
so completeness applies to the final composed action, exact activities are
whitespace-normalized/deduplicated, repair requests receive the actual appended
checks and a 15-character safety margin, and impossible fixed-only compositions
fail visibly. Required steps and the hard 300-character limit remain unchanged.

A subsequent chat-model phase still missed the composed-action budget by four
characters on F-1002. Because repeated prompt-only tuning was no longer a robust
delivery strategy, the final configuration uses the version-bound direct Azure
`gpt-5.6-sol` deployment at the same 250k-token/minute capacity. This is the
related model family to the `gpt-5.6-sol-fast` Copilot regressions, but those
results are not treated as evidence for this distinct final model. A same-model,
API, effort, token-cap and pacing native-schema preflight validated F-1001 after
one composition repair (the first action was 350/300 characters). A separate
preflight of the three prior overflow cases F-1002, F-1007 and F-1012 validated
all three on their first attempts, with final actions within the hard limit.
This deployment uses the selected chat-completions strict-schema path. The
provider remains direct Azure with no tools, fallback or orchestration layer;
the earlier reasoning-model failures had separate structural or semantic causes.

The first direct `gpt-5.6-sol` all-21 run published 21 structurally valid drafts
in 24 requests, but calibrated AI-only review was non-green at 60/63: F-1010
grounding and F-1020 planning failed, and F-1009 grounding needed review. This
observation is retained at
`eval\results\triage\direct-azure-final-sol-v5` and is not relabelled as final
acceptance. A disclosed medium-reasoning preflight resolved the F-1010 issue and
showed F-1009's impact rationale was permitted but still omitted part of
F-1020's required restoration-control sequence. `triage-policy-v5` therefore
keeps v4 scoring unchanged while code-owning the generic sequence for any
confirmed unlogged protection impairment whose restoration is false or
unverified: verify current control alignment, reconcile the impairment/deviation
record, and close only after a witnessed passing function test. This is a
test-informed change; it is not an untouched frozen-test result.

The final run permits at most 42 direct requests (21 findings, at most two
attempts each), with SDK/HTTP retries disabled and explicit token accounting.
Before the policy-v5 v7 final run, retained final-phase attempts and preflights
consumed 95 direct
requests across separate disclosed ledgers; no ledger was reset to relabel an
old phase as untouched.
USD cost depends on the Azure deployment tariff and is reported as unknown unless
a sourced rate is available; request/token usage is retained so reproduction
cost can be estimated without claiming subscription credits are free.

The first policy-v5 medium-reasoning preflight failed closed before producing
F-1011 because all 4096 completion tokens were consumed by reasoning and Azure
returned `finish_reason=length`; no draft text or output was published. The
final configuration therefore provides 8192 completion-token headroom. This
does not add retries or alter the two-attempt application budget; any non-`stop`
finish reason still fails visibly.

The first all-21 policy-v5 phase validated 19 findings, then Azure exceeded the
120-second deadline on F-1020; dispatch outcome was recorded as unknown, F-1021
was not attempted, and no output was published. The v7 phase changes only the
provider deadline to 180 seconds and uses a fresh ledger/evidence directory.
It does not retry the ambiguous dispatch inside the old phase or change model,
reasoning effort, prompt, knowledge, policy or ticket requirements.

## Run

Install on Windows with Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`, then run:

```powershell
.\.venv\Scripts\python.exe -B -m triage `
  --provider azure `
  --findings docs\candidate-pack\candidate-pack\data\inspection_findings.csv `
  --registry docs\candidate-pack\candidate-pack\data\equipment_registry.csv `
  --knowledge-store knowledge\source-first `
  --activation config\triage-activation-v5.json `
  --config config\final-run.json `
  --output tickets.json `
  --evidence .delivery-state\final-run-sol-v7 `
  --allow-inference
```

The command consumes billable inference, writes complete evidence, and publishes
only after all 21 tickets pass deterministic validation. The committed config
uses a repository-relative ledger under ignored `.delivery-state`. A rerun in
the same working tree must use a fresh evidence directory and a fresh ledger path;
a clean clone starts with neither. The ledger's 42-attempt budget covers the
whole batch and must never be reset to conceal consumed attempts.
