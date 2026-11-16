# Inspection Finding Triage

Evaluation-first candidate exercise, now with reusable Azure OpenAI and Copilot
text/JSON inference adapters and a code-controlled triage workflow. The primary
workflow now consumes source-first knowledge through native bundle 3 with
separate workflow scoring policy and explicit activation pins. The earlier
three-ticket Copilot smoke used the legacy interface; it does not qualify this
migration. Full semantic evaluation, strict acceptance and final delivery remain gated.

## Generated test artifacts

Commit test code, fixtures, frozen evaluation specifications and curated evidence,
not every generated payload. `eval\results\artifacts-manifest.json` records local
archive locations, SHA-256 hashes, retained evidence and pruning outcomes.
Existing inference observations, calibration, paid-call records, summaries and
failure observations remain unchanged.

Bulky synthetic snapshots from completed runs are archived under ignored
`.artifacts\evidence`; a hash-verified second copy is kept outside the checkout
at the backup path recorded in the manifest. Routine offline command logs remain
local but ignored. These local copies are **not uploaded, committed or a durable
shared backup**; transfer a verified archive to an approved evidence store before
discarding either copy or relying on another machine to reproduce the run.
`git clean -fdx` would remove the in-checkout copy.

To inspect a run whose raw dependencies were archived, first check its archive
hash and extract to a **new staging directory**, not over current run files:

```powershell
$manifest = Get-Content eval\results\artifacts-manifest.json -Raw | ConvertFrom-Json
$archive = $manifest.archives | Where-Object area -eq knowledge
if ((Get-FileHash -LiteralPath $archive.local_path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $archive.sha256) { throw "Archive hash mismatch" }
Expand-Archive -LiteralPath $archive.local_path -DestinationPath .artifacts\restore\knowledge
python -B -c "import hashlib,json; from pathlib import Path; r=Path(r'.artifacts\restore\knowledge'); m=json.loads((r/'__archive_manifest__.json').read_text('utf-8')); assert all((r/x['path']).stat().st_size==x['bytes'] and hashlib.sha256((r/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in m['files']); print('Extracted contents verified')"
```

Verify every extracted member against the embedded inventory, then restore only
the required absent payload directories to the manifest's `original_root`.
Never overwrite changed reports or reset live-call budget ledgers. Archive
availability is required to reproduce the original raw-artifact hashes; retained
summaries alone do not prove that the original checks pass on current code.

Two bounded read-only AI reviews informed this cleanup: terminal-report linkage,
per-file checks, a verified second copy and a pre-deletion recovery journal were
accepted. Command logs were retained rather than deleted. The cross-review found
no significant issues; this is storage housekeeping, not system acceptance.

## Read the work in order

| Order | Document | Purpose |
|---|---|---|
| 01 | `docs\01_INITIAL_INVESTIGATION.md` | Understand the brief, domain rules, data and open decisions |
| 02 | `docs\02_DATA_EVALUATION_PLAN.md` | Profile the data; justify the development/test split and evidence references |
| 03 | `docs\03_EVALUATION_ACCEPTANCE.md` | Define acceptance gates, panel-question coverage, review decisions and readiness |
| 04 | `docs\04_INFERENCE_LIBRARY.md` | Inference API, implementation process, real probes and provider-parity limits |
| 05 | `docs\05_TRIAGE_WORKFLOW.md` | Owner-approved component design; deterministic workflow implementation, offline evidence and remaining integration/eval gates |
| 06 | `docs\06_KNOWLEDGE_DESIGN_DECISION.md` | Current knowledge Design Decision: extraction/retrieval evaluation, code-versus-LLM gates, source-first editing and workflow tool contract |

`DESIGN.md` is reserved for the project owner to create later. Inference design,
deferred system-design notes and implementation evidence are in document 04;
they are not the approved final system design.

## Inference library

