# Routing: what happens after the check

```text
question + sources ──► cheap model drafts ──► VAKYN checks the draft
                                                 │
     supported, at or above the bar ─────────────┼──► send the cheap draft
     cannot_answer_from_sources, above the bar ──┼──► send the "not in our sources" reply (or a person)
     anything else, or VAKYN failed ─────────────┴──► expensive model answers ──► VAKYN checks it
                                                            supported above the bar ──► send it
                                                            anything else ───────────► person / review queue
```

## The routes

| Cheap draft's verdict | Route | Why |
|---|---|---|
| `supported` ≥ bar, and every sentence too (long drafts) | `accept_cheap`: send it | the only case the cheap draft goes out |
| `cannot_answer_from_sources` ≥ bar | `decline`: a fixed reply that the sources do not cover it, or a person | the expensive model gets the same sources; it cannot find what is not there. Log these: they show gaps in the documents or in retrieval |
| `unsupported`, `off_topic`, anything below the bar | `escalate` | the cheap draft is not safe to send |
| VAKYN failed (timeout, `5xx`, an option that was not offered) | `escalate`; if the second check fails the same way, send the expensive answer unchecked | behaves as before the cascade; VAKYN being down never makes answers worse |

The expensive answer goes through **the same check, once**. `supported` above the bar → send it.
Anything else → a person or a review queue, with both texts and both verdicts; the user gets a
holding reply ("a member of our team will reply"). **Never loop**: no third draft, no retry with
a different prompt, no "ask the cheap model again". Two failed drafts on the same sources usually
mean the sources are wrong or missing; a person is the right next step.

Some products cannot hold a reply for a person. Then the person picks one of two: send the
expensive answer with a note to review it later, or send the decline reply. Write that choice as
a named setting, not a silent default.

## In code

The templates ([cascade.py](../examples/cascade.py), [cascade.ts](../examples/cascade.ts)) have
these parts. Write them into the person's own pipeline, around their existing chat-model call.

| Part | Does |
|---|---|
| `trim_sources` | keeps retrieved passages in order while they fit the budget; done once, before drafting |
| `cheap` / `expensive` | the person's existing chat-model call, with the model name a parameter; returns text and token usage |
| `check` | one VAKYN request: `verdict`, plus one question per sentence for long drafts; checks the pick is an offered option |
| `accepted` | `supported` at or above `CASCADE_MIN_CONFIDENCE` for the verdict and every sentence |
| `answer` | the routes above, the mode ([rollout](rollout.md)), one log line per request |

The same drafting prompt goes to both models: "answer only from the sources; if they do not
contain the answer, say so". A cheap model that declines honestly is cheaper than one that guesses.

## Time

An accepted draft takes one cheap call plus one check. An escalated one takes the cheap call, the
check, the expensive call and a second check, one after another. Log the time of each step (`ms`)
and compare in the pilot. If the escalated path is too slow for the product, see
[when not to cascade](fit.md).
