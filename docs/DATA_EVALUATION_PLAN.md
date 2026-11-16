# Data Understanding and Evaluation Contract

## Status and scope

Version 1.2 is a non-blind, AI-assisted reference for development and evaluation.
The freeze is effective only when `eval\split.json` says `frozen` and the offline
validator verifies its source and artifact hashes. It is not expert-certified
ground truth, a production safety assessment, or a completed triage system.

`EVALUATION_ACCEPTANCE.md` adds the A-D acceptance scenarios, output-assessment
commands, and prototype routing/urgency constraints in v1.1. It closes the
precautionary-policy gap noted below without claiming that the system exists.
The source package, evidence cards, and split membership are unchanged from v1.0.
Version 1.2 completes the coverage audit with stability and reproducible-delivery
scenarios; see the readiness section of `EVALUATION_ACCEPTANCE.md`.

This phase profiles the supplied data, identifies context dependencies, partitions
finding IDs, and specifies evidence-based expectations. It does not choose a
provider, calibrate numeric scores, implement inference or urgency, or generate
`tickets.json`. The intended effort for this phase is 60-90 minutes within the
brief's 4-6 hour exercise; no claim of measured effort is made.

The original review remains in `INITIAL_INVESTIGATION.md`. Its Downloads path is
historical; the current source of truth is the unmodified package at
`docs\candidate-pack\candidate-pack`, relative to the repository root.

## 1. Reproducible data profile

Run from the repository root on Windows with Python 3.11+; only the standard library
is used. The current manifest and validator use Windows paths; POSIX execution is
not supported by this phase:

```powershell
python -B eval\validate.py
python -B -m unittest discover -s eval -p "test_*.py"
```

The first command prints a freshly computed profile and checks the eval artifacts.
The second exercises failures that the artifact validator must detect. Neither
command calls a model or evaluates generated tickets. A successful artifact
validation does not establish semantic correctness of an annotation.
During drafting, `python -B eval\validate.py --allow-draft` explicitly permits
pre-freeze checks. The plain command must succeed to verify the final freeze.

| Check | Observed result |
|---|---|
| Finding rows / registry rows | 21 / 18 |
| Missing or blank CSV cells | 0 / 0 |
| Duplicate finding / equipment primary keys | 0 / 0 |
| Finding equipment IDs absent from registry | 0 |
| Finding equipment types inconsistent with registry | 0 |
| Invalid ID formats, ISO dates, score ranges, or SCE values | 0 |
| Finding date range | 2026-06-02 through 2026-06-22 |
| Registry SCE distribution | 10 Yes, 8 No |
| Explicit redundant partners missing from registry | LB-4101, referenced by LB-4102 |

Registry redundancy values comprise 11 `None` entries, one bypass, one voted 2oo3,
two duplicated instruments, and three N+1 entries. `None` is an explicit category,
not a null. Free-text redundancy is interpreted only to extract explicit tagged
partners for profiling; this is not a general redundancy parser.

The missing lifeboat partner is a context gap, not an orphan finding. All finding
foreign keys resolve. The package also lacks POB, certified remaining evacuation
capacity, a full impairment/deviation register, repair history, and a common
assessment timestamp. Absence of these inputs is not evidence that no deviations
exist, no repairs happened, or evacuation capacity is insufficient.

The profile establishes data integrity, not fitness for autonomous decisions.

## 2. Context and split boundaries

### Binding groups

These are curated evaluation boundaries, not a hard-coded runtime context builder.
The future system must derive applicable relationships from its inputs.

| Group | Findings | Why keep together? |
|---|---|---|
| Compressor train | F-1001, F-1016, F-1019 | Same compressor observations plus its discharge protection; distinguish process, documentation, and dropped-object issues |
| Firewater pair | F-1003, F-1017 | Explicit reciprocal N+1 relationship; both findings change credit for redundancy |
| Separator protection/control | F-1002, F-1013, F-1018, F-1021 | PSV and duty level transmitter explicitly serve V-1201; duplicated backup completes the control pair |
| Structure | F-1008, F-1009 | Same equipment, but crack and coating deterioration must remain distinct |
| Deluge | F-1011, F-1020 | Same north-quadrant system with a later valve-state change |

The other six findings are single-case groups. The manifest enumerates all groups
and their sources.

Grouping does not transfer a defect from one component to another. In particular,
F-1016 is not evidence of failed compressor relief protection, F-1009 is not a
second confirmed structural crack, and F-1019 does not establish compressor
functional failure.

