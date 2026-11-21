# From Candidate Brief to Engineering Problem

> **Document status:** current requirement analysis and design assessment. It
> explains the problem framing without serving as implementation or acceptance
> evidence.

## Abstract

The assignment is not a text-transformation exercise. It asks for a system that
turns incomplete inspection observations into reviewable maintenance drafts
while keeping engineering judgment, deterministic control and human authority
separate.

The central design problem is therefore: **where should probabilistic
interpretation stop and predictable software control begin?** The supplied
material requires an LLM or equivalent reasoning component to interpret
free-text evidence, but explicitly requires code-derived urgency and a human
approval boundary. This document derives the engineering questions from the
Candidate Brief and domain notes, identifies the assumptions that the source
package does not resolve, and records the design principles applied by the
current triage workflow.

## 1. What Falkor actually asks the candidate to demonstrate

The required deliverable is one generated `tickets.json` containing a draft for
each of 21 findings. The brief creates the following connected engineering
questions:

| Candidate Brief expectation | Engineering question created |
|---|---|
| Structured tickets and explicit failure behavior | How can malformed, structurally invalid and semantically unsupported output remain visibly different? |
| Maintainable domain knowledge | How do source rules and `engineer_comment` reach assessment, and what does an engineer edit six months later? |
| Code-derived urgency | Which judgments belong to the model, which arithmetic and escalation belong to code, and why? |
| Deferral and human approval | When must the system refuse to score rather than invent a plausible answer? |
| Reproducible, low-cost execution | What identity, accounting and evidence are required to reproduce one result? |
| Defensible summaries, scores and actions | How will grounded quality be assessed beyond schema validity? |

Code style and test coverage support these outcomes, but the brief does not score
them as substitutes for system design or output quality.

## 2. Source-derived domain constraints

The following are interpretations of the supplied package, not independently
certified engineering rules.

### 2.1 Likelihood is not the reliability field

`reliability_score` is a prior whose direction is easy to misuse: 10 means
highly reliable, while likelihood 10 means near-term failure is highly likely or
already confirmed. Copying or merely rescaling the registry field would ignore
the finding evidence and reverse the meaning of the scale.

### 2.2 Impact is not repair cost

Impact concerns failure of the required function and its consequences. It must
consider actual redundancy, delayed or hidden consequences, escalation
potential, and the protected major-accident scenario for Safety Critical
Elements. `criticality_score` is therefore a prior, not the answer.

### 2.3 Redundancy is a claim requiring current evidence

Labels such as `2oo3`, `N+1` or `Duplicated` establish a relationship. They do
not prove that the partner is healthy, available or capable at assessment time.
The system must inspect current partner evidence before granting consequence
credit. Missing partner evidence remains unknown.

### 2.4 Fact state changes policy

The domain notes distinguish confirmed, false, suspected and unknown facts.
That distinction is operationally important: a supplied override requiring
confirmed absence of a deviation cannot be activated merely because no deviation
record was provided. “Not present in the input” is not equivalent to “confirmed
absent.”

### 2.5 Urgency is a transparent attention policy

The brief requires urgency to be derived from likelihood and impact by a
documented function, not authored directly by the model. It must behave
sensibly at both asymmetric corners and support explicit overrides. This creates
a deliberate boundary: the model interprets evidence; code owns the final
arithmetic and rule trace.

## 3. Current design principles

The current system is evaluated against the following principles. Concrete
providers, rubrics, formulas, storage and publication mechanisms remain
implementation choices within these boundaries.

The source constraints require more than accurate prompting. Reliability and
criticality must remain directed priors; redundancy and override facts require
explicit evidence states; and urgency must remain reproducible in code. Combined
with the brief's requirements for maintainable knowledge, visible failure and
one complete output, they lead to the five system-level principles below. These
principles are not a one-to-one restatement of the domain rules: each consolidates
several source constraints and delivery requirements into an enforceable
boundary.

### Decision 1 — Treat the model as an assessor, not the workflow owner

**Decision.** Ask the model to propose likelihood, impact, fact states,
uncertainty, summary and activity. Keep identity, schema, score ranges, urgency,
attempts, coverage and publication in code.

**Rationale.** Free-text evidence requires contextual interpretation. The output
contract, arithmetic and failure policy are deterministic invariants that can be
tested and must not vary with wording. Code-owned attempts, failure diagnostics
and publication keep those controls independent of response wording.

**Rejected alternative.** Asking the model for the complete final ticket,
including urgency, violates the brief and makes retry/publication behavior
prompt-dependent.

### Decision 2 — Preserve uncertainty rather than manufacture completeness

**Decision.** A supported draft may carry a targeted verification requirement.
If the evidence cannot justify required L/I scores, generation fails visibly.

**Rationale.** Human review cannot legitimize fabricated scores. A review flag is
useful only when the assessment is already supportable and the remaining check is
specific.

**Rejected alternative.** Midpoint defaults, placeholder tickets or treating
unknown facts as false would produce complete-looking but ungrounded output.

### Decision 3 — Use the supplied sources as bounded authority

**Decision.** Preserve and deliver the supplied domain notes, registry comments,
finding text and relevant related history. Keep project policy visibly separate
from supplied rules.

**Rationale.** The corpus is small and relationship-heavy. Source fidelity and
bounded context are more important than adding external authority or retrieval
complexity to this exercise.

