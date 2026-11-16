# Initial Investigation: Inspection Finding Triage

## Purpose and work completed

This report records the initial requirements and domain investigation before
implementation. It separates explicit requirements from interpretations and
unresolved assumptions.

Work completed:

- Read the exercise brief and both reference documents.
- Read the example ticket and both input CSVs.
- Identified scoring constraints, cross-finding dependencies, and missing evidence.
- Recorded implementation implications and questions that need explicit decisions.

No triage system, generated tickets, or automated validation has been implemented
at this stage. The observations below are qualitative, not final ticket scores.

## Source material

The supplied package was reviewed at
`.\candidate-pack\candidate-pack`.
Paths below are relative to that package:

| Source | Role |
|---|---|
| `README.md` | Scope, scoring definitions, constraints, deliverables, and assessment criteria |
| `data/inspection_findings.csv` | 21 observations, dated 2-22 June 2026 |
| `data/equipment_registry.csv` | 18 equipment records, including scores, redundancy, and engineer comments |
| `reference/domain_knowledge.md` | Written record of current triage practice |
| `reference/example_ticket.json` | Required ticket shape and an example of evidence-based reasoning |
| `reference/README.md` | Clarification that example scores are illustrative and domain knowledge must inform decisions |

## 1. Understanding the assignment

The operational problem is to turn inspection observations into draft maintenance
tickets that an integrity engineer can review. The output must support a planning
meeting without requiring the reader to reopen each inspection record.

The required transformation is:

`findings + equipment context + domain knowledge -> draft tickets`

This is not just extraction or paraphrasing. The system must assess functional
failure likelihood, failure consequences, and action urgency, while preserving
evidence and exposing uncertainty.

The assessment explicitly prioritizes:

1. System design and structured-output handling, especially model/code boundaries.
2. Maintainable encapsulation of domain knowledge.
3. Output quality, defensible scores, and grounded rationales.
4. The design explanation in `DESIGN.md`.

Interpretation: a small, explainable pipeline is more relevant than a broad
application. The expected effort is 4-6 hours; no UI or deployed service is required.

## 2. Explicit implementation and delivery requirements

| Area | Requirement |
|---|---|
| Coverage | Generate one ticket per input finding, covering all 21 findings |
| Output | One `tickets.json` with `generated_at`, `tickets_generated`, and `tickets` |
| Identity | `TKT-####` ticket IDs; finding and equipment references must match inputs |
| Text | Summary and recommended action each at most 300 characters |
| Scores | Integer likelihood, impact, and urgency scores from 1 to 10, each with a rationale |
| Review | Boolean `review_required`; a reason is required when true |
| Summary | Explain what is wrong, on what equipment, and why it matters; do not merely restate the observation |
| Action | Name a specific activity; "investigate further" is insufficient |
| Urgency | Compute from likelihood and impact using a documented function, not a direct model score |
| Urgency constraints | Neither a plain average nor a plain maximum; explain both asymmetric corners and support overrides |
| Generation | No hand-written or hand-corrected ticket content |
| Execution | One documented end-to-end command, dependency manifest, and reproducible cost |
| Tooling | Provider inference SDKs and schema libraries allowed; high-level AI orchestration frameworks prohibited |
| Security | No committed API keys |
| Submission | Source, generated tickets, `DESIGN.md`, and Git commit history |

`DESIGN.md` must explain schema enforcement, malformed responses, structural
violations, valid-but-incorrect scores, and failure to produce a ticket. It must
also cover knowledge maintenance, urgency derivation, human deferral, exclusions,
assumptions, and AI assistance including where its suggestions were overridden.

## 3. Scoring principles extracted from the domain notes

### Likelihood is about the equipment performing its function

- An already confirmed functional failure belongs at the top of the range.
- An ongoing trend, repeated failure, active degradation, or late-stage detection
  increases concern.
- Remaining design margin, a measurement within acceptance criteria, or equipment
  not required in service can reduce concern.
