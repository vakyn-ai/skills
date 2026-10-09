# API reference (Jev-compatible)

Base URL: the person's server, default `http://127.0.0.1:8080`. HTTPS goes through a reverse proxy.

| Method | Path | Does |
|---|---|---|
| `POST` | `/v1/systemone` | Answer questions about a state |
| `GET` | `/v1/models` | List the loaded model and the `jev-latest` alias |

Auth: `Authorization: Bearer vk_...`. Every response carries `x-typesafe-request-id`; log it.
There is no streaming and no batch endpoint: send independent requests concurrently instead.

## Request

```json
{
  "model": "jev-latest",
  "state": {"ticket": "I was charged twice this month and need one refunded."},
  "questions": {
    "team":    {"type": "choice", "instructions": "Which team should handle state.ticket?",
                "criteria": {"billing": "Charges, invoices, refunds",
                             "access": "Sign-in and permissions",
                             "other": "None of these fits"}},
    "refund":  {"type": "noul", "instructions": "Does state.ticket ask for money back?"},
    "urgency": {"type": "score", "instructions": "How soon does state.ticket need a reply?",
                "criteria": ["Can wait", "Today", "Within the hour"]}
  }
}
```

- `model`: `jev-latest` or the name from `/v1/models`.
- `state`: a string, an object or an array; never null. Every question sees all of it.
- `questions`: an object; the key is the question's name and the key you read the answer by.
  - `type`: `noul`, `choice` or `score`.
  - `instructions`: the question, in words.
  - `criteria`:
    - `choice`: required object `{option: description}`, 1–255 options (use at least 2).
    - `score`: required list of level descriptions, lowest first, 1–10 levels (use at least 2).
    - `noul`: optional `{"true": "...", "false": "..."}` to define what yes and no mean.
- No other fields. Questions in one request cannot see each other's answers.

## Response

```json
{
  "model": "VAKYN-4B",
  "answers": {
    "team":    {"type": "choice", "choice": "billing", "confidence": 0.97,
                "probabilities": {"billing": 0.98, "access": 0.01, "other": 0.01}, "stats": {}},
    "refund":  {"type": "noul", "noul": 0.93, "stats": {}},
    "urgency": {"type": "score", "score": 1.12, "legend": {"0": "Can wait", "1": "Today", "2": "Within the hour"},
                "probabilities": {"0": 0.12, "1": 0.64, "2": 0.24}, "confidence": 0.64, "stats": {}}
  },
  "usage": {"input_tokens": 98, "output_tokens": 0},
  "assets_used": null
}
```

(Numbers here show the shape; they are not a recorded answer.)

- `noul`: probability that the answer is yes. There is no separate confidence: distance from 0.5
  is the confidence.
- `choice`: the top option, its `confidence`, and `probabilities` over every option.
- `score`: the probability-weighted level (fractional), the `legend`, and `probabilities` per level.
  Round or threshold it in code; the top level is `max(probabilities)`.
- Values are rounded to 2 decimals. The same request always gets the same numbers.

## Limits

| Limit | Value |
|---|---|
| State plus the longest question | 32,768 tokens |
| State plus all questions | 65,536 tokens |
| Options per `choice` | 1–255 |
| Levels per `score` | 1–10 |
| Request body | 64 MiB |

Over a limit → `400`; nothing is cut. Rough size: 1 token ≈ 4 characters of English.

## Errors

| Status | Means | Do |
|---|---|---|
| `400` | over a limit, or an unknown model | shrink the state, split questions, check `model` |
| `401` | missing, wrong or revoked key | check the env variable |
| `422` | body does not match the schema | run the pre-send checklist |
| `429` | queue full (`retry-after`, `retry-after-ms`) | wait and retry; lower concurrency |
| `503` | model still loading (`retry-after`) | wait |
| `500` | server error | log the request id; retry once |
