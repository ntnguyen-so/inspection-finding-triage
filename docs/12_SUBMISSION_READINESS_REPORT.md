# Submission readiness report

## 1. Decision

The promoted root `tickets.json` is the byte-identical v31 delivery with
SHA-256
`2bb8d0f34da36142042c6f5f983622be358e45fc4690378a935e28ba189f1f98`.
It contains all 21 supplied findings, passes the deterministic output contract,
has a verified atomic-publication receipt, and received a calibrated
exact-artifact AI review of 63/63 pass.

This closes the requested prototype-output work. It does **not** convert the
drafts into approved maintenance instructions or independent domain
certification. Human approval remains mandatory, and hidden provider HTTP
attempts plus actual Copilot cost remain unknown.

## 2. Candidate Brief requirements and evidence

| Requirement | Final evidence | Result |
|---|---|---|
| Complete structured output | Root `tickets.json`; v31 final receipt | 21/21, contract pass |
| Grounded L/I and planning | v31 `final\primary-reviews.json` | 63/63 provisional pass |
| Code-derived urgency | `triage-policy-v16`; deterministic tests | Pass |
| Selective exceptional review | Six explicit routes with `Why:` and checks | Pass; below target of seven |
| Fail-closed publication | v27 failure retained; v31 atomic receipt verified | Pass |
| X01 stability | v31 development pair and adjudication | Pass under frozen rule |
| Reproducibility/accounting | Hashes, configs, receipts, run evidence | Partial: hidden HTTP/cost unknown |
| Human authority | Every ticket remains a draft | Required outside generation |

## 3. Final behavior

The urgency distribution is U4=2, U5=1, U6=3, U7=2, U8=6 and U9=7. Fifteen
tickets are in the weekly-or-faster bands, down from the earlier 19/21
concentration. This is an observed result, not a histogram target or calibrated
risk truth.

Exceptional prequeue review is required for six findings:
F-1002, F-1008, F-1012, F-1013, F-1017 and F-1020. Every draft still receives
ordinary human approval. The exceptional flag is reserved for unresolved
protection, evacuation, redundancy or restoration decisions and carries a
specific reason plus verification activity.

## 4. Closure of the requested defects

| Issue | Final disposition |
|---|---|
| F-1007 only checked the diaphragm | Closed: action checks the diaphragm and full injection path, then proves sustained dose/pressure |
| F-1012 omitted recertification | Closed: class recertification is required before return to use |
| F-1019 mixed compressor loss and dropped-object bases | Closed: L/I both assess local cladding detachment and personnel strike exposure |
| Review queue saturation | Closed for the requested target: 6/21 exceptional reviews |
| Review reasons were vague | Closed: each flagged ticket contains `Why:` and concrete checks |
| F-1017 treated partial pressure evidence as confirmed duty failure | Closed: L6/I8/U8, suspected protection impairment and exceptional review |
| F-1011 omitted later valve chronology | Closed: v4 projection exposes the model-selected F-1020 reason and exact source-labelled quote without transferring its fact state |
| X01 repeat stability | Closed: 13/13 bands and review flags match; visible numeric/rule drift was adjudicated with no unsupported claim |
| Post-publication proof | Closed: output reread/hash and atomic `publication.json` receipt bind the final bytes |

## 5. Controlled failures and rejected changes

The retained history is part of the evidence:

- v27 failed closed at F-1021 because schema limits contradicted the prompt;
  no partial batch was published.
- v28 generated 21 tickets and 4 review flags, but its all-21 repeat was
  over-scoped and unstable.
- v29 passed development X01, but its first frozen all-21 semantic review failed
  F-1011 at 61/63. The artifact remains retained.
- v30 attempted a prompt-only chronology repair. It was rejected before a final
  run because development X01 changed two urgency bands and one review flag.
- v31 retained prompt v7 and used deterministic, source-labelled provenance
  projection. Its development pair passed after disclosed drift adjudication,
  and its single all-21 delivery passed 63/63.

These are disclosed test-informed iterations. No frozen card, expected answer,
split, fingerprint or evaluator rule was weakened to produce the result.

## 6. X01 evidence

The v31 pair processed the 13 development findings twice with identical input,
model, prompt, policy, context and implementation pins. Both publication
receipts are valid. All 13 urgency bands and review flags match.

Two findings had adjacent numeric drift, and F-1004 had a non-binding rule-set
drift. The same calibrated reviewer passed both artifacts 39/39 and adjudicated
the differences as supported, visible and non-material. No better run was
selected and no unsupported claim was found. This supports observed stability
for this configuration only; it is not a determinism guarantee.

## 7. Final evidence paths

- Delivery: `eval\results\triage\structured-planning-v31\final`
- Publication receipt: `final\evidence\publication.json`
- Final run evidence: `final\evidence\run.json`
- Exact-artifact review: `final\primary-reviews.json`
- Reviewer observation: `final\reviewer-observation.json`
- X01 comparison/adjudication:
  `structured-planning-v31\x01-development-comparison.json` and
  `x01-development-adjudication.json`
- Controlled-change record: `docs\08_BEHAVIOR_CALIBRATION_STUDY.md` section 15

## 8. Verification

The final implementation passed 325 production tests, 127 evaluator tests,
`python -B -m eval.validate`, `git diff --check`, the all-21 output contract,
the exact-artifact semantic assessor, receipt/hash verification and byte-for-byte
root promotion.

The remaining limitations are explicit: reviewer judgments are AI-only,
human/domain approval is outstanding, clean-checkout reproduction was not
repeated for this dirty-worktree revision, SDK-inclusive hidden attempts are
not exposed, and actual Copilot USD allocation is unknown.
