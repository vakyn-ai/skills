# Sources: find the calls, then rewrite them

Each section says what was checked, against which official page or package, how to find the
calls in the person's code, and what changes. The names, packages and variables below are the
old service's: they are here so the calls can be found. Checked 2026-10-09. These services change: when
the person's code does not match what is written here, read their code and the provider's
current docs; do not fill the gap from memory.

All moves end at the same place: a direct HTTP call, `POST {base}/v1/systemone` with
`Authorization: Bearer $VAKYN_API_KEY` and a `{state, questions}` body, from the Python standard
library, `fetch` or curl ([HTTP guide](../../get-started/references/http.md)). `{base}` is
`VAKYN_BASE_URL`: `https://api.vakyn.com` by default (VAKYN Cloud, key from vakyn.com/console/keys,
`model` left out so `vakyn-max` answers), or the person's own open-server (key from
`vakyn keys create`, `model` the name its `GET /v1/models` lists).

| From | Body | The change | Section |
|---|---|---|---|
| Hosted Jev, `typesafe-sdk` / `@typesafe-ai/sdk` | same | SDK calls → one HTTP function; key, model | [1](#1-hosted-jev-through-the-typesafe-sdks) |
| Hosted Jev, raw HTTP | same | URL, key, model name | [2](#2-hosted-jev-raw-http) |
| OpenRouter `/api/v1/systemone` | same | SDK or HTTP call → VAKYN HTTP call; key, model | [3](#3-openrouter) |
| OpenRouter `/api/alpha/decisions` | close | URL, key, model, drop routing fields | [3](#3-openrouter) |
| Vercel AI Gateway | same or close | depends on the path used | [4](#4-vercel-ai-gateway) |
| Cloudflare Clef on Workers AI | close | URL, key, model, response envelope | [5](#5-cloudflare-clef) |
| OpenJev or another server on `/v1/systemone` | same | URL, key, model name | [6](#6-other-servers-on-v1systemone) |
| OpenAI Decisions API | different | field mapping | [7](#7-openai-decisions-api) |
| A framework adapter | via adapter | [adapters](adapters.md) | |
| Anything else | unknown | read their code and the provider's docs, or ask | |

## 1. Hosted Jev through the TypeSafe SDKs

Checked in the package source (`typesafe-sdk` 0.7.2, `@typesafe-ai/sdk` 0.6.0) and
docs.typesafe.ai. Both SDKs read three variables: `TYPESAFE_BASE_URL` (default
`https://api.typesafe.ai`), `TYPESAFE_API_KEY`, `TYPESAFE_DEFAULT_MODEL` (default `jev-latest`).
Code options win over variables: Python `TypeSafeClient(api_key=, base_url=, model=)`,
TypeScript `new TypeSafeClient({ apiKey, baseURL, defaultModel })`, and `model` per call.

Find: `grep -rnE "typesafe_sdk|TypeSafeClient|AsyncTypeSafeClient|@typesafe-ai/sdk|system_one\(|systemOne\(|TYPESAFE_" .`
and the model names: `grep -rnE "jev-[0-9]|jev-latest|jev-preview" .`

Change: rewrite the SDK calls as direct HTTP calls.
- One `decide(state, questions)` function with the standard library (Python) or `fetch`
  (TypeScript), reading `VAKYN_API_KEY` and `VAKYN_BASE_URL` (root, no `/v1`; their own server's
  URL when self-hosted). The client object and the SDK import go.
- `Choice(...)`, `Noul(...)`, `Score(...)` (Python) and `choice()`, `noul()`, `score()` (TypeScript)
  become plain JSON questions with the same `instructions` and `criteria`. Typed results become
  JSON lookups: [SDK calls](field-maps.md#hosted-jev-sdk-calls).
- Model: drop pinned hosted names (`jev-1.13.0`), `jev-preview` and `jev-latest`. On VAKYN Cloud
  leave `model` out (`vakyn-max`), or `vakyn-fast` from config when price matters most; on
  open-server the name from `/v1/models`. An unknown name gets `400`.
- Write out what the SDK did: a timeout (the SDKs used 10 s per attempt; raise it if their own
  server runs on CPU), a bounded retry on `408`, `429`, `5xx` honouring `retry-after`, and a thread
  pool or `Promise.all` where `AsyncTypeSafeClient` or many concurrent calls were used.
- The SDK package stays in their dependencies only while the old path is kept for rollback.
- Before/after: [sdk_before.py](../examples/sdk_before.py), [sdk_after.py](../examples/sdk_after.py).

## 2. Hosted Jev, raw HTTP

Checked on docs.typesafe.ai (quick start, API reference): `POST https://api.typesafe.ai/v1/systemone`,
`Authorization: Bearer …`, body `{model, state, questions}`.

Find: `grep -rnE "api\.typesafe\.ai|/v1/systemone" .`

Change: the URL to `$VAKYN_BASE_URL/v1/systemone`, the key variable to `VAKYN_API_KEY`, the
model (left out on VAKYN Cloud; the `/v1/models` name on open-server). Move the URL
and model into config if they are literals. Code that reads the error body: VAKYN errors have a
`detail` field (a message on open-server, `{"error_type", "message"}` for VAKYN Cloud's own
errors); see [differences](differences.md).
Before/after: [http_before.sh](../examples/http_before.sh), [http_after.sh](../examples/http_after.sh).

## 3. OpenRouter

Checked on openrouter.ai/docs (Jev guide, TypeSafe SDK guide, Decisions API reference).

- **`https://openrouter.ai/api/v1/systemone`**: used through the TypeSafe SDKs with base URL
  `https://openrouter.ai/api` and an OpenRouter key, or over HTTP. Same body. Rewrite as in
  section 1 (SDK) or 2 (HTTP). OpenRouter accepts `jev-latest`, `jev-1.13` or
  `typesafe/jev-1.13`; on VAKYN leave `model` out (VAKYN Cloud) or use the `/v1/models` name.
- **`POST https://openrouter.ai/api/alpha/decisions`**: same `model`, `state`, `questions`
  shape, plus OpenRouter-only fields. Map with [field maps](field-maps.md#openrouter-decisions).
  Model names `typesafe/jev-1.13`, `~typesafe/jev-latest`.

Find: `grep -rnE "openrouter\.ai/api|alpha/decisions|typesafe/jev|OPENROUTER_API_KEY" .`

## 4. Vercel AI Gateway

Checked on vercel.com/docs (TypeSafe API with AI Gateway; Decision).

- **TypeSafe path** `https://ai-gateway.vercel.sh/typesafe` (+ `/v1/systemone`),
  key `AI_GATEWAY_API_KEY`, model `typesafe-ai/jev`. Same body; rewrite as in section 1 or 2.
  Drop `providerOptions` (gateway fallbacks); the response loses `provider_metadata`.
- **Gateway Decision API** `POST https://ai-gateway.vercel.sh/v1/evaluate`: `boolean` instead
  of `noul`, `probability` instead of `noul` in answers, camelCase `usage`. Map with
  [field maps](field-maps.md#ai-gateway-v1evaluate).
- **AI SDK `experimental_decide` with a model string** (`model: 'typesafe-ai/jev'`) goes
  through the gateway. Rewrite it as a `fetch` call: [adapters](adapters.md#vercel-ai-sdk).
- **OpenAI-compatible path** (`https://ai-gateway.vercel.sh/v1`, `decisions.create`): treat as
  section 7.

Find: `grep -rnE "ai-gateway\.vercel\.sh|typesafe-ai/jev|experimental_decide|experimental_evaluate|decisionModel\(|AI_GATEWAY_API_KEY" .`

## 5. Cloudflare Clef

Checked on blog.cloudflare.com/clef-decision-models, developers.cloudflare.com/workers-ai/models/clef
and huggingface.co/Cloudflare/clef. Clef takes the same state and questions, but on Workers AI
the path is not `/v1/systemone`:

- REST: `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef`,
  `Authorization: Bearer $CLOUDFLARE_AUTH_TOKEN`; Workers binding `env.AI.run("@cf/cloudflare/clef", {...})`.
- Body `model` (`clef` or `clef-flash`), `state`, `questions` (1–64), optional `images`.
- Map with [field maps](field-maps.md#cloudflare-clef-on-workers-ai).

Find: `grep -rnE "@cf/cloudflare/clef|ai/run/|AI\.run\(|\"clef(-flash)?\"|CLOUDFLARE_AUTH_TOKEN" .`

The Hugging Face weights run through Python code in the model repo, not an HTTP server; a team
running Clef that way has its own wrapper. Read it before changing anything.

## 6. Other servers on `/v1/systemone`

A server that serves `POST /v1/systemone` with the same body: VAKYN takes the same state and
questions, so the body moves over as it is and the call is rewritten as in section 1 or 2.
Confirm the body from that server's own docs or code first. Checked example: OpenJev
(github.com/razorback16/openjev, README) serves `POST /v1/systemone` and `GET /v1/models`, with
model ids such as `openjev-latest`; its hosted endpoint is `https://api.codiv.ai/v1/systemone`.

Find: `grep -rnE "/v1/systemone|TYPESAFE_BASE_URL|codiv|openjev" .` and any base URL in config.

## 7. OpenAI Decisions API

Checked on developers.openai.com (Decisions guide; API reference "Create a decision").
`POST /v1/decisions`, SDK `client.decisions.create(...)`, model `gpt-6-luna`. The shape differs:
`input` instead of `state`, `questions` is a list, `predicate` instead of `noul`, choices and
levels are objects, answers come back as a list, and a question can come back as `refusal`.
Map with [field maps](field-maps.md#openai-decisions-api) and the runnable
[openai_decisions_map.py](../examples/openai_decisions_map.py).

Find: `grep -rnE "decisions\.create|/v1/decisions|gpt-6-luna|\"predicate\"" .`

## Not checked

Anything not above: other gateways, other SDK languages, other adapters, request fields not
named here. Read the person's code and the provider's current docs, or ask the person for the
docs link. Write no mapping for a field you have not seen documented.
