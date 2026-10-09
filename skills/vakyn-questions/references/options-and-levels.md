# Options and levels

The model reads each option as `name: description` and each score level as written. These words
steer the answer more than anything else in the request.

## Choice options

- **Name:** a stable snake_case id your code reads (`billing`, `calmkettle_17`). Never a position
  (`option_1`, `"A"`).
- **Description:** one line that says what belongs in the option, including the cases people get
  wrong: `"billing": "Invoices, charges, refunds and plan changes for an existing customer"`. A bare
  label (`"billing": "Billing"`) leaves the boundary to guesswork.
- **Exclusive:** two options should never both fit the same state. If they can, rewrite the
  boundary in the descriptions ("refund requests go to billing, even when the product is broken")
  or ask one `noul` per option.
- **Covering:** every state that can arrive fits some option. That is what the escape option is for.
- **Same level of detail:** do not mix broad options (`product`) with narrow ones
  (`export_timeout_bug`); the narrow one wins whatever it touches.

## The escape option

Without one, VAKYN must pick a real option even when none fits, and it may do so with high
confidence. Add one whenever an unexpected input is possible, which is almost always.

| Situation | Escape option | Description, for example |
|---|---|---|
| Input may be off-topic | `other` | "Anything that is not a support request for these teams: sales, partnerships, spam" |
| Nothing in a list may fit | `no_match` / `none` | "None of the candidates fits what the customer asked for" |
| The state may not say enough | `not_enough_evidence` | "The document does not say enough to decide" |
| The user's intent is unclear | `ask_user` | "The request is too vague to act on without asking" |

Describe what the escape option covers, like any other option. Code then routes it: a person, a
default queue, or a clarifying question. See [no-escape](../examples/no-escape.md).

## Score levels

- **Lowest first.** Level 0 is the least. The `score` in the answer is the probability-weighted
  level, so the order is the meaning.
- **Describe what you would observe**, not a grade: "Mentions alternatives, renewal doubts or a
  budget review" beats `"3"` or `"medium"`. Bare numbers (`"1"`–`"5"`) give the model nothing to
  compare against.
- **3 to 5 levels.** More levels than you can describe apart only spread the probability. The
  maximum is 10.
- **One dimension.** "Polite and correct" is two scales; ask two scores and combine them in code.
- **Cover both ends.** Include a level for "none at all" so a clean input has somewhere to land.

See [conclusion-in-state](../examples/conclusion-in-state.md).

## `noul` criteria

Optional `{"true": "…", "false": "…"}`. Add them when where yes ends is a policy, not plain language:

```json
"refund": {"type": "noul", "instructions": "Does state.message ask for money back?",
  "criteria": {"true": "Asks for a refund, a chargeback or money returned",
               "false": "Asks for something else: a replacement, store credit, a repair, or nothing"}}
```

Only the keys `true` and `false` count. Do not write `yes` / `no` keys; the checklist flags them.

## Instructions

`instructions` is the question, written for a careful colleague: one question, its subject named
by state field ("state.message"), and any reading rule that matters ("store credit counts as a
refund"). Keep it short. Rules that need counting or comparing belong in code, not here.
