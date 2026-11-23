# Requirements and Design Principles

## Abstract

The system must do more than rewrite inspection text. It must turn incomplete
observations into maintenance drafts that a human can review.

The main design question is: **what should the model decide, and what must code
control?** A large language model (LLM), or another reasoning component,
interprets the free-text evidence. Code calculates urgency. A human approves
every draft before anyone acts.

The supplied package leaves some questions open. This document explains the
assumptions and design choices used by the current workflow.

Sections 1-3 explain the brief, the supplied rules and the design choices.
Section 4 reports current evidence. It does not change the requirements.

## 1. Requirements and engineering questions

The system must generate one `tickets.json` with a draft for each of the 21
findings. The brief raises these questions:

| Brief requirement | Engineering question |
|---|---|
| Structured tickets and explicit failure behavior | How do we distinguish unreadable JSON, fields that break the schema, and claims that lack evidence? |
| Maintainable domain knowledge | How do source rules and `engineer_comment` reach the model? What will an engineer edit six months later? |
| Code-derived urgency | What does the model judge? What calculations and escalation rules does code apply? |
| Deferral and human approval | When must the system refuse to score instead of inventing an answer? |
| Reproducible, low-cost execution | What versions, usage records and evidence does someone need to repeat a run? |
| Defensible summaries, scores and actions | How do we check evidence and meaning, not just the JSON structure? |

Code style and tests help. They do not replace good system design or good tickets
in the brief's assessment.

Throughout this document, **L** is model-proposed likelihood, **I** is
model-proposed impact and **U** is code-derived urgency. All three use an
**ordinal** 1-10 scale: larger values mean higher priority. The numbers are not
probabilities or estimates of expected loss.

## 2. Source-derived domain constraints

The following points explain how this project reads the supplied package.
Independent engineering experts have not certified these interpretations.

### 2.1 Likelihood is not the reliability field

The registry's `reliability_score` is a **prior**: a starting point that the
finding evidence can change. Its scale runs in the opposite direction to
likelihood. Reliability 10 means highly reliable. Likelihood 10 means near-term
failure is highly likely or already confirmed.

Copying or simply rescaling reliability would ignore the finding evidence and
reverse the scale's meaning.

### 2.2 Impact is not repair cost

Impact asks what happens if the equipment cannot perform its required function.
The assessment must consider available backup equipment, delayed or hidden
effects, and whether the failure could grow into a larger incident.

A **Safety Critical Element (SCE)** protects against a major accident. Its impact
must be judged against that accident, not just repair cost. The registry's
`criticality_score` is a starting point, not the final answer.

### 2.3 Redundancy is a claim requiring current evidence

**Redundancy** means that another item can provide the required function.
Labels such as `2oo3` (two-out-of-three voting), `N+1` (one spare beyond required
capacity) or `Duplicated` describe an arrangement. They do not prove that the
other item is healthy, available or capable now.

The system must check current evidence before reducing impact because of backup
equipment. If that evidence is missing, the backup's state remains unknown.

### 2.4 Fact state changes policy

The domain notes distinguish confirmed, false, suspected and unknown facts.
These states affect which rules apply.

For example, an override may require confirmed absence of a recorded deviation.
A **deviation** is the record used to manage an impaired protection layer.
No deviation record in the input does not prove that no deviation exists.
“Not present in the input” is not equivalent to “confirmed absent.”

### 2.5 Urgency is a transparent attention policy

The brief requires a documented function that calculates urgency from likelihood
and impact. The model must not choose urgency directly.

The function must handle both low-likelihood/high-impact and
high-likelihood/low-impact cases. It must also support explicit overrides backed
by supplied rules or confirmed facts. The model interprets evidence. Code does
the final calculation and records which rules it applied.

## 3. Current design principles

A good prompt alone is not enough. The system must use reliability and
criticality in the correct direction. It must record what is known about backup
equipment and override conditions. Code must calculate urgency repeatably.

These rules, plus the need for editable knowledge, visible failures and a
complete output, lead to the five principles below. The provider, scoring guide
(**rubric**), formula, storage and publication method are project choices within
these rules.

### 3.1 The model assesses; the workflow controls

The model proposes likelihood, impact, fact states, uncertainty, a summary and
an activity. Code checks ticket identity, the **schema** (allowed fields and
types), score ranges and coverage. Code also controls urgency, attempts and
publication.

The model interprets free-text evidence in context. The output rules,
calculations and failure policy are **deterministic**: the same inputs must
produce the same code behavior. Tests check these rules. Different wording must
not change them.

We rejected asking the model for the final ticket, including urgency. That would
break the brief and let the prompt control retries and publication.

### 3.2 Preserve uncertainty rather than manufacture completeness

A draft with supported scores may still require a specific check. If the
evidence cannot justify the required L/I scores, generation fails visibly.

Human review does not make invented scores acceptable. A review flag is useful
only when the assessment has evidence and the remaining check is specific.

We rejected default midpoint scores, placeholder tickets and treating unknown
facts as false. They make the output look complete without supporting evidence.

### 3.3 Use the supplied sources as bounded authority

The system preserves the supplied domain notes, registry comments, finding text
and relevant related history, and sends them to the model. It labels project
policy separately from supplied rules.

