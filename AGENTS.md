# Repository working rules

These rules apply to coding assistants working in this repository across design,
implementation, evaluation and delivery. They are development guidance, not
runtime triage knowledge or a substitute for executable acceptance checks.

## 1. Read the contract before changing the system

Start with `README.md`, then:

- `docs\candidate-pack\candidate-pack\README.md` and
  `reference\domain_knowledge.md` inside that package: panel requirements and
  supplied triage rules. Preserve the entire supplied package unchanged.
- `docs\02_DATA_EVALUATION_PLAN.md`: data/context boundaries and split rationale.
- `docs\03_EVALUATION_ACCEPTANCE.md` and `eval\spec\acceptance.json`: agreed
  prototype policies, scenario IDs, acceptance criteria and required evidence.
- `eval\spec\split.json`: current reference version, membership and fingerprints.
  Inspect `eval\results` for actual observations, not presumed system success.

The supplied brief/domain rules are authoritative; the evaluation contract adds
declared engineering choices within them. This file must not override either.
Surface conflicts before proceeding with the affected change. Do not silently
weaken the evaluation or present a chosen prototype policy as a panel requirement
or expert-certified engineering truth.

## 2. Use a requirement-to-evidence change loop

Before substantive work, identify the requirement, affected scenario IDs and
expected evidence. Use the existing mapping rather than inventing another rubric:

| Area | Scenarios | What needs evidence |
|---|---|---|
| A: structured output | A01-A04 | Schema, coverage, recovery, semantic errors |
| B: knowledge | B01-B03 | Actual context, maintained knowledge, isolation |
| C: urgency | C01-C04 | Code derivation, corners, overrides, fact assessment |
| D: limits | D01-D04 | Deferral, inability to assess, exclusions, provenance |
| Cross-cutting | X01-X02 | Decision stability, reproducibility, cost, delivery |

Implement the smallest change that satisfies the requirement; add focused tests
for introduced/fixed behavior. Run relevant checks and record actual outcomes.
Use the brief's time/cost scope to reject unnecessary infrastructure, not to skip
core requirements. Do not add a new evaluation platform or extra benchmarks
without a concrete unresolved requirement.

## 3. Follow the phase gates

1. **System Design:** root `DESIGN.md` (including case variants such as `design.md`)
   is reserved for the project owner to create later. Do not create, recreate or
   modify it unless the owner explicitly authorizes that file. Document component
   designs and work in the appropriate numbered document under `docs`; inference
   design belongs in `docs\04_INFERENCE_LIBRARY.md`. This does not satisfy or waive
   the final system-design gate: the owner-approved system design must answer brief
   section 6 A-D, including alternatives rejected, assumptions, model/code
   boundaries, knowledge-maintenance surface, failure policy and AI assistance/
   overrides. Choose the model/provider, explicit L/I rubric, urgency function,
   configuration and usage budget before a paid baseline.
2. **Implementation and development:** build against the agreed scenarios using
   development findings. Keep a documented end-to-end command and dependency
   manifest. Exercise deterministic failure paths, then review real development
   outputs; mocks cannot establish model quality or knowledge influence.
3. **Test evaluation:** once applicable development gates pass, freeze the code,
   model, prompt, knowledge, policy, reference and run configuration; run test once.
   Record failures. Any subsequent test-informed fix/rerun is disclosed as such,
   never relabeled as an untouched or newly blind test.
4. **Delivery:** automatically generate the final `tickets.json` for all supplied
   findings. Require actual applicable acceptance evidence, reproducibility and
   cost records, `DESIGN.md`, dependencies, run instructions and honest Git history.
   Never hand-write or hand-correct final tickets.

The current split is non-blind and AI-assisted, not independent gold. Read shared
registry/domain material as needed, but do not use test outputs/cards to tune
development. Development provider context must exclude test finding descriptions;
do not enrich shared registry/knowledge with test answers.

## 4. Preserve the engineering boundaries

- The assessment layer proposes grounded likelihood/impact, concise planning
  text, explicit fact states and uncertainty. Code owns identity/coverage/schema
  checks, urgency derivation/escalation, retry accounting and output publication.
  Asking the model to choose urgency does not satisfy the brief.
- Use reliability/criticality only as the correctly directed priors described in
  the domain notes. Check actual partner evidence before crediting redundancy;
  include major-accident, delayed and hidden consequences where supported.
- Distinguish confirmed, false, suspected and unknown facts. Missing evidence is
  not confirmed absence. Apply the contract's precautionary review/urgency policy
  explicitly, without inflating L/I or fabricating an override condition.
  Inability to justify required scores is visible failure, not a scored fallback.
- Test urgency math separately from fact assessment, with independently worked
  expectations. Preserve the contract's corner, monotonicity and escalation
  constraints; neither a plain average nor a plain maximum is acceptable.
- Keep maintainable knowledge separate from orchestration; a PSV policy change
  must not require finding-ID branches. Identity joins are valid; lookup tables
  of per-finding answers, case-specific score branches and copied gold are not.
