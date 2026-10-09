---
name: vakyn-workflow
description: Design a new VAKYN decision workflow from a plain-language task: the questions, state builder, Python or TypeScript code, batching and unsure path. Use for routing, categorize, triage, intent detection, moderation, guardrail, spam filter, next-tool or next-step pick for a new assistant, claim check (hallucination, grounding, fact-check), LLM-as-judge or eval grader, rubric grading, rerank or relevance filter, best match, risk flags, CI failure triage, alert triage, document intake, or form steps.
---

# VAKYN workflow: design something new

The person describes a task in plain words ("someone reads every returns email and decides what
happens to it"). You turn it into a working decision workflow: the questions, a state builder
(what evidence, from where), the code, and what happens when VAKYN is unsure. Start from the
closest of eight patterns; each has a request and code that were run against a VAKYN 4B.

Shared material: [fit check](../vakyn/references/fit-check.md),
[API reference](../vakyn/references/api.md), [SDK guide](../vakyn/references/sdk.md),
[pre-send checklist](../vakyn/references/checklist.md), and the `vakyn-questions` rules for
writing each question.

## Pick the pattern

| The task is to… | Pattern | Types |
|---|---|---|
| Send each item to one team, queue or person | [route](references/patterns/route.md) | `choice` |
| Sort a batch by type and urgency | [triage](references/patterns/triage.md) | `choice` + `score`, concurrent |
| Choose the next tool or step for an assistant | [tool pick](references/patterns/tool-pick.md) | `choice` with `none`, `ask_user` |
| Check a statement against a document | [check a claim](references/patterns/check-claim.md) | `choice`: supported / contradicted / not enough evidence |
| Grade on a scale, one or several criteria | [rate with a rubric](references/patterns/rubric.md) | one `score` per criterion, combined in code |
| Pick one item from a short list | [pick the best match](references/patterns/best-match.md) | `choice` over item ids + `no_good_match` |
| Flag what needs a person (refund, legal, safety) | [spot risk](references/patterns/spot-risk.md) | one `noul` per risk, combined in code |
| Choose the next field or question in a form | [fill a form step](references/patterns/form-step.md) | `choice` over empty fields + endings |
| Several of these in a row | [compose patterns](references/compose.md) | |

Writing replies, summaries or tool arguments is not a decision: that stays with a chat model or a
person. Converting an existing prompt or tool-calling app is the `vakyn-convert` skill.

## Steps

1. **Fit check.** Run the [fit check](../vakyn/references/fit-check.md) on the task. Split off
   the parts that write text and the parts code can do exactly.
2. **Pick the pattern(s)** from the table. Read the pattern page and open its example request
   and code. Most tasks are one pattern, or two [composed](references/compose.md).
3. **Write the design sheet** ([design](references/design.md#1-the-design-sheet)): decisions and
   their types, code rules, what stays with the chat model, state fields and their source,
   which questions share a request, the unsure path, the volume. Ask only what you cannot
   default (usually the options and where unsure answers go).
4. **Design the questions** with the `vakyn-questions` rules: one judgment per question, options
   with one-line descriptions and an escape option, score levels described lowest first, the
   subject named (`state.message`). Rules, sums, dates and thresholds stay in code.
5. **Write the state builder**: `build_state(record)` copies evidence from the person's data,
   each field under a plain name. No conclusions, no candidates that fail a hard rule
   ([design](references/design.md#3-the-state-builder)). Documents over 32,768 tokens: pick the
   relevant part in code, or split and combine ([long documents](references/long-documents.md)).
6. **Write the code** in the project's language (Python or TypeScript) with the official SDK,
   starting from the pattern's example. Batch by [dependency and volume](references/batching.md):
   independent questions in one request; dependent steps as separate requests; many records
   concurrently with a cap and `429` retry.
7. **Add the unsure path** for every decision ([unsure](references/unsure.md)): a threshold as a
   named setting, and where unsure answers and escape options go (a person, a chat model, a
   review queue, a safe default).
8. **Run the [checklist](../vakyn/references/checklist.md)** on every request. Save each request
   as a `.json` file next to the code.
9. **Send and test.** If a server is reachable, send each request and show the real answers.
   Then point to the `vakyn-check` skill for a test on about 30 of the person's own records
   before going live. No server: say so and never invent answers.

## What to hand over

- The design sheet (a table, a few lines per decision).
- Each request as a `.json` file, passing the checklist.
- The code file: constants for options and levels, `build_state`, the requests, the code rules,
  the option check, the thresholds as settings, the unsure path, request ids logged.
- One line per decision on what happens when VAKYN is unsure.
- The next step: `vakyn-check` on about 30 real records.

## Examples

| Pattern | Request | Code |
|---|---|---|
| route | [route.request.json](examples/route.request.json) | [route.py](examples/route.py), [route.ts](examples/route.ts) |
| triage | [triage.request.json](examples/triage.request.json) | [triage.py](examples/triage.py), [triage.ts](examples/triage.ts) |
| tool pick | [tool-pick.request.json](examples/tool-pick.request.json) | [tool_pick.py](examples/tool_pick.py) |
| check a claim | [check-claim.request.json](examples/check-claim.request.json) | [check_claim.py](examples/check_claim.py) |
| rubric | [rubric.request.json](examples/rubric.request.json) | [rubric.py](examples/rubric.py) |
| best match | [best-match.request.json](examples/best-match.request.json) | [best_match.py](examples/best_match.py) |
| spot risk | [spot-risk.request.json](examples/spot-risk.request.json) | [spot_risk.py](examples/spot_risk.py), [spot_risk.ts](examples/spot_risk.ts) |
| form step | [form-step.request.json](examples/form-step.request.json) | [form_step.py](examples/form_step.py) |

## Rules

- **Code decides what is exact.** Arithmetic, dates, thresholds, required fields, filters and
  business rules live in code, before or after the VAKYN answer.
- **Every `choice` has an escape option**, and every escape option has a path in code.
- **Read answers by name** and check a pick is one of the offered options before acting on it.
- **Every decision has an unsure path.** Thresholds are named settings, tuned later on the
  person's own records with `vakyn-check`.
- **Never invent answers.** No server, no numbers. Write the requests and code; say how to send them.
- **Keys stay out of the chat and out of files**: `TYPESAFE_API_KEY` in the environment.
