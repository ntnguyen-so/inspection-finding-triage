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
- **L/I/U** mean model-assessed likelihood and impact, and code-calculated urgency.
- **Rubric** means the declared rules and anchors for assigning L/I scores.
- **Pin** means an exact version or content hash, not only a file name.

## 1. What to edit six months later

Sections 1.1-1.5 are separate options, not steps to perform in order.
Choose the option matching the requested change. If the change covers several
types, follow each relevant option and review their combined effect.

### 1.1 Change general PSV evidence or interpretation

Use this option when approved engineering guidance changes but the current
likelihood/impact scoring rules still apply.

1. **Start from the active release.** Read `knowledge_version` and the prompt
   version from `config\triage-activation.json`. Use a separate comparison copy
   of the knowledge store, with its working candidate based on that release.
   Do not assume the current working candidate equals the active release.
2. **Add or amend the source.** Keep approved guidance outside the preserved
   candidate package. Use `import-source` for a new document, or `edit` with
   `--text-file` for an existing item. An edit creates a new revision and keeps
   its source history; it does not change the original source bytes. If new
   guidance replaces old guidance, explicitly record the replacement and its
   effective date rather than leaving contradictory rules active together.
3. **Review and publish.** Run `check` to inspect extracted text, equipment
   scope, source spans, item IDs and the candidate digest. Review each pending
   item only after checking its meaning. Each review changes the digest, so
   use the latest returned value. Publish the reviewed candidate to obtain
   its immutable `knowledge_version`.
4. **Approve a comparison activation.** Generate a draft with
   `activation_candidate`, explicitly retaining the intended production prompt
   version. Have the runtime approver check the exact release, prompt, selector
   and policy hashes, then save a separate reviewed activation and matching
   run configuration. Publication alone does not activate the release.
5. **Compare before promotion.** Generate baseline and changed-release drafts
   into separate run directories. Keep the inputs, model, prompt and policies
   fixed for a knowledge-only comparison. Review the target, a negative control
   and other non-target findings. Check actual provider-bound context as well
   as ticket meaning. Promote only after the applicable checks and approval;
   otherwise keep the baseline activation.

