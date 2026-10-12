# Sources: find the calls, then change them

Each section says what was checked, against which official page or package, how to find the
calls in the person's code, and what changes. Checked 2026-10-09. These services change: when
the person's code does not match what is written here, read their code and the provider's
current docs; do not fill the gap from memory.

All moves end at the same place: `POST {base}/v1/systemone` on the person's server, model
`jev-latest` (or the name from `GET /v1/models`), key `vk_…` from `vakyn keys create`.

| From | Wire format | The change | Section |
|---|---|---|---|
| Hosted Jev, official SDKs | same | base URL, key, model name | [1](#1-hosted-jev-through-the-official-sdks) |
| Hosted Jev, raw HTTP | same | URL, key, model name | [2](#2-hosted-jev-raw-http) |
| OpenRouter `/api/v1/systemone` | same | base URL, key, model name | [3](#3-openrouter) |
| OpenRouter `/api/alpha/decisions` | close | URL, key, model, drop routing fields | [3](#3-openrouter) |
| Vercel AI Gateway | same or close | depends on the path used | [4](#4-vercel-ai-gateway) |
| Cloudflare Clef on Workers AI | close | URL, key, model, response envelope | [5](#5-cloudflare-clef) |
| OpenJev or another server on `/v1/systemone` | same | base URL, key, model name | [6](#6-other-servers-on-v1systemone) |
| OpenAI Decisions API | different | field mapping | [7](#7-openai-decisions-api) |
| A framework adapter | via adapter | [adapters](adapters.md) | |
| Anything else | unknown | read their code and the provider's docs, or ask | |

## 1. Hosted Jev through the official SDKs

Checked in the package source (`typesafe-sdk` 0.7.2, `@typesafe-ai/sdk` 0.6.0) and
docs.typesafe.ai. Both SDKs read three variables: `TYPESAFE_BASE_URL` (default
`https://api.typesafe.ai`), `TYPESAFE_API_KEY`, `TYPESAFE_DEFAULT_MODEL` (default `jev-latest`).
Code options win over variables: Python `TypeSafeClient(api_key=, base_url=, model=)`,
TypeScript `new TypeSafeClient({ apiKey, baseURL, defaultModel })`, and `model` per call.

Find: `grep -rnE "typesafe_sdk|TypeSafeClient|AsyncTypeSafeClient|@typesafe-ai/sdk|system_one\(|systemOne\(|TYPESAFE_" .`
and the model names: `grep -rnE "jev-[0-9]|jev-latest|jev-preview" .`

Change, config first:
- `TYPESAFE_BASE_URL=http://127.0.0.1:8080` (root, no `/v1`), `TYPESAFE_API_KEY` = the `vk_` key.
- Model: remove hardcoded `model=` / `defaultModel` / per-call `model` that name a pinned
  hosted release (`jev-1.13.0`) or `jev-preview`; set `TYPESAFE_DEFAULT_MODEL=jev-latest`. The
  server answers an unknown name with `400 Unknown model` (seen on open-server).
- Raise `timeout` if the server runs on CPU (default 10 s per attempt).
- Before/after: [sdk_before.py](../examples/sdk_before.py), [sdk_after.py](../examples/sdk_after.py).

## 2. Hosted Jev, raw HTTP

Checked on docs.typesafe.ai (quick start, API reference): `POST https://api.typesafe.ai/v1/systemone`,
`Authorization: Bearer …`, body `{model, state, questions}`.

Find: `grep -rnE "api\.typesafe\.ai|/v1/systemone" .`

Change: the URL to `$VAKYN_BASE_URL/v1/systemone`, the key variable, the model. Move the URL
and model into config if they are literals. Code that reads the error body: open-server
errors are `{"detail": "..."}` (seen on open-server); see [differences](differences.md).
Before/after: [http_before.sh](../examples/http_before.sh), [http_after.sh](../examples/http_after.sh).

## 3. OpenRouter

Checked on openrouter.ai/docs (Jev guide, TypeSafe SDK guide, Decisions API reference).

- **`https://openrouter.ai/api/v1/systemone`**: for the official SDKs, base URL
  `https://openrouter.ai/api`, OpenRouter key. Same wire format. Change as in section 1.
  OpenRouter accepts `jev-latest`, `jev-1.13` or `typesafe/jev-1.13`; on open-server use
  `jev-latest`.
- **`POST https://openrouter.ai/api/alpha/decisions`**: same `model`, `state`, `questions`
  shape, plus OpenRouter-only fields. Map with [field maps](field-maps.md#openrouter-decisions).
  Model names `typesafe/jev-1.13`, `~typesafe/jev-latest`.

Find: `grep -rnE "openrouter\.ai/api|alpha/decisions|typesafe/jev|OPENROUTER_API_KEY" .`

## 4. Vercel AI Gateway

Checked on vercel.com/docs (TypeSafe API with AI Gateway; Decision).

- **TypeSafe-compatible path** `https://ai-gateway.vercel.sh/typesafe` (+ `/v1/systemone`),
  key `AI_GATEWAY_API_KEY`, model `typesafe-ai/jev`. Same wire format; change as in section 1.
  Drop `providerOptions` (gateway fallbacks); the response loses `provider_metadata`.
- **Gateway Decision API** `POST https://ai-gateway.vercel.sh/v1/evaluate`: `boolean` instead
  of `noul`, `probability` instead of `noul` in answers, camelCase `usage`. Map with
  [field maps](field-maps.md#ai-gateway-v1evaluate).
- **AI SDK `experimental_decide` with a model string** (`model: 'typesafe-ai/jev'`) goes
  through the gateway. Switch to the TypeSafe provider: [adapters](adapters.md#vercel-ai-sdk).
- **OpenAI-compatible path** (`https://ai-gateway.vercel.sh/v1`, `decisions.create`): treat as
  section 7.

Find: `grep -rnE "ai-gateway\.vercel\.sh|typesafe-ai/jev|experimental_decide|experimental_evaluate|decisionModel\(|AI_GATEWAY_API_KEY" .`

## 5. Cloudflare Clef

Checked on blog.cloudflare.com/clef-decision-models, developers.cloudflare.com/workers-ai/models/clef
and huggingface.co/Cloudflare/clef. Cloudflare calls the API Jev-compatible, but on Workers AI
the path is not `/v1/systemone`:

- REST: `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef`,
  `Authorization: Bearer $CLOUDFLARE_AUTH_TOKEN`; Workers binding `env.AI.run("@cf/cloudflare/clef", {...})`.
- Body `model` (`clef` or `clef-flash`), `state`, `questions` (1–64), optional `images`.
- So the SDK base-URL swap does not apply. Map with [field maps](field-maps.md#cloudflare-clef-on-workers-ai).

Find: `grep -rnE "@cf/cloudflare/clef|ai/run/|AI\.run\(|\"clef(-flash)?\"|CLOUDFLARE_AUTH_TOKEN" .`

The Hugging Face weights run through Python code in the model repo, not an HTTP server; a team
running Clef that way has its own wrapper. Read it before changing anything.

## 6. Other servers on `/v1/systemone`

A server that serves `POST /v1/systemone` with the same body needs only base URL, key and
model. Confirm it from that server's own docs or code first. Checked example: OpenJev
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
