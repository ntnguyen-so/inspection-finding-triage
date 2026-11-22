# Requirements and Design Principles

## Abstract

The assignment is not a text-transformation exercise. It asks for a system that
turns incomplete inspection observations into reviewable maintenance drafts
while keeping engineering judgment, deterministic control and human authority
separate.

The central design problem is therefore: **where should probabilistic
interpretation stop and predictable software control begin?** The supplied
material requires an LLM or equivalent reasoning component to interpret
free-text evidence, but explicitly requires code-derived urgency and a human
approval boundary. The resulting engineering questions expose assumptions that
the source package does not resolve; the sections below set out the design
principles used by the current triage workflow.

Sections 1-3 move from the brief, to source-derived constraints, to the design
principles chosen in response. Section 4 then reports current evidence against
those principles; it does not redefine the original requirements.

## 1. Requirements and engineering questions

The required deliverable is one generated `tickets.json` containing a draft for
each of 21 findings. The brief creates the following connected engineering
questions:

| Brief requirement | Engineering question |
|---|---|
| Structured tickets and explicit failure behavior | How can malformed, structurally invalid and semantically unsupported output remain visibly different? |
| Maintainable domain knowledge | How do source rules and `engineer_comment` reach assessment, and what does an engineer edit six months later? |
| Code-derived urgency | Which judgments belong to the model, which arithmetic and escalation belong to code, and why? |
| Deferral and human approval | When must the system refuse to score rather than invent a plausible answer? |
| Reproducible, low-cost execution | What identity, accounting and evidence are required to reproduce one result? |
| Defensible summaries, scores and actions | How will grounded quality be assessed beyond schema validity? |

Code style and test coverage support these outcomes, but the brief does not score
them as substitutes for system design or output quality.

Throughout this document, **L** is model-proposed likelihood, **I** is
model-proposed impact and **U** is code-derived urgency. All three are ordinal
1-10 prioritisation scales, not probabilities or expected-loss estimates.

## 2. Source-derived domain constraints

The following are interpretations of the supplied package, not independently
certified engineering rules.

### 2.1 Likelihood is not the reliability field

The equipment registry's `reliability_score` is a prior whose direction is easy
to misuse: 10 means highly reliable, while likelihood 10 means near-term failure
is highly likely or already confirmed. Copying or merely rescaling the registry
field would ignore the finding evidence and reverse the meaning of the scale.

### 2.2 Impact is not repair cost

Impact concerns failure of the required function and its consequences. It must
consider actual redundancy, delayed or hidden consequences, escalation
potential, and the protected major-accident scenario for Safety Critical
Elements (SCEs). The equipment registry's `criticality_score` is therefore a
prior, not the answer.

### 2.3 Redundancy is a claim requiring current evidence

Labels such as `2oo3` (two-out-of-three voting), `N+1` (one spare beyond the
required capacity) or `Duplicated` establish a relationship. They do not prove
that the partner is healthy, available or capable at assessment time. The
system must inspect current partner evidence before granting consequence credit.
Missing partner evidence remains unknown.

### 2.4 Fact state changes policy

The domain notes distinguish confirmed, false, suspected and unknown facts.
That distinction is operationally important: a supplied override requiring
confirmed absence of a deviation cannot be activated merely because no deviation
record was provided. “Not present in the input” is not equivalent to “confirmed
absent.”

### 2.5 Urgency is a transparent attention policy

The brief requires urgency to be derived from likelihood and impact by a
documented function, not authored directly by the model. It must behave
sensibly when likelihood is low but impact is high, and when likelihood is high
but impact is low. It must also support explicit source-backed or confirmed-fact
overrides. This creates a deliberate boundary: the model interprets evidence;
code owns the final arithmetic and rule trace.

## 3. Current design principles

The source constraints require more than accurate prompting. Reliability and
criticality are directed priors; redundancy and override facts need explicit
evidence states; and urgency must be reproducible in code. Together with the
brief's requirements for maintainable knowledge, visible failure and one
complete output, they lead to five system-level principles. Provider, rubric,
formula, storage and publication details remain implementation choices within
those boundaries.

### 3.1 The model assesses; the workflow controls

The model proposes likelihood, impact, fact states, uncertainty, summary and
activity. Identity, schema, score ranges, urgency, attempts, coverage and
publication remain in code.

Free-text evidence requires contextual interpretation. The output contract,
arithmetic and failure policy are deterministic invariants that can be tested
and must not vary with wording.

Asking the model for the complete final ticket, including urgency, was rejected
because it violates the brief and makes retry and publication behavior
prompt-dependent.

### 3.2 Preserve uncertainty rather than manufacture completeness

A supported draft may carry a targeted verification requirement. If the
evidence cannot justify required L/I scores, generation fails visibly.

Human review cannot legitimize fabricated scores. A review flag is useful only
when the assessment is already supportable and the remaining check is specific.