Python 3.11+ is required. Production inference uses the separate direct Azure
module; it needs no Copilot executable, login or subscription. Set the process
environment variables shown in `.env.example` using your secret manager or
local shell. That example file is documentation, not automatically loaded.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
@{model=$env:AZURE_OPENAI_DEPLOYMENT; system="Reply concisely."; user="What is 2 + 2?"} |
  ConvertTo-Json -Compress |
  .\.venv\Scripts\python.exe -B -m llm_inference --provider azure --azure-max-completion-tokens 1024 --request -
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py"
```

The CLI returns one JSON result, or exits 1 with a JSON diagnostic on stderr.
Python callers use `AzureOpenAIProvider` and `InferenceRequest` (document 04).
`model` means the Azure **deployment name**. API-key mode reads
`AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`. For Microsoft Entra, add
`--azure-auth entra` and supply an authorized `DefaultAzureCredential` identity;
an Azure CLI login alone does not grant data-plane permission. There is no
authentication fallback. GA `/openai/v1/` ignores `AZURE_OPENAI_API_VERSION`.
JSON Schema is validated locally; `--azure-native-json` additionally requests
Azure-native strict JSON Schema on a compatible deployment. Unsupported schemas
or controls fail rather than silently falling back. SDK/HTTP retries and redirects
are disabled.

The development-cost alternative requires an installed, authenticated Copilot
CLI and account/model access; Copilot usage is still billable:

```powershell
.\.venv\Scripts\python.exe -B -m llm_inference --models
'{"model":"gpt-5.6-sol-fast","reasoning_effort":"none","system":"Reply concisely.","user":"What is 2 + 2?"}' |
  .\.venv\Scripts\python.exe -B -m llm_inference --provider copilot --request -
```

Copilot remains the CLI default for backward compatibility. Each call uses a
fresh tool-disabled session. Native JSON, token caps and internal HTTP-retry
guarantees are unavailable through Copilot; it is not fully provider-equivalent.

Panel reproduction, from the repository root with Azure environment configured
and Copilot authenticated (consumes real usage, maximum 20 nominal sends per
declared experiment; preserve the ledger):

```powershell
.\.venv\Scripts\python.exe -B -m tools.compare_inference --output eval\results\inference\panel-comparison.json --copilot-model gpt-5.6-sol-fast --include-native
```

Add `--azure-only` for an Azure-only check without a Copilot runtime. Select a
Copilot model actually matching the underlying Azure deployment, not its friendly
name. Reusing the same ledger skips prior slots; `--case role` explicitly repeats
and consumes budget. Do not delete/reset evidence to bypass the limit.
Active synthetic fixtures use English with a Unicode checkmark
(`english-unicode-v2`). Older ledgers are read-only historical evidence and
cannot be resumed with revised fixtures; a new paid experiment still needs an
explicit budget/authorization.
Recorded observations: six paired synthetic cases agreed on expected data,
plus one Azure-native JSON pass. This does not establish identical model behavior,
cost, hidden processing or triage accuracy. Evidence and limits are under
`eval\results\inference` and document 04.

## Knowledge editor and context module

**Current design:** document 06 is the single knowledge Design Decision. It
defines extraction/relevant-active-retrieval evaluation before reimplementation,
source-faithful intake/editing, lifecycle and the module-owned callable tool.
Workflow owns L/I interpretation and code-derived U. Code is the baseline; an
LLM strategy needs explicit fidelity, retrieval, review-benefit and budget evidence.
Bounded AI critique and adjudication are recorded in document 06 section 12.
The default CLI/editor use source-first entrypoints. The owner has now explicitly
authorized publication of the unchanged supplied domain as a conservative C0
integration release; see document 06 section 11.5. This neither enables C1 nor
upgrades or publishes the old numeric-band/PSV starter.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[editor]"
.\.venv\Scripts\python.exe -B -m triage_knowledge --store knowledge\source-first import-source --source docs\candidate-pack\candidate-pack\reference\domain_knowledge.md --source-id domain --name "Supplied domain"
.\.venv\Scripts\python.exe -m streamlit run triage_knowledge\editor.py --server.address 127.0.0.1 --browser.gatherUsageStats false
.\.venv\Scripts\python.exe -B -m triage_knowledge --store knowledge\source-first check
.\.venv\Scripts\python.exe -B -m triage_knowledge --store knowledge\source-first status
```

The default store now has eight owner-approved items, zero pending items and one
immutable release. The import command above is for a new store/source, not a
required repeated startup step. Publication and current-build integration
preflight are recorded in `eval\results\knowledge\source-owner-promotion-1`;
`activation.integration.json` contains its original release and reviewed pins.
Policy-v2 integration deliberately refreshes execution pins separately in
`eval\results\triage\native-owner-activation-v2`; never silently reuse stale pins.
`knowledge\source-first` stores exact source blobs, immutable revisions and the
editable schema-3 candidate; published releases are separate. The old
`knowledge\drafts\working.json` is unused legacy, not the current knowledge base.

