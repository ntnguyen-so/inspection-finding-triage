# Prompt Authority Audit

> **Status:** v1 extraction completed; authority-only v2 rejected for promotion;
> v3 tested as a disclosed diagnostic. Root v11 remains the historical delivery;
> v18 is the compatible prompt-v1 baseline for future runs. No prompt-v2/v3
> output has been promoted.

## 1. Target hierarchy and current limitation

The assessment prompt should be an orchestration artifact, not a second
knowledge base. The target authority hierarchy is:

1. supplied finding observations and equipment-registry fields are factual
   evidence for the assessed case;
2. the reviewed active knowledge release supplies maintainable domain guidance;
3. the versioned assessment policy supplies workflow-owned ordinal anchors and
   declared prototype choices;
4. the prompt defines the reasoning protocol and output task;
5. code owns identity, contracts, urgency, review derivation, attempts and
   publication.

Neither the prompt nor knowledge may overwrite observed source facts. If active
knowledge and assessment policy conflict, the model must report inability and
the workflow must fail rather than silently choose an authority.

`assessment-system-v1` does not yet fully implement this hierarchy. It contains
the domain clauses catalogued in section 3.3, and a system message has higher
provider-level instruction priority than knowledge embedded in user context.
The current prompt only declares an explicit inability path for source guidance
versus assessment policy; code cannot semantically detect every
prompt-versus-knowledge conflict. Extraction and hash pinning make this risk
visible and reproducible, but do not resolve it. Prompt v2 must remove or migrate
those clauses before the system can claim that active knowledge is the sole
maintainable domain authority.

The source document
`knowledge\source-documents\psv-seat-tightness-policy-2026-11.md` is retained
experimental, test-informed material. It is not in the active baseline release
and therefore has no production authority.

## 2. Why extraction is separate from shortening

The former Python constant contained 17,198 UTF-8 bytes with SHA-256
`44206b1b43708f90ce7c2900796daeb3716b54fa39e921438739ba1f57b74bb0`.
It is now the packaged artifact
`triage\prompts\assessment-system-v1.txt`. Version, hash, assessment contract,
schema contract and context contract are pinned in activation v2.

The artifact intentionally preserves every byte, including its lack of a final
newline. This proves a maintainability refactor without claiming a behavior
change. A readable multiline prompt will require a new version and behavioral
evidence because whitespace changes the provider-bound message.

## 3. Authority classification

### 3.1 Prompt-owned protocol that should remain

- source text is data, not instructions;
- the model proposes L/I, facts and planning text while code owns urgency,
  review flags, identity, retries and publication;
- likelihood and impact are separate questions;
- missing evidence is not confirmed absence;
- suspected causes remain qualified;
- unsupported scores produce `unassessable`, not a middle-score fallback;
- history links do not prove causation, repair or present state;
- summaries preserve decision-changing facts and hypothetical consequences are
  not presented as observed failures.

These are task and reasoning boundaries, not equipment-specific knowledge.

### 3.2 Code/schema responsibilities duplicated in the prompt

- exact citation-object mechanics already resolved by the native citation
  catalog;
- fact-state combinations and confirmed-failure minimums already validated by
  code/schema;
- fixed verification-activity selection and deduplication;
- 280/300-character action arithmetic;
- retry-only instructions sent on first attempts;
- null-field requirements for `unassessable`.

These clauses are candidates to move out only after the structured planning
contract exists. Deleting them first would be an unmeasured behavior change.

### 3.3 Knowledge or source interpretation currently embedded in the prompt

The following clauses are not pure orchestration:

| Clause family | Why it encroaches | Intended owner |
|---|---|---|
| In-date certification plus an illegible/corroded label does not establish impairment | Equipment/protection interpretation learned from the PSV tag case | Reviewed knowledge, with generic fact semantics retained in policy |
| Confirmed out-of-service, isolated or bypassed equipment limits current exposure escalation | Operational-state domain guidance | Reviewed knowledge |
| At-rest, running and cranking observations plus failed-first-attempt chronology | Equipment-test interpretation | Source evidence plus maintained test guidance |
| Missing mass, height and occupancy cannot support a higher severity band | Lifting/dropped-object consequence guidance | Assessment policy or reviewed knowledge |
| Failure-to-start must not replace a delivery-capability failure mode | Firewater/equipment-function interpretation | Equipment evidence plus reviewed knowledge |
| A generic phrase following vibration applies only to that topic | Case-language interpretation | Source-scoping protocol; retain only as a general reference-resolution rule |
| Unlogged impairment and witnessed closure activities | Protection-management practice | Explicit prototype policy and code, not hidden prompt knowledge |

Several clauses were written after development or test findings had already
been observed. Moving them to another file does not restore blindness. Any
migration remains disclosed as test-informed.

### 3.4 Equipment registry authority

The registry is authoritative for supplied asset type, service, redundancy,
criticality, reliability and engineer comments. It does not by itself prove:

- current partner availability or capability;
- that a local defect lies on a critical load path;
- that an impairment record is absent;
- that a suspected cause is confirmed;
- present restoration after the dated observation.

