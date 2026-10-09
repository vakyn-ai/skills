# When to cascade, and when not

A cascade pays when three things hold:

1. **The answer must rest on sources the code has.** Help articles, a contract, a product sheet, a
   ticket history, an invoice. VAKYN checks the draft against them. No sources, nothing to check.
2. **The cheap model is right most of the time.** Every escalated request pays for both models
   plus two checks. The cascade saves money only while the escalated share stays under
   `1 − cheap cost / expensive cost` per request ([cost summary](rollout.md#4-cost-saved-summary)).
3. **Two calls in a row are acceptable on the escalated path.** An escalated request waits for the
   cheap draft, a check, the expensive answer and a second check.

## Do not cascade when

| Situation | Why | Instead |
|---|---|---|
| Free-form writing: marketing copy, stories, brainstorming, a reply with no facts to check | "supported by the sources" has no meaning; a good draft and a bad one both pass or both fail | keep one model; grade samples offline with the `vakyn-judge` skill if quality is the worry |
| The answer needs facts the sources do not hold (general knowledge, live data, arithmetic) | correct drafts come back `unsupported` or `cannot_answer_from_sources` and escalate | add the facts to the sources in code (a lookup, a calculation), or do not cascade |
| The pilot shows a high escalation rate | above the break-even rate the cascade costs more than always-expensive | improve the cheap model's prompt or retrieval first, pick a stronger cheap model, or stop |
| Latency on every request matters more than cost (voice, live typing) | the escalated path is two model calls plus two checks in a row | keep the expensive model; or check only, without a cheap draft |
| Only the cheap model runs today | there is nothing to save | the check alone (draft → VAKYN → person on failure) adds safety, at the cost of the check |

## A high escalation rate: what to look at

Read the escalated lines grouped by `vakyn_pick`:

- **Mostly `unsupported`, VAKYN confident:** the cheap model adds facts. Tighten its prompt ("only
  from the sources"), or try a stronger cheap model.
- **Mostly `cannot_answer_from_sources`:** retrieval misses, or the documents lack the answer.
  These should be `decline`, not escalations; check that route is on and the bar is right.
- **Mostly `off_topic`:** the cheap model answers a different question; often the prompt or a
  truncated question.
- **Mostly `supported` below the bar:** the threshold may be stricter than needed, or the options
  overlap for this domain. Check with labels before lowering it
  ([thresholds](../../vakyn-check/references/thresholds.md)); never lower it to save money alone.
- **Many sentence-level failures on good drafts:** the split makes fragments; join short ones or
  raise the sentence count where per-sentence checks start.
