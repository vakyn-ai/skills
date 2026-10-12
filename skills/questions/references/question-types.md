# Choose the question type

Ask one thing per question. Then pick the shape of its answer.

| The judgment is… | Type | Example |
|---|---|---|
| Yes or no about one fact | `noul` | "Does the customer's message ask for money back?" |
| One of several named options that exclude each other | `choice` | "Which team should handle the customer's message?" |
| A place on a scale where higher means more | `score` | "How soon does the customer's message need a reply?" |
| Several facts that can be true at the same time | one `noul` per fact | "mentions a lawyer", "mentions a chargeback", "threatens a review" |
| A sum, a date, a comparison, a lookup, a policy rule | code | "order total over $500", "older than 30 days" |
| Text to write (a reply, a summary) | not VAKYN | keep the chat model for it |

## How to tell them apart

- **`noul` or `choice`?** If the answer is yes or no, use `noul`. If you catch yourself writing
  "is it billing?", "is it access?", "is it product?" as separate nouls and only one can be true,
  that is one `choice`.
- **`choice` or several nouls?** Can two options be true together? Then they are not options. A
  message can complain about price *and* ask for a refund. A `choice` would split the probability
  between them and you would see two weak answers instead of two strong ones. Ask a `noul` per
  fact in the same request.
- **`choice` or `score`?** Can you put the options in order, with each one "more" than the last?
  Urgency, severity, fit, risk: `score`. Teams, topics, products, tools: `choice`. A `score` over
  unordered options gives a meaningless average.
- **`score` or `noul`?** If the person will act on a cut-off ("flag if risky"), a `noul` with
  clear `true` / `false` descriptions is simpler. If they will sort, rank or combine several
  criteria, a `score` keeps the shades.

## One proposition per `noul`

"Is the customer angry and asking for a refund?" is two questions. A calm refund request and an
angry message with no refund both land near the middle, and you cannot tell which half failed.
Watch for `and`, `or`, `but`, `both`, `either`, "and also". Split them:

```json
"angry":  {"type": "noul", "instructions": "Does the writer of the customer's message sound angry?"},
"refund": {"type": "noul", "instructions": "Does the customer's message ask for money back?"}
```

Combine the answers in code (`angry > 0.8 and refund > 0.8`). Code combines exactly; a single
question combines vaguely. Renaming the pair does not help: "Does it break our rules?" with a
rule that says "personal information or insults" is still two questions, in a string or in a
structured `instructions` object. Keep the old name in code instead: `remove = personal_info >
0.8 or insult > 0.8`. See [compound-noul](../examples/compound-noul.md).

## Ask by name, not by position

- **Name the subject in plain words.** "Does the agent's reply answer the question in the
  customer's message?", not "Does the second text answer the first?" or "Does it answer the
  question?". When the state has several texts, an unnamed "it" can attach to the wrong one.
  `state.reply` and backticked paths also work; plain words that name the field did best in our
  test ([state](state.md#refer-to-fields)).
- **Name the options.** Option names are read by the model together with their description
  (`calmkettle_17: Calmkettle 1.7L, quiet boil mode`). `option_1`, `"A"`, `"2"` carry no meaning,
  and "answer 1, 2 or 3" makes the model count. Use the item's own id or a short snake_case name.
- **Question names are for your code.** The model does not see the key (`team`, `refund`); it only
  sees `instructions` and `criteria`. So the instructions must say everything.

## One request or two

All questions in a request read the same state and cannot see each other's answers.

- **Independent questions share one request.** Team, refund and urgency for the same message: one
  call. The state is read once, so ten questions cost about the same as one.
- **Dependent questions go in a follow-up request.** If question B only makes sense after A's
  answer, send A first, then put A's answer in B's state as a fact:

```json
{"model": "jev-latest",
 "state": {"message": "…", "team": "billing"},
 "questions": {"billing_topic": {"type": "choice", "instructions": "Which billing topic is the customer's message about?",
   "criteria": {"refund": "Wants money back", "invoice": "Needs an invoice or receipt changed",
                "plan_change": "Wants to upgrade, downgrade or cancel", "other": "Another billing topic"}}}}
```

  Two-step picks also work around the 255-option limit: a `choice` over groups, then a `choice`
  over the items in the chosen group.
- **Or ask B up front with its premise stated.** When the request is cheap and the wait matters,
  ask every branch's question in the first request ("If this message is about billing, which
  billing topic is it?") and let code read only the branch it takes. See the `workflow`
  pattern [fan-out](../../workflow/references/patterns/fan-out.md).
- **Code decides whether to ask B at all.** Skip the follow-up when A's answer is unsure; send it
  to a person instead.