The current production prompt is `assessment-system-v7`. The helper defaults
to v1 unless `prompt_version` is supplied. Taking that default would change
both knowledge and prompt, so it would not isolate a knowledge change. If the
new interpretation overlaps rules already in the prompt, first complete the
[Document 06 compatibility review](06_TRIAGE_WORKFLOW.md#prompt-authority-and-controlled-change).

The [historical PSV source](../knowledge/source-documents/psv-seat-tightness-policy-2026-11.md)
was rejected; do not use it as approved guidance. Sections 4-5 explain the real
maintenance experiment and rejection. [Section 8](#8-command-example-and-replay-record)
keeps the concrete command example and the later unchanged-source replay
separate from this procedure.

### 1.2 Change a fact about one asset

Create a new registry snapshot outside the candidate package. Preserve its exact
bytes and hash. Keep the approved knowledge release and activation if they are
otherwise unchanged. Pass the new snapshot with `--registry`, generate to a new
comparison path, and save output/evidence tied to those exact bytes. Review the
affected and related findings before adopting it. A registry-only update does
not require republishing knowledge. Do not edit the supplied registry.

### 1.3 Change a generic likelihood or impact anchor

Edit the score anchors and instructions in `triage\assessment_policy.py`.
Update the focused cases in `tests\test_triage.py`, then run:

```powershell
python -B -m unittest tests.test_triage
```

Then follow steps 4-5 of section 1.1. Keep the active knowledge release and
intended prompt version when calling `activation_candidate`; the changed
assessment-policy hash requires a new compatibility review and activation.
Rerun the affected acceptance scenarios and review of meaning before using the
new scoring rules.

### 1.4 Change urgency or exceptional-review routing

Edit the code-owned formula, minimum urgency values or escalation rules in
`triage\policy.py`. Update expectations worked out independently of the
implementation in `tests\test_triage.py`, then run:

```powershell
python -B -m unittest tests.test_triage
```

Follow steps 4-5 of section 1.1, keeping the active knowledge release and
intended prompt version. Review the changed policy hashes and create a new
activation. Compare urgency and review-routing changes. The model does not
choose urgency.

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

Editing either file changes the pinned implementation hash. Follow steps 4-5
of section 1.1 with the active knowledge release and intended prompt version.
If extraction changes must apply to existing source content, re-extract and
review that content and publish a new release first: a code change does not
rewrite stored items. A selector-only change need not republish unchanged
items. Obtain new activation approval before a production run.

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

## 8. Command example and replay record

This section is a software walkthrough, not the PSV change studied in sections
4-5. It imports the **unchanged supplied notes** into a new store. No new
engineering interpretation is invented or approved. A real update instead
starts from the active release and follows section 1.1.

### 8.1 Concrete command example

Run these blocks from the repository root in one PowerShell session. Item IDs,
digests and the release version are taken from command output, not copied from
old logs. The review loop is only for this unchanged-source software example;
do not automatically approve new engineering guidance.

**Create the isolated store, import and inspect.**

```powershell
$ErrorActionPreference = "Stop"
$python = (Resolve-Path ".venv\Scripts\python.exe").Path
$run = Join-Path (Get-Location) (
    ".runs\doc07-example-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffffffZ")
)
New-Item -ItemType Directory -Path $run | Out-Null
$store = Join-Path $run "store"
$source = Join-Path $run "domain-notes-copy.md"
Copy-Item -LiteralPath `
  "docs\candidate-pack\candidate-pack\reference\domain_knowledge.md" `
  -Destination $source
$import = & $python -B -m triage_knowledge --store $store import-source `
  --source $source --name "domain-notes-command-example" | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Import failed" }
$check = & $python -B -m triage_knowledge --store $store check | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Check failed" }
$digest = $check.candidate_digest
$items = @($check.candidate.items.PSObject.Properties | Sort-Object Name)
$items | ForEach-Object { $_.Value }
```

**Record software-only reviews and publish.**

```powershell
foreach ($item in $items) {
    $review = & $python -B -m triage_knowledge --store $store review `
      --item $item.Name --expected-digest $digest `
      --reviewer "software-replay-not-domain-approval" `
      --reason "Unchanged supplied domain; isolated software workflow check only." |
      ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Review failed: $($item.Name)" }
    $digest = $review.candidate_digest
}
$status = & $python -B -m triage_knowledge --store $store status | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Status failed" }
$status.review_counts
$publish = & $python -B -m triage_knowledge --store $store publish `
  --expected-digest $digest --author "software-command-replay" `
  --reviewer "software-replay-not-domain-approval" `
  --reason "Isolated publication of unchanged supplied domain; not production approval." |
  ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Publication failed" }
$version = $publish.knowledge_version
$publish
```

For these notes, `check` returns eight items. Each `review` returns a new
digest; its generic status remains `pending_review`. The final store counts
should be 0 pending, 8 reviewed and 0 rejected. Publication returns
`knowledge_version` and `local_declaration_not_authenticated`: a reviewer
string does not authenticate a domain owner.

**Prepare a comparison activation with the current production prompt.**

```powershell
@'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from run_triage import build_config
from triage.source_context import activation_candidate
from triage_knowledge import SourceKnowledgeStore

run, version, store = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
production = json.loads(
    Path(r"config\triage-activation.json").read_text(encoding="utf-8")
)
candidate = activation_candidate(
    SourceKnowledgeStore(store), version,
    prompt_version=production["assessment_prompt"]["version"],
)
assert candidate["review"] is None
(run / "activation.draft.json").write_text(
    json.dumps(candidate, indent=2) + "\n", encoding="utf-8"
)
candidate["review"] = {
    "reviewer": "software-replay-not-domain-approval",
    "reason": "Unchanged supplied domain; isolated software example, not production approval.",
    "reviewed_at": datetime.now(timezone.utc).isoformat(),
    "source_policy_compatible": True,
}
(run / "activation.json").write_text(
    json.dumps(candidate, indent=2) + "\n", encoding="utf-8"
)
config = build_config(
    "copilot", "gpt-6.1-sol", run / "attempts.experimental-ledger.json",
    version, "medium",
)
config["execution_mode"] = "copilot_experiment"
(run / "config.json").write_text(
    json.dumps(config, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"knowledge_version": version, "prompt": candidate["assessment_prompt"]}, indent=2))
'@ | & $python -B - $run $version $store
if ($LASTEXITCODE -ne 0) { throw "Activation/configuration failed" }
```

The saved draft has `review: null`. The separate test activation above uses an
explicit software-only declaration; a real update requires the runtime
approver's compatibility review instead. There is no activation-approval CLI.
Neither file replaces the production activation.

**Optional live generation.** The previous blocks use no model calls. This
block sends billable requests and needs a compatible authenticated Copilot
runtime. It permits at most 42 application sends; hidden provider attempts
remain unknown.

```powershell
& $python -B -m triage `
  --provider copilot `
  --findings docs\candidate-pack\candidate-pack\data\inspection_findings.csv `
  --registry docs\candidate-pack\candidate-pack\data\equipment_registry.csv `
  --knowledge-store $store `
  --activation (Join-Path $run "activation.json") `
  --config (Join-Path $run "config.json") `
  --output (Join-Path $run "tickets.experimental.json") `
  --evidence (Join-Path $run "evidence") `
  --allow-inference
if ($LASTEXITCODE -ne 0) { throw "Generation failed; inspect the JSON diagnostic and evidence" }
```

The `.experimental.json` suffix is mandatory in `copilot_experiment` mode.
A successful command means complete structurally valid drafts, not semantic
acceptance or permission to promote.

### 8.2 What actually ran on 24 November 2026

The [retained replay record](../eval/results/knowledge-command-replay-20261124.json)
keeps the original commands, outcomes, hashes, usage and failures. **That live
run used helper-default prompt v1, not production v7.** Section 8.1 now selects
the production prompt explicitly. Its non-inference steps were checked
separately; the historical v1 output is not presented as a v7 run.

| Stage | Actual outcome |
|---|---|
| Import, check and eight reviews | All exited 0; final counts were 0 pending, 8 reviewed and 0 rejected |
| Publication | Created release `sha256-f6bc1e73a1b8dfea57ad782d4d1f4dbdea4b4f89cb5b359b2fc4a296ec369258` |
| Test activation | Selected that release, prompt v1, policy v16 and `gpt-6.1-sol` with medium reasoning |
| Generation | Exited 0; 21 experimental drafts from 25 application sends in 718.891 seconds |
| Recovery | F-1003, F-1010 and F-1012 first failed policy verification; F-1021 first returned malformed JSON. All four passed on their second attempt |
| Publication and preservation | Experimental output publication verified; all 29 protected files unchanged, including root tickets, production activation/store and the supplied package |
| Review and promotion | 13 extra-review flags; no semantic review, new engineering approval or promotion |

Two earlier failures are also retained. CLI `1.0.114` reported protocol 4,
incompatible with pinned SDK `1.0.34` (protocol 3). An existing CLI `1.0.112`
backup worked for that run; this machine-specific workaround is not an
installation procedure. A first generation configuration used `tickets.json`
and was rejected with zero sends. A new run used the required
`tickets.experimental.json` filename.

Selected fields from the successful CLI response were:

```json
{
  "run_status": "experimental_draft_generated",
  "published_output": true,
  "tickets_generated": 21,
  "application_send_count": 25,
  "semantic_status": "not_reviewed",
  "acceptance_eligible": false
}
```

To inspect the retained local batch without another model call:

```powershell
$batch = Get-Content -LiteralPath `
  ".runs\doc07-command-replay-20261124T0500018156886Z\tickets.experimental.json" `
  -Raw | ConvertFrom-Json
$batch.tickets |
  Where-Object { $_.finding_id -in @("F-1002", "F-1005", "F-1016") } |
  Select-Object finding_id,
    @{Name="L"; Expression={$_.likelihood_of_failure.score}},
    @{Name="I"; Expression={$_.impact_of_failure.score}},
    @{Name="U"; Expression={$_.urgency.score}},
    review_required
```

| Finding | L | I | U | Extra review required |
|---|---:|---:|---:|---|
| F-1002 | 7 | 8 | 8 | true |
| F-1005 | 10 | 6 | 9 | true |
| F-1016 | 2 | 7 | 7 | false |

Measured usage, including repairs, was 1,188,873 input and 48,488 output tokens.
Reusing the declared US$2/million input and US$10/million output rates gives
US$2.862626 without cache adjustment. Rates were not checked again, and this
is not an actual Copilot charge.

This replay checks the command path, not whether a PSV knowledge change improves
output. Raw files remain local under `.runs`, not a shared evidence archive.
The compact JSON preserves observed statuses and artifact hashes. The earlier
full command listing remains in Git commit `d977810`; its implicit v1 prompt
must not be mistaken for the current knowledge-only procedure.