Midpoint defaults, placeholder tickets and treating unknown facts as false were
rejected because they produce complete-looking but ungrounded output.

### 3.3 Use the supplied sources as bounded authority

The system preserves and delivers the supplied domain notes, registry comments,
finding text and relevant related history. Project policy remains visibly
separate from supplied rules.

The corpus is small and relationship-heavy, so source fidelity and bounded
context are more useful than external authority or additional retrieval
complexity.

Autonomous web retrieval and generated engineering guidance were rejected
because they add unverifiable authority and weaken reproducibility.

### 3.4 Evaluate semantics separately from structure

Contract behavior is tested deterministically. Grounded quality is assessed
through explicit scenarios and retained real-model observations.

Valid JSON can still contain an unsupported score or unsafe activity.
Conversely, an evaluator self-test proves only that the evaluator software
detects a deliberately seeded contradiction.

Schema conformance, unit-test count and AI reviewer agreement are not treated as
system acceptance because each would overstate the available evidence.

### 3.5 Publish a complete batch or fail closed

Publication occurs only after every selected finding has produced a
contract-valid ticket and the complete batch passes coverage checks. A failed
run preserves any previous output.

The assignment requires one complete `tickets.json`. A partial batch could be
mistaken for successful coverage and silently omit the finding that most needs
explicit deferral.

Publishing valid drafts while omitting or replacing a failed finding would
improve partial availability, but it would weaken the required file's meaning
and move failure detection onto downstream readers.

## 4. Current evidence against the design principles

Deterministic tests, bounded experiments and AI-only semantic review support
different claims and are not interchangeable.

For evaluation, the 21 findings are partitioned into 13 development and eight
designated test findings. Development model inputs should exclude test finding
descriptions; the retained runs did not preserve that isolation. The
`Supported` and `Partial` labels below summarize current evidence, not production
readiness. [Document 03](03_EVALUATION_ACCEPTANCE.md) defines the full acceptance
scenarios and status rules.

The retained model route uses an existing GitHub Copilot subscription. Its
measured tokens can be repriced at public API rates for comparison, but that
estimate is not the subscription's actual billed cost.

| Design principle | Current evidence | Interpretation and remaining limit |
|---|---|---|
| Treat the model as an assessor | Tests and retained runs show that identity, coverage, urgency and publication remain code-owned while provider failures stay visible. | **Supported at the application boundary.** The retained delivery has an approximately US$2.35 API-equivalent token estimate; hidden provider retries and actual Copilot billing remain unknown. |
| Preserve uncertainty | Unsupported scores fail instead of receiving defaults. Six tickets are flagged `review_required` for extra review before normal queuing; every draft still requires ordinary approval. | **Supported provisionally.** The exceptional-routing threshold remains project-defined and operationally uncalibrated. |
| Use supplied sources as bounded authority | The source-first lifecycle demonstrates edit, review, immutable release and separate runtime approval. One synthetic comparison shows bounded knowledge influence, but every development provider input also contained all eight test-set finding descriptions. | **Partially supported; development/test isolation failed.** Maintenance mechanics and one bounded influence claim are demonstrated, but case-isolated inference, broad causal use and domain correctness are not. |
| Evaluate semantics separately from structure | The root artifact is contract-valid and has a provisional AI-only semantic review, but reviewer calibration was minimal and one required review behavior was not exercised. | **Supported as a design principle; semantic-error acceptance remains Partial.** AI review is not expert certification or human approval. |
| Publish a complete batch or fail closed | Fault tests preserve old output on handled failures. The workflow wrote and verified a 21-ticket output in an experiment directory; root `tickets.json` is a byte-identical copy by SHA-256. | **Supported for current code and observed experimental publication.** The copy to root has no separate workflow-issued record, clean-checkout reproduction remains unresolved, and the design sacrifices partial availability. |

Root `README.md` and `eval\results\README.md` contain the detailed observations
and current acceptance status.

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
| Replaying the retained model route requires access to the configured Copilot entitlement | A first-time reviewer can reproduce deterministic checks without that access, but cannot replay the provider call. Measured usage and API-equivalent cost remain inspectable; the actual Copilot billing allocation is not exposed |

Numeric calibration, acceptable false-positive cost and the organization’s final
review-routing policy are not supplied. The prototype must therefore label its
thresholds as project-defined policy rather than certified engineering truth.

## 6. Requirement-to-evidence chain

The requirement-to-evidence chain is:

```text
Brief and domain notes
  -> Document 02: data, context and evidence boundaries
  -> Document 03: observable acceptance and fixed-identity reliability protocol
  -> Documents 04-06: component and workflow decisions
  -> Documents 07-08: controlled knowledge and behavior studies
  -> root README + eval\results: delivery status, observations and limits
```

## 7. Known limitations

Requirements traceability does not establish that the urgency policy is
calibrated, that the model uses delivered knowledge, that semantic review is
correct, or that generated drafts are operationally approved. Those claims
require executable evidence and, for operational use, domain-owner judgment.