- `reliability_score` runs in the opposite direction: 10 means highly reliable.
  It is a prior, not a final likelihood score or a prescribed arithmetic conversion.

### Impact is about the consequences of failure

- Evaluate the equipment's function, available alternatives, protection layers,
  delayed consequences, and escalation potential.
- Safety Critical Elements (SCEs) are assessed against the major accident they
  protect against, not repair cost.
- Credit redundancy only when the alternative is available and capable.
- `criticality_score` is a prior, not a final impact score.
- A degraded 2oo3 arrangement is not the same as a defeated arrangement.

### Urgency is a separate, code-derived decision

The domain notes map urgency bands to action windows:

| Score | Action window |
|---|---|
| 9-10 | Today |
| 7-8 | This week |
| 5-6 | This month |
| 3-4 | Next planned shutdown |
| 1-2 | Backlog |

The derivation must not treat a near-certain inconsequential failure as equivalent
to a low-likelihood major-accident exposure. In particular, the notes say a
low-likelihood, high-impact SCE finding still needs attention this week.

Two conditions override the derived value to immediate action:

1. A protection layer is impaired without a recorded deviation.
2. Evacuation capacity is below the personnel-on-board (POB) count.

The package does not prescribe a complete numeric scoring rubric or an urgency
formula. Both require explicit design decisions. Example ticket F-1005 scores
likelihood/impact/urgency as 10/7/9, but the brief explicitly says this is one
defensible assessment, not a reference answer.

## 4. Data observations and decision implications

| Evidence | Domain connection | Implication and limit |
|---|---|---|
| F-1001: compressor vibration rises from 2.1 to 4.6 mm/s over six weeks without plateauing; registry says no spare | A continuing trend matters before an alarm; absence of redundancy affects consequences | Do not dismiss because the alarm threshold has not been reached. The text does not establish a confirmed compressor failure. |
| F-1002: PSV hissing and hydrocarbon smell below set pressure; PSV-1310 comment treats passing/weeping as protection impairment | Detection by ear/smell can indicate advanced damage; relief protection has compliance implications | Address potential protection impairment, not just nuisance noise. Passing is indicated, but its precise mechanism is not proven. |
| F-1003 and F-1017: firewater pump B initially fails to start; pump A delivers 9.2 barg against 11 barg design | Redundancy must be checked across findings | Neither pump can simply be assumed to provide healthy backup. This is not evidence that both pumps are completely unavailable; pump A's flow was not measured. |
| F-1004: hydrocarbon line measures 6.2 mm against 7.4 mm minimum, with saturated insulation | Acceptance limits and active corrosion mechanisms matter | Preserve the below-minimum measurement in the assessment. Adjacent acceptable windows do not negate this local finding. |
| F-1005: detector fails two independent gas tests; other two heads respond | Confirmed functional failure; 2oo3 degradation rather than total defeat | Separate the failed head's likelihood from the group's remaining protection. Do not equate SCE status with automatic maximum impact. |
| F-1006: crane rope has six broken wires versus a discard criterion of ten | A measurement within its acceptance criterion moderates likelihood | Retain the margin and poor lubrication as evidence. The supplied criterion does not establish that the rope already meets discard conditions. |
| F-1007: third inhibitor-pump trip this month and roughly ten days of intermittent injection | Repeat failure and delayed consequences | Do not score impact low just because production continues. Downstream corrosion consequences can emerge later. |
| F-1008 versus F-1009: confirmed 45 mm crack at a primary structural connection versus coating breakdown on the same equipment | Failure mechanism matters more than dramatic wording or shared equipment criticality | Treat these as distinct findings; neither apply cosmetic-backlog treatment to the crack nor automatically assign the crack's severity to coating damage. |
| F-1010: temporary refuge differential pressure is 27 Pa against a 50 Pa minimum | Hidden protection-layer consequences | HVAC here is a major-accident protection function, not ordinary building comfort. The exact cause remains suspected. |
| F-1011 and F-1020: poor deluge delivery above producing wellheads; a north-quadrant branch valve is later found closed without an impairment entry and reopened | Actual delivery matters more than healthy header readings; impairment status and chronology matter | Relate the findings without asserting the valve was the sole cause. Reopening does not establish restored nozzle performance; current status requires confirmation. |
| F-1012: lifeboat certificate withheld and craft declared unavailable | Evacuation capacity must be compared with POB | Human review is needed, but the capacity-below-POB override cannot be established from the supplied data alone. Remaining certified capacity and POB are missing. |
| F-1013 and F-1018: duty level transmitter diverges; backup flatlines | Both legs of a duplicated arrangement have findings | Do not recommend switching blindly to the backup or credit it as healthy redundancy. The dates require an explicit batch-state assumption. |
| F-1014: test separator internals damaged, shell sound, equipment not in service and bypass available | Required service state and genuine bypass capability moderate priority | Do not treat this like an operating pressure-boundary failure. Repair requirements before future use still matter. |
| F-1015 and F-1016: dirty gauge glass with normal control; illegible PSV tag with certification confirmed in date | Distinguish visibility/documentation defects from demonstrated functional failure | Do not invent failed level control or expired PSV certification. These findings do not establish those failures. |
| F-1019: loose compressor-line cladding with explicitly no process concern | Finding-specific consequences differ from the equipment's main production function | Address the stated dropped-object hazard without assuming compressor functional failure. |
| F-1021: damp insulation and rust staining on the separator; underlying surface not visible | Active concealed degradation is possible; registry requests integrity review for pressure-boundary concerns | Name a concrete inspection activity to establish condition. Do not claim measured wall loss or a leak when neither has been observed. |

