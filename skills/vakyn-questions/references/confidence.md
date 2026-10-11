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

## Reading it right

- **A `noul` near 0.5 means unsure, not "some".** `noul: 0.5` on "Is the customer angry?" does
  not mean "a bit angry"; it means VAKYN cannot tell. For "how much", ask a `score` with levels.
- **Low confidence on a harmless preference can be fine.** "Which of these five templates fits
  best?" may spread probability over three good ones. If any of them is acceptable, take the top
  pick; send it to review only when a wrong pick costs something.
- **Ignore uncertainty your code does not use.** When a request asks questions for several
  branches up front ([fan-out](../../vakyn-workflow/references/patterns/fan-out.md)), only the
  answers on the branch taken matter. An unsure answer on a branch the code skips is not a
  problem.
- **Confidence is not permission to act.** A sure answer still goes through the code rules
  (amounts, limits, who may approve). Confidence decides between "act" and "ask a person" only
  for actions the code already allows.

## Thresholds

Never pick a threshold from a feeling or from 0.5 by default.

1. Start from what a mistake costs. An automatic refund needs a high bar; a suggested tag can take
   a low one.
2. Keep a middle band for `noul`: act on a clear yes or a clear no, send the rest to review.
3. Set the number on the person's own data: records where the right answer is known, run through
   VAKYN, accuracy checked at each confidence level. The `vakyn-check` skill does this.

Starting values and how many labeled records you need: one page,
[thresholds](../../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes). Until
the real number exists, write the code with the threshold as a named setting and an "unsure" path
(a person, a chat model, or a review queue).
