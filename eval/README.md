# Evaluation

This directory separates the **system acceptance contract** from component
experiments and observed results. It is not part of the production runtime.

## Navigation

| Path | Purpose | Panel relevance |
|---|---|---|
| `spec` | Frozen system scenarios, split, probes and knowledge-component reference | Defines what counts; specifications are not results |
| `data` | System evidence cards and synthetic knowledge-extraction fixtures | Evaluator inputs only; never production context |
| `assess.py` | Validates and summarizes semantic reviews against the declared contract | System-level evaluation |
| `validate.py` | Validates source, split and specification integrity | Integrity check only |
| `tests` | Evaluator self-tests, separated into system and knowledge-component tests | Verifies evaluator software, not ticket quality |
| [`knowledge`](knowledge/README.md) | Isolated knowledge extraction, selector and lifecycle evaluation harnesses | Component evidence only |
| [`results`](results/README.md) | Retained observations, failures, cost and current evidence status | Evidence authority |

## System-level commands

Run from the repository root:

```powershell
python -B -m eval.validate
python -B -m eval.assess --help
python -B -m unittest discover -s eval\tests -p "test_*.py"
```

`eval.validate` and evaluator tests establish artifact/software integrity. They
do not establish model accuracy, domain certification or human approval.

## Boundaries

- Production code does not import this package.
- Expected answers, reviewer judgments and synthetic evaluation overlays are
  excluded from provider-bound production context.
- Frozen specifications are changed only through the controlled process in
  `AGENTS.md` and Document 03.
- New results belong under `results`; generated scratch output and local raw
  transcripts should not be promoted unless they support a declared requirement,
  material failure or current delivery.
