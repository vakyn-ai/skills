# Answer key: shop-agent-ts

A small TypeScript shop assistant on the Anthropic SDK with tool calling.

## Decision spots

| Where | What it decides | Question type | Signs in the code |
|---|---|---|---|
| `src/agent.ts:14` `chatTurn` | which of 6 tools to call next (or none, and answer) | `choice` over the tool names, plus `none` and `ask_user` | `tools`, `tool_choice: { type: "auto" }`, `tool_use` blocks |
| `src/moderation.ts:10` `moderateReview` | publish or hold a product review | `noul` (or one `noul` per rule: insults, personal data, links, off-topic) | "exactly one word: APPROVE or REJECT", `max_tokens: 5`, `=== "APPROVE"` |

For the tool pick, VAKYN picks the tool and the chat model keeps filling in the arguments
(pick-then-fill). Next skill for both: `vakyn-convert`.

## Writing spots (keep)

| Where | What it writes | Why it stays |
|---|---|---|
| `src/agent.ts:14` `chatTurn` (final turn) | the reply to the customer | free text; same call as the tool pick, so only the pick moves |
| `src/catalog.ts:11` `writeDescription` | product page description | free text, and it runs a few dozen times a week |

## Not chat-model calls

`src/handlers.ts` (runs the tools against shop services), `src/tools.ts` (tool list, input to
`vakyn-convert`), `src/server.ts` (routes; its comments give the volumes).