The source collection is small, and many findings are related. Keeping the
source meaning intact and limiting the model's context is more useful here than
adding external guidance or a complex search system.

We rejected automatic web searches and model-generated engineering guidance.
They would add authority that we cannot verify and make runs harder to repeat.

### 3.4 Evaluate semantics separately from structure

Code tests check the contract rules. Defined scenarios and saved real-model
outputs check whether tickets are supported by evidence.

Valid JSON can still contain an unsupported score or unsafe activity.
An evaluator self-test checks something different: whether the evaluation
software detects a contradiction deliberately added to a test fixture.

Correct structure, many unit tests and agreement between AI reviewers do not
establish system acceptance. Each supports a narrower claim.

### 3.5 Publish a complete batch or fail closed

The system publishes only after every selected finding has a ticket that meets
the contract and the batch passes coverage checks. A failed run leaves any
previous output unchanged. This is **fail closed**: failure does not publish a
new result.

The assignment requires one complete `tickets.json`. Readers could mistake a
partial batch for success. It could omit the very finding that needs the system
to stop and request help.

Publishing only the successful drafts would make some results available sooner.
We rejected it because the required file would no longer mean “all findings are
covered.” Readers would have to detect the missing or replaced finding.

## 4. Current evidence against the design principles

Code tests, limited experiments and AI-only review of ticket meaning
(**semantic review**) support different claims. One cannot replace another.

For evaluation, the 21 findings are partitioned into 13 development and eight
designated test findings. Development model inputs should exclude test finding
descriptions. Instead, every retained development provider input contained all
eight test finding descriptions. B01 is therefore not met.

The `Supported` and `Partial` labels below describe current evidence, not
readiness for operational use. [Document 03](03_EVALUATION_ACCEPTANCE.md) defines
the acceptance scenarios and status rules.

The retained runs used an existing GitHub Copilot subscription. Applying public
API prices to measured tokens gives a comparison estimate, called
**API-equivalent cost**. It is not the actual subscription charge.

| Design principle | Current evidence | Interpretation and remaining limit |
|---|---|---|
| Treat the model as an assessor | Tests and saved runs show that code controls identity, coverage, urgency and publication. Provider failures remain visible. | **Supported at the application boundary.** The delivery's API-equivalent estimate is about US$2.35. Hidden provider retries and actual Copilot billing remain unknown. |
| Preserve uncertainty | Unsupported scores cause failure, not default scores. Six tickets have `review_required` for extra review before entering the normal work queue. Every draft still needs ordinary approval. | **Supported provisionally.** The project chose the extra-review threshold. It has not been calibrated for operational use. |
| Use supplied sources as bounded authority | The knowledge process supports editing, review, releases that cannot be changed, and separate approval for runtime use. One synthetic comparison shows limited knowledge influence. Every development provider input also contained all eight test finding descriptions. | **Partially supported; development/test isolation failed.** Knowledge maintenance and one limited influence claim are demonstrated. Case-isolated inference, wider use of knowledge and domain correctness are not established. |
| Evaluate semantics separately from structure | Root `tickets.json` meets the structural contract and has provisional AI-only semantic review. Reviewer calibration was minimal, and one required review behavior was not tested. | **Supported as a design principle; semantic-error acceptance remains Partial.** AI review is not expert certification or human approval. |
| Publish a complete batch or fail closed | Fault tests leave old output unchanged on handled failures. The workflow wrote and verified 21 tickets in an experiment directory. Root `tickets.json` is an exact copy, verified by SHA-256. | **Supported for current code and the observed experimental publication.** The root copy has no separate workflow record. Reproduction from a clean checkout remains unresolved. The design does not provide partial results. |

Root `README.md` and `eval\results\README.md` contain the detailed observations
and current acceptance status.

## 5. Assumptions requiring explicit ownership

| Assumption | Consequence |
|---|---|
| The supplied files are the complete selected snapshot | The system does not invent later repairs, deterioration or operating states |
| Registry comments are evidence, not final conclusions | The model must interpret and cite them, not copy them as unquestioned truth |
| L/I/U are ordinal scales | Calculations express priority policy, not probability or expected loss |
| Missing records remain unknown | An override based on confirmed facts needs positive evidence |
| One trusted local process writes the file | Replacing the whole file in one step on the same volume is sufficient. Safety with multiple distributed writers is not claimed |
| Every draft needs ordinary human approval; `review_required` marks extra review before queuing | No ticket authorizes maintenance, shutdown or work. The extra flag does not replace approval of every draft |
| The example ticket illustrates the format | Its scores are not an answer key |
| AI-assisted reference material is not expert-verified truth | Reference and reviewer limits must stay visible |
| Repeating the retained model route requires the configured Copilot access | A new reviewer can run code checks without that access, but cannot repeat the provider call. Usage and API-equivalent cost can still be inspected. Actual Copilot billing allocation is not exposed |

The supplied material does not calibrate numeric scores, define the acceptable
cost of unnecessary alerts, or set the organization's final review-routing
policy. The prototype must label its thresholds as project policy, not certified
engineering truth.

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

Linking requirements to evidence does not prove that urgency is calibrated,
that the model uses the knowledge it receives, that semantic review is correct,
or that the drafts are approved for use. Those claims need checks that can be
run. Operational use also needs the domain owner's judgment.
