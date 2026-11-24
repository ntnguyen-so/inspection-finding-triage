# Evaluation evidence and status index

This directory retains the smallest panel-facing evidence set needed to inspect
the current result, important failure history and deterministic controls.
Specifications under `eval\spec` define gates; they are not results.

> **CURRENT STATUS — GENERATED DELIVERABLE, HUMAN APPROVAL PENDING.**
> Root `tickets.json` contains all 21 findings and matches the v31 final output.
> The AI reviewer reports 63/63 after test-informed seeded calibration, but the
> runtime did not expose every reviewer-configuration identity required by the
> semantic protocol. The retained DEV runs also sent all eight TEST finding
> records in provider context, so B01 is not met and later TEST results are
> regression evidence rather than case-isolated evaluation. Six tickets require
> exceptional prequeue review, and every draft still requires ordinary human
> approval. Clean-checkout reproduction, hidden HTTP attempts and actual
> Copilot billing allocation remain unresolved.
> Measured tokens support a US$2.350286 API-equivalent estimate for the retained
> delivery under the declared public-rate convention.

The current scenario-by-scenario adjudication against the frozen acceptance
contract is in [`acceptance-status.md`](acceptance-status.md).

## Evidence review path

1. `..\..\tickets.json` — promoted 21-ticket deliverable.
2. `triage\structured-planning-v31\final\reviewer-observation.json` — final
   semantic result and limitations.
3. `triage\structured-planning-v31\final\evidence\run.json` — exact final
   provider-bound context, hashes, decisions, timing and accounting limits.
4. `triage\structured-planning-v31\final\evidence\publication.json` —
   publication receipt for the experimental output promoted byte-identically to
   root `tickets.json`; the root copy has no separate workflow receipt.
5. [`delivery-cost-summary.json`](delivery-cost-summary.json) — compact measured
   token, Copilot metering and API-equivalent cost evidence, bound to the raw run
   by SHA-256 and linked to the declared OpenAI pricing source.
6. [`behavior-calibration-replay.json`](behavior-calibration-replay.json) —
   compact, hash-bound replay showing that current routing removes nine baseline
   flags while six additional protection-case removals depend on changed
   assessment inputs.
7. `triage\structured-planning-v31\final\producer-source\producer-source-manifest.json`
   — recovery record for the exact producing workflow bytes that were not in a
   reachable commit at execution.
8. `triage\structured-planning-v31\x01-development-adjudication.json` — repeat
   stability result and visible drift dispositions. Its internal
   `x01.status: pass` is the execution-time operational adjudication; Document
   03 section 8 applies the complete reviewer-identity protocol and reports X01
   as inconclusive.
9. `triage\v10-calibration\b02-execution\negative-control-semantic-review.json`
   — bounded knowledge influence/isolation conclusion. The adjacent historical
   `report.json` intentionally retains its earlier pending-review state.
10. `design-behavior-demonstration.json` and
   `triage\native-v2-fault-evidence-1\report.json` — deterministic behavior and
   fail-closed fault evidence.
11. `inference\doc04-all21-replay-20261118\summary.json` — current-code all-21
   replay, comparison, Copilot metering and equivalent-price assumptions; the
   replay is contract-valid but not semantically reviewed. The adjacent
   `contract-assessment.json` records that contract result and pending semantic
   checks. Its `raw` directory retains the generated output, run evidence,
   ledger, configuration and recorded activation needed to inspect the
   observation.
12. [`inference\azure-gpt61-parity-20261118-summary.json`](inference/azure-gpt61-parity-20261118-summary.json)
   — Azure `gpt-6.1-sol` parity replay that
   generated and atomically published 21 temporary tickets. It records one
   repaired schema violation, 22 sends, measured tokens, retail-rate estimates
   and the execution-policy identity used by the run.