## 5. Unresolved assumptions and design decisions

These are not additional rules supplied by the company:

- **Assessment time:** findings span several dates. Define whether the run treats
  the batch as an unresolved set at a stated assessment date. The generation
  timestamp alone should not silently turn the exercise into months of assumed
  unattended degradation.
- **Cross-finding state:** absent repair records do not prove a defect was repaired.
  Conversely, historical symptoms do not prove complete present unavailability.
  Preserve that distinction when checking redundancy.
- **Scoring calibration:** define consistent score anchors without presenting an
  invented 1-10 rubric as company policy.
- **Review policy:** the example routes every SCE ticket to a human. Adopting that
  generally is a defensible policy, but must be documented. Clarify how the flag
  relates to the brief's statement that a human approves the draft.
- **Missing operational records:** no full impairment/deviation register, POB
  count, or remaining lifeboat capacity is supplied. Distinguish explicitly absent
  records, such as F-1020's missing entry, from information simply not provided.
- **Failed generation:** define how to surface an unproducible ticket without
  silently skipping a finding, fabricating a score, or claiming complete output.

## 6. Implementation implications, not completed features

- Give the assessment access to the relevant registry record, its engineer
  comment, domain rules, and related findings, rather than assessing isolated rows.
- Keep evidence-based likelihood and impact assessment separate from deterministic
  urgency calculation and escalation.
- Validate both structure and input/output consistency; valid JSON cannot establish
  that a score is semantically correct.
- Make domain-policy changes traceable. The PSV scoring-change scenario in the
  brief should not require hunting through unrelated orchestration code.
- Use focused checks for the demonstrated failure modes: inverted reliability,
  falsely credited redundancy, SCE overstatement, missed thresholds, and unsupported
  override claims.
- Preserve uncertainty in the rationale and human-review path instead of hiding it
  behind uniform mid-range scores.

No language, provider, numeric formula, orchestration layout, or retry policy has
been selected by this investigation.

## AI assistance

GitHub Copilot assisted with reading and synthesizing the supplied package and
drafting this report. Interpretations and proposed implementation implications are
identified separately from explicit requirements. This document does not claim
independent offshore engineering verification or completed implementation.
No implemented scoring policy or engineering decision has yet been overridden;
later implementation decisions and departures from AI suggestions should be
recorded in `DESIGN.md`.