Import preserves source bytes and creates pending items, never an approved
rubric. The editor supports source edits, evidence-backed metadata, context links,
review and lifecycle; every change requires fresh review. Publishing and workflow
activation are separate. Use one trusted local writer.
There is no automatic paid extraction in the editor: unqualified LLM extraction
is limited to explicitly authorized isolated evaluation.

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.test_source_knowledge tests.test_source_context tests.test_source_cli tests.test_source_editor
.\.venv\Scripts\python.exe -B -m unittest discover -s eval\tests -p "test_knowledge*.py"
.\.venv\Scripts\python.exe -B -m unittest eval.tests.test_run_knowledge
.\.venv\Scripts\python.exe -B -m eval.run_knowledge --output eval\results\knowledge\extraction\<new-run>
```

The offline runner preserves raw C0 proposals and leaves retrieval pending without
reviewed input. An explicit `--synthetic-review-diagnostic` exercises actual
publication/retrieval in isolated, clearly labelled software fixtures; it cannot
establish human approval or qualification. Pending/failed evaluation exits nonzero.
Real Copilot measurements require the separate `--copilot-experiment
--allow-inference` controls, a new output directory and the fixed persistent
ledger; do not reset it or rerun a failed semantic slot.

Software checks and synthetic review declarations are not actual human content
approval or system acceptance. Native `build_source_context` and independently
regenerating `validate_source_context` use history-aware contract 3 with separate workflow-owned
`assessment_policy`. Retain one context for all retries, with explicit release,
time, strategy and policy pins. Do not use legacy rubric/context APIs or silently
substitute archived source text. Publication and workflow activation are separate;
a new draft never mutates an older pinned release.

Actual package observation `eval\results\knowledge\source-package-regression-4`
passes eight mechanical goals using all 21 supplied findings and 18 registry rows,
including 24 contexts and 14 rejection checks. Historical `source-handoff-2`
records a real development-only Copilot context acknowledgement, not knowledge
influence or triage quality. The two handoff sends exhausted their cumulative
ceiling; historical `source-handoff-1` stays bound to its original freeze.
The source-first code baseline preserves all required atoms but historically
fails selective usefulness; it remains a disclosed conservative baseline.
`extraction\completion-v4-run1` passes all automated C1 gates: 13/13 source/repeat
slots on first attempts, 24/24 retrieval cases with full required-atom recall,
and 8/8 usefulness cases (78.65%-100% irrelevant-byte reduction, 20% required).
298 committed-root/evaluator software tests and the isolated wheel check pass.
The source-unit evidence format uses code-expanded citations, not model-copied
quotes; old failed profiles remain failed. This is disclosed non-blind synthetic
regression conditional on its registered vocabulary, not field qualification.
Exact offline replay of all 24 cases passes using retained immutable releases
without drafts or provider calls; see document 06 section 11.4.
Separate zero-provider checks of concurrent integration edits also pass: 298
software tests, the actual-package mechanical goals and all 24 captured
selections. These observations do not rebind frozen model receipts to new code.

**Automated component gates pass; C1 adoption remains unqualified.** Independent
human correction-benefit, verified USD and hidden HTTP accounting are not
established. LLM extraction stays experimental/default-off; the separately
owner-authorized C0 integration release does not qualify that strategy.
See `eval\results\knowledge\source-integration-readiness.json` for the historical
v4 pins, actual sends and remaining gates, and `source-owner-promotion-1` for the
later actual source publication. Integration must pin its own delivered build.
Never reset a spent ledger
or treat software-fixture review as engineer approval.
Document 06 section 11 distinguishes retained legacy evidence, including the
four-send real Copilot knowledge probe:
both synthetic positives were unassessable, so knowledge influence remains
failed/inconclusive; mechanically valid controls are not semantic acceptance.
Legacy schema-1/2 commands and forms are available only through
`python -m triage_knowledge.legacy_cli` and `triage_knowledge\legacy_editor.py`
for recorded replay. The legacy exporter re-appends archived domain text; do not
use it to claim active-only behavior of the source-first path.

## Triage workflow (eval-driven, bottom-up)

`triage` owns input/context validation, ordinal L/I policy, code-derived urgency,
review policy, bounded recovery and all-or-nothing draft publication. The module
owns source extraction, active retrieval and context assembly. Workflow pins a
reviewed schema-3 release/selector/index, calls the public native builder and
independently rebuilding consumer validator, then retains validated bundle 3 for
every finding/retry. It never imports legacy scoring bands,
appends archived domain text or substitutes an old release.

Run the deterministic checks and retain evidence, with no live model calls:

```powershell
.\.venv\Scripts\python.exe -B -m tools.verify_triage --output eval\results\triage\local-check-1
```

Use a new directory each time (change `local-check-1` for the next run). This runs production-component tests with synthetic inference, actual source-first
store/release/retrieval/builder/CLI integration, inference/evaluator regressions
and frozen-reference validation.
It is **not** semantic evaluation, knowledge influence or full system acceptance.
The observation in `eval\results\triage\offline-implementation-7\verification.json`
records the earlier offline increment. Current Copilot integration regressions
were recorded in `eval\results\triage\offline-copilot-1\verification.json`.
The corrective increment is recorded in
`eval\results\triage\offline-fix-2\verification.json`.

The source-first migration's stable, isolated software observation is
`eval\results\triage\source-first-snapshot-verification-2\verification.json`
(300 passing software tests plus integrity/import checks). Two shared-checkout
captures were invalidated by concurrent upstream edits; a first isolated attempt
hit a long Windows path. Their failed observations remain retained.
The installed wheel's 30 runtime modules match the captured source hashes.
`source-first-migration-summary.json` records actual release blockers and the
separate, narrow AI-only reviewer calibration. None is a full system/model pass;
the local snapshot/wheel is not a durable shared release package.

The CLI is available via `python -B -m triage --help`. Publish reviewed source
content using the document 06 editor/CLI first. Prepare an activation **candidate**
from the actual immutable release, then record an explicit compatibility review:

```powershell
.\.venv\Scripts\python.exe -B -c "import json; from pathlib import Path; from triage import activation_candidate; from triage_knowledge.source_store import SourceKnowledgeStore; pins=activation_candidate(SourceKnowledgeStore(r'<reviewed-store>'), '<sha256-release-id>'); Path(r'<activation.json>').write_text(json.dumps(pins, indent=2), encoding='utf-8')"
```

The generated `review=null` deliberately blocks inference. An operator must review
the exact sources against workflow policy and replace it with
`{"reviewer":"<identity>","reason":"<compatibility basis>","reviewed_at":"<timezone-aware-time>","source_policy_compatible":true}`.
This is an unauthenticated local declaration, not proof of human/domain approval.
Never fabricate it to bypass the knowledge/evaluation gates. Any release,
selector/index or workflow policy change requires new pins/review.

After source review, activation and the remaining baseline gates, the single
end-to-end generation command is:

```powershell
.\.venv\Scripts\python.exe -B -m triage --findings <selected-findings.csv> --registry <registry.csv> --knowledge-store <reviewed-store> --activation <activation.json> --config <run-config.json> --output <draft-tickets.json> --evidence <new-run-directory> --allow-inference
```

For final generation select the unchanged supplied all-21 findings and registry;
do not do so before development/frozen-test gates. These command shapes are not
evidence of an executed live run. There is no promoted source-first release in
this checkout. Native B02 now has an explicit `isolated_probe` consumer contract
and `tools.probe_native_knowledge` prepare/execute driver; software checks do not
establish actual knowledge influence. It uses honest `evaluation_input` and
workflow-owned policy overlays, never ordinary/final generation. Legacy exports remain usable only with `--context-export <path>
--legacy-replay`, for disclosed replay, not native acceptance.

`run-config.json` contains `model` (approved Azure deployment), `knowledge_version`,
timezone-aware `assessment_time`, `phase_attempt_budget`, and `attempt_ledger`
(persistent phase-ledger path). Optional controls are `max_context_bytes` (64000),
`timeout_seconds` (90), `reasoning_effort` (`"low"`),
`minimum_request_interval_seconds` (0), and `azure_max_completion_tokens` (4096,
integer 1-32768 including reasoning). The direct provider uses
native JSON Schema, explicit token cap, no tools/retries/redirects. The request
schema binds identities/allowed source addresses and valid applicability states;
original-schema, exact-quotation and semantic checks still apply. Compatibility,
deployment, pricing and budget sign-off are still prerequisites, not established
by offline checks. Reuse the same ledger and ceiling for a phase, including repeats;
do not reset it to evade the budget. One writer per output/phase ledger is supported.

`azure_api` defaults to `"chat_completions"`; explicitly set `"responses"` for
a deployment requiring the direct Responses endpoint. No API/model fallback or
agent orchestration is added. Both bounded drivers accept `--azure-api`,
`--reasoning-effort`, `--azure-max-completion-tokens` and `--timeout-seconds`
when preparing a new immutable plan; execution uses its recorded configuration.
The development driver also accepts `--minimum-request-interval-seconds` for
prospectively pinned quota pacing. Native assessment v2 uses snapshot-bound
source-line selectors, correlated assessed/unassessable frames and a joint
function-failure/likelihood constraint. Code resolves selected literal evidence,
validates separately evidenced source timing and derives urgency; it does not
repair model-authored values or establish semantic truth.

Exit 0 means only **draft generated**, never accepted or human-approved. Any
blocking failure returns nonzero with JSON stderr and leaves the old output
unchanged. `run.json` is intentionally persisted **before** the final atomic
replacement and remains `ready_to_publish`; stdout is the success receipt.
Retain it with the output and compare the intended/actual hashes. No fallible
evidence write occurs after publication; crash/interruption reconciliation is
not claimed. All drafts require human approval.

### Bounded native development integration

For source-first store-to-model-to-publication testing, use the bounded
`tools.integrate_triage` prepare/execute/repeat commands in document 05 sections 14-15.
They use only development findings and an isolated, explicitly SOFTWARE-reviewed
copy of the unchanged domain, not a claim of real KB approval. One phase ledger caps the
initial observation plus one fixed-config repeat at 52 actual direct HTTP dispatches
(or 52 application sends for the explicitly limited Copilot mode).
Experimental output and semantic assessment do not establish release acceptance.
Current offline evidence is `eval\results\triage\native-v2-regression-2\report.json`:
314 component checks,126 evaluator checks and source/reference validation passed.
Prepared development/all-21 capacity is125700/146359 bytes,93 schema properties
and nesting5. An intermittent knowledge software-fixture failure from the first
run is retained in `native-v2-regression-1`; its cause is unresolved, not hidden
by the later passing runs. `native-v2-fault-evidence-1` retains22 native lifecycle/
fault-path checks and their synthetic artifacts. None establishes model quality.
`native-v2-package-1\report.json` verifies all30 installed runtime files and
three isolated CLIs in a fresh environment, not final all-21 reproduction.
The historical `native-handoff-system-summary.json` and all twelve Copilot sends
remain retained. Direct chat deployments completed13-ticket batches but failed
semantic review; actual observations, partial failures and bounded reasoning
continuations are under `native-strict-development-*`, `native-strict-model53`
and `native-strict-o4`. Direct Responses observations and preserved schema
diagnostics are under `native-strict-codex`. No accepted baseline, frozen test or final tickets is
claimed. The owner-promoted real release has deliberately reviewed policy-v2
integration pins in `native-owner-activation-v2`; its source projection matches
the software development fixture, but real-release live evaluation remains
separate. This checkout is **not release-ready**.

The workflow CLI defaults to Azure/`execution_mode="strict"`. Copilot is explicit:
`--provider copilot` requires `execution_mode="copilot_experiment"`, a persistent
`.experimental-ledger.json`, and an output ending `.experimental.json`. It has no
Azure fallback. This development mode audits actual messages/model/tool/session
events but cannot establish hidden HTTP attempts, output-token caps, USD cost or
the brief's raw-endpoint compliance. Its results are never acceptance-eligible.
New `tools.integrate_triage` Copilot plans default to `gpt-5.6-sol-fast`; pass
`--model` to pin another catalog model. Azure plans still require an explicit
deployment. Existing plans, ledgers and observations retain their frozen model.

Actual account-visible catalog metadata is in
`eval\results\triage\copilot-catalog-1\catalog.json`. The selected `gpt-6-luna` was
among the lowest exposed token-price values, not demonstrated monetary savings.
The initial actual-model observations (`copilot-integration-2` and
`copilot-integration-3`) used **4/6 authorized application sends**, targeting only
F-1005; all three descriptions were in context, but F-1010/F-1012 were not assessed.
That diagnostic repeat was disclosed development-informed
regression, not a new baseline. The last response passed assessment validation but
paraphrased mandatory action text instead of retaining it verbatim, so publication
was blocked. Those failures remain preserved.

The owner's subsequent corrective request is documented in section 12 of
document 05. Code now composes the validated core action and mandatory verification
activities, preserving all text and rejecting totals above 300 characters.
Prompt guidance exposes the existing conditional activity contract and separates
qualified assessment from genuine inability; no evidence or scoring validator
was relaxed.

**Passing live smoke:** `eval\results\triage\copilot-correction-3` contains
`tickets.experimental.json`, the CLI success receipt, captured requests/responses
and audits. All three development targets (F-1005/F-1010/F-1012) produced tickets;
one evidence error recovered within the two-attempt cap. The successful observation
used four sends; the corrective phase used 10/12, on its single shared ledger
under `copilot-correction-1`. Including the prior closed phase, total use is
14/16 authorized sends. Inference stopped after this pass. Earlier failed
observations and both ledgers remain intact; do not reset them to evade ceilings.

These are development-informed experimental integration results, not a calibrated
semantic pass or frozen test. Document 05 records usage and review limitations.
`python -B -m tools.probe_triage --help` describes the bounded collector and its
explicit same-ledger repeat option.
`eval\results\triage\postrun-provenance.json` distinguishes later parallel knowledge
edits after the earlier failed smoke. The corrective pass has its own source
snapshots; `copilot-correction-3\verification.json` binds output/receipt checks.

The original package is preserved at `docs\candidate-pack\candidate-pack`.
Document numbers indicate the real sequence of work, not reconstructed Git
history. Git begins with an actual snapshot taken before this reorganization.

## Evaluation layout

```text
eval\
  assess.py                 Ticket-output assessment CLI
  validate.py               Reference/data integrity CLI
  data\
    development.jsonl       13 development finding references
    test.jsonl              8 test finding references
  spec\
    split.json              Current version, partitions, groups and fingerprints
    acceptance.json         17 preregistered system scenarios
    probes.json             Synthetic policy probe and known-false controls
  tests\
    test_assess.py          Tests of the output assessor
    test_validate.py        Tests of reference validation
  results\
    readiness.json          Observed readiness evidence, not system acceptance
    calibration\
      reviewer-a.json       Actual disclosed review judgments
      reviewer-b.json       Separate review provenance
