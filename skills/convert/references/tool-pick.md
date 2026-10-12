# Tool pick: from a tool list to one `choice`

In a tool-calling app the chat model does two jobs each step: it **picks** which tool to call and
it **fills** the tool's arguments. Picking is a decision. Filling is writing (an email address, a
search query, an order id copied from the chat). VAKYN takes the pick; the chat model keeps the
fill. This is **pick-then-fill**.

Read the tool list first: [OpenAI](openai-tools.md), [Anthropic](anthropic-tools.md),
[MCP](mcp-tools.md). Each reader gives you a list of `(name, description)`. Then:

## 1. One option per tool

- **Name:** the tool's name, unchanged, so code maps the pick straight back to the tool. Tool
  names that clash with `none` or `ask_user`, or tools from two MCP servers with the same name,
  get a prefix (`tracker__search`) and a lookup table in code.
- **Description:** one line, written from the tool's own description. Keep what it does and when
  it is the right tool. Cut parameter details, return formats, examples and instructions to the
  chat model ("always call X first"). About 6–15 words.
- **Draw the line between look-alike tools.** `get_invoice` and `refund_charge` both touch money:
  say when each is right ("…once the customer asked for money back and the charge is known").
  `open_incident` vs a personal problem: "an outage that affects many people, not one person".
- **Say what must come first.** When one tool needs an id another tool finds, say so in both:
  "Find a contact and their id…; needed first when the id is not known yet" and "Log a call with
  a contact whose id is already known". Turns that need several tools still get lower confidence
  than one-tool turns; that is the threshold doing its job.
- **No description in the tool?** Write one from the name and what the app does with it. Ask the
  person if the name is unclear; never guess from the parameter names alone.
- **Parameter schemas are never sent.** They add tokens and pull the pick toward tools with
  matching field names. The chat model gets the schema at fill time.

## 2. Add two escape options

```json
"none":     "No tool is needed now: answer the customer directly",
"ask_user": "The request does not say what is wrong or what is wanted (\"it doesn't work\"); ask the customer first"
```

Without them VAKYN must pick a tool even for "thanks!" or "it doesn't work". Give `ask_user` a short
quoted example of a vague request: on a running VAKYN 4B, "can you help" went from `none` (0.55)
to `ask_user` (0.89) once the description carried one, while clear requests kept their tools.

## 3. Build the state

```json
{
  "assistant": "Support assistant for Lumen, a reporting app. It calls one tool at a time.",
  "user_request": "<the latest user message>",
  "recent_turns": [{"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}],
  "tools_already_called": ["get_invoice"],
  "last_tool_result": {"tool": "get_invoice", "result": {"...": "..."}}
}
```

- **`assistant`:** one line on what the app is. Not the whole system prompt.
- **`user_request`:** the goal of this step, usually the latest user message.
- **`recent_turns`:** the last few user and assistant turns that matter, as text, cut to a sane
  length. Not the whole chat.
- **`tools_already_called` and `last_tool_result`:** so VAKYN can tell "look it up" from "act on
  what was found" from "done, answer now". Cut long results; "none yet" when there are none.
- **Untrusted text is data.** User messages, emails and tool results sit under their own keys. They
  never go into `instructions`.

## 4. Ask the question

```json
"next_tool": {"type": "choice",
  "instructions": "Which tool should the support assistant call next to handle state.user_request? Use state.last_tool_result: a tool already called does not need to be called again.",
  "criteria": {"get_invoice": "Fetch an invoice, its charges and payment status, when they are not known yet",
               "refund_charge": "Refund a card charge, once the customer asked for money back and the charge is known",
               "none": "...", "ask_user": "..."}}
```

Name the subject (`state.user_request`). Run the [checklist](../../start/references/checklist.md).
Size: the state plus this one question must stay under 32,768 tokens, so cut long tool results.

## 5. Fill and act (in code)

| VAKYN picks | Code does |
|---|---|
| a tool | call the chat model with **only that tool** and force it (OpenAI `tool_choice={"type": "function", "function": {"name": ...}}`, Anthropic `tool_choice={"type": "tool", "name": ...}`); run the tool call it returns |
| `none` | call the chat model with no tools; it writes the reply |
| `ask_user` | call the chat model with no tools and a note to ask one clarifying question (or send a fixed question) |
| something not offered, an error, or confidence under the threshold | the chat model picks with the full tool list, as before |

Code always checks the pick is one of the offered options before acting on it.

One pick per step. If the app relies on the chat model calling several tools at once, keep the
chat model for those steps, or loop: pick, run, pick again with the new tool result.

## More than 255 tools: two stages

A `choice` takes at most 255 options. Above that, or when tools fall into clear families:

1. **Group the tools** by what they act on (calendar, email, billing…), by MCP server, or by name
   prefix. Each group gets a one-line description that covers its tools. Keep each group under
   about 250 tools so `none` and `ask_user` still fit.
2. **Stage one:** `choice` over the groups plus `none` and `ask_user`
   ([tool-groups.request.json](../examples/tool-groups.request.json)).
3. **Stage two:** a second request, same state, `choice` over the tools in the picked group plus
   `none` ("no tool in this group fits") and `ask_user`.
4. Unsure at either stage, or `none` at stage two: the chat model picks from the full list.
5. Log both stages in the same log line (`vakyn_group`, then the usual fields).

The two calls run one after the other, because stage two needs stage one's answer.
