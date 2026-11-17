# What changes when the calls move to VAKYN

Go through this list with the person before any code changes. Each row says what to look for
in their code. The VAKYN side is in the [API reference](../../get-started/references/api.md); the old
side is what the provider documents (checked 2026-10-09) or what their code shows. VAKYN Cloud is
the default target; the open-server column applies when they run their own.

| Topic | On VAKYN Cloud | On the person's open-server | Look in their code for |
|---|---|---|---|
| Client | plain HTTP: one `POST /v1/systemone` from the standard library, `fetch` or curl; nothing to install | same | SDK and adapter imports (`typesafe_sdk`, `@typesafe-ai/sdk`, `@ai-sdk/typesafe-ai`, …): their calls are rewritten as HTTP calls |
| Base URL | `VAKYN_BASE_URL`, default `https://api.vakyn.com` (root, no `/v1`) | their server's root, default `http://localhost:8080`; HTTPS through their reverse proxy | literals in code; whether the setting includes `/v1` (only the AI SDK provider's does) |
| Keys | `VAKYN_API_KEY`; start with `vk_`, made and revoked at [vakyn.com/console/keys](https://vakyn.com/console/keys) | start with `vk_`, made with `vakyn keys create`, revoked there | where the old key lives (env var, secret store, CI); the new one goes to the same kind of place, never into code. A key works only where it was made |
| Model names | leave `model` out (`vakyn-max` answers), or `vakyn-fast`; alias `vakyn-latest`; anything else `400` | the name from `GET /v1/models`; `model` is required; anything else `400 Unknown model` | the old service's names, which all go: `jev-latest`, pinned hosted names (`jev-1.13.0`), `jev-preview`, provider prefixes (`typesafe/…`, `~typesafe/…`, `typesafe-ai/jev`), `clef`, `gpt-6-luna`, `openjev-latest` |
| Limits | state plus the longest question ≤ 32,768 tokens; state plus all questions ≤ 65,536; 1–255 options; 1–10 levels; body ≤ 64 MiB; over a limit → `400`, nothing is cut | same | requests near the limits; code that relied on a provider that accepts more (Clef lists a 65,536-token window and up to 64 questions) |
| Extra fields | none in the API; do not rely on unknown fields being ignored | same | routing, tracing and fallback fields (`provider`, `session_id`, `user`, `trace`, `providerOptions`, `safety_identifier`): remove them |
| Images | no image field | same | `images`, `input_image`: those requests stay on the old service |
| Errors | `{"detail": {"error_type", "message"}}` for its own errors; `400`, `401`, `402` no balance, `422`, `429` rate limit with `retry-after`, `502`, `503` | `{"detail": "..."}`; `400` limit or model, `401` key, `422` schema, `429` queue full with `retry-after`, `503` loading with `retry-after`, `500` | code that parses error bodies or status codes the old service used (hosted docs list `529` for overload; AI Gateway documents `{message, error_type}`) |
| Retries | nothing retries for them: the HTTP function retries `408`, `429`, `5xx` and connection errors a few times, waiting `retry-after` seconds when given | same | code that relied on the old SDK's automatic retries (the TypeSafe SDKs retried these); hand-written loops stay bounded and honour `retry-after` |
| Load | 60 requests per second per key, then `429` | one queue on their machine (`--max-queue`, default 32), then `429` | concurrency settings tuned for another limit; keep under the new one |
| Streaming and batch | no streaming, no batch endpoint: send independent requests concurrently (a thread pool, `Promise.all`) | same | batch or streaming calls, `AsyncTypeSafeClient` with `asyncio.gather`; replace with bounded concurrency (`batch` skill for files and tables) |
| Cost | per input token from a prepaid balance (output free, errors free); price from `GET /v1/models`, never from memory | their own hardware | code reading `usage.cost` or gateway cost metadata (no such field); `usage.input_tokens` is there |
| Speed | measure it in the side-by-side run | depends on their hardware and model file; measure it | timeouts sized for the old service (the TypeSafe SDKs used 10 s per attempt); set one on every call |
| Answers | a different model: answers can differ from the old service | same | anything that assumes the same numbers; thresholds tuned on the old model must be checked again |
| Request id | the `x-vakyn-request-id` response header | open-server versions that send only `x-typesafe-request-id` (its earlier name): read that one there | logs keyed on the old provider's ids (`id`, `generationId`, the SDKs' `request_id`) |

Never say how the answers compare in quality, speed or price with the old service before the
person's own side-by-side run has measured it, and then only for their records.
