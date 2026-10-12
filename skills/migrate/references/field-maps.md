# Field maps to `/v1/systemone`

Only fields shown in the provider's official docs (checked 2026-10-09) are mapped. A field the
person's code uses that is not here: read the provider's current docs, or ask. Never guess
what an unknown field does.

Target shape: [API reference](../../start/references/api.md). Every mapped request passes the
[pre-send checklist](../../start/references/checklist.md).

## OpenRouter decisions

`POST https://openrouter.ai/api/alpha/decisions` → `POST {base}/v1/systemone`.
Example: [openrouter-decisions.before.json](../examples/openrouter-decisions.before.json).

| OpenRouter request | VAKYN |
|---|---|
| `model` `typesafe/jev-1.13`, `~typesafe/jev-latest` | `jev-latest` |
| `state`, `questions` (same `type`, `instructions`, `criteria`) | unchanged |
| `provider`, `session_id`, `user`, `trace` | drop (OpenRouter routing and tracing) |

| OpenRouter response | VAKYN |
|---|---|
| `id` | none; use the `x-typesafe-request-id` header |
| `provider`, `usage.cost` | none |
| `model`, `answers`, `usage.input_tokens`, `usage.output_tokens` | same |

## AI Gateway `/v1/evaluate`

`POST https://ai-gateway.vercel.sh/v1/evaluate` → `/v1/systemone`.

| Gateway | VAKYN |
|---|---|
| `model` `typesafe-ai/jev` | `jev-latest` |
| question `type: "boolean"` | `type: "noul"` (same `instructions`, `criteria` `{true, false}`) |
| `choice`, `score` questions | unchanged |
| `providerOptions` | drop |
| answer `{type: "boolean", probability}` | `{type: "noul", noul}` |
| `usage.inputTokens`, `usage.outputTokens`, `providerMetadata` | `usage.input_tokens`, `usage.output_tokens`; no metadata |

The gateway's choice and score examples show no `confidence`; VAKYN returns one.

## Cloudflare Clef on Workers AI

`POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef`
(or `env.AI.run`) → `/v1/systemone`.

| Clef | VAKYN |
|---|---|
| `model` `clef`, `clef-flash` | `jev-latest` |
| `state`, `questions` | unchanged (Clef allows 1–64 questions) |
| `images` | no field in the VAKYN API; keep image questions where they are, or put a text description in the state |
| `Authorization: Bearer $CLOUDFLARE_AUTH_TOKEN` | `Bearer $VAKYN_API_KEY` |

Response: the model page lists `model`, `answers`, `usage`, but does not show whether the REST
response wraps them in an outer object. Read one real response from the person's logs before
changing the code that reads it.

## OpenAI Decisions API

`POST /v1/decisions` (`client.decisions.create`) → `/v1/systemone`. Runnable both ways:
[openai_decisions_map.py](../examples/openai_decisions_map.py) on
[openai-decisions.before.json](../examples/openai-decisions.before.json) gives
[openai-decisions.request.json](../examples/openai-decisions.request.json).

| OpenAI request | VAKYN |
|---|---|
| `model` `gpt-6-luna` | `jev-latest` |
| `input` (string) | `state` (string) |
| `input` (list of user messages) | `state`: the text parts; an `input_image` part has no mapping |
| `questions` (list; `name` optional) | `questions` (object); key = `name`, or a made-up `q0`, `q1`… |
| `type: "predicate"` | `type: "noul"` |
| `choice`: `choices: [{value, description}]` (2–255) | `criteria: {value: description}`; a boolean `value` becomes the key `"true"`/`"false"` |
| `score`: `levels: [{label, description}]` | `criteria: ["label: description", …]`, same order |
| `safety_identifier` | drop |

| OpenAI answer (list) | VAKYN answer (object by question key) |
|---|---|
| `{type: "predicate", name, probability}` | `{type: "noul", noul}` |
| `{type: "choice", name, choice, confidence, probabilities: [{value, probability}]}` | `{type: "choice", choice, confidence, probabilities: {key: p}}` |
| `{type: "score", name, score, confidence, probabilities: [{label, probability, value}]}` | `{type: "score", score, confidence, legend, probabilities: {"0": p, …}}` |
| `{type: "refusal", name}` | none; VAKYN always answers. Code that handles refusals keeps working, it just stops seeing them |
| `usage` with `*_details`, `total_tokens` | `usage.input_tokens`, `usage.output_tokens` |

Check with the person:
- **Level order.** OpenAI documents level indices from 0; VAKYN reads the first level as the
  lowest. Confirm their levels run lowest first.
- **`value` in score probabilities.** The reference lists `value` but not what it holds; the
  mapper writes the level index. Compare with one real response from their logs.
- **Images.** Requests with images stay on the old API.
