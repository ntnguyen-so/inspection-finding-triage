# Original Decision Process

This directory preserves the exact **working-tree** bytes of Documents 01-06 as
they existed when the panel-facing redesign began on 2026-11-17. It is not a
claim that every file matches the last commit.

The originals are retained because they contain the chronological investigation,
draft decisions, failed approaches, experiment handoffs and test-informed
corrections that produced the current system. They are development evidence, not
the shortest panel reading path. The files at `docs\01_*.md` through
`docs\06_*.md` are the concise panel-facing versions.

`manifest.json` records the byte length, SHA-256 digest, source status, HEAD
revision and HEAD-content digest for every preserved file. The copies were
verified against their working-tree sources immediately after creation.
Historical experiment claims remain bound to the code, configuration and
document hashes recorded by those experiments; this archive does not make old
results current.

Documents 02 and 03 require special care. Archived Document 02 is byte-identical
to HEAD. Archived Document 03 is the pre-rewrite reference-v1.3 working contract;
the committed v1.2 contract remains recoverable from revision `92734d6` and has
SHA-256 `ed0d6488673615857d47d396f148217e218469d2289704e3410308ea4a662e70`.
The executable specifications under `eval\spec` are the machine-checked authority
for the current working reference.

## Files

| Preserved file | Historical role |
|---|---|
| `01_INITIAL_INVESTIGATION.md` | Requirement extraction, domain traps and initial assumptions |
| `02_DATA_EVALUATION_PLAN.md` | Data profile, split rationale and evidence boundaries |
| `03_EVALUATION_ACCEPTANCE.md` | Detailed acceptance scenarios and assessor procedure |
| `04_INFERENCE_LIBRARY.md` | Inference-adapter development and provider experiments |
| `05_TRIAGE_WORKFLOW.md` | Workflow evolution, policy revisions and model-run history |
| `06_KNOWLEDGE_DESIGN_DECISION.md` | Knowledge-module experiments, redesign and integration |

Use the primary numbered documents for the current rationale, `DESIGN.md` for the
system-level answer, and `eval\results\README.md` for observed results.

The archived Document 04 is intentionally unchanged. A later retrospective
clarification—that the existing Copilot CLI subscription reduced marginal
development spend and motivated provider portability—is recorded in the
panel-facing Document 04 and `DESIGN.md`, not inserted into the historical
snapshot.

The archive also retains the historical order `05 Workflow -> 06 Knowledge`.
The panel-facing order is intentionally `05 Knowledge -> 06 Workflow` so the
reader sees the knowledge authority and retrieval contract before the workflow
that consumes it. Renaming the archived files would break their snapshot
identity and historical references.

The runtime assessment-policy phrase `Document 05 section 4` is one such
historical reference. It points to archived `05_TRIAGE_WORKFLOW.md` §4, where the
prototype L/I rubric was approved; it must not be reinterpreted as current panel
Document 05. The runtime string remains unchanged to preserve prompt/policy
identity until a separately declared freeze changes it.
