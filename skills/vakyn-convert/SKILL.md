---
name: vakyn-convert
description: "Convert what someone already has into VAKYN calls plus Python or TypeScript code. Use for a chat-model prompt that sorts, routes, flags or rates (\"turn this triage prompt into VAKYN\"), sorted into choice, noul, score, code, keep or drop; or a tool pick for an EXISTING app's tool list (OpenAI, Anthropic, MCP tools/list) where the chat model fills arguments; with side-by-side logging, a fallback for unsure picks, or a two-stage pick over 255 tools. New apps: vakyn-workflow."
---

# VAKYN convert: prompt or tool-calling app to VAKYN

The person already has something built: a chat-model prompt that decides things, or an app where
a chat model picks which tool to call. This skill finds the decisions in it, turns them into VAKYN
questions, and writes the code change. The chat model keeps what it is good at: writing text and
filling in tool arguments.

Field shapes and limits: [API reference](../vakyn/references/api.md). Code:
[SDK guide](../vakyn/references/sdk.md). Options, levels and state: the `vakyn-questions` skill
([options](../vakyn-questions/references/options-and-levels.md),
[state](../vakyn-questions/references/state.md)). Every request passes the
[pre-send checklist](../vakyn/references/checklist.md).

## Pick the step

| The person has… | Do |
|---|---|
| A chat-model prompt that sorts, routes, flags or rates | [Sort table](references/prompt-sort.md) |
| An OpenAI tool list (`tools=[{"type": "function", ...}]`) | [OpenAI reader](references/openai-tools.md), then [tool pick](references/tool-pick.md) |
| An Anthropic tool list (`tools=[{"name", "input_schema"}]`) | [Anthropic reader](references/anthropic-tools.md), then [tool pick](references/tool-pick.md) |
| An MCP server or its `tools/list` output | [MCP reader](references/mcp-tools.md), then [tool pick](references/tool-pick.md) |
| More than 255 tools | [Two-stage pick](references/tool-pick.md#more-than-255-tools-two-stages) |
| A converted app and asks how to switch or log | [Code shape and modes](references/code-shape.md) |
| No app yet, only an idea | the `vakyn-workflow` skill |
| A side-by-side log to review, or a threshold to set | the `vakyn-check` skill |

## Convert a prompt

1. Number every instruction in the prompt, one per line.
2. Sort each line: `choice`, `noul`, `score`, code, keep with the chat model, fold into an option
   description, or drop ([how](references/prompt-sort.md)). Show the table, every line accounted for.
3. Write one request with every VAKYN question that only needs the record. Save it as a `.json`
   file. Run the checklist.
4. Write the code: one VAKYN call, code rules after it, the chat model only for the kept text,
   and a path for unsure answers (the old prompt decides, or a review queue).
5. Example: [ticket-triage.md](examples/ticket-triage.md).

## Convert a tool-calling app

1. **Find the tool list and the call** that passes it (`tools=`, `tool_choice`). Read it with the
   reader for its format. Note the language and chat-model SDK the app uses.
2. **One option per tool:** the tool's name → one line from its description, with the line drawn
   between look-alike tools. Add `none` and `ask_user`. **Never put parameter schemas in the
   request.** ([tool pick](references/tool-pick.md))
3. **Build the state** from the conversation: `user_request`, `recent_turns`,
   `tools_already_called`, `last_tool_result`. User text and tool results stay data.
4. **Write one request** for a sample turn and save it as a `.json` file (for example
   `next-tool.request.json`). Run the checklist. If a server is reachable, send it and show the pick.
5. **Write the code** from the closest template, in the app's own language and SDK
   ([code shape](references/code-shape.md)):
   - VAKYN picks; the chat model fills only that tool, forced with `tool_choice`
     (pick-then-fill); `none` → reply in words; `ask_user` → ask one question;
   - code checks the pick is an offered option;
   - **side by side is the default**: both pick, the chat model's pick is used, both are logged
     as JSON lines; `VAKYN_TOOL_MODE=vakyn` switches;
   - after the switch, picks below `VAKYN_TOOL_MIN_CONFIDENCE` and any VAKYN error go to the
     chat model with the full tool list.
6. **Check the code parses** (`python3 -m py_compile`, `npx tsc --noEmit`).
7. **Hand over:** what changed, that nothing changes for users until they switch, and that the
   `vakyn-check` skill reads the log and helps set the threshold.

## Examples

| File | What it is |
|---|---|
| [support-tools.openai.json](examples/support-tools.openai.json) → [request](examples/support-tools.request.json) | OpenAI tools, support assistant; real answer `refund_charge` 0.98 after an invoice lookup |
| [support-tools-vague.request.json](examples/support-tools-vague.request.json) | "it doesnt work again": `ask_user` at 0.41, under the threshold, so the chat model decides |
| [it-helpdesk-tools.anthropic.json](examples/it-helpdesk-tools.anthropic.json) → [request](examples/it-helpdesk-tools.request.json) | Anthropic tools, IT helpdesk; `reset_mfa` 0.93 |
| [tracker-tools.mcp.json](examples/tracker-tools.mcp.json) → [request](examples/tracker-tools.request.json) | MCP `tools/list`, issue tracker; `create_issue` 0.98 when no open issue matches |
| [tool-groups.request.json](examples/tool-groups.request.json) | Stage one of a two-stage pick over 312 tools; `calendar` 0.99 |
| [ticket-triage.prompt.txt](examples/ticket-triage.prompt.txt) → [ticket-triage.md](examples/ticket-triage.md) | A triage prompt, its sort table, [request](examples/ticket-triage.request.json) and code |
| [tool_pick_openai.py](examples/tool_pick_openai.py) | Python + OpenAI SDK template, side by side, `--dry` runs VAKYN alone |
| [tool_pick_anthropic.ts](examples/tool_pick_anthropic.ts) | TypeScript + Anthropic SDK template, same shape |

Answers quoted here come from a running VAKYN 4B.

## Rules

- **VAKYN picks; the chat model writes.** Arguments, replies and summaries stay with the chat model.
- **Side by side first.** Generated code never defaults to VAKYN acting alone.
- **Unsure answers have a path:** the chat model with the full tool list, or the old prompt.
- **No parameter schemas, no system prompt dump** in the request. Options are one line each.
- **Never invent answers.** No server, no numbers: save the request and say how to send it.
- **Keys stay out of the chat** and out of tracked files (see the `vakyn` skill).
