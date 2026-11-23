# Knowledge Change Study

This study answers a practical maintenance question: **if an integrity engineer
needs to change how pressure safety valve (PSV) evidence is interpreted six
months from now, what do they edit, how does the model receive the change, and
how do they decide whether it is ready for production?**

The short answer is:

- change an approved knowledge source when the engineering interpretation
  changes within the existing likelihood/impact scoring rules;
- change policy code when scoring, urgency or review-routing rules change;
- publish and activate knowledge as separate steps; and
- compare the resulting behavior and review the evidence before approving the
  new release for use.

The saved maintenance exercise shows that this process can change model behavior
and that the change can be rolled back. It does **not** show that the experimental
PSV rule was correct. The rule was not promoted. Production stayed on the
baseline knowledge release.

In this document:

- **Publish** means creating a reviewed release whose contents cannot be edited.
- **Activate** means approving one exact combination of release, policy and
  prompt for a run.
- **Promote** means replacing the production activation after comparison and
  review requirements pass.
- **L/I/U** mean likelihood, impact and urgency calculated by code.
- **Rubric** means the declared rules and anchors for assigning L/I scores.
- **Pin** means an exact version or content hash, not only a file name.

## 1. What to edit six months later

Sections 1.1-1.5 are separate options, not steps to perform in order.
Choose the option matching the requested change. If the change covers several
types, follow each relevant option and review their combined effect.

### 1.1 Change general PSV evidence or interpretation

Use this option when approved engineering guidance changes but the current
likelihood/impact scoring rules still apply.

1. Create a new approved source file outside the preserved candidate package.
   The retained
   [experimental PSV source](../knowledge/source-documents/psv-seat-tightness-policy-2026-11.md)
   shows the expected file format and how to record its source. It was rejected
   and is not approved for runtime use. Use it only as a format example, not as
   engineering guidance.
2. Import, review and publish it:

   ```powershell
   python -B -m triage_knowledge --store knowledge\source-first import-source `
     --source "path\to\approved-psv-guidance.md" `
     --name "approved-psv-source"
   python -B -m triage_knowledge --store knowledge\source-first check
   python -B -m triage_knowledge --store knowledge\source-first review `
     --item "<item-id from check>" `
     --expected-digest "<candidate_digest from check>" `
     --reviewer "reviewer" --reason "scope and source checked"
   python -B -m triage_knowledge --store knowledge\source-first publish `
     --expected-digest "<candidate_digest from review>" --author "author" `
     --reviewer "reviewer" --reason "approved"
   ```

   The `check` output lists extracted item IDs and the current candidate digest
   (content hash). Review every pending item. Use the latest digest returned
   after each review, because review changes the candidate. The publish command
   returns the immutable `knowledge_version` needed in the next step.
3. Generate an activation-manifest draft with the Python helper:

   ```python
   import json
   from pathlib import Path

   from triage.source_context import activation_candidate
   from triage_knowledge import SourceKnowledgeStore

   store = SourceKnowledgeStore(Path("knowledge/source-first"))
   candidate = activation_candidate(
       store,
       "<knowledge_version from publish>",
   )
   print(json.dumps(candidate, indent=2))
   ```

   The returned dictionary fixes the release, retrieval strategy and index.
   It includes hashes of extraction and selection code, assessment policy,
   execution policy and prompt. The `review` field is `None`, so the dictionary
   is a draft for approval, not an active release.
4. Have the runtime approver check that those exact versions match the intended
   change and are compatible. If they are, create a unique comparison directory.
   Save a reviewed activation and matching run configuration there. Continue in
   the same Python script or session used in step 3:

   ```python
   import json
   from pathlib import Path

   from run_triage import build_config

   run = Path(".runs/psv-comparison-<unique-id>")
   run.mkdir(parents=True, exist_ok=False)
   candidate["review"] = {
       "reviewer": "<approver>",
       "reason": "<why the exact source/policy binding is compatible>",
       "reviewed_at": "<ISO-8601 timestamp>",
       "source_policy_compatible": True,
   }
   (run / "activation.json").write_text(
       json.dumps(candidate, indent=2) + "\n",
       encoding="utf-8",
   )
   config = build_config(
       "copilot",
       "gpt-6.1-sol",
       run / "attempts.experimental-ledger.json",
       candidate["knowledge_version"],
       "medium",
   )
   (run / "config.json").write_text(
       json.dumps(config, indent=2) + "\n",
       encoding="utf-8",
   )
   ```

   There is currently no activation-approval command-line interface (CLI).
   The root delivery uses
   `config\triage-activation.json`, but replacing that file is a production
   promotion step, not part of a comparison run.
5. Generate comparison tickets with the run-specific activation:

   ```powershell
   python -B -m triage `
     --provider copilot `
     --findings docs\candidate-pack\candidate-pack\data\inspection_findings.csv `
     --registry docs\candidate-pack\candidate-pack\data\equipment_registry.csv `
     --knowledge-store knowledge\source-first `
     --activation .runs\psv-comparison-<unique-id>\activation.json `
     --config .runs\psv-comparison-<unique-id>\config.json `
     --output .runs\psv-comparison-<unique-id>\tickets.json `
     --evidence .runs\psv-comparison-<unique-id>\evidence `
     --allow-inference
   ```

   Before promotion, compare the target finding, a negative control (a finding
   where the new rule should not apply), and other non-target findings.
   This command calls the provider and may incur inference charges. Use a new
   directory for every run so old evidence cannot look like new evidence.

