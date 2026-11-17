# Curated evaluation evidence

This directory contains the reviewer-facing evidence set. Compact ledgers,
accounting reports, failure summaries and calibration records remain in Git.
Historical raw runs, intermediate plans, duplicated stores, request/response
bodies and synthetic payloads are retained in the verified archive recorded in
`artifacts-manifest.json`, not in the main checkout.

## Current status

- `triage/direct-azure-final-sol-v5/` is the latest direct-Azure all-21
  observation. Contract validation passed, but semantic review was non-green
  (60/63); it is retained as a disclosed failed observation, not final
  acceptance. Its request/token/cost accounting was not retained in the original
  observation and remains unknown.
- `triage/copilot-gpt61-policy-v5-all21/` is a disclosed Copilot experimental
  all-21 observation with 62/63 calibrated AI-only dimensions. F-1015 planning
  failed; its reviewer used the same model in a separate session.
- `triage/copilot-gpt6-policy-v5-all21/` is a Copilot experimental all-21
  observation with 63/63 provisional AI-only dimensions and 27 application
  sends. It loaded the pre-correction prompt while source changed during the
  run, so it is not current-code or acceptance-eligible evidence.
- `triage/copilot-gpt61-f1015-guidance/` retains the one-case, test-informed
  spot check for the revised visibility/readability planning guidance. It is not
  an all-21 result; F-1015 is no longer held out.
- `triage/policy-v4-composite-21/` is a provisional AI-reviewed composite of
  separately generated partitions. It is regression evidence, not one final
  inference or domain-expert certification.
- Root `tickets.json` is still to be produced as the required final delivery
  artifact; none of the evidence directories above substitutes for it.

## Evidence map

| Requirement | Retained evidence | Scope |
|---|---|---|
| A: output and recovery | `triage/native-v2-fault-evidence-1/report.json`, `triage/native-v2-regression-2/report.json` | Deterministic contract, retry and fail-closed checks |
| B: maintained knowledge | `knowledge/source-integration-readiness.json`, `knowledge/source-owner-promotion-1/`, `knowledge/copilot-b02-1/` | Source lifecycle, activation and disclosed influence probe |
| C: urgency | `triage/native-v2-regression-2/report.json`, production tests | Code-owned formula and policy checks |
| D: limits and deferral | `triage/native-v2-fault-evidence-1/report.json`, `triage/native-handoff-system-summary.json` | Failure routing and historical integration limitations |
| X01: stability | `triage/policy-v4-final-phase-2/x01-review.json`, `triage/final-regression-phase-4/x01-review.json`, `triage/history-policy-v3-phase/x01-review.json` | Stable and failed comparisons retained explicitly |
| X02: reproducibility | `triage/native-v2-package-1/report.json`, `inference/delivery-verification.json` | Package and provider-component evidence; not final all-21 reproduction |
| Output quality | `triage/direct-azure-final-sol-v5/assessment-report.json`, `triage/copilot-gpt61-policy-v5-all21/`, `triage/copilot-gpt6-policy-v5-all21/`, `triage/copilot-gpt61-f1015-guidance/` | Direct run failed 60/63; Copilot experiments are 62/63 and pre-correction 63/63; current guidance has only a one-case spot check |
| Reviewer calibration | `calibration/`, `triage/source-first-calibration-1/report.json` | Known-fixture calibration only |

`readiness.json` is the original pre-implementation readiness record and must not
be read as current system acceptance.

## Archive recovery

`artifacts-manifest.json` records the full pre-curation archive, its SHA-256,
embedded per-file inventory and a separately verified backup copy. The same
files remain recoverable from Git revision `3997d00`. Restore to a new staging
directory; never extract over current results. Retained ledgers remain
authoritative for their original phases and must never be reset or replaced by
archived copies to obtain a fresh budget.

```powershell
$manifest = Get-Content eval\results\artifacts-manifest.json -Raw | ConvertFrom-Json
$archive = $manifest.archives | Where-Object scope -eq full_pre_curation_eval_results
if ((Get-FileHash -LiteralPath $archive.local_path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $archive.sha256) { throw "Archive hash mismatch" }
Expand-Archive -LiteralPath $archive.local_path -DestinationPath .artifacts\restore\eval-results
```

The local and backup paths are machine-local evidence copies, not a durable
shared artifact service. Preserve the archive before moving or cleaning this
checkout.