### Context relationships that do not bind this split

PL-1002 feeds V-1201, and inhibitor injection protects downstream carbon steel.
These are real process relationships, retained in the shared registry. The supplied
findings do not establish that the specific pipe defect or pump fault caused the
separator, PSV, or transmitter symptoms. We do not merge the whole production
process merely because equipment is connected.

This is a design assumption: findings are grouped for shared state that directly
changes the assessment, not for every process adjacency. If a later system requires
cross-boundary finding evidence, revise the split and expectations explicitly
before claiming a frozen evaluation; do not silently load extra findings.

### Split decision

| Partition | Finding IDs | Cases / groups |
|---|---|---|
| Development | F-1001, F-1003, F-1004, F-1005, F-1006, F-1007, F-1008, F-1009, F-1010, F-1012, F-1016, F-1017, F-1019 | 13 / 9 |
| Test | F-1002, F-1011, F-1013, F-1014, F-1015, F-1018, F-1020, F-1021 | 8 / 4 |

This revises the preliminary conversation split: the whole V-1201 protection/control
group stays in test, while the structural pair moves to development. Keeping only
the transmitter pair together would miss the host-vessel and PSV relationship.
The 13/8 ratio is incidental, not statistically optimized.

Development exercises a redundant pair, repeated findings on an asset, confirmed
functional failure, numeric acceptance limits, delayed consequences, SCE protection,
and uncertain evacuation capacity. Test exercises another redundant pair within a
host system, deluge chronology, suspected concealed damage, and two lower-concern
service/visibility cases. Not every behavior appears independently in both sets;
for example, test has no independent 2oo3 detector example.

All 21 findings and the example were already read before partitioning. F-1005 is
development-only because its illustrative ticket is published in the package.
Test is a procedural, non-blind freeze, not evidence of unseen-data or field
generalization. Eight test cases are only four curated groups, not eight independent
samples. No confidence interval or deployment-accuracy claim is justified.

### Isolation contract for later execution

- Select findings from the manifest *before* context construction. A development
  run must not load test findings into inference context.
- The registry and domain notes are shared legitimate inputs, including static
  equipment relationships and engineer comments.
- Evidence cards are evaluator-only: neither development nor test annotations are
  runtime knowledge. The example may inform development, never serve as test gold.
- Generic rules legitimately learned from domain notes can apply to test. Do not
  encode test-specific facts as general rules or few-shot examples.
- This phase has no inference loader; mechanical prompt isolation must be tested
  when it is implemented. The artifact validator checks partitioned references,
  not future prompt construction or separation of assistant conversation history.

## 3. Evaluation contract

Every card statement has a basis (`data`, `domain`, or `design`) and citations.
`data` means a source observation or its direct comparison, `domain` means a rule
applied to evidence, and `design` means a proposed evaluation or review policy.
Citations identify CSV row IDs and fields or exact Markdown section headings.
The validator checks that references resolve, not that a cited passage entails
every sentence; that remains a review responsibility.

| Layer | Acceptance / review criterion | Basis and owner |
|---|---|---|
| Output contract | Valid wrapper, timestamp, fields/types, integer scores 1-10, <=300 character summary/action, valid identity mapping, exactly one ticket per selected finding, review reason when required | Brief section 3; deterministic code |
| Score semantics | Likelihood concerns functional failure; impact concerns consequences; reliability and criticality are priors, not copied answers | Brief section 3 and domain sections; evidence-based review |
| Urgency | Recompute from the documented L/I function and approved escalation facts; verify neither plain mean nor maximum | Brief section 3; deterministic calculation plus reviewed fact extraction |
| Grounding | Preserve decision-changing measurements, repeated occurrences, service state, and partner condition; do not promote suspicion to confirmation | Domain output expectations and case evidence; review |
| Planning utility | Summary explains what/where/why, action names a concrete activity rather than generic investigation | Brief section 3; review |
| Uncertainty | Distinguish missing data, confirmed absence, suspected cause, and confirmed function loss; explain meaningful deferral | Domain output expectations / brief section 6; review and chosen routing policy |
| Knowledge maintenance | A PSV-rule edit has an identifiable knowledge source and affected checks, without rewriting orchestration | Brief section 6B; later change-impact exercise |

No exact numeric gold scores or arbitrary acceptable score intervals are supplied.
F-1005 demonstrates the top-end confirmed-failure principle, but its complete
10/7/9 assessment is not an exact-match target. A numeric score can pass schema
and still fail its evidence review. A low reliability prior does not require every
finding on that equipment to have higher likelihood than every other equipment.

