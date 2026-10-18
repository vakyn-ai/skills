---
name: migrate
description: "Move existing decision-API code to VAKYN Cloud (api.vakyn.com), or to the person's own VAKYN open-server when they ask for it. Use when code calls hosted Jev (typesafe-sdk, @typesafe-ai/sdk, api.typesafe.ai), OpenRouter decisions, Vercel AI Gateway, Cloudflare Clef, OpenJev or the OpenAI Decisions API, or uses a Pydantic AI, AI SDK, TanStack AI, LangChain or Langfuse adapter, and they want it on VAKYN: find call sites, change config, map fields, compare side by side, switch, roll back. Chat-model prompts or tool calls: convert. First setup: start."
---

# VAKYN migrate: move decision calls to VAKYN

The person already calls a decision API: hosted Jev, a gateway, another Jev-compatible model,
or OpenAI's Decisions API, directly or through a framework adapter. This skill moves those
calls to VAKYN with as little code change as possible, proves the move on their requests, and
leaves a way back.

The default target is **VAKYN Cloud** (`https://api.vakyn.com`, a key from
[vakyn.com/console](https://vakyn.com/console)): for a Jev-compatible client the move is the base
URL and the key. The target is their **own open-server** when they ask for it or their data
cannot leave their network; then the base URL is their server's.

Target shape: [API reference](../start/references/api.md). SDKs: [SDK guide](../start/references/sdk.md).
Key and settings: [VAKYN Cloud](../start/references/cloud.md), or
[self-hosting](../start/references/self-hosting.md). Every request passes the
[pre-send checklist](../start/references/checklist.md).

## Pick the step

| The person… | Do |
|---|---|
| Uses the official TypeSafe SDK or raw HTTP to `api.typesafe.ai` | [Sources 1–2](references/sources.md#1-hosted-jev-through-the-official-sdks) |
| Uses OpenRouter, Vercel AI Gateway, Clef or another `/v1/systemone` server | [Sources 3–6](references/sources.md#3-openrouter) |
| Uses OpenAI's Decisions API | [Field maps](references/field-maps.md#openai-decisions-api) |
| Uses Pydantic AI, the AI SDK, TanStack AI, LangChain or Langfuse | [Adapters](references/adapters.md) |
| Asks what will be different | [Differences](references/differences.md) |
| Is ready to compare, switch or plan a rollback | [Side by side, switch, roll back](references/switch.md) |
| Uses a service or field not covered here | Read their code and the provider's current docs, or ask ([below](#unverified-sources)) |
| Has no VAKYN key yet | the `start` skill first |
| Has a chat-model prompt or tool-calling app, not a decision API | the `convert` skill |

## Steps

1. **Find every call site.** Run the grep for each source the person might use
   ([sources](references/sources.md)); also search config, CI and deploy files. List each
   one: file and line, which service, how it is called (SDK, HTTP, adapter).
2. **List the settings.** Every model name, base URL, key variable and env file name in use.
   Name key locations by file and line; never print a key, never read `.env`. Confirm the target:
   VAKYN Cloud unless they want their own server.
3. **Go through the [differences](references/differences.md)** that touch their code: model
   names, `vk_` keys, limits (32,768 / 65,536 tokens, 255 options, 10 levels), errors and
   retries, no streaming or batch endpoint, the rate limit or queue, cost, provider-only fields.
4. **Change config before code.** Where the SDK or adapter reads variables, change only
   variables. Move literals (URLs, model names) into config in the same change. Map fields only
   where the wire format differs, and only fields documented in [field maps](references/field-maps.md).
5. **Save one request** in the new shape as a `.json` file and run the checklist. If VAKYN is
   reachable, send it and show the answer.
6. **Compare side by side** on about 30 recorded requests (on VAKYN Cloud, 30 requests from
   their balance; say so) with
   [compare.py](examples/compare.py): agreement per question, every disagreement, failed lines,
   measured time. Agreement is not accuracy; labels decide. More in the `check` skill.
7. **Switch by config**, check thresholds again, and write the
   [rollback plan](references/switch.md#5-rollback-plan) before the switch.

Show the person a short plan after steps 1–3 (call sites, settings, what changes) before
editing their files.

## Examples

| Move | Before | After |
|---|---|---|
| Python SDK, config only | [sdk_before.py](examples/sdk_before.py) | [sdk_after.py](examples/sdk_after.py) |
| Raw HTTP | [http_before.sh](examples/http_before.sh) | [http_after.sh](examples/http_after.sh) + [bike-desk.request.json](examples/bike-desk.request.json) |
| AI SDK, gateway to VAKYN | [ai_sdk_before.ts](examples/ai_sdk_before.ts) | [ai_sdk_after.ts](examples/ai_sdk_after.ts) |
| OpenAI Decisions request | [openai-decisions.before.json](examples/openai-decisions.before.json) | [openai_decisions_map.py](examples/openai_decisions_map.py) → [openai-decisions.request.json](examples/openai-decisions.request.json) |
| OpenRouter decisions request | [openrouter-decisions.before.json](examples/openrouter-decisions.before.json) | [field map](references/field-maps.md#openrouter-decisions) |
| Compare two services | [recorded.sample.jsonl](examples/recorded.sample.jsonl) | [compare.py](examples/compare.py) (`--dry` sends nothing) |

## Unverified sources

What is in [sources](references/sources.md) was checked against official docs or package
source on 2026-10-09. For anything else (another gateway, another SDK, a field not listed, a
newer API version):

- Read the person's code to see exactly which fields and options they use.
- Read the provider's current official docs or package source for those fields. If you cannot
  reach them, ask the person for the docs link or a sample request and response from their logs.
- Map only what you have seen documented or in their logs. Say which parts are unchecked.
  Never invent a field, an endpoint or a model name.

## Rules

- **Name other services by fact only.** Say what they are and how they are called. No quality,
  speed or price comparisons, and no hint of a partnership.
- **Ask before data leaves the machine or money is spent.** Replaying requests against a hosted
  service, the old one or VAKYN Cloud, costs money and sends data out; prefer old answers from
  their logs. VAKYN Cloud cost: input tokens × the price from `GET /v1/models`
  ([cost](../start/references/cloud.md#cost)); never a price from memory.
- **Keys stay out of the chat and out of code.** See the `start` skill rules.
- **Measure, never guess.** Agreement and times come from the person's run, with where it ran
  named. VAKYN not reachable, no numbers: write the script and the commands to run it.
- **Keep the way back.** Old settings stay one change away until the person retires them.
