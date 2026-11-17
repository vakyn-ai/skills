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

## Many items: one noul each, or one pick

A record is matched against a list in the state: an order and the parcels in today's delivery
scan, a claim and the receipts attached to it. There are two shapes:

- **One `noul` per item**: `parcel_0` … `parcel_29`, the same instructions with the index
  ("Does parcel [3] in the delivery scan belong to the customer's order?").
- **One `choice` over the items**, with a `none` option: "Which parcel in the delivery scan
  belongs to the customer's order?"

The test: **can more than one item be right at once?** An order shipped in three parcels has
three right answers. Each `noul` is answered on its own, so all three get a high yes. A `choice`
names one item; the other two are lost and nothing says so. When it can be more than one, keep
one `noul` per item. Pick the `choice` only when the items exclude each other (exactly one, or
none).

Switching between the two shapes is a design change, not a rewording:

- **Keys and code change.** The answers are read differently (a yes per item against one pick),
  so ask the person before switching, and change the code that reads them.
- **Confidence is on another scale.** A `choice` spreads its probability over every item, so its
  top probability can be well below a `noul`'s yes on the same right item. A `noul` cut-off
  does not carry over; set the threshold again from labeled cases (the `check` skill).
- **Speed.** All questions are answered from one reading of the state, but each still takes its
  own time, so dozens of nouls over a long state answer slower than one `choice`. To keep the
  split case and stay fast, filter the candidates in code first: drop the items whose fields
  cannot match (a different customer, address or order number, compared loosely), then ask a
  `noul` only for the few left.

Made-up example, after the code filter kept two parcels:

```json
{"state": {"order": "Order 4471, 3 garden chairs and 1 table, to J. Doe, 12 Elm Street",
           "parcels": "[0] 1 table, to J. Doe, Elm St 12\n[1] 3 chairs, to J. Doe, 12 Elm Street"},
 "questions": {
   "parcel_0": {"type": "noul", "instructions": "Does parcel [0] in the parcels list belong to the order?"},
   "parcel_1": {"type": "noul", "instructions": "Does parcel [1] in the parcels list belong to the order?"}}}
```

Both can be yes; code then checks that the parcels together cover the order.

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
{"state": {"message": "…", "team": "billing"},
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
