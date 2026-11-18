# Knowledge Component Evaluation

This package contains the isolated evaluation harness for source extraction,
review/release mechanics, selector behavior and provider handoff. It supports
the knowledge architecture described in Document 05; it is not the production
knowledge store and does not score inspection findings.

## Package map

| Module | Responsibility |
|---|---|
| `evaluate.py` | Loads the frozen component suite and grades extraction/retrieval observations |
| `query_inputs.py` | Builds the source-derived synthetic registry fixture |
| `run.py` | Runs the baseline offline or explicitly authorized Copilot component experiment |
| `completion.py` | Runs the bounded completion/regression experiment |
| `package.py` | Exercises source package, review, release and context mechanics offline |
| `handoff.py` | Captures one bounded provider transport acknowledgement |
| `attempts.py` | Persistent component-experiment attempt accounting |
| `copilot.py` | Restricted Copilot request/receipt driver for component experiments |

The frozen component reference remains at
`eval\spec\knowledge_extraction.json`; its synthetic sources and reference data
remain under `eval\data\knowledge_extraction`. Historical and current
observations remain under `eval\results\knowledge`.

## Commands

```powershell
python -B -m eval.knowledge.run --help
python -B -m eval.knowledge.completion --help
python -B -m unittest discover -s eval\tests\knowledge -p "test_*.py"
```

Live provider execution always requires the harness-specific explicit
authorization flag. Offline component passes demonstrate software behavior,
not domain correctness, production knowledge influence or system acceptance.
