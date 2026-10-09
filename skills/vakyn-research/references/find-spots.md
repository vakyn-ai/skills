# Find the chat-model calls

Goal: a list of every place the code sends a prompt to a chat model, then a verdict per place:
**decision** or **writing**. Search, then read each hit and follow it to the caller.

## 1. Search

Run these as Grep searches over the repo (skip `node_modules`, `.venv`, `dist`, `build`, vendored
code and tests unless the person asks). One hit is often a shared wrapper (`ask()`, `llm.call()`);
then search for the wrapper's callers: each caller is a spot.

| Stack | Search for |
|---|---|
| OpenAI (Python, TS) | `chat.completions.create`, `responses.create`, `beta.chat.completions.parse`, `from openai`, `"openai"` |
| Azure OpenAI | `AzureOpenAI`, `azure_endpoint`, `openai.azure.com` |
| Anthropic | `messages.create`, `messages.stream`, `@anthropic-ai/sdk`, `import anthropic` |
| Google Gemini | `generate_content`, `generateContent`, `google.genai`, `@google/genai`, `GenerativeModel` |
| AWS Bedrock | `invoke_model`, `converse(`, `InvokeModelCommand`, `ConverseCommand`, `bedrock-runtime` |
| LiteLLM | `litellm.completion`, `acompletion(`, `litellm` in config files |
| LangChain / LangGraph | `ChatOpenAI`, `ChatAnthropic`, `init_chat_model`, `.invoke(`, `with_structured_output`, `bind_tools`, `StateGraph`, `add_conditional_edges` |
| Vercel AI SDK | `generateText`, `generateObject`, `streamText`, `streamObject`, `from "ai"` |
| LlamaIndex | `llm.complete`, `llm.chat`, `as_query_engine`, `RouterQueryEngine`, `LLMSingleSelector` |
| OpenAI Agents SDK | `Agent(`, `Runner.run`, `handoffs=`, `@function_tool` |
| MCP clients | `ClientSession`, `list_tools`, `call_tool`, `mcpServers` |
| Raw HTTP | `/v1/chat/completions`, `/v1/messages`, `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com` |
| Others | `ollama`, `mistralai`, `cohere`, `groq`, `together`, `openrouter` |

Also read config files (`.env.example`, `settings.py`, `config.ts`, YAML) for model names, and code
comments, READMEs, cron and queue settings for how often each path runs. Never read `.env` itself:
it holds keys.

## 2. Decision or writing

Read the prompt, the output handling and the caller. Use the test in
[fit-check.md](../../vakyn/references/fit-check.md): the answer is one of a known set, the
evidence fits in the request, and a careful reader could decide it.

**Signs of a decision** (any one is enough to look closer):

- Output schema with a fixed set of values: `enum`, `Literal[...]`, `z.enum`, a JSON schema with
  `"enum"`, JSON mode returning one field from a list.
- `tools=` / `tool_choice` / `bind_tools` / `handoffs`: the model picks a tool or agent.
- Prompts like "answer only yes or no", "return one of", "reply with the number only", "rate from
  1 to 5", "which of the following", "APPROVE or REJECT".
- Small `max_tokens` (1 to 20).
- Code compares the output to fixed strings: `== "yes"`, `startswith`, `in TEAMS`, a `switch` on
  the answer, `int(answer)`.
- Routers: `add_conditional_edges`, `RouterQueryEngine`, a dict of handlers keyed by the answer.

| Kind of decision | VAKYN question type |
|---|---|
| sort, route, categorize, assign | `choice` with an escape option (`other`, `none`) |
| yes/no check, flag, gate, approve/reject | `noul` (one per rule if the prompt lists several) |
| rate, score, grade, urgency, severity | `score` with described levels, lowest first |
| pick a tool or next step | `choice` over tool names plus `none` and `ask_user`; the chat model fills the arguments |
| pick the best match from a short list | `choice` over the candidates plus `none` |
| extract by choosing (date, amount, name) | code finds candidates, `choice` picks one |
| tag with all that apply | one `noul` per tag, in one request |

**Signs of writing** (mark **keep**): the output is shown to a person or stored as text, the
prompt asks to write, reply, summarize, draft, translate, rewrite or explain, `temperature` above
0, larger `max_tokens`, streaming to a UI.

**Mixed calls.** One call can do both, for example a tool loop that picks tools and then writes the
final answer, or a prompt that returns `{"team": ..., "reply": ...}`. List the decision part as a
spot and the writing part as keep, both at the same `file:line`.

## 3. Does not fit

List these with the reason, not as spots:

- **Needs live data**: the answer depends on a database, an API or today's date that is not in
  the prompt. Code fetches it; VAKYN can only judge what is in the state.
- **Output is free text**: writing (keep).
- **Evidence too long**: the state plus the question would pass 32,768 tokens (see
  [api.md](../../vakyn/references/api.md#limits)), for example a whole week of tickets or a
  long contract. Note whether code could cut it to the relevant part first.
- **More than 255 options**: still fits with a two-step pick; note it as larger effort.
- **Arithmetic, counting, dates, thresholds**: code, not a question.