### Reporting and release gates (chosen policy)

For each applicable check record `pass`, `fail`, or `needs_review`, the finding ID,
check/category, observed output evidence, reference, and reason. No model evaluation
has been run yet, so there are no pass rates to report.

- Report deterministic checks as passed/applicable counts.
- Report semantic review outcomes and unresolved cases separately, by case and
  group. Do not hide them inside a weighted average or treat `needs_review` as pass.
- Block an accepted-baseline claim on missing/duplicate tickets, unsupported
  functional/safety claims, credit for a known degraded backup as healthy, invented
  POB/capacity or certification facts, or a confirmed missed immediate-action rule.
- Wrong handling of a routine finding is also recorded; over-escalation is not
  proof of safety or quality.
- A known blocker may be documented as an open defect, never relabeled success.
  These are prototype review gates, not a claim of operational certification.

Apply a card's required evidence across the ticket, using judgment about placement;
do not require every fact to fit in the 300-character summary. Review meaning, not
exact wording. The action constraints name acceptable activity types, not unique
procedures or authorization to perform hazardous work.

## 4. Model/code ownership and uncertainty

| Model / evidence assessment | Code / application policy |
|---|---|
| Identify relevant facts and distinguish observations from suspected causes | Join registry, restrict context by split, preserve evidence identity |
| Propose likelihood/impact with source-grounded rationale | Validate score types/ranges and output consistency |
| Propose summary, activity, and material uncertainties | Enforce lengths, required fields, IDs, count, and bounded failure behavior |
| Assess protection impairment / deviation / evacuation facts with explicit unknowns | Apply documented urgency function and escalation/routing policy; retain derivation trace |

Override-relevant states must distinguish confirmed present, confirmed absent, and
unknown, with suspicion represented explicitly rather than forced into a boolean.
The following are specifications for later tests, not implemented tests or a chosen
numeric urgency formula:

| Situation | Expected property |
|---|---|
| High likelihood / low impact | Explain why near-certain inconsequential failure need not demand today's intervention |
| Low likelihood / high impact on SCE | Attention this week per domain notes, not an arithmetic averaging-away of consequences |
| Protection impairment AND no recorded deviation established | Immediate (9-10 band); rationale identifies this override |
| Evacuation capacity below POB established | Immediate (9-10 band); rationale identifies this override |
| Deviation status or POB comparison unknown | Do not assert the missing fact; require timely human verification under an explicit precautionary policy |
| F-1020 valve reopened, no restored delivery test | Preserve historical unrecorded impairment and unknown restoration; do not automatically declare either total continuing defeat or resolution |
| Valid L/I and no applicable override | Output equals the versioned function's result, not a model-authored urgency number |

Unknown evidence is not permission to delay: the later routing policy must define
precautionary attention without falsely claiming a proven override. The example
escalates F-1005 despite not supplying a deviation record. We retain this as a
reason to document a conservative policy, not proof that all unprovided records
are confirmed absent. The precautionary attention bands are now specified as prototype design choices
in `EVALUATION_ACCEPTANCE.md`; they are not claims of a confirmed override or
operationally certified rules.

The example's all-SCE human-review policy is defensible but is not a universal rule
explicitly mandated by the brief. If adopted, record it as application policy.
`review_required` never exempts a ticket from grounded scores. The brief's overall
human approval remains in place regardless of that flag.

If bounded generation/validation attempts cannot produce a defensible ticket, the
proposed pipeline fails visibly with the finding ID and a non-zero exit; it must
not fabricate scores, silently drop the case, or overwrite a successful-looking
complete `tickets.json`. Supported but uncertain assessments can be review-routed;
total inability to assess is not a middle-score fallback. This failure policy is
an engineering choice to be implemented and documented in `DESIGN.md`.

## 5. Evidence-card format and provenance

`eval\development.jsonl` and `eval\test.jsonl` contain one card per selected finding:

- Identity, binding group, related same-partition findings, and coverage tags.
- Observed facts and required decision-changing evidence.
- Expected behavior and forbidden unsupported claims.
- Unknowns and concrete action constraints.
- A provisional AI-assisted reference status.

Statements use references such as `finding:F-1004:finding_description`,
`equipment:PL-1002:engineer_comment`, `domain:What moves likelihood`, and
`brief:3. Required output`. These are evaluation annotations, not manually authored
deliverable tickets. They contain no required score answers.