```

`data\test.jsonl` is a dataset; `tests\test_*.py` checks evaluator code. They are
not duplicate tests. There is one current evaluation reference, with its version
in `spec\split.json`; earlier decisions are documented, not parallel eval copies.
The split is non-blind, and the AI-assisted references are not expert-certified.
Reference cards and review results must never enter production inference context.
Synthetic probes belong only in their declared, isolated evaluation experiment,
not normal ticket generation.

## Run from the repository root

Windows, Python 3.11+, standard library only; no installation or API key needed:

```powershell
python -B -m eval.validate
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.assess --partition development --checklist
```

Recheck the recorded known-fixture judgments:

```powershell
python -B -m eval.assess --partition development --calibration-reviews eval\results\calibration\reviewer-a.json
python -B -m eval.assess --partition development --calibration-reviews eval\results\calibration\reviewer-b.json
```

For assessment of future generated tickets, see document 03. A passing integrity
check, evaluator self-test or known-fixture calibration is not a system pass.
Deterministic triage-component, knowledge-handoff and live Copilot smoke
evidence are recorded separately above. The smoke captures actual provider-bound
context; maintained-knowledge influence, calibrated semantic review, frozen test
and delivery gates remain unexecuted. No full scenario acceptance is inferred
from evaluator self-tests, mocks or the passing experimental smoke.

Git preserves raw file bytes, including CRLF, so source/reference SHA-256 checks
survive checkout. Do not normalize the supplied package or regenerate evidence
cards during formatting.

## Working with coding agents

`AGENTS.md` is the canonical working agreement for design, implementation,
evaluation and delivery. `.github\copilot-instructions.md` directs GitHub Copilot
to the same rules. Agents must connect changes to panel requirements and the
existing eval gates, preserve development/test boundaries and record honest
evidence before claiming success.

Instruction-file discovery depends on the tool. If an assistant does not discover
these files, explicitly give it `AGENTS.md`. Instructions are guidance, not an
automated substitute for the acceptance checks.
