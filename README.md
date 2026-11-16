# Inspection Finding Triage

Evaluation-first candidate exercise, now with reusable Azure OpenAI and Copilot
text/JSON inference adapters. The triage system is not implemented yet; no model-generated
tickets or system-acceptance results are claimed.

## Read the work in order

| Order | Document | Purpose |
|---|---|---|
| 01 | `docs\01_INITIAL_INVESTIGATION.md` | Understand the brief, domain rules, data and open decisions |
| 02 | `docs\02_DATA_EVALUATION_PLAN.md` | Profile the data; justify the development/test split and evidence references |
| 03 | `docs\03_EVALUATION_ACCEPTANCE.md` | Define acceptance gates, panel-question coverage, review decisions and readiness |
| 04 | `docs\04_INFERENCE_LIBRARY.md` | Inference API, implementation process, real probes and provider-parity limits |

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
