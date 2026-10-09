# Tool pick: choose the next tool or step

**Use when** an assistant or agent must choose what to do next from a fixed set of tools or steps.
VAKYN picks; your chat model still fills in the tool's arguments and writes the replies.
**Not when** the next step is fixed by code (a status field, a missing id), or when the work is
writing text.

## The request

[examples/tool-pick.request.json](../../examples/tool-pick.request.json): one `choice` whose
options are the tools, each with one line from the tool's own description (no parameter
schemas), plus two escape options:

- `none`: no tool is needed; reply from the conversation.
- `ask_user`: the request is vague or a detail the tool needs is missing.

The state holds the last few turns and the steps already done.

Answer from a running VAKYN 4B: "Can you move it to the 19th instead?" after the booking was found
→ `change_booking`, confidence 0.82.

## The code

[examples/tool_pick.py](../../examples/tool_pick.py)

Pick, then fill: on a tool, your chat model fills that one tool's arguments; on `ask_user`, it
writes one clarifying question; on `none`, it replies without a tool. Code checks the pick is one
of the offered steps.

Run on four conversations: move a booking → `change_booking`; "How many bags can I bring?" →
`baggage_policy`; "Can you change my trip?" with no booking named → `ask_user`; "Thanks, that is
all" → `none`.

## Unsure path

Below `MIN_CONFIDENCE`, the chat model picks the tool itself, as it did before VAKYN. If you are
replacing a working chat-model pick, run both side by side first (`vakyn-convert`) and compare the
logs with `vakyn-check`.

## Common mistakes

- **No `ask_user`.** "Can you change my trip?" first went to `change_booking` (0.97) with
  `ask_user` at 0.02. Adding one sentence to the instructions, "A tool step needs the booking and
  any new date to be known", moved it to `ask_user` (0.72). Say in the question when a tool is
  ready to run.
- **Parameter schemas in the options.** They make options long and alike. One line of purpose per tool.
- **The whole history in the state.** Keep the last few turns and a list of steps done.
- **More than 255 tools.** Pick a group first, then a tool in that group (two requests).