The machine validator verifies CSV integrity, group coverage, partition isolation
of finding references, card coverage/identity/shape, resolvable citations, literal
`F-####` identifiers in statement text, and frozen hashes. The prose check catches
only literal cross-partition finding IDs, not semantic leakage or equipment names;
the registry is intentionally shared. It neither judges prose meaning nor implements
ticket generation, ticket-schema validation, an inference context builder, or
semantic model evaluation. Negative citation, card-coverage, and prose-ID tests
exercise both partitions.

## 6. Review and freeze protocol

1. Draft references and manifest against the package, without tuning a model.
2. Run offline validation and focused negative tests.
3. Use two AI reviewers: the second also challenges the first review.
4. Record accepted/rejected/unresolved findings below and fix material defects.
5. Freeze source bytes, both annotation files, and this contract by SHA-256 in
   the manifest; mark the version frozen only after the final checks.

A freeze is a change-detection convention, not a tamper-proof signature. This
manifest is not immutable or an independent Git history. The manifest itself is
not hash-covered: the checks detect source/artifact drift against a trusted
manifest, not every manifest edit or deliberate replacement of hashes. Membership
and group consistency are checked independently against the cards. A later Git
commit provides a reviewable anchor; this phase has no committed anchor because
author identity has not been configured. Changing references or sources requires
review, a version bump, updated hashes, and a stated reason. Do not silently
regenerate hashes to make an unexpected change pass or use `--allow-draft` to
describe draft references as frozen.

After implementation, develop only against development; record model, prompt,
knowledge/policy versions, input hashes, cost, and errors. Repeat a few representative
development cases only to investigate decision stability, not identical wording.
Freeze the system configuration before a test run. Any subsequent change informed
by test outcomes must be disclosed as test-informed development/regression.
Final delivery still requires an automatic run on all 21 source findings.

### Review decision log

| Decision | Disposition | Reason |
|---|---|---|
| Skip eval/data work and build immediately | Rejected from planning review | Conflicts with the requested phase; keep the scope bounded instead |
| Use every linked group only in test | Rejected from planning review | Development must exercise context-sensitive redundancy |
| Treat all seen data as a blind holdout | Rejected | Prior exposure cannot be undone by partitioning |
| Use fixed low/high score bands as invariants | Rejected from planning review | Brief supplies principles, not a complete calibrated numeric rubric |
| Emit a placeholder ticket after failed assessment | Rejected from planning review | Review flags cannot justify fabricated required scores |
| V-1201 pressure protection and control across partitions | Rejected during data review | Group the four directly related findings together |
| Formula and unsupported-score detection | Open for implementation design | Must be addressed before accepting a model baseline; v1.1 acceptance contract now fixes prototype routing and corner constraints |
| First artifact reviewer: manifest is outside hash coverage | Accepted limitation; blocking classification rejected after cross-review | Reference/card consistency catches many split edits; document the trusted-manifest boundary instead of adding circular digest machinery or pretending Git history exists |
| First artifact reviewer: negative card tests only exercised development | Accepted and fixed | Citation and coverage mutations now exercise both partitions |
| First artifact reviewer: literal finding IDs can leak through prose | Accepted and fixed as a partial check | Validate literal IDs in statement text; semantic leakage remains a review concern |
| Both artifact reviewers: F-1020 historical trigger versus current unknown restoration | Accepted and clarified | Card labels immediate current review as design policy, distinguishes the discovery event, and does not claim continuing total defeat |
| Second artifact reviewer: F-1011 retest wording implies valve still needs reopening | Accepted and clarified | Require confirmation of alignment and correction of remaining delivery defects; acknowledge the recorded reopening |
| Portability and draft-command documentation | Accepted and documented | Windows/Python 3.11 scope; plain command is the final freeze check |
| Test described as held out from card design | Rejected from second review wording | Test cards were authored in this phase too; only procedural future tuning isolation is claimed |
| Actual-artifact review coverage | Completed with limits | First reviewer examined all cards/code and ran validation/tests; second cross-reviewed the freeze and deluge evidence, did not independently re-audit every card |

## AI assistance and limits

GitHub Copilot assisted with profiling, annotation, validation code, and synthesis.
Two planning reviewers disagreed; their suggestions were adjudicated rather than
accepted by vote. Artifact-review outcomes are recorded above before freeze.
AI reviewers are not independent domain experts, and source citation does not
certify engineering correctness. Human/domain review of provisional references
remains desirable; it is not misrepresented as completed.