If the guidance overlaps interpretation already in the prompt, complete the
prompt-compatibility review in Document 06 before activation.

### 1.2 Change a fact about one asset

Create a new registry snapshot outside the candidate package. Preserve its exact
bytes and hash. Follow section 1.1's comparison procedure, using the new snapshot
for `--registry` in step 5. Save output and evidence tied to that exact registry.
Do not edit the supplied registry.

### 1.3 Change a generic likelihood or impact anchor

Edit the score anchors and instructions in `triage\assessment_policy.py`.
Update the focused cases in `tests\test_triage.py`, then run:

```powershell
python -B -m unittest tests.test_triage
```

Then repeat steps 3-5 of section 1.1. Pass the currently active
`knowledge_version` from `config\triage-activation.json` to
`activation_candidate`, because the assessment-policy hash has changed.
Rerun the affected acceptance scenarios and review of meaning before using the
new scoring rules.

### 1.4 Change urgency or exceptional-review routing

Edit the code-owned formula, minimum urgency values or escalation rules in
`triage\policy.py`. Update expectations worked out independently of the
implementation in `tests\test_triage.py`, then run:

```powershell
python -B -m unittest tests.test_triage
```

Repeat steps 3-5 of section 1.1, passing the currently active
`knowledge_version` from `config\triage-activation.json` to
`activation_candidate`. Compare urgency and review-routing changes. The model
does not choose urgency.

### 1.5 Change extraction or selection behavior

Edit `triage_knowledge\source.py` for extraction behavior or
`triage_knowledge\retrieval.py` for selection behavior. Update and run the
focused component tests:

```powershell
python -B -m unittest `
  tests.test_source_workflow `
  tests.test_source_context `
  tests.test_source_knowledge
```

Editing either file changes the pinned implementation hash. Repeat steps 3-5 of
section 1.1 with the currently active `knowledge_version`. If the knowledge
content also changes, first publish a replacement release and use its new
version. Obtain new activation approval before a production run.

These procedures keep approved engineering interpretation separate from
code-owned scoring and routing rules. Document 05 describes the full production
architecture. This study records what happened when the maintenance process was
tested.

## 2. How a knowledge change reaches assessment

```text
approved source bytes
  -> extraction preserving meaning and exact supporting text spans
  -> explicit review
  -> immutable release
  -> separate activation approval
  -> provider-bound context (the exact context prepared for the model request)
  -> regenerated assessment and ticket
  -> before/after review
  -> promotion or rejection
