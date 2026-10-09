# Read an OpenAI tool list

Where to find it: the `tools=` argument of `client.chat.completions.create(...)` (Chat Completions)
or `client.responses.create(...)` (Responses API), often a `TOOLS` constant or built from Pydantic
models with `pydantic_function_tool`.

## Shape

Chat Completions:

```json
[{"type": "function",
  "function": {"name": "refund_charge",
               "description": "Refund a card charge in full or in part. Only after the customer asked for money back.",
               "parameters": {"type": "object", "properties": {"charge_id": {"type": "string"}}}}}]
```

Responses API (flat, no `function` wrapper):

```json
[{"type": "function", "name": "refund_charge", "description": "...", "parameters": {"...": "..."}}]
```

## Read

| Option field | From |
|---|---|
| name | `function.name` (Chat Completions) or `name` (Responses) |
| description | first sentence or two of `description`, rewritten to one line ([tool-pick](tool-pick.md#1-one-option-per-tool)) |
| ignored | `parameters`, `strict` |

Skip entries whose `type` is not `function` (built-in tools such as `web_search` or
`file_search`): leave them with the chat model, or add an option by hand if the person wants
VAKYN to pick them too.

Sample: [support-tools.openai.json](../examples/support-tools.openai.json) →
[support-tools.request.json](../examples/support-tools.request.json).

## Where the pick happens in the app

```python
response = client.chat.completions.create(model=..., messages=messages, tools=TOOLS, tool_choice="auto")
call = response.choices[0].message.tool_calls  # the chat model's pick: call[0].function.name
```

`tool_calls` empty means the chat model picked "no tool" (log it as `none`).

## Fill one tool

```python
forced = {"type": "function", "function": {"name": pick}}
message = client.chat.completions.create(
    model=..., messages=messages, tools=[TOOLS_BY_NAME[pick]], tool_choice=forced,
).choices[0].message
args = json.loads(message.tool_calls[0].function.arguments)
```

Responses API: `tool_choice={"type": "function", "name": pick}`.

Template: [tool_pick_openai.py](../examples/tool_pick_openai.py).
