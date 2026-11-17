# From Candidate Brief to Engineering Problem

> **Document status:** retrospective requirement analysis. It explains the
> problem framing that drove the system; it is not implementation or acceptance
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
package does not resolve, and records the alternatives rejected before
implementation.

## 1. What Falkor actually asks the candidate to demonstrate

The required deliverable is one generated `tickets.json` containing a draft for
each of 21 findings. The panel assesses four connected capabilities:

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

## 3. Initial design decisions

### Decision 1 — Treat the model as an assessor, not the workflow owner

**Decision.** Ask the model to propose likelihood, impact, fact states,
uncertainty, summary and activity. Keep identity, schema, score ranges, urgency,
attempts, coverage and publication in code.

**Rationale.** Free-text evidence requires contextual interpretation. The output
contract, arithmetic and failure policy are deterministic invariants that can be
tested and must not vary with wording. A provider-neutral boundary also permits
economical development through the candidate's existing Copilot CLI entitlement
without making that personal subscription a production dependency.

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

**Rationale.** The corpus is small and relationship-heavy. Source fidelity is
more important than introducing retrieval infrastructure without an observed
need.

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

## 4. Assumptions requiring explicit ownership

| Assumption | Consequence |
|---|---|
| The supplied files are the complete selected snapshot | The system does not invent later repair, deterioration or operational state |
| Registry comments are evidence, not conclusions | They must be interpreted and cited rather than copied as truth |
| L/I/U are ordinal scales | Arithmetic expresses prioritization policy, not probability or expected loss |
| Missing records remain unknown | Confirmed overrides require positive evidence |
| One trusted local writer publishes the file | Atomic same-volume replacement is sufficient; distributed-concurrency safety is not claimed |
| Every generated ticket requires human approval | No ticket authorizes maintenance, shutdown or work execution |
| The example ticket is illustrative | Its scores are not a hidden answer key |
| AI-assisted reference material is not expert gold | Reviewer and reference limitations remain visible |

Numeric calibration, acceptable false-positive cost and the organization’s final
review-routing policy are not supplied. The prototype must therefore label its
thresholds as candidate-owned policy rather than Falkor-certified truth.

## 5. Requirement-to-evidence chain

This investigation produced questions, not results:

```text
Candidate Brief and domain notes
  -> Document 02: data, context and evidence boundaries
  -> Document 03: observable acceptance scenarios
  -> Documents 04-06: component and workflow decisions
  -> Document 07: frozen-version reliability method
  -> eval\results: observations, including failures and unknowns
```

The current system and observed status are described in `DESIGN.md` and
`eval\results\README.md`. The exact chronological investigation that preceded
this panel version is preserved in
`docs\original-decision-process\01_INITIAL_INVESTIGATION.md`.

## 6. Limits of this document

This analysis can establish traceability from the assignment to engineering
questions. It cannot establish that the chosen urgency policy is calibrated,
that the model uses delivered knowledge, that semantic review is correct, or
that a final accepted output exists. Those require executable evidence and, for
operational use, domain-owner judgment.