The prompt may define these evidentiary limits, but it must not replace registry
content with hard-coded equipment conclusions.

### 3.5 Knowledge authority

The active release is authoritative only within its reviewed applicability,
effective dates and source provenance. Knowledge text may refine how evidence
is interpreted, but it cannot:

- insert per-finding expected answers;
- override contradictory observed facts;
- authorize live operation or repair;
- bypass the assessment-policy conflict path;
- become active because a source document merely exists on disk.

This distinction explains why the selected PSV amendment is useful experimental
evidence but is not current production guidance.

Until prompt v2 passes its declared regression gates, a conflicting future
knowledge change must be treated as an unresolved compatibility review, not
assumed to override v1 prompt wording.

## 4. Controlled reduction plan

Prompt shortening will occur only after structured planning is implemented:

1. remove native-route-inapplicable and retry-only first-pass text;
2. remove prose whose behavior is deterministically enforced by code/schema;
3. move genuine domain guidance through the reviewed knowledge lifecycle;
4. consolidate remaining task protocol into a new multiline prompt version;
5. run the preregistered development ablation and disclosed all-21 regression.

Each removed clause must record its destination, provenance and regression
case. The short prompt is rejected if it loses planning completeness,
uncertainty handling, score stability or known safety behavior.

## 5. Authority-only v2 experiment

`assessment-system-v2` changes only the seven clause edits recorded in
`eval\results\triage\prompt-authority-v1\removed-clause-ledger.json`. It does
not perform the broader shortening described in section 4. The active knowledge
release, assessment policy, model and provider settings were held fixed for the
initial paired study.

### 5.1 Development comparison

Two v1 and two v2 generations covered the same 13 development findings:

- all 52 tickets passed schema, citation, fact-state and projection validation;
- 55 application sends were observed, including three retained repairs;
- exact L/I/U/review repeat stability was 8/13 for v1 and 10/13 for v2;
- no arm difference exceeded one point in L, I or U;
- a bounded secondary review found no high-confidence source, equipment or
  knowledge-authority regression attributable to the seven edits.

The stability count is descriptive at two repeats, not evidence that v2 is more
reliable. Review was true and urgency was unchanged for every paired finding,
so those two non-inferiority checks had little power.

The review exposed a separate planning defect: failed protection tests could
lose the post-correction function test in model-authored action text. Code now
appends the fixed activity `Witness post-correction protection-function test
against approved acceptance criteria.` whenever `P-FAILED-TEST` applies. Four
subsequent F-1003/F-1005 tickets contained the exact activity. This is a
workflow correction, not evidence for the prompt edit itself.

### 5.2 Causal authority checks

Deterministic directional checks were primary; model review was secondary.
Across two repeats:

| Changed authority | Held fixed | Observed result |
|---|---|---|
| Applicable knowledge rule | finding, registry, prompt and code | F-1002 changed L6/I8 to L9/I8; F-1016 negative control stayed L2/I7 |
| Verified equipment redundancy | finding, knowledge, prompt and code | F-1006 changed L4/I6 to L4/I5 |
| Observed broken-wire count | registry, knowledge, prompt and code | F-1006 changed from L4/I6 to L7/I6 and L8/I6 |
| Confirmed isolation/depressurisation | defect, consequence and parallel availability | confirmed state was L7/I3/U5; unconfirmed state was L7-8/I4/U7 |

These are bounded passes for sensitivity and scope isolation. They do not prove
that the synthetic values are domain-correct or that every future knowledge or
registry change will influence the model correctly.

The first operational-state fixture was retained as inconclusive because it
changed consequence and parallel-vessel evidence as well as isolation; one
unconfirmed repeat correctly returned `unassessable`. A prospectively declared
replacement changed only isolation, pressure and inventory evidence.

The documentation-only fixture stayed at L1/I2-3/U2-3 and created no safety
floor, but failed its stricter `review_required=false` assertion because the
model treated replacement-identity verification as material review. This is
reported as a mixed result, not converted to a pass.

### 5.3 Disclosed all-21 regression

After the causal gates, v2 and the code-owned failed-test activity generated all
21 supplied findings in seven parallel groups:

- 21/21 tickets passed the deterministic output contract;
- 30 application sends produced 21 validated tickets: seven action-overflow
  repairs and two malformed-JSON repairs;
- every one of the six `P-FAILED-TEST` tickets contains the exact code-owned
  post-correction test;
- the previous eight planning gaps now contain explicit acceptance or
  verification activities;
- root `tickets.json` remained byte-identical at SHA-256
  `641c8ee358544d562267e40b215ed2bdbe3f2221259437783156a90d889b9694`.

Compared with root v11, eleven findings changed at least one score or review
value. Most shifts were one point. F-1014 changed from L4/I3/U4 to L5/I3/U7
because the dated out-of-service observation did not establish current
isolation, pressure or inventory; the isolated causal fixture showed U5 when
those facts were confirmed. The all-21 cross-review treats the real F-1014
result as a high-confidence regression: the source and registry describe a
non-SCE, bypassable test separator whose findings can usually wait for a
planned shutdown, while v2 escalates it to this week without establishing a
severe consequence path. The directional fixture justified running the real
case but did not prove that the unconfirmed branch was acceptable. F-1015
changed from no review to material review and now includes the previously
missing readable-level comparison.

