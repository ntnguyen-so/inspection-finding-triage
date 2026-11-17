# Inspection Finding Triage

## System in three lines

Inputs: 21 inspection findings, an equipment registry and source-controlled domain guidance.
Assessment: an LLM proposes grounded likelihood, impact and planning text; Python validates evidence and derives urgency.
Output: one fail-closed, atomically published `tickets.json` of draft tickets for human approval.

## Current delivery status

- **Built:** implementation, deterministic tests, system design and curated
  model-run evidence.
- **Missing:** a system-generated root `tickets.json`; this is not a final
  accepted delivery.
- **Why:** the strict provider route has not completed an accepted v8 batch.
  One pre-v8 policy-v5 gpt-6 experiment reviewed 63/63, but a later pre-v8
  gpt-6.1 retry
  reviewed 60/63 twice. The former also flags all 21 tickets for targeted review
  and puts 19 at urgency 7-9, so quality and discrimination are unresolved.

See `eval\results\README.md` for run-by-run status, accounting and limitations.

## Five-minute panel path

1. **0:00 — Status and command:** read this page for the problem, current gate,
   final command and deterministic verification.
2. **0:45 — Design:** read `DESIGN.md` for model/code boundaries, knowledge,
   urgency, recovery, deferral and trade-offs; use `docs\README.md` to follow why
   the development process is ordered 01-07.
3. **2:15 — Behavior and output evidence:** read the historical
   `eval\results\design-behavior-demonstration.json`, then inspect the pre-v8
   policy-v5 artifact at
   `eval\results\triage\copilot-gpt6-current-all21\tickets.experimental.json`
   with its `assessment-report.json` and the matching-model X01 failure at
   `eval\results\triage\copilot-gpt6-current-x01\run-summary.json`.
4. **3:15 — Evidence:** read `eval\results\README.md` and
   `eval\results\reproducibility\clean-235bdd1.json`.
5. **4:15 — Implementation:** inspect `triage\workflow.py`,
   `triage\assessment.py`, `triage\policy.py` and `knowledge\source-first`.

## Install and run

Python 3.11+ and Azure credentials named in `.env.example` are required. The
command shape below installs the package and performs the billable all-21
workflow, but it is **not freeze-ready as written**: the current v8 activation
has invalid review provenance and `config\final-run.json` retains a stale v7
ledger. A final run must substitute a newly approved activation file and fresh
run configuration.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -B -m triage `
  --provider azure `
  --findings docs\candidate-pack\candidate-pack\data\inspection_findings.csv `
  --registry docs\candidate-pack\candidate-pack\data\equipment_registry.csv `
  --knowledge-store knowledge\source-first `
  --activation config\triage-activation-v8.json `
  --config config\final-run.json `
  --output tickets.json `
  --evidence .delivery-state\panel-final-run `
  --allow-inference
```

The workflow publishes nothing unless every ticket passes deterministic
validation. Use a fresh evidence directory for each live run.

`config\final-run.json` pins the Azure deployment in its `model` field; the
`AZURE_OPENAI_DEPLOYMENT` example variable does not override it. A reviewer using
a different deployment must copy the config and change `model`. On a fresh clone
the configured ignored ledger path starts empty; in this working checkout the v7
ledger already has two reservations, so a new run must also use a fresh ledger.
That is a new run, not reproduction of a recorded model observation. On Windows,
use a short checkout path because deep synthetic fixture paths can exceed the
legacy path limit.

## Falkor assessment-criteria map

| Candidate-brief criterion | Where to review it |
|---|---|
| 1. System design and structured-output handling; model/code boundary | `DESIGN.md` A/C; Documents 04 and 06; production `triage` code |
| 2. Domain knowledge encapsulation and maintainability | `DESIGN.md` B; Document 05; `knowledge\source-first` |
| 3. Output quality: summaries, defensible scores and grounded rationales | Document 06; retained model observations and failures in `eval\results\triage` |
| 4. `DESIGN.md` | Root `DESIGN.md`, including limits, assumptions, rejected alternatives and AI-assistance disclosure |

Code style, tests and packaging support these criteria but are not separately
weighted by the supplied brief.

For the rationale/evidence chain and why each step precedes the next, read
`docs\README.md`. For superseded approaches and failed phases, follow its
Original Decision Process link.

## Deterministic verification

Run from the repository root:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.validate
```

Retained clean-checkout results at revision
`235bdd1d57d87cfb7c4669adf6a7b56aa50011a9`: 276 production tests run
(272 passed, 4 environment-dependent skips), 126 evaluator tests passed, and
reference validation passed for 21 findings / 18 equipment records, reference v1.2.
Evidence: `eval\results\reproducibility\clean-235bdd1.json`.

The later `eval\results\design-behavior-demonstration.json` is pre-stabilized-v8
worktree evidence: 125 component tests, 63 inference/provider tests, 81
knowledge/context tests, 126 evaluator tests and reference validation passed.
Production code has changed since that observation, so it is historical rather
than current certification. No retained clean-checkout result yet certifies the
current v8 code, live-provider behavior or domain quality.

The evaluator has also changed since the clean revision above: the working
reference is v1.3 and the current evaluator suite contains 127 tests. No retained
clean-checkout run yet certifies that working evaluator/configuration.

## Repository map

| Path | Purpose |
|---|---|
| `DESIGN.md` | Required final system design and declared limitations |
| `triage` | Assessment orchestration, validation, urgency and publication |
| `llm_inference` | Provider-neutral boundary: subscription-backed Copilot development and strict direct-Azure inference |
| `knowledge\source-first` / `triage_knowledge` | Versioned knowledge data and maintenance tooling |
| `config` | Pinned activation and final-run configuration |
| `tests` / `eval` | Production tests, evaluator, frozen specification and retained evidence |
| `docs\README.md` | Development argument, panel reading path and documentation authority |
| `docs\candidate-pack\candidate-pack` | Unchanged supplied brief, data and domain references |
| `pyproject.toml` | Python version, dependencies and package manifest |

## Panel decision process

| Step | Document | Contribution |
|---:|---|---|
| Guide | `docs\README.md` | Separates current panel-facing records from the historical process |
| 01 | `docs\01_INITIAL_INVESTIGATION.md` | Derives the engineering problem and assumptions from the brief |
| 02 | `docs\02_DATA_EVALUATION_PLAN.md` | Explains data, context, split and evidence boundaries |
| 03 | `docs\03_EVALUATION_ACCEPTANCE.md` | Summarizes the A-D/X acceptance contract and claim limits |
| 04 | `docs\04_INFERENCE_LIBRARY.md` | Explains provider isolation, subscription-backed development economics and accounting limits |
| 05 | `docs\05_KNOWLEDGE_DESIGN_DECISION.md` | Explains the independent source-faithful knowledge lifecycle, retrieval contract and maintenance boundary |
| 06 | `docs\06_TRIAGE_WORKFLOW.md` | Explains how workflow consumes inference/knowledge contracts and owns fail-closed orchestration |
| 07 | `docs\07_VERSION_RELIABILITY_PROTOCOL.md` | Defines how one frozen version is measured without tuning between runs |

Exact pre-rewrite Documents 01-06 are preserved with SHA-256 hashes under
`docs\original-decision-process`. The archived Documents 02/03 retain the frozen
evaluation-contract bytes; the primary files are panel summaries.