- Production must not import the evaluator or consume evidence cards, reviewer
  judgments or expected probe answers. Synthetic inputs/policy overlays are
  allowed only in their declared, isolated evaluation experiment, not final
  generation. Capture actual provider-bound context to check the boundary.
- Provider inference SDKs, structured-output features and schema/data utilities
  are permitted. Implement core orchestration yourself; do not introduce the
  high-level orchestration frameworks or structured-generation harnesses
  prohibited by the brief.
- Enforce the total attempt budget in the acceptance specification, including SDK
  retries. Follow its nonzero-exit/JSON diagnostic and no-publication-on-failure
  contract; an old output stays unchanged and cannot masquerade as current success.
  Drafts still require human approval; no live operational action is authorized.

## 5. Produce evidence, not success-shaped claims

Run commands from the repository root on Windows, Python 3.11+:

```powershell
python -B -m eval.validate
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.assess --help
```

Use the README/document 03 commands for checklists, actual ticket assessment and
reviewer calibration. Select tests relevant to the change; documentation-only
work needs lightweight consistency checks, not a paid model run or full suite.

Reference validation checks integrity; self-tests check evaluator software;
known-fixture calibration checks disclosed contradictions. None is system
acceptance, model accuracy or domain certification. Calibrate the actual semantic
reviewer/configuration before relying on its judgments; old reviewer files do
not qualify a different reviewer. Record provenance and output-bound quotes as
required by the assessor. `needs_review` and unexecuted checks are not passes.

Store observed results under `eval\results`, separately from specifications.
Record commands, input/output hashes, code revision/dirty state, reference and
knowledge/prompt/policy versions, exposed model/settings, assessment time, cache
mode, attempts/errors, usage, latency and cost as applicable. State unknown or
estimated values honestly; never invent metrics, credentials, timestamps or model
IDs. Do not include secrets in captured requests/logs. Keep failed observations.
No composite score or reviewer agreement can substitute for the required gates.

Keep reviewable summaries, live-call accounting and relevant failure observations
in Git; do not commit every regenerated synthetic snapshot or command log. Raw
artifacts may be archived losslessly with their original paths, per-file hashes
and an archive hash recorded in `eval\results\artifacts-manifest.json`. Verify
the archive and a separate backup before pruning loose copies. Never prune an
active run, tracked evidence, or the only copy of a failed observation. Archived
dependencies must be restored before replay; a local ignored archive is not a
shared or durable evidence store. See README's generated-artifact retention
instructions. Do not blanket-ignore `eval\results`.

## 6. Change frozen evaluation only deliberately

Do not edit expectations, partitions, fixtures, evaluator code or fingerprints
just to make a failing result pass. For a genuine source-backed gap, grader bug
or authorized requirement change:

1. Document the reason, affected gates, proposed change and comparability impact.
2. Obtain the bounded review below and preserve the prior snapshot in Git.
3. Make an explicit reference-version change for semantic changes; identify
   layout-only revisions separately. Preserve the supplied package and split
   disclosures. Update dependent references and focused tests together.
4. Refresh only intentionally changed artifact fingerprints and rerun affected
   checks/reviews before freezing. Never disable validation, rewrite source
   fingerprints to hide edits, or attach old results to new hashes without reruns.

Specifications are preregistered snapshots, not progress trackers. Record proposed
component architecture/formulas in the appropriate numbered design/process document
and executed scenarios in results rather than flipping historical snapshot fields.
Respect the reserved `DESIGN.md` ownership rule above. Keep one current reference
layout; use Git for history instead of accumulating parallel version folders.

## 7. Use bounded, critical multi-agent review

For substantive phase plans, architecture/policy changes and implementations,
use two reviewing agents when available: one challenges the proposal/diff against
requirements and evidence; the second cross-critiques those findings and checks
remaining risks. Give each a bounded objective. Do not nest reviewers, launch a
large workflow by default, or have reviewers mutate the same files.

The implementing agent adjudicates accepted/rejected suggestions with reasons;
agreement is not proof. Record the disposition in the relevant existing design/
process document or commit/PR description, not a new report for every small edit.
Typos and mechanical edits need proportionate direct checks. If review tools are
unavailable, disclose the limitation in the work record and handoff; do not claim
multiple reviewers, independence or domain expertise that did not exist.

## 8. Keep the repository reviewable

Write authored documentation, code comments, prompts, examples and generated
planning/ticket text in English. Unicode tests should use English text with
Unicode symbols, not another language. Preserve supplied source material and
verbatim historical observations unchanged; do not translate recorded evidence.

Preserve unrelated user edits, source/data bytes and `.gitattributes`; do not
normalize frozen files during formatting. Keep diffs focused and dependencies
justified. Number new authored process documents under `docs` in work order;
keep required delivery filenames such as `DESIGN.md` and `tickets.json` when their
creation is authorized, and maintain README navigation instead of duplicating
documents. A delivery requirement does not authorize creating the reserved
`DESIGN.md` early.

Commit/push only when requested, with logical changes and real history. Do not
amend, rewrite history, force-push or change visibility without authorization.
Never commit API keys, environment files containing secrets or sensitive logs.
Before claiming completion, verify the requested outcome and distinguish any
still-unexecuted system gates from the completed task.
