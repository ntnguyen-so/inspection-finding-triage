# Evaluation evidence and status index

This is the single reviewer-facing index for observed evaluation evidence. Read
`DESIGN.md` for the system design and this file for what was actually exercised.
Specifications such as `eval\spec\acceptance.json` define gates; they are not
results.

> **GATE BANNER — NOT YET SUBMISSION-READY.** Deterministic implementation and
> evaluator checks pass. One pre-v8 policy-v5 gpt-6 Copilot experiment at
> revision `235bdd1` reviewed 63/63, but a later pre-v8 gpt-6.1 first run failed
> before completion and
> its retry failed two separate AI-only reviews at 60/63. Root `tickets.json`
> does not exist. The latest completed acceptance-eligible direct-Azure run
> failed closed and did not publish output. A later local v7 state is abandoned,
> predates current assessment code and is not result evidence.
> Human approval is always required.

Production code has changed since the latest clean, isolated deterministic run at
revision `235bdd1`. The evidence collector was subsequently corrected and rerun
in a dirty worktree; that is retained historical behavior evidence, not a
current-v8 clean-checkout observation.

## Evidence and status legend

| Mark | Meaning |
|---|---|
| **T** | Tracked in Git at the cited path. |
| **W** | New retained worktree evidence; commit before submission. |
| **L** | Local and ignored; exists in this checkout but is not shared evidence. |
| **A** | Archive-only raw dependency; recover using `artifacts-manifest.json`. |
| **D-pass** | Deterministic executable evidence passed its stated scope. |
| **Provisional** | AI-only/model evidence passed its stated review; not expert certification or system acceptance. |
| **Fail** | The observed run or required review failed. |
| **Pending** | Required evidence or deliverable does not yet exist. |
| **Inconclusive** | The experiment did not establish the intended claim. |

## Requirement-to-evidence matrix

