# Inspection Finding Triage

Evaluation-first preparation for the candidate exercise. The triage system is
not implemented yet; no model-generated tickets or system-acceptance results are
claimed.

## Read the work in order

| Order | Document | Purpose |
|---|---|---|
| 01 | `docs\01_INITIAL_INVESTIGATION.md` | Understand the brief, domain rules, data and open decisions |
| 02 | `docs\02_DATA_EVALUATION_PLAN.md` | Profile the data; justify the development/test split and evidence references |
| 03 | `docs\03_EVALUATION_ACCEPTANCE.md` | Define acceptance gates, panel-question coverage, review decisions and readiness |

The original package is preserved at `docs\candidate-pack\candidate-pack`.
Document numbers indicate the real sequence of work, not reconstructed Git
history. Git begins with an actual snapshot taken before this reorganization.

## Evaluation layout

```text
eval\
  assess.py                 Ticket-output assessment CLI
  validate.py               Reference/data integrity CLI
  data\
    development.jsonl       13 development finding references
    test.jsonl              8 test finding references
  spec\
    split.json              Current version, partitions, groups and fingerprints
    acceptance.json         17 preregistered system scenarios
    probes.json             Synthetic policy probe and known-false controls
  tests\
    test_assess.py          Tests of the output assessor
    test_validate.py        Tests of reference validation
  results\
    readiness.json          Observed readiness evidence, not system acceptance
    calibration\
      reviewer-a.json       Actual disclosed review judgments
      reviewer-b.json       Separate review provenance
```

`data\test.jsonl` is a dataset; `tests\test_*.py` checks evaluator code. They are
not duplicate tests. There is one current evaluation reference, with its version
in `spec\split.json`; earlier decisions are documented, not parallel eval copies.
The split is non-blind, and the AI-assisted references are not expert-certified.
Reference cards, probes and review results must never enter runtime inference
context.

## Run from the repository root

Windows, Python 3.11+, standard library only; no installation or API key needed:

```powershell
python -B -m eval.validate
python -B -m unittest discover -s eval\tests -p "test_*.py"
python -B -m eval.assess --partition development --checklist
```

Recheck the recorded known-fixture judgments:

```powershell
python -B -m eval.assess --partition development --calibration-reviews eval\results\calibration\reviewer-a.json
python -B -m eval.assess --partition development --calibration-reviews eval\results\calibration\reviewer-b.json
```

For assessment of future generated tickets, see document 03. A passing integrity
check, evaluator self-test or known-fixture calibration is not a system pass.
All 17 system scenarios remain unexecuted until an implementation exists.

Git preserves raw file bytes, including CRLF, so source/reference SHA-256 checks
survive checkout. Do not normalize the supplied package or regenerate evidence
cards during formatting.