**Rejected alternative.** Autonomous web retrieval or generated engineering
guidance would add unverifiable authority and weaken reproducibility.

### Decision 4 — Evaluate semantics separately from structure

**Decision.** Test contract behavior deterministically and assess grounded
quality through explicit scenarios and retained real-model observations.

**Rationale.** Valid JSON can still contain an unsupported score or unsafe
activity. Conversely, an evaluator self-test proves only that the evaluator
software detects its seeded fixture.

**Rejected alternative.** Treating schema conformance, unit-test count or AI
reviewer agreement as system acceptance would overstate the evidence.

### Decision 5 — Publish a complete batch or fail closed

**Decision.** Publish only after every selected finding has produced a
contract-valid ticket and the complete batch passes coverage checks. Preserve
any previous output when the new run fails.

**Rationale.** The assignment requires one complete `tickets.json`. A partial
batch could be mistaken for successful coverage and silently omit the finding
that most needs explicit deferral.

**Rejected alternative.** Publishing the other valid drafts with a missing or
placeholder ticket would improve partial availability, but would weaken the
required file's meaning and move failure detection onto downstream readers.

The provider and model, numeric L/I rubric, urgency formula, knowledge packaging,
atomic replacement mechanism and review-routing thresholds are engineering
choices, not requirements supplied by Falkor.

## 4. Current assessment of the design hypotheses

Deterministic tests, bounded experiments and AI-only semantic review support
different claims and are not interchangeable.

| Design principle | Current evidence | Interpretation and remaining limit |
|---|---|---|
| Treat the model as an assessor | Current tests and run evidence show that identity, coverage, urgency and publication remain code-owned while provider failures stay visible. | **Supported at the application boundary.** Measured token usage supports an approximately US$2.35 API-equivalent estimate for the retained delivery; hidden provider retries and the actual Copilot billing allocation remain unknown. |
| Preserve uncertainty | Unsupported scores fail instead of receiving defaults; the current root delivery has six explicit exceptional-review routes while every draft still requires ordinary approval. | **Supported provisionally.** The routing threshold remains candidate-owned and operationally uncalibrated. |
| Use supplied sources as bounded authority | The source-first lifecycle supports edit, review, immutable release and separate activation. Current B02 evidence includes one bounded synthetic influence comparison with a negative control (Document 07; evidence indexed in `eval\results\README.md`). | **Partially supported.** Maintainability and one isolated influence claim are demonstrated; broad causal use and domain correctness are not. |
| Evaluate semantics separately from structure | The current root artifact is contract-valid and has a provisional 63-dimension AI review whose reviewer identity is incomplete under the declared protocol. | **Supported as an evaluation principle.** AI review is not expert certification or human approval. |
| Publish a complete batch or fail closed | Current fault tests preserve old output on handled failures. The 21-ticket experimental output has a verified publication receipt, and root `tickets.json` is byte-identical by SHA-256 after separate promotion. | **Supported for current code, observed experimental publication and hash-checked promotion.** The root copy has no separate workflow receipt; clean-checkout reproduction remains unresolved, and the design sacrifices partial availability. |

Detailed observations and current gate status remain in root `README.md` and
`eval\results\README.md`; this section records what those observations imply
for the initial design reasoning.

## 5. Assumptions requiring explicit ownership

| Assumption | Consequence |
|---|---|
| The supplied files are the complete selected snapshot | The system does not invent later repair, deterioration or operational state |
| Registry comments are evidence, not conclusions | They must be interpreted and cited rather than copied as truth |
| L/I/U are ordinal scales | Arithmetic expresses prioritization policy, not probability or expected loss |
| Missing records remain unknown | Confirmed overrides require positive evidence |
| One trusted local writer publishes the file | Atomic same-volume replacement is sufficient; distributed-concurrency safety is not claimed |
| Every generated ticket requires ordinary human approval; `review_required` identifies exceptional prequeue review | No ticket authorizes maintenance, shutdown or work execution, and the exceptional flag does not replace universal approval |
| The example ticket is illustrative | Its scores are not a hidden answer key |
| AI-assisted reference material is not expert gold | Reviewer and reference limitations remain visible |
| The retained successful route depends on access to the configured provider entitlement | A first-time reviewer may reproduce deterministic checks without being able to replay the model run; measured usage and API-equivalent cost remain inspectable even though the actual Copilot billing allocation is not exposed |

Numeric calibration, acceptable false-positive cost and the organization’s final
review-routing policy are not supplied. The prototype must therefore label its
thresholds as candidate-owned policy rather than Falkor-certified truth.

## 6. Requirement-to-evidence chain

The requirement-to-evidence chain is:

```text
Candidate Brief and domain notes
  -> Document 02: data, context and evidence boundaries
  -> Document 03: observable acceptance and fixed-identity reliability protocol
  -> Documents 04-06: component and workflow decisions
  -> Documents 07-08: controlled knowledge and behavior studies
  -> root README + eval\results: submission status, observations and limits
```

The current system and observed status are described in `DESIGN.md` and
`eval\results\README.md`.

## 7. Limits of this document

This analysis can establish traceability from the assignment to engineering
questions. It cannot establish that the chosen urgency policy is calibrated,
that the model uses delivered knowledge, that semantic review is correct, or
that the generated drafts are operationally approved. Those require executable
evidence and, for operational use, domain-owner judgment.