```

Each stage answers a separate question:

| Boundary | Question |
|---|---|
| Source and extraction | Which exact approved text supports the guidance? |
| Review | Was the extracted meaning and scope approved? |
| Immutable release | Can both the old and new states be reconstructed? |
| Activation | Which reviewed release may affect a run? |
| Provider capture | Did the selected release reach the model request? |
| Before/after comparison | Did behavior change in the intended case? |
| Negative and non-target controls | Did unrelated cases also change? |
| Promotion decision | Is the evidence strong enough to approve the change for runtime use? |

The prototype sends complete source and registry context within a size limit.
There are only 21 findings and 18 equipment records. This avoids leaving out
evidence because of retrieval ranking, but uses more input tokens.
The selector does not isolate guidance for each finding. Guidance for a specific
equipment type enters shared batch context, and the model decides whether it
applies to a finding.

Delivery, influence and correctness are different claims. Saved context can
prove what was sent. A before/after comparison can support a claim that guidance
affected behavior. Neither proves that the engineering rule is correct.

## 3. Change ownership in this study

The exercise changed an experimental engineering source and selected its release
through an activation used only for that run. It did not change the prompt,
L/I scoring rules, urgency or review-routing policy.

The exercise later exposed a separate defect in editor code. Fixing it changed
how knowledge was maintained, not the experimental interpretation. The source
change and code fix therefore required separate review and activation decisions.

The ownership rule is:

- source-backed interpretation inside the existing L/I rubric belongs in an
  approved domain source and knowledge release;
- a generic numeric L/I anchor belongs in
  `triage\assessment_policy.py`; and
- an urgency floor or exceptional-review escalation belongs in
  `triage\policy.py`.

Publishing and activating knowledge does not “escalate it into code.”
Activation selects one exact reviewed combination of source, policy and prompt
for a run. The experimental source in section 4 crossed these responsibility
boundaries by prescribing L9/I8 directly. That was one reason for rejection.

## 4. Maintenance-path exercise

This experiment tested the process for a future engineering-knowledge update.
It did not edit the prompt. It added an experimental source treating audible
tailpipe hissing and hydrocarbon odour below set pressure as evidence about PSV
seat tightness. It then used the actual knowledge store and full triage command.

The intended edit was to domain knowledge: add a source, publish an immutable
experimental release, and select it through a run-specific activation.
The source also prescribed L9/I8 directly. That mistake was deliberately kept
visible. Engineering sources should describe the supported interpretation;
`triage\assessment_policy.py` owns generic numeric anchors. The prescribed
scores alone would have blocked promotion.

The exercise passed through three states:

1. the first source described itself as an experiment, so the model declined to
   treat it as engineering authority;
2. a revised source was published as release
   [`a39d...`](../knowledge/source-first/releases/sha256-a39db135667b8b13df866500124c3b0417f0e899e3576303cfd45a532863c5da.json)
   and run twice, but an editor defect was later found to have removed its
   equipment-type scope and links to exact supporting source spans; and
3. after the editor fix, release
   [`63f1...`](../knowledge/source-first/releases/sha256-63f1855f93f63d48f2bec3e0032e82e4cbdf5a3f2adf282d9575b37bd70f242a.json)
   restored those fields and received one verification run.

In state 3, the code fix changed `SourceKnowledgeStore.edit_item(...)` in
`triage_knowledge\source_store.py`. An edit now re-extracts scope, aliases and
source evidence, and an edit producing multiple items is rejected. Activation
includes this code's hash. The unchanged baseline production release therefore
also needed a newly reviewed activation after the fix. The experimental PSV
content still was not promoted.

All three states remained experimental and were rejected in section 5.

The change went through source import, extraction, review, immutable publication,
separate activation and generation for all 21 findings. No code branch for a
specific finding ID was added. No ticket was hand-corrected.

This exercise used `gpt-6.1-sol` and `triage-policy-v11`; it predates the
delivered `triage-policy-v16` calibration. It demonstrates the maintenance
process for its recorded setup. It does not revalidate the delivered system.

### 4.1 Observed output

| Finding | Baseline | Experimental release | Interpretation |
|---|---|---|---|
| F-1002, PSV seat-tightness observation | Two runs at L7/I8/U8 | Two runs at L9/I8/U9 | The source declared L9/I8; the code-owned minimum for confirmed loss of function also enforces L9. U9 follows from the L9/I8 calculation, not an urgency override |
| F-1016, tag-only defect | L2 in both runs | L2 in both runs | The seat-tightness rule did not change likelihood for the tag-only condition |
| F-1005, non-target protection case | L10 in both runs | L9 in all three experimental runs | A possible non-target effect remained unresolved |

The two experimental repeats used release `a39d...`. An editor defect had removed
its structured scope and source-evidence fields. The item was therefore stored
as general guidance. The F-1002 change shows visible influence through the real
lifecycle. But the release did not have correct scope, so this is not clean
proof that knowledge text alone caused likelihood to rise by two points.

After the editor was fixed, release `63f1...` restored explicit
`Pressure Safety Valve` scope and one source-evidence span. Its one retained
verification run produced:

- F-1002: L9/I8/U9;
- F-1016: L2/I8/U7; and
- F-1005: L9/I6/U9.

The target behavior remained after scope was restored. One run does not show
that repeated runs would be stable. F-1016 likelihood stayed at L2 in baseline
and experimental repeats, but its impact varied. Other non-target scores also
varied in the saved repeats. The study did not establish whether the source
update caused those changes.

Evidence:
[full-batch study](../eval/results/controlled-studies/knowledge-kb-edit-v1-study.json).

### 4.2 What the exercise revealed

The exercise found problems that a successful example alone would have hidden:

1. **Experiment wording entered engineering guidance.** The first source called
   itself an evaluation-only proposal, so the model correctly declined to treat
   it as active authority. Experiment status was moved to release metadata.
2. **The editor lost scope and evidence.** The editor removed the equipment type
   to which the rule applied and its links to exact supporting source spans. It
   was fixed to re-extract scope, aliases and source evidence and to reject
   ambiguous edits. Evidence from earlier releases was preserved, not rewritten.
3. **Restored scope did not create per-finding isolation.** The scoped PSV item
   entered the shared batch knowledge pool and appeared in every request.
   The model still had to decide whether the rule applied.
4. **Non-target behavior was not stable.** F-1005 changed, and F-1016 impact
   varied even though its likelihood control remained intact.
5. **The proposed rule conflicted with an evaluation distinction recorded
   before the experiment.** The reference cases distinguish suspected PSV seat leakage
   from evidence that the valve cannot perform its relief function. The
   experimental rule treated those states too similarly and hard-coded numeric
   scores.

These findings show that the maintenance process was tested with failures.
They do not justify accepting the proposed rule.

## 5. Promotion decision

The experimental releases were rejected because:

- the rule was synthetic and developed with access to test evidence;
- it prescribed L9/I8 instead of leaving numeric anchoring to the assessment
  rubric;
- it closely followed test finding F-1002 and was revised after seeing output;
- it conflicted with the reference distinction between suspected seat passing
  and proven inability to relieve;
- the full-batch outputs did not receive the calibrated review of meaning
  required for promotion;
- non-target variance remained unresolved; and
- no domain owner with verified identity approved the interpretation.

The working candidate was reset to the eight-item baseline release.
Approval includes the editor's implementation hash, so the fix invalidated the
existing approval. Production received new approval for the same eight-item
baseline release. Root `tickets.json` did not change.

This is the intended approval outcome: an experiment can demonstrate the
maintenance process while its engineering content is rejected.

Evidence:
[release disposition](../eval/results/controlled-studies/knowledge-kb-edit-v1-release-disposition.json).

## 6. Answers to the maintenance requirements

| Question | Repository answer | Evidence status |
|---|---|---|
| How does `domain_knowledge.md` reach the model? | Original source bytes become reviewed release items. Code selects them into context identified by hash, then checks them again before sending | Delivery is visible. Saved development runs still do not meet B01 context isolation |
| How does `engineer_comment` reach the model? | The selected registry snapshot and comments enter context with references to their source | Saved provider context and component checks |
| What does the engineer modify six months later? | Approved sources and reviewed releases for interpretation changes; policy code for scoring or routing changes | B03 lifecycle steps were tested; content approval was not established |
| Can a released change affect output? | Yes, in the official maintenance exercise | Visible influence shown; not engineering correctness or proof that the source alone caused score changes |
| Can an old release be recovered? | Releases cannot be edited, and replacement history is saved | Component tests and saved releases |
| Can a technically valid release be rejected? | Yes. Publication and activation are separate. No experimental PSV release became approved production guidance | Release decision evidence |

Provider-bound evidence that includes registry comments is retained in the
[final run record](../eval/results/triage/structured-planning-v31/final/evidence/run.json).

## 7. What this study supports

The evidence supports:

- source import, extraction, review, immutable publication and separate
  activation;
- provider delivery of the selected release;
- visible influence on a complete batch through the official knowledge store; and
- rejection and rollback while production remained on the baseline release.

It does not support:

- independent correctness of the experimental PSV rule;
- stable non-target assessments;
- selector-level per-finding isolation;
- proof that the model used every delivered knowledge item;
- approval by a domain owner with verified identity; or
- production promotion of the experimental release.

The production architecture and maintenance commands are in
[Document 05](05_KNOWLEDGE_LIFECYCLE.md). The complete evidence index is
[`eval\results\README.md`](../eval/results/README.md).
