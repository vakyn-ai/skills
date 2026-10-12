---
name: research
description: "Research an existing app, codebase or business process and write one ranked report, vakyn-research.md, of where VAKYN (a decision model) could replace chat-model decisions. Use for \"where could VAKYN help in my app\", \"audit our LLM calls\", \"which of our prompts are decisions\", call logs to sort, or a process in plain words. Reads and estimates only; never changes code or calls VAKYN. For one prompt or tool list the person already picked, use convert."
---

# VAKYN research: find where it helps

Find every place where a chat model (or a person, in a described process) makes a **decision**:
sorts, routes, checks yes or no, rates, picks a tool, picks the best match. Mark every place
that **writes text** as "keep". Rank the decisions by gain against risk and effort, and write it
all to one file: `vakyn-research.md`.

You are the person's guide. This skill reads and estimates; the person picks what to change next.

## Hard rules

- **Read only.** Do not change, move or format any existing file. The only file you create is
  `vakyn-research.md`. Write the file in one go; to revise it, write it again whole.
- **No calls.** Do not call VAKYN, any chat model, or any API. Do not run the app or its tests.
  Real testing belongs to `check`.
- **Logs stay local.** Total call logs on the machine; never paste their contents into the report
  beyond counts, tokens, times and costs.
- **Say where each number comes from:** log, code, or assumed. Never present a guess as measured.
- **Do not stop to ask.** If volumes, prices or details are missing, assume, write the assumption
  down, and offer to update the report when the person answers.

## Steps

1. **Pick the input.**
   - A codebase (the current folder, or a path they name): go to step 2.
   - A process in plain words, no code: follow [references/process.md](references/process.md),
     then go to step 4.
   - Call logs or traces (JSONL, CSV, an export from a tracing tool): use them in step 4 for real
     volume, cost and wait time. Look for them too (`logs/`, `*.jsonl`, `traces/`) and ask if the
     person mentioned some you cannot find.
2. **Find the chat-model calls.** Search with the patterns in
   [references/find-spots.md](references/find-spots.md#1-search). Follow shared wrappers to their
   callers: each caller is one spot. Note `file:line` of the call, the model, the prompt, and
   what the code does with the output.
3. **Sort each call**: decision, writing (keep), or does not fit. Use the signs in
   [references/find-spots.md](references/find-spots.md#2-decision-or-writing) and the test in
   [fit-check.md](../start/references/fit-check.md). A call that does both (picks a tool, then
   writes the answer) is listed twice: the pick as a spot, the writing as keep. For each
   decision, name the question type: `choice`, `noul` or `score`.
4. **Rate and rank** each spot: gain (calls a day, current model, cost, wait time), risk of a
   wrong answer downstream, and effort. Method and scales:
   [references/ranking.md](references/ranking.md). Check the limits in
   [api.md](../start/references/api.md#limits): 255 options, 10 levels, 32,768 tokens for state
   plus the longest question.
5. **Write `vakyn-research.md`** at the root of the repo (or where the person asks; the current
   folder when the code is read-only or there is no code) with
   [references/report-template.md](references/report-template.md): summary (top 3), ranked
   table, details per spot, keep list, does-not-fit list, assumptions and open questions, next
   steps. Example: [examples/helpdesk-py/vakyn-research.example.md](examples/helpdesk-py/vakyn-research.example.md).
6. **Reply in the chat** with the top 3 spots in one line each, the keep list in one line, and the
   next skill to run. Do not paste the whole report.

## Next skill per spot

| The spot is… | Next |
|---|---|
| an existing prompt that decides (sort, check, rate) | `convert` |
| an existing tool list or agent that picks tools | `convert` (VAKYN picks, the chat model fills the arguments) |
| a process step or something not built yet | `workflow` |
| any of these, once questions need wording | `questions` |
| ready to compare with the current chat model on real records | `check` |

## Sample apps

Two small apps with known answers, for trying the skill and checking its output:

- [examples/helpdesk-py/](examples/helpdesk-py/): Python, OpenAI SDK. Answer key:
  [expected.md](examples/helpdesk-py/expected.md).
- [examples/shop-agent-ts/](examples/shop-agent-ts/): TypeScript, Anthropic SDK tool calling.
  Answer key: [expected.md](examples/shop-agent-ts/expected.md).
