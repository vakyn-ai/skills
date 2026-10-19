# Rubric to questions

A rubric is a list of things a good output does. Each item becomes one VAKYN question about one
output. Everything that combines the answers (must-pass gates, weights, the pass mark) is code.

## 1. Sort each criterion

| The criterion is… | Question | Example |
|---|---|---|
| Met or not met | `noul`, with `true` and `false` described | "Is everything `state.output` commits to allowed by `state.rules`?" |
| Met, not met, or impossible to check from the state | `choice` with a cannot-tell option | grounded: `supported` / `unsupported` / `contradicted` / `not_enough_evidence` |
| Truly ordered levels, each one describable | `score`, levels lowest first | tone: rude → stiff → polite → warm |
| A count, a length, a format, a regex, a date | code, not VAKYN | "under 120 words", "mentions the order number", "valid JSON" |
| Two things ("accurate and concise") | split into two criteria | |
| "Overall quality" | split into the criteria an expert actually checks | |

Use `score` only when an expert could tell level 2 from level 3 by reading the output. When the
expert's real call is pass or fail, ask a `noul`: a 1–5 scale with only "fail" and "pass" behind it
spreads the probability over levels that mean nothing. Level wording rules:
[options and levels](../../questions/references/options-and-levels.md).

**Polarity.** Some criteria are failures when true ("Does the reply ask for a password?"). Ask
them that way when it reads naturally, and store which answer means pass next to the question
(`pass_when` in [rubric.py](../examples/rubric.py)). Never write "Does the reply not…".

**Describe `true` and `false`.** The descriptions are where the expert's meaning goes: what counts
as a next step, what does not. In the [alignment](alignment.md) example, a sharper question plus
these two descriptions moved held-out agreement on `next_step` from 6 of 12 to 10 of 12.

## 2. The state

```json
{"task": "what the model was asked to do",
 "input": "the user's message or the agent's goal",
 "output": "the output being graded, exactly as produced",
 "reference": "a known good answer, when one exists",
 "sources": [{"id": "hb-4.2", "text": "the documents the output had to use"}],
 "rules": ["the policy the output must follow, one rule per line"]}
```

- Each question names the field it judges: `state.output`, `state.sources`.
- Put in the state every fact a criterion needs. If an expert uses a rule that is not in
  `state.rules`, add the rule; that is missing evidence, not a wording problem.
- No conclusions: not the generating model's own notes, not another judge's verdict.
- Agent runs: put the final answer in `output` and the tool calls and results that matter in
  `steps` (a list). Long traces: keep the steps the criterion is about
  ([state](../../questions/references/state.md), size limits in the
  [API reference](../../get-started/references/api.md)).

## 3. One output per request, every criterion in it

- All criteria for one output share one request: they are independent judgments of the same state.
- Never put two outputs in one request ("grade reply A and reply B"): each answer must see one output.
- Many outputs: many requests, sent concurrently with a cap and `429` retry
  ([judge.py](../examples/judge.py)).

## 4. Verdict in code

From [rubric.py](../examples/rubric.py):

1. Each `noul` becomes pass (`>= 0.8` on the pass side), fail (`<= 0.2`) or unsure (between).
   These are starting values; the real ones come from the person's labels
   ([thresholds](../../check/references/thresholds.md#starting-values-and-sample-sizes)).
2. A `score` passes at a level set in code (`pass_at`). `score` is a weighted average, not a level.
3. Overall: any must-pass criterion fails → `fail`; any must-pass criterion unsure → `review` (a
   person grades it); otherwise `pass` when the weighted score (probability of pass for each
   `noul`, `score / top level` for each `score`) reaches the pass mark.

## Example: support replies

Five criteria: `answers_request`, `follows_rules`, `asks_for_secret` (must-pass, fails when true),
`next_step`, `tone`. Answers from a VAKYN 4B (Q8_0, one RTX 5090):

| Request | answers_request | follows_rules | asks_for_secret | next_step | tone | Verdict |
|---|---|---|---|---|---|---|
| [good reply](../examples/support-reply-rubric.request.json) | 0.99 | 0.95 | 0.00 | 1.00 | 1.87 | pass, weighted 0.91 |
| [failing reply](../examples/support-reply-failing.request.json) (card refund, asks for card number, promises 9:00) | 0.81 | 0.00 | 1.00 | 0.97 | 1.75 | fail: `follows_rules`, `asks_for_secret` |

The failing reply is polite and gives a next step, so a single "how good is this reply?" score
would rate it well. Separate must-pass criteria catch it.

[grounded-answer.request.json](../examples/grounded-answer.request.json): a handbook answer that
adds "4 weeks of unpaid leave", which no source says. `grounded` → `unsupported` (confidence 0.96),
`answers_question` 0.99, `complete` 0.06 (it leaves out the notice rule in the sources).

## Pairwise: two outputs

To compare two outputs (model A vs model B, old prompt vs new), ask one `choice` with both in the
state and a `neither` option, then ask again with the two swapped. Combine in code:

```python
def compare(client, item, a, b):
    q = {"better": Choice(
        instructions="Which reply would serve the customer in state.input better, given state.rules?",
        criteria={"reply_a": "state.reply_a serves the customer better",
                  "reply_b": "state.reply_b serves the customer better",
                  "neither": "Both serve the customer equally well or equally badly"})}
    first = client.system_one(state={**item, "reply_a": a, "reply_b": b}, questions=q).choices["better"].choice
    second = client.system_one(state={**item, "reply_a": b, "reply_b": a}, questions=q).choices["better"].choice
    swapped = {"reply_a": "reply_b", "reply_b": "reply_a", "neither": "neither"}[second]
    return first if first == swapped else "tie"  # the two orders disagree: position decided it, not quality
```

[pairwise.request.json](../examples/pairwise.request.json) picked `reply_a` (confidence 1.00); with
the replies swapped it picked `reply_b` (0.99): the same reply both times. When the orders
disagree often, the two outputs are close; grade each against the rubric instead.