| Requirement | Evidence and class | Status no stronger than evidence |
|---|---|---|
| Brief §3: 21-ticket JSON, identities, fields, lengths, L/I/U and planning text | **T** `triage\native-v2-fault-evidence-1\report.json`; **T** current experimental ticket assessment under `triage\copilot-gpt6-current-all21\` | **D-pass** for contract/failure machinery; **Provisional** for one non-eligible 21-ticket artifact; final root artifact **Pending** |
| Brief §5: own orchestration, bounded retry, one command, no keys, low reproducibility cost | **T** `triage\native-v2-package-1\report.json`; **T** `reproducibility\clean-235bdd1.json`; source/dependency inspection in repository | **D-pass** for package and retry contracts. Existing Copilot subscription reduced separately billed development spend, but per-run subscription allocation/provider cost remains unknown; successful final one-command run **Pending** |
| Brief §6A: structured output, malformed/structural/semantic handling, fail-closed publication | **W** `design-behavior-demonstration.json`; **T** `triage\native-v2-fault-evidence-1\report.json`; **T** `triage\direct-azure-final-sol-v5\assessment-report.json` | Structural/recovery paths **D-pass**; valid-but-wrong output was retained as **Fail**, not repaired silently |
| Brief §6B: domain knowledge, engineer comments, PSV maintenance path | **T** `knowledge\source-integration-readiness.json`; **T** `knowledge\source-owner-promotion-1\`; **T** `triage\history-context-2\verification.json`; `DESIGN.md` §B | Delivery/lifecycle **D-pass**; behavior probe `knowledge\copilot-b02-1\observation.json` is **Inconclusive** |
| Brief §6C: code-derived urgency, corners, overrides, alternatives | **W** `design-behavior-demonstration.json`; **T** `triage\native-v2-regression-2\report.json`; `DESIGN.md` §C | Formula, monotonic grid, corners and fact-state rules **D-pass**; policy is prototype engineering choice, not calibrated truth |
| Brief §6D: deferral, human review, deliberate exclusions | **T** `triage\native-v2-fault-evidence-1\report.json`; **T** `triage\native-handoff-system-summary.json`; `DESIGN.md` §D | Failure/deferral machinery **D-pass**; output-level judgments remain model/reviewer-limited |
| Brief §6 assumptions and AI assistance/overrides | `DESIGN.md` “High-impact assumptions” and “AI assistance and candidate overrides” | Documented; historical test-informed changes and rejected suggestions disclosed |
| Brief §7: `tickets.json`, source, manifest, run command, DESIGN, Git history | `pyproject.toml`, `README.md`, `DESIGN.md`, Git log; root `tickets.json` absent | Source/design/history present; required generated deliverable **Pending**, so delivery gate not passed |
| Brief §8.1: model/code boundary and structured-output handling | `DESIGN.md` §A/C; deterministic reports above | **D-pass** for implemented boundary; final provider/output acceptance pending |
| Brief §8.2: knowledge encapsulation/maintainability | Source-first evidence above; `docs\05_KNOWLEDGE_DESIGN_DECISION.md` | Lifecycle, module boundary and edit surface **D-pass**; influence evidence incomplete |
| Brief §8.3: output quality and defensibility | **T** direct-Azure 60/63 failure; **T** gpt-6 63/63 provisional pass; **W** later gpt-6.1 60/63 failures | Mixed: the best pre-v8 AI-only result was not reproduced; all model evidence is non-eligible and the gpt-6 artifact has 21/21 targeted-review flags plus 19/21 urgency 7-9 |
| Brief §8.4: DESIGN quality | `DESIGN.md`; **T** `triage\design-verification.json`; **T** `knowledge\design-verification.json` | Required topics present; panel judgment remains external |
| Domain trap: reliability direction and priors | Deterministic context/policy tests; current artifact review | Implemented/tested; current non-eligible output **Provisional** |
| Domain trap: SCE impact means major-accident consequence, not repair cost | Policy tests and semantic cards | Implemented; AI-only semantic evidence, not domain certification |
| Domain trap: voted 2oo3 is degradation, not defeat | F-1005 reviews in retained assessment sets | Current artifact **Provisional** |
| Domain trap: redundancy must be healthy; paired batch findings matter | **T** history/context verification and F-1003/F-1017, F-1013/F-1018 reviews | Context delivery **D-pass**; output interpretation **Provisional** |
| Domain trap: delayed/hidden consequence and active mechanisms | F-1007/F-1004/F-1021 retained reviews | Current artifact **Provisional** |
| Domain trap: known/false/suspected/unknown; missing evidence is not absence | Fact-state deterministic tests and F-1012/F-1020 reviews | Machinery **D-pass**; current output **Provisional** |
| Domain trap: two urgency overrides only on confirmed facts; precautionary policy labelled | Urgency fact-state matrix in regression evidence | **D-pass** |
| Domain trap: summaries retain measurements, repeats, partner state and uncertainty; avoid uniform middle scores | Semantic assessments and X01 diagnostics | Latest Copilot artifact **Provisional**; historical direct-Azure artifact **Fail** |

## Acceptance scenario status (A01–X02)

| ID | Status | Best retained evidence / limitation |
|---|---|---|
| A01 | **D-pass; final pending** | Mutation/coverage checks in `triage\native-v2-fault-evidence-1\report.json`; no final root output |
| A02 | **D-pass** | Malformed/structural recovery and two-attempt accounting in the same report |
| A03 | **D-pass** | Exhaustion, nonzero failure, old-output preservation and no partial publication |
| A04 | **Provisional** | Seeded contradiction calibration passes; real reviews remain AI-only and adjacent scores may remain reviewable |
| B01 | **D-pass for delivery, not use** | `triage\history-context-2\verification.json` and captured provider contexts; delivery does not prove model use |
| B02 | **Inconclusive** | `knowledge\copilot-b02-1\observation.json`: positive cases unassessable; negative control not fully calibrated |
| B03 | **Documented / D-pass checks** | `DESIGN.md` §B and source-owner promotion evidence |
| C01 | **D-pass** | 100-cell grid, anchors, monotonicity and versioned formula |
| C02 | **Documented / D-pass checks** | Worked asymmetric corners and rejected mean/max in `DESIGN.md` §C |
| C03 | **D-pass** | Confirmed/false/unknown override and precautionary fact-state matrix |
| C04 | **Mixed** | Pre-v8 Copilot artifact provisional; direct-Azure v5 failed F-1010 grounding; no later accepted Azure result |
| D01 | **Provisional** | Pre-v8 F-1012 ticket has explicit review/verification; no expert adjudication |
| D02 | **D-pass** | Invalid identity, unassessable scores, missing partner and no-default-score fault tests |
| D03 | **Provisional** | Pre-v8 F-1016/F-1008/F-1009 reviews pass AI-only cards; direct-Azure F-1009 remained pending |
| D04 | **Documented; system gate pending** | Limits, exclusions, assumptions and AI disclosure exist; final output/provider evidence incomplete |
| X01 | **Fail, non-eligible** | Pre-v4 F-1016 drift changed this-week→this-month; a pre-v8 gpt-6 attempt failed closed before repeat; a later clean-detached gpt-6 pair completed but reviewed 38/39 then 37/39 and recorded `x01_result=fail`. Stable-band policy-v3/v4/gpt-6.1 observations do not rescue it |
| X02 | **Partial** | Clean deterministic reproduction **D-pass**; final provider cost/semantic evidence and root artifact **Pending** |

## Deterministic commands and observed results

Run from the repository root on Windows/Python 3.11+:

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.validate
```

