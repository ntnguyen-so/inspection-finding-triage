# Semantic Review Protocol

## Purpose

Semantic review checks the generated ticket against the frozen evidence card. It
does not redesign the ticket, invent engineering best practice or search for a
new issue after every run. `eval.assess` validates review structure and quoted
output evidence; it does not generate reviewer judgments.

This protocol was written after the v22 ad hoc review disagreement and applies
only to future reviews. It does not rescore or override historical reviews.
Only one frozen primary reviewer configuration may determine the semantic gate.
A secondary reviewer is sensitivity evidence only. Reviewer disagreement is
reported as inconclusive and must not be resolved by majority vote or repeated
reviews until one returns green.

## Frozen inputs

Before reviewing, record:

- exact ticket-file SHA-256;
- reference version and partition;
- reviewer provider, model, reasoning setting and prompt SHA-256;
- calibration result for `eval\spec\probes.json`;
- the generic checklist from:

```powershell
python -B -m eval.assess --partition all --checklist
```

This generic checklist has `output_sha256=null` and is guidance only. Generate
the artifact-bound assessment report with:

```powershell
python -B -m eval.assess --partition all --tickets <tickets.json>
```

Its `review_template` contains the exact ticket SHA-256 and is the review input.
Before real output review, validate the same reviewer configuration against the
seeded probes:

```powershell
python -B -m eval.assess --partition development `
  --calibration-reviews <calibration-reviews.json>
```

The reviewer may use only the supplied source records, domain knowledge and the
unchanged expectation fields embedded in the artifact-bound template.
Production prompts and generation context must not consume evidence cards or
expected answers.

## Dimension checklist

### Grounding

Check only:

1. `observed_facts`;
2. `required_evidence`;
3. `expected_behavior`;
4. `forbidden_claims`;

Verdicts:

- **fail:** direct source contradiction, forbidden claim, fabricated material
  fact, materially absent `required_evidence`, or violation of an applicable
  `expected_behavior` item;
- **needs_review:** adjacent score or consequence-scope judgment that the
  supplied evidence cannot resolve;
- **pass:** every applicable grounding expectation is met and the judgment is
  defensible within supplied evidence, even if another engineering choice could
  also be reasonable.

Do not fail for score concentration, stylistic preference, or a more conservative
alternative that is not required by the card.

### Planning

Check only the card's `action_constraints`. Every listed constraint applies by
default. If applicability itself is genuinely disputed, use `needs_review`;
never silently exclude the item and pass.

Verdicts:

- **fail:** a listed required activity or closure condition is absent, or the
  action directs a forbidden/unsafe operation;
- **needs_review:** the requirement may be covered but the wording is genuinely
  ambiguous;
- **pass:** every explicit constraint is materially covered.

Do not add preferred maintenance steps, authorities, tests, thresholds or wording
that the card and source do not require. Concision and telegraphic phrasing are
not failures when the required activity remains clear.

### Uncertainty

Check only the card's `unknowns`, plus `review_required` and `review_reason`.
Every listed unknown applies by default. If its applicability or materiality is
genuinely disputed, use `needs_review`; never silently exclude it and pass.

Verdicts:

- **fail:** a listed unknown is asserted as known, a confirmed fact is treated
  as absent, or a listed unknown is omitted without a concrete verification
  route;
- **needs_review:** the materiality or decision effect cannot be resolved from
  supplied evidence;
- **pass:** relevant uncertainty is preserved and routed without fabrication.

Do not require missing data or generic engineering unknowns that are not listed
in the card.

## Stability rules

The primary reviewer must:

1. pass the two seeded contradiction probes before reviewing real output;
2. review exactly 63 finding/dimension pairs once;
3. quote the exact ticket field supporting every pass or fail;
4. use `needs_review` rather than guessing when evidence is insufficient;
5. reject any proposed issue that cannot be mapped to one frozen expectation;
6. keep the first complete result, including failures.

No rerun is allowed merely to obtain a better count. A changed reviewer
implementation is a new reviewer configuration: it must be calibrated again,
its predecessor remains recorded, and the change must be disclosed. A rerun
requires a changed ticket artifact, a newly approved reference version, or a
preregistered reliability repeat. A preregistered repeat that disagrees with the
first review makes that dimension inconclusive; it is not a green-seeking retry.

## Gate interpretation

- Any primary `fail`: semantic gate fails.
- No fail but one or more `needs_review`: semantic gate remains pending.
- All 63 pass after calibration: provisional AI-only semantic pass.
- Primary/secondary or preregistered repeat disagreement: preserve both records
  and mark the disputed dimension inconclusive, holding the semantic gate at
  pending unless a primary fail already fails it.

Even a 63/63 AI-only result is not domain certification, human approval or full
A-D system acceptance.
