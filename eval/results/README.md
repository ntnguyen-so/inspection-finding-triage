# Evaluation evidence and status index

This is the single reviewer-facing index for observed evaluation evidence. Read
`DESIGN.md` for the system design and this file for what was actually exercised.
Specifications such as `eval\spec\acceptance.json` define gates; they are not
results.

> **GATE BANNER — GENERATED DELIVERABLE, HUMAN APPROVAL PENDING.** Root
> `tickets.json` now contains all 21 findings and passes the deterministic
> contract. `triage\structured-planning-v31\final` records the exact run,
> reviewer judgments and output hash. The checklist-bound primary AI review is
> 63/63 after seeded calibration; human/domain approval has not occurred.
> Six tickets require exceptional review. V29 and v30 are retained failed
> test-informed iterations; v31 development X01 passed after visible drift
> adjudication. Reference-1.3
> B02 is a bounded causal-influence/isolation pass. Clean-checkout reproduction
> has not been run. The receipt states `acceptance_eligible=false`. Observed
> runtime was 617.75 seconds; actual Copilot usage/USD and hidden HTTP attempts
> are unknown. Human approval is always required.

Production code has changed since the latest clean, isolated deterministic run at
revision `235bdd1`. The evidence collector was subsequently corrected and rerun
in a dirty worktree; that is retained historical behavior evidence, not a
current-v11 clean-checkout observation.

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
| Brief §3: 21-ticket JSON, identities, fields, lengths, L/I/U and planning text | Root `tickets.json`; **W** `triage\structured-planning-v31\final\primary-reviews.json`; deterministic fault evidence | Root artifact **D-pass** for the output contract and exact coverage; calibrated primary AI review 63/63 |
| Brief §5: own orchestration, bounded retry, one command, no keys, low reproducibility cost | **W** `triage\structured-planning-v31\final\evidence\run.json`; **T** package/reproduction evidence | One-command delivery completed in 617.75 s and 21 application sends. Actual Copilot USD allocation and hidden HTTP attempts are unknown |
| Brief §6A: structured output, malformed/structural/semantic handling, fail-closed publication | **W** `design-behavior-demonstration.json`; **T** `triage\native-v2-fault-evidence-1\report.json`; **T** `triage\direct-azure-final-sol-v5\assessment-report.json` | Structural/recovery paths **D-pass**; valid-but-wrong output was retained as **Fail**, not repaired silently |
| Brief §6B: domain knowledge, engineer comments, PSV maintenance path | Source lifecycle/delivery evidence; **W** `triage\v10-calibration\b02-execution`; exploratory `triage\knowledge-release-change-v1-*` through `v4-*` | Delivery/lifecycle **D-pass**; reference-1.3 B02 is a bounded influence/isolation pass; v4 demonstrates one actual immutable release replacement after three disclosed failed iterations |
| Brief §6C: code-derived urgency, corners, overrides, alternatives | **W** `design-behavior-demonstration.json`; **T** `triage\native-v2-regression-2\report.json`; `DESIGN.md` §C | Formula, monotonic grid, corners and fact-state rules **D-pass**; policy is prototype engineering choice, not calibrated truth |
| Brief §6D: deferral, human review, deliberate exclusions | **T** `triage\native-v2-fault-evidence-1\report.json`; **T** `triage\native-handoff-system-summary.json`; `DESIGN.md` §D | Failure/deferral machinery **D-pass**; output-level judgments remain model/reviewer-limited |
| Brief §6 assumptions and AI assistance/overrides | `DESIGN.md` “High-impact assumptions” and “AI assistance and candidate overrides” | Documented; historical test-informed changes and rejected suggestions disclosed |
| Brief §7: `tickets.json`, source, manifest, run command, DESIGN, Git history | Root `tickets.json`, `pyproject.toml`, `README.md`, `DESIGN.md`, Git log; current delivery summary | Required generated file is present. Semantic/human approval and exact-code reproducibility remain pending, so this is not an accepted frozen result |
| Brief §8.1: model/code boundary and structured-output handling | `DESIGN.md` §A/C; deterministic reports above | **D-pass** for implemented boundary; final provider/output acceptance pending |
| Brief §8.2: knowledge encapsulation/maintainability | Source-first evidence above; `docs\05_KNOWLEDGE_DESIGN_DECISION.md`; `docs\09_KNOWLEDGE_CHANGE_STUDY.md`; reference-1.3 B02 | Lifecycle, module boundary and edit surface **D-pass**; bounded influence and one exploratory release-change observation demonstrated, general correctness not certified |
| Brief §8.3: output quality and defensibility | Current v31 root assessment; retained historical reviewer sensitivity | Checklist-bound primary review is 63/63 after seeded calibration; it remains AI-only, with reviewer model/prompt identity not exposed by the agent runtime |
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
| A01 | **D-pass; root produced** | Mutation/coverage checks plus root `tickets.json`: exact 21-ticket contract passes |
| A02 | **D-pass** | Malformed/structural recovery and two-attempt accounting in the same report |
| A03 | **D-pass** | Exhaustion, nonzero failure, old-output preservation and no partial publication |
| A04 | **Provisional** | Seeded contradiction calibration passes; real reviews remain AI-only and adjacent scores may remain reviewable |
| B01 | **D-pass for delivery, not use** | `triage\history-context-2\verification.json` and captured provider contexts; delivery does not prove model use |
| B02 | **Bounded pass** | `triage\v10-calibration\b02-execution`: positive L6/I3→L8/I3, code stable, both tag-only negative controls semantically excluded the synthetic rule |
| B03 | **Documented / D-pass checks** | `DESIGN.md` §B and source-owner promotion evidence |
| C01 | **D-pass** | 100-cell grid, anchors, monotonicity and versioned formula |
| C02 | **Documented / D-pass checks** | Worked asymmetric corners and rejected mean/max in `DESIGN.md` §C |
| C03 | **D-pass** | Confirmed/false/unknown override and precautionary fact-state matrix |
| C04 | **Mixed** | Pre-v8 Copilot artifact provisional; direct-Azure v5 failed F-1010 grounding; no later accepted Azure result |
| D01 | **D-pass machinery; output provisional** | V9/v10 failures exposed suppressed material review; v11 restores `bool(rules)`, verification activities and 20/21 review routing |
| D02 | **D-pass** | Invalid identity, unassessable scores, missing partner and no-default-score fault tests |
| D03 | **Provisional** | Pre-v8 F-1016/F-1008/F-1009 reviews pass AI-only cards; direct-Azure F-1009 remained pending |
| D04 | **Documented; system gate pending** | Limits, exclusions, assumptions and AI disclosure exist; final output/provider evidence incomplete |
| X01 | **Provisional pass** | V31 development pair: both outputs reviewed 39/39; 13/13 urgency bands and review flags matched; visible numeric/rule drift was adjudicated without selecting a better run or finding unsupported claims |
| X02 | **Partial** | V31 root artifact, hashes, configs, two publication receipts and 617.75 s final runtime exist; actual Copilot USD/HTTP attempts and clean-checkout reproduction remain unresolved |

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
| B02 controlled Copilot probe, **T** `knowledge\copilot-b02-1\`; later v1.2 policy-v6 run, **W** `knowledge\copilot-b02-policy-v6-reference-1.2\` | **Inconclusive/fail**: likelihood-only overlays left impact unsupported, so positive cases were unassessable; negative controls remained unchanged | Non-eligible historical experiments; test-informed reference v1.3 later corrected and reran this probe, recorded below |
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
| Stabilized-v8 controlled series, **T** `triage\v8-reliability\summary.json` | **3/3 completed**, 21/23/21 sends, two malformed responses repaired; exact L/I/U agreement 15/21, 19/21, 17/21; bands 21/21, review flags 20/21; primary reviews retain 9/4/3 pending dimensions and no fail | Hash-pinned dirty-worktree evidence; sensitivity disagreement retained; clean-freeze/reproducible-cost gate inconclusive |
| Fresh v8 delivery, **W** `triage\v9-calibration\comparison\v8-baseline\tickets.json` and `triage\v8-reliability\delivery-*` | 21 drafts in 21 sends; contract pass; primary AI review 61/63; 635.64 s; equivalent OpenAI API estimate US$2.37 | Superseded root artifact retained byte-for-byte; human approval was pending and actual Copilot USD/hidden HTTP attempts remain unknown |
| V9/v10 behavior calibration, **W** `triage\v9-calibration` and `triage\v10-calibration` | Four all-21 runs completed; v9 23/22 sends, v10 21/21; every primary review failed mandatory uncertainty routing; v10 did not reduce concentration | **Rejected**, retained with exact policy snapshots and full negative evidence |
| Reference-1.3 B02, **W** `triage\v10-calibration\b02-execution` | Four conditions completed in four sends; positive L6/I3→L8/I3; both F-1016 negative controls excluded the synthetic passing rule | **Bounded pass** for causal influence/isolation; synthetic and non-eligible |
| Actual knowledge-release replacement, `triage\knowledge-release-change-v1-*` through `v4-*` | V1 harness failure; v2/v3 knowledge-policy conflicts rejected as unassessable; v4 completed L4/I7→L8/I7 with both tag controls L2/I7. Four v4 sends, 100.859 s, 124,075 input and 5,330 output tokens; illustrative API equivalent US$0.3015 | **Exploratory bounded lifecycle observation**, tuned after retained failures; not a prospective B02 pass, calibrated semantic review or domain certification |
| Official-store full-batch KB edit, `triage\knowledge-kb-edit-v1-*` | Existing editor/CLI imported, amended, reviewed and published the source; two baseline and two revised 21-ticket runs repeated test finding F-1002 L7/I8/U8→L9/I8/U9 while F-1016 stayed L2. The study exposed and fixed amendment scope loss; `knowledge-kb-edit-v1-scoped` retained structured PSV scope and repeated F-1002 L9. | **Test-informed delivery/influence and editor-regression observation**, not acceptance: source was tuned against a test case, non-target variance/reference conflict remain, semantic review is pending, working candidate reset and no production promotion |
| V11 root delivery, **W** `triage\v11-delivery` and `..\..\tickets.json` | 21 drafts in 21 sends; contract pass; primary AI review 54/63 with zero fail; 688.11 s; equivalent API estimate US$2.37 | Preregistered zero-fail gate passed; human approval and clean reproduction pending |

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
