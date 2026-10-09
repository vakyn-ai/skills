# Route: send each item to the right team

**Use when** every item goes to exactly one place: a team, a queue, an inbox, a person.
**Not when** an item can belong to several places at once (use one `noul` per place), or the
places have an order such as priority levels (use a `score`).

## The request

[examples/route.request.json](../../examples/route.request.json): one `choice` over five
support teams, each with a one-line description of what it handles, and `other` for anything that
is not a support request. The state holds the ticket and facts from the customer record.

Answer from a running VAKYN 4B: a ticket about Slack alerts that stopped after a token change →
`integrations`, confidence 1.00.

## The code

[examples/route.py](../../examples/route.py) · [examples/route.ts](../../examples/route.ts)

- `build_state(ticket)` copies the subject, the body and the plan from your records. Nothing else.
- One request per ticket. Read the answer by name: `result.choices["team"]`.
- Code checks the pick is one of `TEAMS` before it moves the ticket.

Run on three tickets: Slack alerts → `integrations` (1.00), a double charge → `billing` (1.00),
a podcast sponsorship pitch → `other` (1.00), which the code sends to the triage queue.

## Unsure path

`other`, or confidence below `MIN_CONFIDENCE` → a person's triage queue. Log the request id and
the full probabilities, so the misses can be read later with `vakyn-check`.

## Common mistakes

- **No `other`.** Without it, a sales pitch lands on a support team with high confidence.
- **Team names without descriptions.** `"bugs": "Bugs"` tells the model nothing about the line
  between `bugs` and `integrations`. Write what belongs in each.
- **Rules in the question.** "Send business-plan customers to priority" is code: route first,
  then apply the plan rule.
- **A follow-up in the same request.** "Which billing topic?" only makes sense after
  `team == "billing"`; send it as a second request ([compose](../compose.md)).
