# Evaluation evidence and status index

This directory retains the smallest panel-facing evidence set needed to inspect
the current result, important failure history and deterministic controls.
Specifications under `eval\spec` define gates; they are not results.

> **CURRENT STATUS — GENERATED DELIVERABLE, HUMAN APPROVAL PENDING.**
> Root `tickets.json` contains all 21 findings and matches the v31 final output.
> The calibrated primary AI reviewer reports 63/63 provisional pass, six tickets
> require exceptional prequeue review, and every draft still requires ordinary
> human approval. Clean-checkout reproduction, hidden HTTP attempts and actual
> Copilot cost remain unresolved.

## Five-minute evidence path

1. `..\..\tickets.json` — promoted 21-ticket deliverable.
2. `triage\structured-planning-v31\final\reviewer-observation.json` — final
   semantic result and limitations.
3. `triage\structured-planning-v31\final\evidence\run.json` — exact final
   provider-bound context, hashes, decisions, timing and accounting limits.
4. `triage\structured-planning-v31\final\evidence\publication.json` — output
   publication receipt.
5. `triage\structured-planning-v31\x01-development-adjudication.json` — repeat
   stability result and visible drift dispositions.
6. `triage\v10-calibration\b02-execution\negative-control-semantic-review.json`
   — bounded knowledge influence/isolation conclusion. The adjacent historical
   `report.json` intentionally retains its earlier pending-review state.
7. `design-behavior-demonstration.json` and
   `triage\native-v2-fault-evidence-1\report.json` — deterministic behavior and
   fail-closed fault evidence.
8. `..\..\docs\12_SUBMISSION_READINESS_REPORT.md` — requirement closure and
   residual limitations.

## Requirement-to-evidence map

| Candidate-brief area | Retained evidence | Honest status |
|---|---|---|
| Required 21-ticket JSON and field contract | Root `tickets.json`; v31 final tickets and reviews | Deterministic contract pass; semantic result is provisional AI-only 63/63 |
| Structured output, bounded repair and failure policy | Production tests; `design-behavior-demonstration.json`; native fault report | Deterministic pass |
| Domain knowledge and maintainability | `knowledge\`; v10 B02 semantic review; Documents 05 and 09 | AI-reviewed bounded influence/isolation pass; general domain correctness is not certified |
| Code-derived urgency | `triage\policy.py`; deterministic tests; `DESIGN.md` section C | Deterministic pass for the declared prototype policy |
| Deferral and review | v31 final reviews; projection/policy tests | Six exceptional review routes; all drafts still require human approval |
| Repeat stability | v31 development tickets/reviews, comparison and adjudication | Provisional X01 pass with disclosed numeric/rule-trace drift |
| Reproducibility and cost | v31 configs, run record and receipt | Partial: command, hashes and runtime retained; clean checkout, hidden retries and actual cost unresolved |

## Retained failed and rejected observations

- `triage\structured-planning-v29\final` retains the 61/63 F-1011 chronology
  failure as reviews, observation, ticket output and publication receipt.
- `triage\structured-planning-v30` retains the rejected development comparison
  and both ticket outputs. Raw provider transcripts were removed from the
  panel-facing tree because they duplicate the comparison and ticket evidence.
- The final v31 directory retains the complete final run. Development runs keep
  tickets, receipts and reviews; the X01 comparison/adjudication records their
  material differences without retaining duplicate multi-megabyte transcripts.

## Deterministic verification

Run from the repository root on Windows with Python 3.11+:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.validate
```

The cleanup baseline passed 325 production tests, 127 evaluator tests and frozen
reference validation. These checks establish software and artifact integrity;
they do not provide human/domain approval.

## Retention policy

The current tree intentionally excludes loose superseded transcripts, duplicate
generated tickets, old model-selection runs and obsolete run configurations.
All 457 removed files are preserved losslessly in
`archive\superseded-evidence-071d29e.zip`. `artifacts-manifest.json` records
their original paths, per-file hashes, source commit, archive hash and verified
separate-backup status. The archive SHA-256 is
`bc31bdb141e3de51f024e069c528ca20235ddd2067e6312bd3d778d771a1b48f`.
Git history was not rewritten, and local ignored experiment data was not
promoted into the repository.

This keeps failure history auditable without making the panel navigate hundreds
of generated files. New evidence should be committed only when it supports a
declared requirement, a material failure or the currently promoted result.
