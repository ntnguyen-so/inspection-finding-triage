# Inspection Finding Triage

## System in three lines

Inputs: 21 inspection findings, an equipment registry and source-controlled domain guidance.
Assessment: an LLM proposes grounded likelihood, impact and planning text; Python validates evidence and derives urgency.
Output: one fail-closed, atomically published `tickets.json` of draft tickets for human approval.

## Current delivery status

- **Built:** implementation, deterministic tests, system design and curated
  model-run evidence.
- **Generated:** root `tickets.json` contains all 21 findings and passes the
  deterministic output contract. Its SHA-256 is
  `2bb8d0f34da36142042c6f5f983622be358e45fc4690378a935e28ba189f1f98`.
- **Provisional semantic pass:** the checklist-bound primary AI reviewer passed
  calibration and reports 63 pass, 0 `needs_review`, 0 fail across 63
  dimensions. Human approval remains mandatory; the run receipt remains
  `acceptance_eligible=false`.
- **Final routing:** six tickets require exceptional prequeue review; every
  draft still requires ordinary human approval. The v31 development pair passed
  X01 after visible drift adjudication, and the final all-21 artifact passed
  63/63 calibrated AI review.
- **Provenance limitation:** the observations are hash-pinned dirty-worktree
  evidence, not clean-checkout reproduction. Hidden HTTP attempts and actual
  Copilot USD allocation are unknown.   The v31 delivery took 617.75 seconds. Actual usage and Copilot allocation were
  not exposed, so no final-run USD amount is invented.
  The file is a real system-generated deliverable, not domain-certified or
  human-approved.

See `eval\results\README.md` for run-by-run status, accounting and limitations.

## Five-minute panel path

1. **0:00 — Status and command:** read this page for the problem, current gate,
   final command and deterministic verification.
2. **0:45 — Design:** read `DESIGN.md` for model/code boundaries, knowledge,
   urgency, recovery, deferral and trade-offs; use `docs\README.md` to follow why
   the development process is ordered 01-07.
3. **2:15 — Behavior and output evidence:** inspect root `tickets.json`,
   `eval\results\triage\structured-planning-v31\final\primary-reviews.json` and
   `docs\12_SUBMISSION_READINESS_REPORT.md`, then
   `docs\08_BEHAVIOR_CALIBRATION_STUDY.md`; for the official knowledge lifecycle,
   read `docs\09_KNOWLEDGE_CHANGE_STUDY.md` and the retained bounded B02
   conclusion at
   `eval\results\triage\v10-calibration\b02-execution\negative-control-semantic-review.json`.
4. **3:15 — Evidence:** read `eval\results\README.md` and
   `eval\results\triage\structured-planning-v31\x01-development-adjudication.json`.
5. **4:15 — Implementation:** inspect `triage\workflow.py`,
   `triage\assessment.py`, `triage\policy.py` and `knowledge\source-first`.

## Install and run

Python 3.11+ and the pinned dependencies in `pyproject.toml` are required. The
retained root artifact was generated through this reviewed Copilot route. This
exact command records the retained v31 final run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -B -m triage `
  --provider copilot `
  --findings docs\candidate-pack\candidate-pack\data\inspection_findings.csv `
  --registry docs\candidate-pack\candidate-pack\data\equipment_registry.csv `
  --knowledge-store knowledge\source-first `
  --activation config\triage-activation-v31.experimental.json `
  --config config\triage-v31-final.experimental.json `
  --output eval\results\triage\structured-planning-v31\final\tickets.experimental.json `
  --evidence eval\results\triage\structured-planning-v31\final\evidence `
  --allow-inference
```

The workflow publishes nothing unless every ticket passes deterministic
validation. Replay requires copied configuration with fresh evidence and ledger
paths; reusing the retained paths is invalid. Copilot application sends are
bounded, but hidden HTTP attempts and actual per-run Copilot USD allocation
remain unknown. See
`eval\results\triage\structured-planning-v31\final\evidence\run.json`.

Root `tickets.json` is a byte-identical promotion of that reviewed draft output.
Human approval remains required. Replay requires copied configuration with fresh output, evidence and
attempt-ledger paths.

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
