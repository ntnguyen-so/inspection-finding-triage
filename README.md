# Inspection Finding Triage

Evaluation-first candidate exercise, now with reusable Azure OpenAI and Copilot
text/JSON inference adapters and source-first knowledge editing/retrieval. Knowledge
qualification and coordinated workflow activation remain gated; no system acceptance
is claimed by this component.

## Read the work in order

| Order | Document | Purpose |
|---|---|---|
| 01 | `docs\01_INITIAL_INVESTIGATION.md` | Understand the brief, domain rules, data and open decisions |
| 02 | `docs\02_DATA_EVALUATION_PLAN.md` | Profile the data; justify the development/test split and evidence references |
| 03 | `docs\03_EVALUATION_ACCEPTANCE.md` | Define acceptance gates, panel-question coverage, review decisions and readiness |
| 04 | `docs\04_INFERENCE_LIBRARY.md` | Inference API, implementation process, real probes and provider-parity limits |
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
'{"model":"gpt-6-sol","system":"Reply concisely.","user":"What is 2 + 2?"}' |
  .\.venv\Scripts\python.exe -B -m llm_inference --provider copilot --request -
```

Copilot remains the CLI default for backward compatibility. Each call uses a
fresh tool-disabled session. Native JSON, token caps and internal HTTP-retry
guarantees are unavailable through Copilot; it is not fully provider-equivalent.

Panel reproduction, from the repository root with Azure environment configured
and Copilot authenticated (consumes real usage, maximum 20 nominal sends per
declared experiment; preserve the ledger):

```powershell
.\.venv\Scripts\python.exe -B -m tools.compare_inference --output eval\results\inference\panel-comparison.json --copilot-model gpt-6-sol --include-native
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
`activation.integration.json` contains the exact release and reviewed pins.
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
regenerating `validate_source_context` use contract 2 with separate workflow-owned
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
All 17 system scenarios remain unexecuted until an implementation exists.

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
