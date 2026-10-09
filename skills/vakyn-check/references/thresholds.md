# Thresholds from labeled examples

A threshold splits answers in two: at or above it the app acts on VAKYN's answer; below it the
record goes to a person, a chat model or a review queue. The right number depends on the
person's data and on what a mistake costs. It comes from records a person labeled, never from a
feeling or a default. What confidence means: [confidence](../../vakyn-questions/references/confidence.md).

## What you need

- **Labeled records**: VAKYN's answer plus what a person says is right. At least 50; a few hundred
  give a firm number. A side-by-side log with a `label` field added works as it is.
- **A target error rate** on the answers VAKYN handles alone, from the person: "at most 2% wrong".
- Records from the real flow, including hard and "none" cases. Labels made by a person, not by a
  chat model.

Format (one per line): `{"id", "vakyn_pick", "vakyn_confidence", "label"}` for `choice` and
`score`; `{"id", "noul", "label": true|false}` for `noul`. Sample:
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

## In code

Keep the threshold as a named setting, not a literal. Log every answer with its confidence, so the
share below the threshold can be watched after go-live. Re-run this page after any change to the
question, the options, the state builder or the model file: confidence moves when they change.
