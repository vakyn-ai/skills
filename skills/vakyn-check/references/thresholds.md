# Thresholds from labeled examples

A threshold splits answers in two: at or above it the app acts on VAKYN's answer; below it the
record goes to a person, a chat model or a review queue. The right number depends on the
person's data and on what a mistake costs. It comes from records a person labeled, never from a
feeling or a default. What confidence means: [confidence](../../vakyn-questions/references/confidence.md).

## Starting values and sample sizes

This is the one place for these numbers; other pages link here. Use the starting values in code
until the person's labeled records give the real number, and say they are starting values.

| Decision | Starting value | Unsure (goes to the unsure path) |
|---|---|---|
| `noul` | act on yes at `noul >= 0.8`, on no at `noul <= 0.2` | the middle band between them (the same as `abs(2 * noul - 1) < 0.6`) |
| `choice` or `score` that only moves work around (routes, tags, sorts a queue) | `confidence >= 0.6` | below it, or the escape option |
| `choice` or `score` that is hard to undo or seen by customers (refunds, published claims) | `confidence >= 0.8` | below it, or the escape option |
| Tool pick in an existing app (`vakyn-convert`) | `confidence >= 0.8` | below it: the chat model picks with the full tool list, as before |

Labeled records needed:

- **50 to start.** Enough for a first threshold, not enough to prove it.
- **A few hundred to prove a low error rate.** With `n` answered records and no errors, the true
  rate could still be up to about `3 / n`. Proving 2% takes about 150 answered records with no errors.
- **About 100 per option** for any claim about one option: a per-option threshold, or "it is
  right on `billing`".

## What you need

