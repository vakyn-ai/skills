---
name: vakyn-workflow
description: "Design a new VAKYN decision workflow from a plain-language task: questions, state builder, Python or TypeScript code, batching, unsure path. Use for routing, triage, intent, moderation, guardrails, next-tool pick, claim check (hallucination, grounding), LLM-as-judge or rubric grading, rerank or best match, risk flags, form steps, fan-out, extracting a value or date by picking instead of generating, rebuilding headings and lists, scoring once to rank many ways, triage-first investigation that stops early, or checking each field of an agent's structured output against its cited evidence."
---

# VAKYN workflow: design something new

The person describes a task in plain words ("someone reads every returns email and decides what
happens to it"). You turn it into a working decision workflow: the questions, a state builder
(what evidence, from where), the code, and what happens when VAKYN is unsure. Start from the
closest of thirteen patterns; each has a request and code that were run against a VAKYN 4B.

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
| Ask every branch's follow-up at once, read only the branch taken | [fan out](references/patterns/fan-out.md) | `choice` + branch questions with stated premises |
| Get a value, date or sentence out of text, or rebuild headings and lists | [pick instead of generate](references/patterns/pick-value.md) | `choice` over candidates code found + `none_of_these` |
| Rank or filter items many ways without asking again | [judgments as data](references/patterns/reusable-judgments.md) | one `score` or `noul` per dimension, stored |
| Investigate a list of items (search hits, alerts) and open only what could change the outcome | [triage first, stop early](references/patterns/triage-first.md) | one `noul` per item in one request, then code |
| Check a structured output field by field against the evidence it cites | [check each field](references/patterns/check-fields.md) | one `choice` per field: supported / contradicted / not in evidence |
| Several of these in a row | [compose patterns](references/compose.md) | |

Writing replies, summaries or tool arguments is not a decision: that stays with a chat model or a
person. Copying out a value that is already in the text is a pick, not writing. Converting an
existing prompt or tool-calling app is the `vakyn-convert` skill.

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
   with descriptions and an escape option, score levels described lowest first, the subject
   named in plain words ("the customer's message"). Rules, sums, dates and thresholds stay in
   code.
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
| fan out | [fan-out.request.json](examples/fan-out.request.json) | [fan_out.py](examples/fan_out.py) |
| pick instead of generate | [pick-value.request.json](examples/pick-value.request.json), [line-roles.request.json](examples/line-roles.request.json) | [pick_value.py](examples/pick_value.py) |
| judgments as data | [judgments.request.json](examples/judgments.request.json) | [judgments.py](examples/judgments.py) |
| triage first | [triage-first.request.json](examples/triage-first.request.json) | [triage_first.py](examples/triage_first.py) |
| check each field | [check-fields.request.json](examples/check-fields.request.json) | [check_fields.py](examples/check_fields.py) |

## Rules

- **Code decides what is exact.** Arithmetic, dates, thresholds, required fields, filters and
  business rules live in code, before or after the VAKYN answer.
- **Every `choice` has an escape option**, and every escape option has a path in code.
- **Read answers by name** and check a pick is one of the offered options before acting on it.
- **Every decision has an unsure path.** Thresholds are named settings, tuned later on the
  person's own records with `vakyn-check`.
- **Never invent answers.** No server, no numbers. Write the requests and code; say how to send them.
- **Keys stay out of the chat and out of files**: `TYPESAFE_API_KEY` in the environment.