The retained clean-checkout observation is **T**
`reproducibility\clean-235bdd1.json`: revision
`235bdd1d57d87cfb7c4669adf6a7b56aa50011a9`, Python 3.11.9, isolated editable
install; 276 production tests ran (272 passed, 4 environment-dependent skips);
126 evaluator tests passed; reference validation passed for 21 findings, 18
equipment rows and reference v1.2. It performed no live inference, semantic
review or publication. The pre-stabilized-v8 dirty-worktree behavior demonstration is **W**
[`design-behavior-demonstration.json`](design-behavior-demonstration.json):
125 component tests, 63 inference/provider tests, 81 knowledge/context tests,
126 evaluator tests and frozen-reference validation passed in about 77 seconds.
It binds its local report by hash and records the evidence-collector correction,
but predates the current v8 production changes and the 127-test evaluator suite.
It is historical, not a clean-checkout, current-v8 or live-inference acceptance
result.

`readiness.json` remains a reference-v1.2/layout-1 historical summary. No
reference-v1.3 readiness report or current-v8 clean-checkout result has been
recorded.

## Experiment ledger

| Experiment / retained location | Outcome | Eligibility and current interpretation |
|---|---|---|
| Offline component, fault, package and source-first phases, **T** `triage\native-v2-fault-evidence-1\report.json`, `triage\native-v2-regression-2\report.json`, `knowledge\source-integration-readiness.json` | Deterministic passes plus retained earlier fixture/regression failures | Software evidence only; mocks do not establish model quality |
| B02 controlled Copilot probe, **T** `knowledge\copilot-b02-1\`; later v1.2 policy-v6 run, **W** `knowledge\copilot-b02-policy-v6-reference-1.2\` | **Inconclusive/fail**: likelihood-only overlays left impact unsupported, so positive cases were unassessable; negative controls remained unchanged | Non-eligible knowledge experiments; test-informed reference v1.3 adds shared synthetic impact 3 and varies only likelihood, but B02 has not been rerun |
| Early Copilot integration/correction phases, **T** `triage\copilot-integration-1\observation.json`, `triage\copilot-correction-3\verification.json` | Initial integration failures followed by a validated local correction | Historical, non-eligible |
| Policy-v3 test, **T** `triage\history-policy-v3-test-phase\test-1\` | **Fail 22/24** | Frozen failed observation retained |
| Disclosed corrected test regression, **T** `triage\final-test-regression-phase\test-regression-1\` | **Provisional 24/24** | Test-informed, AI-only, non-eligible |
| Pre-v4 development repeat, **T** `triage\final-regression-phase-4\` | **Fail**: F-1016 drifted 1/9/7→1/8/6, this-week→this-month; repeat 38/39 | Retained failure; led to the disclosed test-informed high-impact SCE floor |
| Policy-v3 development repeat, **T** `triage\history-policy-v3-phase\x01-review.json` | **Provisional pass**: numeric drift, 13/13 urgency/review gates stable; 39/39 both outputs | Non-eligible, AI-only historical comparison |
| Policy-v4 development/repeat, **T** `triage\policy-v4-final-phase-2\` | **Provisional 39/39** per output; 5 numeric values drifted across 4 findings while 13/13 urgency bands and review flags remained stable | Non-eligible development evidence |
| Partition composites, **T** `triage\final-composite-21\` and `triage\policy-v4-composite-21\` | **Provisional 63/63** | Separate partitions, not one inference; not acceptance evidence |
| Direct-Azure model exploration, **T** `triage\native-strict-o4\`, `triage\native-strict-codex\`, `triage\native-strict-model53\` | Structural and/or semantic failures; gpt-5.3 development also required repairs and failed review | Historical failures; older policy/knowledge |
| Initial all-21 phase, **T** `triage\final-all-21-phase\observation.json` | **Fail**, zero sends, zero tickets | Preflight/configuration failure; non-eligible |
| Dedicated chat final phases, **L** `.delivery-state\final-run-v2`, `.delivery-state\final-run-v3`, `.delivery-state\final-run-v4` | **Fail closed** at F-1012 action overflow, F-1007 duplicated activities, then F-1002 overflow; no publication | Local ignored evidence; historical raw dependencies may be **A** |
| gpt-5.6-sol preflights, **L** `.delivery-state\azure-sol-preflight`, `.delivery-state\azure-sol-overflow-preflight` | F-1001 validated after one repair; F-1002/F-1007/F-1012 validated first attempt | Local-only preflight, not all-21 acceptance |
| Direct-Azure all-21 v5, **T** `triage\direct-azure-final-sol-v5\` with new **W** `usage-summary.json` (local run: **L** `.delivery-state\final-run-sol-v5`) | Policy v4; 21 contract-valid tickets in 24 requests; semantic **Fail 60/63**: F-1010 grounding and F-1020 planning failed, F-1009 pending; 1,289,873 prompt + 45,878 completion tokens, including 16,474 reasoning | Closest completed direct-provider run; not accepted; USD unverified because no deployment tariff was recorded |
| Policy-v5 token preflight, **L** `.delivery-state\policy-v5-deluge-preflight` | **Fail closed**: 4096 completion tokens exhausted by reasoning | Local-only failure; no ticket |
| Policy-v5 8192-token preflight, **L** `.delivery-state\policy-v5-deluge-preflight-8192` | Two cases validated | Local-only preflight |
| Direct-Azure all-21 v6, **L** `.delivery-state\final-run-sol-v6` | **Fail closed** after 19 validated findings; F-1020 exceeded 120 s, F-1021 not attempted; no publication | Acceptance-eligible configuration attempt, failed |
| Copilot gpt-6.1-sol all-21, **T** `triage\copilot-gpt61-policy-v5-all21\` | **Fail 62/63**: F-1015 planning | Non-eligible; AI-only reviewer |
| Copilot gpt-6-sol pre-correction all-21, **T** `triage\copilot-gpt6-policy-v5-all21\` | **Provisional 63/63**, 27 sends | Source changed during run; not current-code or eligible |
| F-1015 guidance spot check, **T** `triage\copilot-gpt61-f1015-guidance\` | One case validated | Test-informed, not all-21 and not held out |
| Pre-v8 policy-v5 Copilot all-21, **T** `triage\copilot-gpt6-current-all21\` | Revision `235bdd1`; 21 tickets, 25 application sends, 4 failed sends; contract pass; calibrated AI-only **63/63** | Selected after multiple model attempts and a disclosed F-1015 correction on the same 21 non-blind cases; non-eligible; HTTP retries and USD cost unknown |
| Later pre-v8 gpt-6.1 all-21, **W** `triage\copilot-gpt61-current-all21\` | First run **failed** at F-1015 after 15 sends; retry produced 21 tickets in 23 sends after two malformed-JSON repairs; two separate calibrated AI-only reviews each **failed 60/63** | Retained contradiction to the earlier best result; overlapping F-1005/F-1015 planning failures; non-eligible, no root publication |
| Pre-v8 gpt-6.1 X01 repeat, **W** `triage\copilot-gpt61-current-x01\` | Same 13-case plan/configuration: 3/39 impact values drifted; urgency scores, bands and review flags unchanged; one threshold rule trace changed; both outputs reviewed 39/39 | **Provisional pass**, non-eligible and AI-only; one repeat, backend cache uncontrolled, threshold fragility retained |
| Pre-v8 gpt-6 X01 first run, **W** `triage\copilot-gpt6-current-x01-failure\` | **Fail closed** at F-1017 after malformed JSON on both attempts; 17 sends across 12 attempted findings, 4 repairs succeeded; repeat not executed; no output | Did not complete the 13-case X01 plan; transient 02/03 edits recorded by execution were reverted and production does not consume them |
| Later pre-v8 gpt-6 X01 completed pair, **T** `triage\copilot-gpt6-current-x01\` | Two contract-valid 13-ticket outputs; first review `needs_review` 38/39, repeat **failed** 37/39 on F-1003/F-1005 planning; `x01_result=fail` | Matching-model evidence that the separate 63/63 all-21 artifact did not close X01; AI-only and non-eligible |
| Direct-Azure all-21 v7, **L** `.delivery-state\final-run-sol-v7\run.json` | **Abandoned/stale** after F-1001; F-1002 remains reserved, 2/42 ledger attempts consumed; source hash predates current `assessment.py`; no output or semantic review | Pre-v8 mutable local state, not result evidence |

## Artifact-location legend

- **Tracked retained evidence:** paths beneath `eval\results`; compact reports,
  ledgers, reviews, calibration and selected exact outputs are reviewable in Git.
- **Local ignored live state:** `.delivery-state\...`; may contain requests,
  responses, receipts and active ledgers. It is machine-local, mutable and not
  submission evidence unless curated into a tracked, hash-bound report.
- **Local archives:** `.artifacts\evidence\...`; ignored and removable by
  `git clean -fdx`.
- **Archive-only dependencies:** raw historical payloads removed from HEAD after
  lossless curation. Their paths, hashes and inventories are in **T**
  `artifacts-manifest.json`. That manifest is a timestamped curation snapshot,
  not a live inventory of evidence added later.
- **Historical Git recovery:** full pre-curation tracked results are recoverable
  from revision `3997d00`; restore to staging, never over live ledgers.

## Limitations and archive recovery

No retained result is independent domain-expert certification. The split is
non-blind and AI-assisted; semantic reviewers are AI-only. A calibration pass on
two seeded contradictions does not prove general reviewer accuracy. Unknown
provider retries or cost are not zero. Historical results remain bound to their
recorded code, prompt, model, knowledge and policy hashes.

For archive hashes, verified-copy status and embedded per-file inventories, use
**T** [`artifacts-manifest.json`](artifacts-manifest.json). Restore historical
tracked files from revision `3997d00` into a staging directory; never extract an
archive over live ledgers or current evidence. The local and backup archive paths
are not a durable shared artifact service.