- **Labeled records**: VAKYN's answer plus what a person says is right, as many as the
  [list above](#starting-values-and-sample-sizes) says. A side-by-side log with a `label` field
  added works as it is.
- **A target error rate** on the answers VAKYN handles alone, from the person: "at most 2% wrong".
- Records from the real flow, including hard and "none" cases. Labels made by a person, not by a
  chat model.

Format (one per line): `{"id", "vakyn_pick", "vakyn_confidence", "label"}` for `choice` and
`score`; `{"id", "noul", "label": true|false}` for `noul`. A side-by-side log from a converted
prompt has one line per question with a `question` field
([log format](log-summary.md#log-format)); set one threshold per question, with
`--question <name>`. Sample:
[labeled.sample.jsonl](../examples/labeled.sample.jsonl) (79 support tickets, real VAKYN answers).

## Which number to threshold

| Type | Confidence | Note |
|---|---|---|
| `choice` | `confidence` | One cut-off for all options, or one per option if some cost more when wrong |
| `score` | `confidence` | Also decide in code how to round the weighted `score` |
| `noul` | distance from 0.5: `abs(2 * noul - 1)` | Or separate cut-offs: act on yes at `noul >= hi`, on no at `noul <= lo`, when a wrong yes costs more than a wrong no |

## Steps

1. **Hold out part of the labels** (about 30%, picked at random) before looking at any number.
2. **On the rest, for each candidate threshold**, count: answered (confidence at or above it),
   coverage (answered / all), errors among answered, error rate on answered.
3. **Pick the lowest threshold where it and every higher one meet the target.** That answers the
   most records automatically within the error rate.
4. **Check it on the held-out part.** If it misses the target there, the number is not stable:
   label more or pick the next higher threshold.
5. **Say how sure the number is.** With few answered records, zero errors does not prove a low
   rate: with `n` answered and no errors, the true rate could still be up to about `3 / n` (95%).
   Proving 2% needs about 150 answered records with no errors.
6. **List confident mistakes** (wrong answers at or above the threshold). A threshold cannot catch
   them; they usually mean a vague option or a missing escape option. Fix the question
   ([diagnose](../../vakyn-questions/references/diagnose.md)), then redo this page.

Script for their project: [thresholds.py](../examples/thresholds.py) (standard library only):
`python3 thresholds.py labeled.jsonl --target 0.02`.

## Example (sample file, target 2%)

Tuning part, 56 records:

| Threshold | Answered | Coverage | Errors | Error rate | Could be up to (95%) |
|---|---|---|---|---|---|
| ≥ 0.80 | 47 | 84% | 3 | 6.4% | 15.7% |
| ≥ 0.90 | 44 | 79% | 2 | 4.5% | 13.6% |
| ≥ 0.95 | 43 | 77% | 1 | 2.3% | 10.6% |
| ≥ 0.99 | 33 | 59% | 0 | 0.0% | 8.7% |

Chosen: ≥ 0.99, so 59% go through automatically and 41% go to the unsure path. The held-out 23
records: 16 answered, 0 wrong. But 33 answered records cannot prove 2%; the true rate could be up
to 8.7%. Say so, and ask for more labels before relying on it.

## When one kind of mistake costs more

Some decisions are lopsided: clearing a real safety report, a real sanctions match or a real fraud
case costs far more than flagging a harmless one for a second look. One error target for both
sides hides that. Choose the two cut-offs of a `noul` separately, from the labeled records and the
costs the person states:

1. **Ask for three costs per case**, in any unit (money, minutes, a ratio): clearing a case that was
   really yes, flagging a case that was no, and a person reading a case in the middle band.
   Write them down with the threshold; they are part of the policy version.
2. **On the tuning part, try every pair** of cut-offs: act on yes at `noul >= hi`, on no at
   `noul <= lo`, a person in between. Total the cost of each pair and pick the cheapest; on a tie,
   fewer reviews, then the lower `lo` (the safer side).
3. **Check the pair on the held-out part**, next to the [starting values](#starting-values-and-sample-sizes).
4. **Say how far the sample proves the costly side.** The `lo` cut-off rests on the real yes cases
   with a low `noul`, the rarest records there are; with `n` real yes cases and none cleared, the
   miss rate could still be up to about `3 / n`.

The same idea works for `choice`: one cut-off per option, from the cost of a wrong pick of that
option ([which number](#which-number-to-threshold)).

### Example (safety reports, live answers)

[safety-labeled.sample.jsonl](../examples/safety-labeled.sample.jsonl): 60 product messages, one
`noul` ("Does the customer's message in state.message describe a product that could hurt
someone?") answered by VAKYN-4B, labeled by a person; 34 are real safety issues. The person's
costs: clearing a real safety issue 50, a false flag to the safety team 2, a person reading one
message 1. `python3 thresholds.py safety-labeled.sample.jsonl --cost-missed 50 --cost-false-flag 2 --cost-review 1`:

```text
noul, cut-offs by cost (clearing a real yes 50, a false flag 2, a review 1); tuning part, 42 records
  clear at <=  flag at >=  cleared but yes  flagged but no  to a person  total cost
         0.2        0.5                0               1            1           3
         0.3        0.5                0               1            1           3
         0.4        0.5                0               1            1           3
        0.05        0.5                0               1            2           4
         0.1        0.5                0               1            2           4
         0.2        0.8                0               0            7           7  <- starting values
Chosen: clear at noul <= 0.2, flag at noul >= 0.5, a person in between.
Held-out check (18 records): 0 cleared but yes, 0 flagged but no, 1 to a person; cost 1 (starting values 0.2 / 0.8: 2).
Only 24 real yes cases in the tuning part: the low cut-off rests on very few of them. Label more.
```

How to read it: a false flag is cheap, so the flag side drops to 0.5 and the safety team sees a
few harmless messages ("The watch strap broke", 0.70). Clearing is the costly side. The tuning part
has nothing between 0.2 and 0.4 to tell those cut-offs apart, so the lower one is kept; on the
held-out part that is what sends "The trampoline net has a tear near the zip" (0.28, a real safety
issue) to a person instead of clearing it. With 24 real yes cases, the miss rate on the clear side
could still be up to about 12%: label more real safety reports before trusting it.

## In code

Keep the threshold as a named setting, not a literal. Log every answer with its confidence, so the
share below the threshold can be watched after go-live. Re-run this page after any change to the
question, the options, the state builder or the model file: confidence moves when they change.
