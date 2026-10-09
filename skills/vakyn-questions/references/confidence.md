# Confidence

Every answer says how sure it is. That number describes how the answer's probability is spread.
It does not say whether the answer is right.

| Type | Field | Meaning |
|---|---|---|
| `noul` | `noul` (no separate field) | Probability of yes. Near 0 or 1 is sure; near 0.5 is unsure. On the same 0–1 footing as a choice: `abs(2 * noul - 1)` |
| `choice` | `confidence` | How far the top option stands above an even split: `(p_top - 1/n) / (1 - 1/n)` for `n` options. 0 = no idea, 1 = all on one option |
| `score` | `confidence` | How tightly the probability sits around the most likely level. Split between neighboring levels lowers it less than split between the ends |

## Confidence is not accuracy

- A badly asked question gets a confident answer to the wrong question. With no "other" option, a
  partnership pitch went to the `product` team at confidence 0.95
  ([no-escape](../examples/no-escape.md)). Fix the question first, then set thresholds.
- Low confidence is a signal about the request as often as about the input. Many unsure answers
  usually mean overlapping options, a missing escape option or missing evidence. Read
  [diagnose](diagnose.md) before lowering a threshold.
- Confidence moves when the wording of a question or its options changes. Re-check thresholds after
  every rewrite.

## Thresholds

Never pick a threshold from a feeling or from 0.5 by default.

1. Start from what a mistake costs. An automatic refund needs a high bar; a suggested tag can take
   a low one.
2. Keep a middle band for people: act on `noul > 0.9` or `< 0.1`, send the rest to review.
3. Set the number on the person's own data: a few hundred records where the right answer is known,
   run through VAKYN, accuracy checked at each confidence level. The `vakyn-check` skill does this.

Until then, write the code with the threshold as a named setting and an "unsure" path (a person, a
chat model, or a review queue).
