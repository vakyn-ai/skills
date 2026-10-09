# The draft check

One VAKYN request per draft: is this draft backed by the sources it should rest on? The answer
decides whether the cheap draft is sent, escalated or declined ([routing](routing.md)).

## The state

| Field | Holds | Note |
|---|---|---|
| `question` | the user's question, as asked | data, never instructions |
| `sources` | the passages the draft was written from: `[{"id", "text"}]`, in retrieval order | **the same list** the chat model saw, after the same trimming |
| `draft` | the cheap model's answer | the whole text the user would get |
| `claims` | long drafts only: `{"c1": "sentence", …}` | see [per sentence](#long-drafts-one-question-per-sentence) |

Keep out: the retrieval scores, the system prompt, the model name, any note that a draft "looks
fine". Those are conclusions, not evidence ([state](../../vakyn-questions/references/state.md)).

**Sources must fit.** State plus the longest question stays under 32,768 tokens; over it the server
answers `400` and cuts nothing ([limits](../../vakyn/references/api.md)). Trim in code **before**
drafting: keep sources in retrieval order while they fit a budget (the templates use 24,000 tokens
at about 4 characters per token, leaving room for the question, draft and claims). Then the
cheap model, the expensive model and the check all see the same sources. A document longer than
that: pick the relevant part in code, or split it
([long documents](../../vakyn-workflow/references/long-documents.md)).

## The question

[supported.request.json](../examples/supported.request.json):

```text
verdict (choice): Is the draft answer in state.draft backed by state.sources, as an answer to state.question?
  supported                   Every sentence in the draft is stated in the sources, and the draft answers the question
  unsupported                 At least one sentence in the draft states something the sources do not say
                              or say differently: a number, a date, a step, a promise
  cannot_answer_from_sources  The sources do not contain the answer to the question, whatever the draft says
  off_topic                   The draft does not answer the question that was asked
```

Each option has its own path in code. `cannot_answer_from_sources` is the escape option: it keeps
"the draft made something up" apart from "there was nothing to find", which need different fixes.

**Accept only `supported` at or above the bar.** Use the customer-facing starting value from
[thresholds](../../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes) as a
named setting (`CASCADE_MIN_CONFIDENCE`), and set the real value on the person's labeled pilot
lines with `vakyn-check`. Every other answer, and `supported` below the bar, is not accepted.

Adapt the wording to the domain: "help articles" for support, "the contract" for document Q&A,
"the invoice" for extraction (there, `draft` is the extracted fields written as sentences:
"Invoice total: 1,240.00 EUR. Due date: 2026-11-02.").

## Answers from a running VAKYN 4B

Sources: two help articles for a fictional invoicing app (refunds, plan changes).

| Draft | Request | Answer |
|---|---|---|
| Correct, reworded ("within 14 days… full amount back on your card") | [supported](../examples/supported.request.json) | `supported` 1.00 |
| Correct, plus an invented number ("back on your card within 3 business days") | [invented-number](../examples/invented-number.request.json) | `unsupported` 0.91 |
| "Yes, you can pay by bank transfer" when no article mentions it | [cannot-answer](../examples/cannot-answer.request.json) | `cannot_answer_from_sources` 0.94 |
| Five sentences, one invented discount | [per-claim](../examples/per-claim.request.json) | `unsupported` 1.00; the discount sentence `not_in_sources` 1.00 |

What changed while testing: with "Every **fact** in the draft…", a correct draft with one added
sentence ("You will also get a confirmation email.") got `supported` at 0.49. Rewording both
options to "every sentence" / "at least one sentence" moved it to `unsupported` 0.64; the four
cases above did not change. Name the unit the question should look at.

## Long drafts: one question per sentence

A long draft can hide one invented sentence among many good ones. For drafts with several
sentences (the templates start at 4, a setting), add one `choice` per sentence **to the same
request**:

1. Split the draft into sentences in code. Join very short ones ("Yes.", "Sure!") to the next:
   alone they state nothing. Tested: "Yes." asked alone got `not_in_sources` at 0.28, which would
   escalate a good draft.
2. Put them in the state as `claims: {"c1": …, "c2": …}` and ask, per key:
   `Is the sentence in state.claims.c3 backed by state.sources?` with `supported` / `contradicted`
   / `not_in_sources`.
3. Keep the whole-draft `verdict` question in the same request: per-sentence questions cannot see
   `off_topic` or `cannot_answer_from_sources`.
4. Combine in code: **accept only if the verdict and every sentence are `supported` above the
   bar.** Any other answer escalates. Log each sentence's answer, so a reviewer sees which one failed.

All questions share one state, so one request covers them; state plus all questions must stay
under 65,536 tokens. Measured on one RTX 5090 with VAKYN 4B and two short articles: 25 to 37 ms
for the whole-draft check, about 75 ms with five sentence questions added (Python client, same machine).

## What the check does not catch

- **A correct but incomplete draft.** "Go to Reports > Invoices and choose Export" is `supported`
  even if the article also says large exports arrive by email. Only the side-by-side comparison or
  a person catches this ([rollout](rollout.md)).
- **Wrong sources.** If retrieval brought the wrong article, a draft faithful to it is
  `supported`. Retrieval quality is a separate check.
- **Tone, length, format.** Check those in code (length, required links) or not at all.
