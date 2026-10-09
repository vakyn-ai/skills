# The converted code: shape and modes

Write the change into the person's own file, in their language, with the official SDK
(`typesafe-sdk` for Python, `@typesafe-ai/sdk` for TypeScript; see the
[SDK guide](../../vakyn/references/sdk.md)). Start from the closest template:

- Python, OpenAI SDK app: [tool_pick_openai.py](../examples/tool_pick_openai.py)
- TypeScript, Anthropic SDK app: [tool_pick_anthropic.ts](../examples/tool_pick_anthropic.ts)

Mixed cases (Python with Anthropic, TypeScript with OpenAI) take the VAKYN part from one template
and the chat-model calls from the [other reader](openai-tools.md).

## The parts

| Part | Does |
|---|---|
| `OPTIONS` | tool name → one line, plus `none` and `ask_user`. Written once, in code, next to the tool list. A start-up check that every tool has an option. |
| `build_state(messages)` | the state from [tool-pick](tool-pick.md#3-build-the-state): goal, recent turns, tools called, last tool result |
| `vakyn_pick(messages)` | one `choice` call; checks the pick is an offered option; returns `None` on any error, so VAKYN being down never stops the app |
| `chat_call(messages, tools, tool_choice)` | the app's existing chat-model call, with the tool list made a parameter |
| `next_step(messages)` | runs the mode below and returns the message the app acts on, as before |
| `log(entry)` | appends one JSON line per step |

The rest of the app (running tools, appending messages, the final reply) does not change.

## Modes

One setting, `VAKYN_TOOL_MODE`, read from the environment or the app's config.

**`side_by_side` (the default).** VAKYN and the chat model pick at the same time (a thread or
`Promise.all`, so the step takes no longer). The chat model's message is used, exactly as before.
Both picks are logged. Nothing the user sees changes. Ship this first.

**`vakyn`.** VAKYN picks, then [pick-then-fill](tool-pick.md#5-fill-and-act-in-code):

- a tool → the chat model fills only that tool, forced;
- `none` → the chat model replies with no tools;
- `ask_user` → the chat model asks one clarifying question;
- error, an option that was not offered, or `confidence` under `VAKYN_TOOL_MIN_CONFIDENCE` → the
  chat model picks with the full tool list, as before (`used: "chat"`).

`VAKYN_TOOL_MIN_CONFIDENCE` defaults to the tool-pick starting value in
[thresholds](../../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes). The real
value comes from the person's own log and labeled turns, with the `vakyn-check` skill. Never switch the default to `vakyn` in the generated
code; the person flips it after reviewing the log.

## The log

One JSON line per step, appended to `VAKYN_TOOL_LOG` (default `vakyn-tool-picks.jsonl`, git-ignored):

```json
{"ts": "2026-10-09T08:37:21.962Z", "request_id": "req_bb9f…", "mode": "side_by_side",
 "vakyn_pick": "search_help_center", "vakyn_confidence": 0.66,
 "vakyn_probabilities": {"search_help_center": 0.7, "none": 0.28, "…": 0.0},
 "chat_pick": "search_help_center", "agree": true, "used": "chat"}
```

| Field | Value |
|---|---|
| `ts` | UTC time |
| `request_id` | VAKYN's request id (`result.request_id`, or `withResponse().requestId` in TypeScript) |
| `mode` | `side_by_side` or `vakyn` |
| `vakyn_pick`, `vakyn_confidence`, `vakyn_probabilities` | VAKYN's answer; `null` when it failed |
| `chat_pick` | the tool the chat model called, `none` for a text reply, `null` when it was not asked |
| `agree` | `vakyn_pick == chat_pick`, `null` when either is missing |
| `used` | `chat` or `vakyn`: whose pick the app acted on |

Add the app's own ids (conversation, user) if it has them. Never log API keys. User text is not in
the log; the `request_id` ties a line to the server's own records.

Reading the log, the agreement rate, where the two differ and choosing the threshold are the
`vakyn-check` skill's job. Name it when you hand over.

## Prompts with several questions

A converted prompt (the [sort table](prompt-sort.md)) asks several questions in one VAKYN call.
Run it side by side the same way: the old prompt's answer is used, VAKYN's is logged next to it.
Write **one line per question**, with the same field names plus `question`:

```json
{"ts": "2026-10-09T09:12:03Z", "request_id": "req_2f35…", "question": "cancel_threat",
 "vakyn_pick": "yes", "vakyn_confidence": 0.76, "vakyn_probabilities": {"yes": 0.88, "no": 0.12},
 "chat_pick": "yes", "agree": true, "mode": "side_by_side", "used": "chat"}
```

| Type | `vakyn_pick` | `vakyn_confidence` | `vakyn_probabilities` |
|---|---|---|---|
| `choice` | the option | `confidence` | the distribution |
| `noul` | `"yes"` if `noul >= 0.5`, else `"no"` | `abs(2 * noul - 1)` | `{"yes": noul, "no": 1 - noul}` |
| `score` | the most likely level index (0, 1, …) | `confidence` | the distribution by level |

`chat_pick` is the old prompt's answer in the same terms: an option, `"yes"` / `"no"`, or a level
index. When the old prompt answers in other terms (a P1–P3 priority built from a level plus rules),
compare after the code rules and log that field as its own `question` (`priority`). All lines of
one record share the `request_id`. When VAKYN fails, write the lines with `null` VAKYN fields.
`vakyn-check` reads this per question.

## Checks before you hand over

- The file parses: `python3 -m py_compile app.py`, or `npx tsc --noEmit` for TypeScript.
- The saved request passes the [checklist](../../vakyn/references/checklist.md).
- With a reachable server, run one turn and show VAKYN's pick next to the request. The templates'
  `--dry` flag runs VAKYN alone, without a chat-model key.
- The person knows the default is side by side and how to switch.
