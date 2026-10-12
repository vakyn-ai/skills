# Options and levels

The model reads each option as `name: description` and each score level as written. These words
steer the answer more than anything else in the request.

## Choice options

- **Name:** a stable snake_case id your code reads (`billing`, `calmkettle_17`). Never a position
  (`option_1`, `"A"`).
- **Description:** what belongs in the option, including the cases people get wrong. One line
  is often enough: `"billing": "Invoices, charges, refunds and plan changes for an existing customer"`. A bare
  label (`"billing": "Billing"`) leaves the boundary to guesswork.
- **Exclusive:** two options should never both fit the same state. If they can, rewrite the
  boundary in the descriptions ("refund requests go to billing, even when the product is broken")
  or ask one `noul` per option.
- **Covering:** every state that can arrive fits some option. That is what the escape option is for.
- **Same level of detail:** do not mix broad options (`product`) with narrow ones
  (`export_timeout_bug`); the narrow one wins whatever it touches.

## Structured descriptions

A description, a score level and `instructions` can be an object or a list instead of a string.
The server shows the model an object as `key: value` lines and a list as `- item` lines, so the
keys are words the model reads: pick plain ones.

Use a structure when an option needs more than a label:

- **a definition**: what the option handles;
- **includes**: the cases that belong here, especially ones a reader would not guess;
- **not**: the nearest case that belongs elsewhere, and where it goes;
- **short examples**: two or three phrases a real input might use.

```json
"billing": {"handles": "money already charged or owed",
            "includes": ["charges", "invoices", "refunds", "failed payments"],
            "not": "prices of plans before buying (sales)"},
"sales":   {"handles": "buying decisions",
            "includes": ["prices", "plans and what they include", "discounts", "trials"],
            "not": "charges already made (billing)"}
```

Full request: [structured-options.request.json](../examples/structured-options.request.json).
"The card on file expired, how do I update it?" went to `other` (0.85) with plain one-line
descriptions ("Charges, invoices and refunds") and to `billing` (1.00) with the structured ones,
because "failed payments" is listed under billing.

Measured on 20 hard routing messages over 5 teams (VAKYN-4B Q8_0, one RTX 5090, one request at
a time): structured 18/20 right, the same words as one long string 17/20, plain one-line
descriptions 16/20. The sample is small, and most of the gain comes from the extra includes and
not information, not from the format. Write the information first; use a structure when it makes
the boundary easier to read. Scripts and results:
`docs/experiments/2026-10-11-question-style/` in the skills repository.

Never send an empty description (`""`, `null`, `{}`, `[]`): the model then sees only the name.

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
in plain words ("the customer's message"; `state.message` also works), and any reading rule that
matters ("store credit counts as a refund"). Keep it short. Rules that need counting or comparing
belong in code, not here.

The question's name (`refund`, `team`) is never sent to the model; it is only the key your code
reads. Everything the model needs to know about the question goes in `instructions`.

`instructions` may also be an object, such as `{"question": "…", "note": "store credit counts as
money back"}`, when a reading rule or a definition sits next to the question. On "The kettle
leaks. I'd be happy with store credit instead of a new one.", "Does the customer's message ask
for money back?" gave `noul` 0.05 alone and 0.84 with that note (VAKYN 4B). A note still serves
one question: a rule that says "X or Y" makes it two.
