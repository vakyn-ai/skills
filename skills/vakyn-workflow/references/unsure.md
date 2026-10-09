# The unsure path

Every decision in a design says what happens when VAKYN is unsure. Pick the path by what a wrong
answer costs and who can fix it.

## Where unsure answers go

| Path | Use when | Examples |
|---|---|---|
| A person | a mistake is costly or visible to customers | refunds, legal, safety, published claims |
| A chat model | the old chat-model flow still works and is good enough as a fallback | tool pick, best match |
| A review queue | the work can wait and someone checks a list daily | triage, rubric grades |
| A fixed default | a plain safe next step exists | ask form fields in a fixed order |

## When an answer is unsure

| Type | Unsure when | Code |
|---|---|---|
| `choice` | the pick is the escape option, or `confidence` is below the setting | `pick.choice == "other" or pick.confidence < MIN_CONFIDENCE` |
| `noul` | between two settings (the middle band) | `CLEAR < p < FLAG` |
| `score` | `confidence` below the setting, or a risky level has real probability | `s.confidence < MIN_CONFIDENCE or s.probabilities[3] > 0.2` |

Escape options (`other`, `none`, `no_good_match`, `not_enough_evidence`, `needs_person`) are
answers, not errors: each has its own path in code.

## Settings, not guesses

- Write each threshold as a named setting with a comment that it is tuned on the person's data.
- Starting values: 0.6–0.7 for a `choice` that only moves work around, 0.8 or more when the action
  is hard to undo; noul bands 0.2 / 0.8.
- Confidence is not accuracy ([confidence](../../vakyn-questions/references/confidence.md)).
  The real numbers come from records where the right answer is known: the `vakyn-check` skill.
- Many unsure answers usually mean a weak question, not a hard input. Read
  [diagnose](../../vakyn-questions/references/diagnose.md) before lowering a threshold.

## Log it

Log the request id, the full probabilities and the path taken for every answer. That log is what
`vakyn-check` reads to set thresholds and find weak options.
