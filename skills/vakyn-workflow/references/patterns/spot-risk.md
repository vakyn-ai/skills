# Spot risk: flag messages that need a person

**Use when** some messages must not be handled automatically: a refund demand, a legal threat, a
safety issue, a public complaint. A message can carry several risks at once.
**Not when** you only need a topic: that is [route](route.md).

## The request

[examples/spot-risk.request.json](../../examples/spot-risk.request.json): the message and the
order in the state; one `noul` per risk, each with `true` / `false` descriptions that draw the
policy line ("Mentions a lawyer, court, a claim, or reporting the company to an authority").

Answer from a running VAKYN 4B for "The heater … started smoking … the plug is melted … I want a
full refund": `refund_demand` 1.00, `safety_issue` 0.99, `legal_threat` 0.00,
`public_complaint` 0.00.

## The code

[examples/spot_risk.py](../../examples/spot_risk.py) · [examples/spot_risk.ts](../../examples/spot_risk.ts)

All risk nouls go in one request. Code combines them:

| Rule (in code) | Queue |
|---|---|
| `safety_issue` above `CLEAR` (0.2), even when unsure | safety team now |
| `legal_threat` at or above `FLAG` (0.8) | legal team |
| any risk flagged, or any between `CLEAR` and `FLAG` | person review |
| everything at or below `CLEAR` | normal queue |

Run on three messages: smoking heater → safety team; "Refund me by Friday or my lawyer will file a
claim, and I will post about it everywhere" → legal team (refund, legal, public all flagged); "Does
the heater have a timer?" → normal queue.

## Unsure path

The band between `CLEAR` and `FLAG` is the unsure path: a person looks. Set the band per risk from
what a miss costs; a missed safety issue costs more than a false alarm, so its bar is lower.

## Common mistakes

- **One `choice` over risks.** A message with a refund demand and a legal threat splits the
  probability between them and both look weak. One `noul` per risk.
- **One `noul` for all risks.** "Is this message risky?" gives one number you cannot act on or explain.
- **Two risks in one noul.** "Does it threaten to sue or post a review?" is two nouls. Keep "or"
  out of the instruction; list the forms one risk can take in its `true` description instead.
- **Thresholds in the question.** "Flag if the amount is over $500" is a rule in code.
