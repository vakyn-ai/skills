# Writing rules into the question

Each round produces **one candidate**: the current best wording plus one rule per group of misses.
A rule is a sentence in the `instructions` or in one or two option descriptions. Everything else
stays as it was, so the score change can be traced to the rules.

## Where a rule goes

| Rule about | Put it in |
|---|---|
| What one option covers | That option's description |
| The boundary between two options | Both descriptions ("not a lost card: CRD"), or one line in the instructions |
| A cue that changes the meaning everywhere | The instructions, as a named line (`"note": "..."` in structured instructions) |
| What counts as `true` for a `noul` | `criteria.true` (and `criteria.false` for the other side) |
| What a score level looks like | That level's description |

Structured instructions keep rules readable as they grow:

```json
"instructions": {
  "question": "Is the tweet in the state ironic?",
  "note": "A hashtag such as #not or #sarcasm at the end flips the literal meaning: count it as irony."
}
```

## How to write one

- **One sentence per rule**, in plain words, about the input the model sees: "A payment the
  customer did not make is DSP, even when the card is lost as well."
- **General, not a case.** Write the pattern the group shares, not the group's texts. A short
  made-up example is fine when it makes the rule clear; a copied case is not, and a reserved case
  never. Examples copied from dev misses raise the dev score and much
  less the reserved one: the clearest sign of a wording that fits its dev cases.
- **Describe, do not rename.** Bare codes get a description, `"CRD": "The card itself: lost,
  stolen, blocked…"`; the key `CRD` stays.
- **Positive wording** ("counts as DSP when…") reads better than a list of exclusions.
- **No computation** in a rule: no sums, dates, thresholds or lists of allowed values. Those are
  code.
- **Name fields in plain words** ("the customer's message"), as the
  [questions](../../questions/SKILL.md) skill does.

## Keep it short

- Prefer rewriting a description over adding a sentence to the instructions.
- A rule that did not help is removed in the next candidate, not left in.
- On a tie in score, the shorter wording is kept: fewer words for the same result fit the flow
  better.
- Five rounds that each add five rules is a sign of fitting the dev cases. Read
  [overfitting](reading-results.md#overfitting).

## Before scoring

1. Same question name, same type, same option keys (or the same number of score levels). The
   script refuses a candidate that changes them.
2. Run the [pre-send checklist](../../start/references/checklist.md).
3. Save it as a **new file** with the next version number; never overwrite the wording in use.
4. Pass each rule to `try` with `--rule "<group>: <rule>"`, so the report lists every rule with
   the misses it was written for.