13. [`knowledge-command-replay-20261124.json`](knowledge-command-replay-20261124.json)
   — Command replay, now described in
   [Document 07 section 8.2](../../docs/07_KNOWLEDGE_CHANGE_STUDY.md#82-what-actually-ran-on-24-november-2026):
   isolated source import, eight
   reviews, publication, activation and 21 experimental drafts from 25 sends.
   It keeps startup/configuration failures and measured usage. The source was
   unchanged and the live default prompt was v1, not delivery v7; this is
   command-path evidence, not a PSV policy change, semantic pass or promotion.

## Requirement-to-evidence map

| Candidate-brief area | Retained evidence | Honest status |
|---|---|---|
| Required 21-ticket JSON and field contract | Root `tickets.json`; final tickets and reviews | Deterministic contract pass; 63/63 AI-only observation has reviewer-identity protocol limits |
| Structured output, bounded repair and failure policy | Production tests; `design-behavior-demonstration.json`; native fault report | Deterministic pass |
| Domain knowledge and maintainability | `knowledge\`; v10 B02 semantic review; Documents 05 and 07; B01 context audit | B01 not met because DEV context included TEST findings; bounded influence is partial and general domain correctness is not certified |
| Code-derived urgency | `triage\policy.py`; deterministic tests; `DESIGN.md` section C | Deterministic pass for the declared prototype policy |
| Deferral and review | v31 final reviews; projection/policy tests | Six exceptional review routes; all drafts still require human approval |
| Repeat stability | v31 development tickets/reviews, comparison and adjudication | Inconclusive for full X01 protocol acceptance: operational routing is stable, but the semantic procedure is supplementary and reviewer identity is incomplete |
| Reproducibility and cost | Final configs, run record, receipt, recovered producer source and replay summaries | Partial: measured Copilot and Azure usage supports explicit retail-rate estimates; independent replay of the exact producing revision, hidden Copilot retries and the Copilot AI-unit-to-USD conversion remain unresolved |

## Retained failed and rejected observations

- `triage\structured-planning-v31\b01-development-context-audit.json` records
  that every retained DEV provider input contained all eight TEST finding
  records. It distinguishes this failure from evaluator-card or expected-answer
  leakage.
- `triage\structured-planning-v29\final` retains the 61/63 F-1011 chronology
  failure as reviews, observation, ticket output and publication receipt.
- `triage\structured-planning-v30` retains the rejected development comparison
  and both ticket outputs. Raw provider transcripts were removed from the
  panel-facing tree because they duplicate the comparison and ticket evidence.
- The final v31 directory retains the complete final run. Development runs keep
  tickets, receipts and reviews; the X01 comparison/adjudication records their
  material differences without retaining duplicate multi-megabyte transcripts.

## Controlled-change study evidence

| Study conclusion | Retained evidence |
|---|---|
| Consequence-anchor, review-routing and urgency interventions | Direct side-by-side baseline artifact at `behavior-calibration\baseline-triage-policy-v5-tickets.json`; superseded raw runs in `archive\superseded-evidence-071d29e.zip`, indexed by `artifacts-manifest.json` under the original `v9-calibration` and `v10-calibration` paths |
| Bounded knowledge-only positive/negative comparison | `controlled-studies\knowledge-bounded-influence-report.json`; `controlled-studies\knowledge-bounded-applicability-review.json`; `controlled-studies\knowledge-bounded-influence-accounting.json` |
| Official-store edit, test-informed full-batch follow-up and editor-scope defect | `controlled-studies\knowledge-kb-edit-v1-study.json`; `controlled-studies\knowledge-kb-edit-v1-release-disposition.json` |
| Prompt extraction, authority reduction and rejected all-21 regression | `controlled-studies\prompt-authority-v1-summary.json`; `prompt-authority-v1-removed-clause-ledger.json`; `prompt-authority-v1-all21-regression.json`; `prompt-authority-v1-review.json` |
| Targeted prompt correction and diagnostic-only follow-up | `controlled-studies\prompt-authority-v3-targeted-summary.json`; `prompt-authority-v3-all21-diagnostic.json`; `prompt-authority-v3-review.json` |
| Final structured-planning chronology and current evidence | `triage\structured-planning-v29`; `structured-planning-v30`; `structured-planning-v31` |

Documents 07 and 08 summarize the decisions supported by these records. The
compact `controlled-studies` records are retained in the panel-facing tree;
large raw experiment directories remain local working evidence and are not
required to follow the documented conclusions.

## Deterministic verification

Run from the repository root on Windows with Python 3.11+:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.validate
```

Run these commands against the checkout being submitted. They establish software
and artifact integrity; they do not provide human/domain approval.

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
