# What changes when the server is your own

Go through this list with the person before any code changes. Each row says what to look for
in their code. The VAKYN side is in the [API reference](../../vakyn/references/api.md); the old
side is what the provider documents (checked 2026-10-09) or what their code shows.

| Topic | On the person's open-server | Look in their code for |
|---|---|---|
| Model names | `jev-latest`, or the name from `GET /v1/models`. Any other name gets `400 Unknown model` | pinned hosted names (`jev-1.13.0`), `jev-preview`, provider prefixes (`typesafe/…`, `~typesafe/…`, `typesafe-ai/jev`), `clef`, `gpt-6-luna`, `openjev-latest` |
| Keys | start with `vk_`, made with `vakyn keys create` on their server; revoked there | where the old key lives (env var, secret store, CI); the new one goes to the same kind of place, never into code |
| Base URL | server root, default `http://127.0.0.1:8080`; HTTPS through their reverse proxy | literals in code; whether the setting includes `/v1` (only the AI SDK provider's does) |
| Limits | state plus the longest question ≤ 32,768 tokens; state plus all questions ≤ 65,536; 1–255 options; 1–10 levels; body ≤ 64 MiB; over a limit → `400`, nothing is cut | requests near the limits; code that relied on a provider that accepts more (Clef lists a 65,536-token window and up to 64 questions) |
| Extra fields | none in the API. Open-server ignored an unknown top-level field in a test; do not rely on that | routing, tracing and fallback fields (`provider`, `session_id`, `user`, `trace`, `providerOptions`, `safety_identifier`): remove them |
| Images | no image field | `images`, `input_image`: those requests stay on the old service |
| Errors | `{"detail": "..."}` body; `400` limit or model, `401` key, `422` schema, `429` queue full with `retry-after`, `503` loading with `retry-after`, `500` | code that parses error bodies or status codes the old service used (hosted docs list `529` for overload; AI Gateway documents `{message, error_type}`) |
| Retries | the official SDKs retry `408`, `429`, `5xx` and connection errors and honor `retry-after` | hand-written retry loops; keep them bounded and honoring `retry-after` |
| Load | one queue on their machine (`--max-queue`); a full queue answers `429` | concurrency settings tuned for a hosted rate limit; lower them |
| Streaming and batch | no streaming, no batch endpoint: send independent requests concurrently | batch or streaming calls; replace with bounded concurrency (`vakyn-batch` skill for files and tables) |
| Speed | depends on their hardware and model file; measure it in the side-by-side run | timeouts sized for the hosted service; the SDK default is 10 s per attempt |
| Answers | a different model: answers can differ from the old service | anything that assumes the same numbers; thresholds tuned on the old model must be checked again |
| Request id | `x-typesafe-request-id` header (`request_id` in the SDKs) | logs keyed on provider ids (`id`, `generationId`) |
| Cost fields | none | code reading `usage.cost` or gateway cost metadata |

Never say how the answers compare in quality, speed or price with the old service before the
person's own side-by-side run has measured it, and then only for their records on their machine.
