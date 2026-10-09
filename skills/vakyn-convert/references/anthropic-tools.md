# Read an Anthropic tool list

Where to find it: the `tools` argument of `client.messages.create(...)` (Python `anthropic`,
TypeScript `@anthropic-ai/sdk`), often a `tools: Anthropic.Tool[]` constant.

## Shape

```json
[{"name": "reset_mfa",
  "description": "Remove the employee's registered two-factor devices so they can enroll a new phone.",
  "input_schema": {"type": "object", "properties": {"employee_id": {"type": "string"}}}}]
```

## Read

| Option field | From |
|---|---|
| name | `name` |
| description | `description`, rewritten to one line ([tool-pick](tool-pick.md#1-one-option-per-tool)) |
| ignored | `input_schema`, `cache_control` |

Entries with a `type` such as `web_search_20250305` or `text_editor_...` are server or built-in
tools: leave them with the chat model, or add an option by hand if the person wants VAKYN to pick
them too.

Sample: [it-helpdesk-tools.anthropic.json](../examples/it-helpdesk-tools.anthropic.json) →
[it-helpdesk-tools.request.json](../examples/it-helpdesk-tools.request.json).

## Where the pick happens in the app

```ts
const res = await anthropic.messages.create({ model, max_tokens, system, tools, messages });
const use = res.content.find((b) => b.type === "tool_use"); // the chat model's pick: use.name
```

No `tool_use` block means the chat model picked "no tool" (log it as `none`). Tool results come
back to the model as `tool_result` blocks in the next user message; read the last one for
`last_tool_result`.

## Fill one tool

```ts
const res = await anthropic.messages.create({
  model, max_tokens, system, messages,
  tools: tools.filter((t) => t.name === pick),
  tool_choice: { type: "tool", name: pick },
});
const input = res.content.find((b) => b.type === "tool_use")?.input;
```

Python is the same with `tool_choice={"type": "tool", "name": pick}`.

Template: [tool_pick_anthropic.ts](../examples/tool_pick_anthropic.ts).
