---
name: cascade
description: "Cut chat-model cost on an answer-writing pipeline (RAG answers, support replies, document Q&A, extraction) without losing quality: a cheap chat model drafts, VAKYN checks the draft against its sources, only failing drafts go to the expensive model or a person. Use for model cascades, small-to-large fallback, grounding or hallucination gates on drafts, a side-by-side pilot, a high escalation rate, or a cost-saved summary. One claim against one document: workflow. Grading outputs offline: judge."
---

# VAKYN cascade: cheap draft, VAKYN check, expensive model only on failure

The person has a pipeline where a chat model writes answers from sources: a RAG answer, a support
reply from help articles, an answer about a contract, fields pulled from an invoice. Most requests
do not need the expensive model. This skill puts a cheap model in front, has VAKYN check each
draft against the sources it should rest on, and sends only the drafts that fail to the expensive
model, then to a person. VAKYN decides; both chat models still write.

Shared material: [API reference](../start/references/api.md), [SDK guide](../start/references/sdk.md),
[pre-send checklist](../start/references/checklist.md), the `questions` rules for
[options](../questions/references/options-and-levels.md) and
[state](../questions/references/state.md), and the single page for
[threshold starting values](../check/references/thresholds.md#starting-values-and-sample-sizes).

## Pick the step

| The person… | Do |
|---|---|
| Asks whether their pipeline should cascade | [When to cascade](references/fit.md) |
| Wants the check: question, state, threshold, long drafts | [The draft check](references/check.md) |
| Wants the code around their existing chat-model call | [Routing](references/routing.md), templates in [examples/](examples/) |
| Is ready to try it on real traffic | [Side by side and the log](references/rollout.md) |
| Has a cascade log and asks what it saved | [Cost-saved summary](references/rollout.md#4-cost-saved-summary) |
| Sees many escalations | [A high escalation rate](references/fit.md#a-high-escalation-rate-what-to-look-at) |
| Checks single statements against a document, no drafting | `workflow`, [check a claim](../workflow/references/patterns/check-claim.md) |
| Wants to switch thresholds or review labels | the `check` skill |

## Steps

1. **Fit.** Find the chat-model call that writes the answer and the sources it gets. No sources,
   free-form writing, or latency that cannot take two calls in a row: say a cascade does not fit
   and why ([fit](references/fit.md)).
2. **Ask** which model is cheap and which is expensive today, and their prices per million tokens.
   Never fill in a price; leave placeholders if they do not know.
3. **Trim sources once, in code, before drafting**, so both models and the check see the same
   list and the state stays under 32,768 tokens ([check](references/check.md#the-state)).
4. **Write the check**: state `{question, sources, draft}` and one `choice` with `supported`,
   `unsupported`, `cannot_answer_from_sources`, `off_topic`, one line each. Long drafts: one more
   `choice` per sentence in the same request, combined in code ([check](references/check.md)).
   Save the request as a `.json` file and run the checklist.
5. **Route** ([routing](references/routing.md)): accept only `supported` at or above the
   customer-facing starting value (a named setting); `cannot_answer_from_sources` → decline reply
   or a person; everything else → the expensive model, checked once more → sent, or a person.
   Never loop. VAKYN down → behave as today.
6. **Write the code** into their pipeline from [cascade.py](examples/cascade.py) or
   [cascade.ts](examples/cascade.ts), with their chat-model client. **Side by side is the
   default**: the expensive answer is still sent; the cheap draft, the verdict and a comparison
   with the expensive answer are logged ([rollout](references/rollout.md)).
7. **Check it runs**: `python3 -m py_compile`, `npx tsc --noEmit`; with VAKYN reachable, run
   the template's `--demo` (canned drafts, real VAKYN answers) and send the saved request.
8. **Hand over**: what changed (nothing for users until they switch), the pilot's extra cost
   (VAKYN's too on VAKYN Cloud: [cost](../start/references/cloud.md#cost)),
   how to read the log with [cost_summary.py](examples/cost_summary.py), and that a person
   spot-checks accepted drafts before `CASCADE_MODE=cascade`.

## Examples

| File | What it is | Answer from a running VAKYN 4B |
|---|---|---|
| [supported.request.json](examples/supported.request.json) | a correct, reworded refund answer | `supported` 1.00 |
| [invented-number.request.json](examples/invented-number.request.json) | the same answer plus "within 3 business days" | `unsupported` 0.91 |
| [cannot-answer.request.json](examples/cannot-answer.request.json) | "yes, pay by bank transfer"; no article mentions it | `cannot_answer_from_sources` 0.94 |
| [per-claim.request.json](examples/per-claim.request.json) | five sentences, one invented discount | `unsupported` 1.00; that sentence `not_in_sources` 1.00 |
| [compare.request.json](examples/compare.request.json) | side by side: cheap export answer vs the expensive one | `draft_incomplete` 0.94 |
| [cascade.py](examples/cascade.py), [cascade.ts](examples/cascade.ts) | the cascade with an OpenAI-style client; `--demo` needs no chat-model key | |
| [cost_summary.py](examples/cost_summary.py) on [cascade.sample.jsonl](examples/cascade.sample.jsonl) | routes, quality checks, tokens and cost per 1,000 requests | |

## Rules

- **Only `supported` above the bar sends a cheap draft.** Every other answer has a path.
- **One escalation, then a person.** Never loop, never retry for a better verdict.
- **Side by side first.** Generated code never defaults to sending cheap drafts.
- **Agreement is not accuracy.** The expensive model as reference shows agreement; a person's
  spot-check shows quality. Say which one a number is.
- **Never invent prices or savings.** Prices come from the person; savings from their log.
- **The log holds user text** when `texts` is on: keep it private or drop it.
- **Keys stay out of the chat and out of files**: `TYPESAFE_API_KEY` and the chat-model keys in
  the environment.