The failed-test planning guarantee improved completeness but exposed a cost and
stability trade-off: six failed-test tickets plus F-1017 needed an action-length
repair. The resulting actions were valid, with median 270 and maximum 286
characters, but this repair rate is too high to call the planning design
finished. Compression also produced duplicated closure wording in F-1020 and
short fragments in some repaired actions.

### 5.4 Disposition

The authority-migration direction is **not rejected**: v2 preserved the main
development behavior and passed the knowledge, equipment and observation
causal checks. The current v2 artifact is **not promotable**:

- the real F-1014 regression fails the preregistered rule against a new
  high-confidence semantic failure attributable to the intervention;
- the all-21 assessor reports contract pass but 63/63 semantic dimensions
  pending because the pinned calibrated reviewer has not run;
- F-1016 still routes certificate/identity matching through a safety
  uncertainty even though the observed defect is documentation-only and no
  functional impairment is asserted;
- seven action-overflow repairs show that a long fixed activity plus free-text
  planning is not an efficient final contract;
- two repeats and test-informed fixtures do not establish unseen reliability.

Keep root v11 unchanged and use v18/v1 as the compatible baseline for any future
run. The next controlled version must first resolve F-1014 using a general,
reviewed rule rather than a finding branch; it should also make
documentation-only identity checks planning-owned unless supplied evidence
makes them decision-critical, and represent post-correction acceptance
structurally rather than relying on an 80-character fixed sentence. Any
promotion requires a new pinned activation, focused regressions including the
real F-1014 case, the calibrated semantic review and an explicit owner decision.

## 6. Prompt v3 correction and diagnostic

V3 makes three generic, test-informed corrections:

1. safety uncertainty requires cited evidence for a credible current safety
   consequence path; missing current-state confirmation alone is insufficient;
2. documentation-only identity verification remains planning or non-safety
   review unless it changes current functional or safety disposition;
3. confirmed failed tests reuse one shorter code-owned closure activity. Policy
   v12 removes exact duplicates and appends the closure after other activities.

No finding ID or equipment-specific branch was added. Two bounded pre-dispatch
reviews required exposure-floor controls for F-1006, F-1009 and F-1019,
positive preservation checks for F-1014/F-1016, deterministic closure ordering
and a policy-label bump.

### 6.1 Targeted result

The target fixes passed in two complete valid repeats:

- F-1014 returned to L4-5/I3/U4 with current isolation and reuse confirmation
  retained as material review/planning, not a safety floor;
- F-1016 retained identity/certificate verification without treating that
  documentation-only check as the safety-uncertainty basis;
- F-1003, F-1005 and F-1020 completed in one send, with exactly one closure
  activity and no action-overflow repair;
- F-1006 and F-1009 retained urgency and exposure-related safety review.

The preregistered targeted study nevertheless failed overall. F-1019 was L6 in
one repeat versus the single-run v2 control value L8, exceeding the declared
one-point control bound. Its urgency, impact and exposure rules were unchanged,
and L6 matches root v11 plus earlier development observations, but the
preregistered numeric failure is retained and cannot be relabelled.

One r2 group stopped on a provider boundary violation
(`assistant.turn_retry`). A complete r3 was added symmetrically; the failed send
remains evidence and no original assertion changed.

### 6.2 All-21 quality diagnostic

Because the user-facing problem was broader than promotion, a separately
declared diagnostic generated all 21 findings. It cannot rescue the failed
targeted gate:

- 21/21 tickets passed the deterministic contract in exactly 21 application
  sends, compared with 30 sends for v2;
- all failed-test tickets contain one closure activity;
- every planning gap listed in Document 08 section 10.1 has some related check,
  but secondary review classifies only F-1015 and F-1018 as fixed; F-1009 has
  an ordering defect, four cases are partial and F-1017 still lacks witnessed
  acceptance;
- F-1014 improved from v2 U7 to U5, and F-1016 no longer uses identity matching
  itself as the safety-uncertainty basis;
- root `tickets.json` remained unchanged.

The diagnostic also shows that the system is not submission-ready:

- F-1014 likelihood varied to L7 in the all-21 context despite L4-5 in targeted
  repeats, demonstrating unresolved model/context instability;
- all 21 tickets require review, compared with 20/21 in root v11;
- 19/21 tickets remain at urgency 7-9;
- median urgency rationale increased from 1,319 to 1,465 characters and median
  review reason from 1,253 to 1,400;
- median action length increased from 251 to 261 characters;
- F-1005 places diagnosis after repair, F-1009 checks steel thickness after
  recoating and F-1016 verifies identity after tag replacement;
- F-1009 consequence scope remains unresolved rather than proven correct.

V3 therefore demonstrates that generic authority rules and code-owned closure
can fix specific defects without case branches, but it does not solve the
free-text planning contract, ticket projection, review-queue concentration or
score stability. Keep v3 diagnostic only. Use v18/v1 for compatible future
runs; any next version needs structured planning fields and a concise ticket
projection before another promotion study.
