# Tuning: change a version only when it is better

Every change to a VAKYN setup is a new version: a reworded question, a new option, a new threshold,
a new rule in the decision code. This page is the discipline for deciding whether the new version
replaces the one in use. Thresholds themselves: [thresholds](thresholds.md); stored answers to
compare versions without model calls: [replay](replay.md).

## Two sets of labeled cases

- **Dev set** (about 70%): the cases you look at while tuning. Read the mistakes, change the
  question or the rule, try again.
- **Reserved set** (about 30%): cases the author never looks at, case by case, while tuning. Only
  their counts are read, once per candidate. A version tuned until it is perfect on the dev set can
  fit those cases and not the flow; the reserved set catches that.
- **Split by a hash of the case id**, not by hand and not by date order, so the split never changes
  between runs and new cases fall on either side.
- Every look at the reserved counts leaks a little. Add fresh labeled cases to it from the live flow
  over time ([sample sizes](thresholds.md#starting-values-and-sample-sizes) say how many are needed
  to prove a rate).

Labels come from a person, from the real flow, as for [thresholds](thresholds.md#what-you-need).

## The promotion rule

Promote a candidate only if **it beats the current version on the dev set and is not worse on the
reserved set**. Say up front what "better" means, in the person's terms: here, fewer cases decided
wrongly (an automatic outcome that is not the label), then fewer sent to a person. Better on dev
but worse on reserved: do not promote; the change fits the dev cases.

Keep the evidence behind each promotion: both version hashes, both scores on both sets, the
verdict, the date. One JSON line per decision to promote, in the repo next to the policy files.

## Which question to rewrite first

On the dev cases the version decides wrongly, take each question's mean confidence (for a `noul`,
`abs(2 * noul - 1)`). **The question with the lowest confidence on the wrongly decided cases is the
one to rewrite first**: its answers are the least settled where it matters. Compare with the same
mean on the cases decided right. If every question is confident on the wrong cases, they are
confident mistakes: a threshold will not catch them, and the fix is in the options of the question
whose answer drove the outcome ([diagnose](../../questions/references/diagnose.md)).

## Each judging step gets the whole rubric

When a policy is split into several questions or steps, each step must receive every part of the
policy its decision depends on: the criteria, the exceptions, the blockers, the scoring. A split
can leave a step with half the policy: "refund within 30 days" in one question, "except sale
items" nowhere. Check it on **the request each step really sends**, not on the code that builds it:

1. Log or print one real request body per step (the JSON sent to `/v1/systemone`).
2. For each question in it, list the policy clauses it decides.
3. Check that each clause, with its exceptions, is in that question's `instructions` or criteria,
   or in the state it reads. A clause found only in another step's request is missing here.

## Steps

1. Store answers and outcomes per case ([audit record](go-live.md#audit-record)) and get labels.
2. Split the labeled cases into dev and reserved by a hash of the id.
3. Write the candidate as a new versioned file (or a new question version). Read its requests.
4. Score both versions on both sets; for rules and thresholds, from the stored answers with no
   model calls ([promote.py](../examples/promote.py)); for a changed question, after a
   [drift check](drift.md) re-asks it.
5. Promote only by the rule above; append the result to the promotion log.
6. Rewrite the lowest-confidence question next, and repeat.

Script for their project: [promote.py](../examples/promote.py) (standard library, plus
[replay.py](../examples/replay.py)).

## Example (sample files)

[answers.sample.jsonl](../examples/answers.sample.jsonl) with person labels in
[labels.sample.jsonl](../examples/labels.sample.jsonl) (the right outcome per ticket). First the
candidate with both edits from the [replay example](replay.md#example-sample-file):

```text
$ python3 promote.py --answers answers.sample.jsonl --labels labels.sample.jsonl \
    --current routing-policy.v1.json --candidate routing-policy.v2.json
100 labeled cases: 71 dev, 29 reserved (split by a hash of the case id).

Dev set (71 cases)
  routing-v1   wrong   3   to a person  16   right  52 of 71
  routing-v2   wrong   4   to a person  11   right  56 of 71
    t068: triage -> access  (label product)
    ...
Better on dev: no. Not worse on reserved: yes.
Verdict: KEEP routing-v1
```

The lower team cut-off adds a wrong case (t068). `routing-v3` keeps only the refund edit:

```text
Dev set (71 cases)
  routing-v1   wrong   3   to a person  16   right  52 of 71
  routing-v3   wrong   3   to a person  13   right  55 of 71
Reserved set (29 cases; counts only)
  routing-v1   wrong   1   to a person   6   right  22 of 29
  routing-v3   wrong   0   to a person   5   right  24 of 29

Better on dev: yes. Not worse on reserved: yes.
Verdict: PROMOTE routing-v3

Mean confidence per question on the 3 wrongly decided dev cases (lowest: rewrite it first):
  team           0.93   (on the other dev cases: 0.89)
  wants_refund   0.97   (on the other dev cases: 0.95)
  t066: decided product (team product 0.95 >= 0.8), label shipping
  t087: decided product (team product 1.00 >= 0.8), label shipping
  t089: decided refunds (wants_refund 0.96 >= 0.8, from any team), label billing
```

How to read it: `team` is the lowest, so it is rewritten first. Both questions are confident on
the wrong cases, so these are confident mistakes: "You sent me the wrong colour" (t066) and broken
glasses in a box (t087) go to `product`, and the `shipping` option does not say it covers wrong or
damaged deliveries. That is an option fix, then a drift check, then this page again. With 29
reserved cases, "not worse" is a weak bar; say so, and grow the reserved set.
