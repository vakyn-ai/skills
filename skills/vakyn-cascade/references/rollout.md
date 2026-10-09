# Rollout: side by side, the log, the cost-saved summary

## 1. Side by side first

`CASCADE_MODE=side_by_side` is the default in generated code. For every request:

- the expensive model answers, and **that answer is sent, as today**;
- at the same time the cheap model drafts and VAKYN checks the draft (the route it **would** take
  is logged);
- VAKYN compares the cheap draft with the expensive answer
  ([compare.request.json](../examples/compare.request.json)), so each line shows whether an
  accepted cheap draft would have said the same.

Nothing users see changes. The pilot costs more than today (both models plus VAKYN on every
request): **say so and ask before turning it on.** On high volume, run it on a share of requests.

The comparison is a separate request from the check, so the expensive answer never sits in the
check's state and cannot sway the verdict:

```text
match (choice): Compared with the reference answer in state.reference_answer, how does the draft in state.draft answer state.question?
  same_answer        same answer, same facts, numbers and steps; wording may differ
  draft_incomplete   same answer, but leaves out a fact or step the reference gives
  different_answer   a different answer, fact, number or step
  cannot_compare     the draft or the reference does not answer the question
```

From a running VAKYN 4B: the export draft that skips "more than 500 invoices are emailed" →
`draft_incomplete` 0.94. This catches what the draft check cannot: a faithful but incomplete draft.

**This is agreement, not accuracy.** The expensive model can be wrong too. In the demo, both
models said Spanish invoices are supported when the article lists English, French and German; the
comparison said `same_answer`. Only a person's label says which answer is right.

## 2. The log

One JSON line per request (`CASCADE_LOG`, git-ignored). The shared side-by-side fields first, so
`vakyn-check` reads it like any other log
([format](../../vakyn-check/references/log-summary.md#log-format)), then the cascade's own:

| Field | Value |
|---|---|
| `ts`, `request_id` | UTC time; VAKYN's request id for the draft check |
| `question` | `draft_check` |
| `vakyn_pick`, `vakyn_confidence`, `vakyn_probabilities` | the verdict on the cheap draft; `null` when VAKYN failed |
| `chat_pick` | side by side: the comparison with the expensive answer (`same_answer`, …); `null` in cascade mode |
| `agree` | side by side: `true` when the route matches the comparison (accepted and `same_answer`, or not accepted and not `same_answer`) |
| `mode`, `used` | `side_by_side` / `cascade`; what was sent: `expensive`, `cheap`, `decline` or `person` |
| `route`, `escalated` | `accept_cheap` / `escalate` / `decline`; `true` when the expensive model is (or would be) needed |
| `claims` | long drafts: each sentence with its answer and confidence |
| `expensive_check` | cascade mode: the verdict on the expensive answer |
| `cheap_model`, `expensive_model` | model names |
| `tokens` | per model `{"in", "out"}` from the provider's usage; add `cost` per model if the provider returns it |
| `ms` | time per step: `cheap`, `check`, `expensive`, `check2` |
| `label` | added by a person during review: `cheap_ok` or `cheap_worse` |
| `texts` | question, cheap draft, expensive answer, for the spot-check. **It holds user text**: keep the log private, set a retention period, or drop `texts` and look drafts up by `request_id` |

Sample: [cascade.sample.jsonl](../examples/cascade.sample.jsonl), seven demo questions in each
mode, real VAKYN answers, canned drafts, token counts estimated from characters, and two labels
added by hand.

## 3. Was an accepted cheap draft worse?

The number that decides the switch: **of the drafts VAKYN accepted, how many were worse than the
expensive answer?**

1. **Expensive model as reference** (every line, free once the pilot runs): count accepted lines
   by `chat_pick`. `draft_incomplete` and `different_answer` on accepted lines are the ones to read.
   Report it as agreement.
2. **Person spot-check** (the real measure): a person reads a random sample of accepted lines and
   every accepted line where `chat_pick` is not `same_answer`, and sets `label`. How many labels
   are needed: [sample sizes](../../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes).
3. Read the escalated lines too: a high escalation rate is cost, not risk, but it decides whether
   the cascade pays ([fit](fit.md)).

Then set the threshold from the labels with `vakyn-check`, and switch with `CASCADE_MODE=cascade`
only when the person agrees.

## 4. Cost-saved summary

[cost_summary.py](../examples/cost_summary.py) reads the log (standard library only):

```sh
python3 cost_summary.py cascade-log.jsonl \
    --cheap-in <price> --cheap-out <price> --expensive-in <price> --expensive-out <price>
```

It reports routes and their shares, verdicts, the comparison on accepted drafts, person labels,
median time per route, tokens per model per 1,000 requests, and, with prices, cost per 1,000
requests for the cascade against always-expensive, the saving, and the break-even escalation rate
(the cascade saves money while escalated share < 1 − cheap cost / expensive cost per request).

- **Prices come from the person.** Ask for their per-million-token prices, or leave the flags as
  placeholders and report tokens only. Never fill in a price.
- From side-by-side lines, always-expensive is **measured** (the expensive model answered every
  request). From cascade lines it is **estimated** from the escalated requests, which may be
  longer or harder than average; say so.
- VAKYN's own cost (the person's server) is not in the number; name it as a separate line.
- The demo log is built to show every route (4 of 7 escalate). Its shares say nothing about a real
  pipeline; only the person's pilot does.
