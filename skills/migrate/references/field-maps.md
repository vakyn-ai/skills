# Field maps to `/v1/systemone`

Only fields shown in the provider's official docs (checked 2026-10-09) are mapped. A field the
person's code uses that is not here: read the provider's current docs, or ask. Never guess
what an unknown field does.

Target shape: [API reference](../../get-started/references/api.md). Every mapped request passes the
[pre-send checklist](../../get-started/references/checklist.md). Every mapped request is sent with
a direct HTTP call ([HTTP guide](../../get-started/references/http.md)).

## Hosted Jev SDK calls

`typesafe-sdk` (Python) and `@typesafe-ai/sdk` (TypeScript) send the same body VAKYN takes, so
the request moves over as it is. What changes is the code around it: the SDK's objects become
plain JSON. Checked in the package source (`typesafe-sdk` 0.7.2, `@typesafe-ai/sdk` 0.6.0).

| Old SDK code | Direct HTTP to VAKYN |
|---|---|
| `TypeSafeClient(api_key=, base_url=, model=, timeout=)`, `new TypeSafeClient({...})` | one `decide(state, questions)` function: `VAKYN_API_KEY`, `VAKYN_BASE_URL`, a timeout on the call |
| `client.system_one(state=, questions=)`, `client.systemOne({state, questions})` | `POST {base}/v1/systemone` with `{"state", "questions"}`; read `["answers"]` |
| `Choice(instructions=, criteria={...})`, `choice(instructions, criteria)` | `{"type": "choice", "instructions": ..., "criteria": {...}}` |
| `Noul(instructions=, criteria=)`, `noul(...)` | `{"type": "noul", "instructions": ...}` (plus `criteria` `{true, false}` if it had one) |
| `Score(instructions=, criteria=[...])`, `score(...)` | `{"type": "score", "instructions": ..., "criteria": [...]}` |
| `result.choices[q].choice`, `.confidence`, `.probabilities` | `answers[q]["choice"]`, `["confidence"]`, `["probabilities"]` |
| `result.nouls[q].noul` | `answers[q]["noul"]` (probability of yes) |
| `result.scores[q].score`, `.legend`, `.probabilities` (integer keys) | `answers[q]["score"]`, `["legend"]`, `["probabilities"]` (string keys `"0"`, `"1"`, …) |
| TypeScript `{ answers }` from `systemOne`, `answers.q.choice` | the same `answers` object from the JSON body |
| `result.request_id`, `.withResponse().requestId` | the `x-vakyn-request-id` response header |
| `result.model`, `result.usage` | `body["model"]`, `body["usage"]["input_tokens"]` |
| SDK errors (`APIStatusError`, …) | non-2xx status with JSON `{"detail": ...}`; Python `urllib.error.HTTPError` (`e.code`, `e.headers`, `e.read()`) |
| automatic retries of `408`, `429`, `5xx` | a small loop: up to 3 retries, sleeping `retry-after` seconds (or 1–2 s) |
| `AsyncTypeSafeClient` + `asyncio.gather` | `concurrent.futures.ThreadPoolExecutor` with a cap; `Promise.all` over batches in TypeScript |
| `model="jev-latest"`, `TYPESAFE_DEFAULT_MODEL` | leave out (`vakyn-max` answers); own open-server: the name from `/v1/models` |

Example: [sdk_before.py](../examples/sdk_before.py) → [sdk_after.py](../examples/sdk_after.py).

## OpenRouter decisions

`POST https://openrouter.ai/api/alpha/decisions` → `POST {base}/v1/systemone`.
Example: [openrouter-decisions.before.json](../examples/openrouter-decisions.before.json).

| OpenRouter request | VAKYN |
|---|---|
| `model` `typesafe/jev-1.13`, `~typesafe/jev-latest` | leave out (`vakyn-max` answers); own open-server: the name from `/v1/models` |
| `state`, `questions` (same `type`, `instructions`, `criteria`) | unchanged |
| `provider`, `session_id`, `user`, `trace` | drop (OpenRouter routing and tracing) |

| OpenRouter response | VAKYN |
|---|---|
| `id` | none; use the `x-vakyn-request-id` header |
| `provider`, `usage.cost` | none |
| `model`, `answers`, `usage.input_tokens`, `usage.output_tokens` | same |

## AI Gateway `/v1/evaluate`

`POST https://ai-gateway.vercel.sh/v1/evaluate` → `/v1/systemone`.

| Gateway | VAKYN |
|---|---|
| `model` `typesafe-ai/jev` | leave out (`vakyn-max` answers); own open-server: the name from `/v1/models` |
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
| `model` `clef`, `clef-flash` | leave out (`vakyn-max` answers); own open-server: the name from `/v1/models` |
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
| `model` `gpt-6-luna` | leave out (`vakyn-max` answers); own open-server: the name from `/v1/models` |
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
