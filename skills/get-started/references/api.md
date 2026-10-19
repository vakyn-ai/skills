# API reference (Jev-compatible)

VAKYN Cloud and open-server serve the same API. Full reference: [vakyn.com/docs/api](https://vakyn.com/docs/api).

| | VAKYN Cloud | Self-hosted (open-server) |
|---|---|---|
| Base URL | `https://api.vakyn.com` | the person's server, default `http://localhost:8080`; HTTPS through a reverse proxy |
| Key | from [vakyn.com/console/keys](https://vakyn.com/console/keys) | `vakyn keys create` or its dashboard |
| `model` | optional: `vakyn-max` (default), `vakyn-fast`, aliases `jev-latest`, `vakyn-latest` | required: `jev-latest` or the name from `/v1/models` |
| Cost | per input token from a prepaid balance; output free, errors free | the person's own hardware |
| Load | 60 requests per second per key, then `429` | `--max-queue` requests at once (default 32), then `429` |

Base URLs have no `/v1`. A key works only where it was made.

| Method | Path | Does |
|---|---|---|
| `POST` | `/v1/systemone` | Answer questions about a state |
| `GET` | `/v1/models` | List the models and aliases (on VAKYN Cloud with live prices, no key needed) |

Auth: `Authorization: Bearer vk_...`. Every response carries `x-typesafe-request-id` (VAKYN Cloud
also sends the same id as `x-vakyn-request-id`); log it.
There is no streaming and no batch endpoint: send independent requests concurrently instead.

## Request

```json
{
  "model": "jev-latest",
  "state": {"ticket": "I was charged twice this month and need one refunded."},
  "questions": {
    "team":    {"type": "choice", "instructions": "Which team should handle the ticket?",
                "criteria": {"billing": "Charges, invoices, refunds",
                             "access": "Sign-in and permissions",
                             "other": "None of these fits"}},
    "refund":  {"type": "noul", "instructions": "Does the ticket ask for money back?"},
    "urgency": {"type": "score", "instructions": "How soon does the ticket need a reply?",
                "criteria": ["Can wait", "Today", "Within the hour"]}
  }
}
```

- `model`: `jev-latest` runs on both; on VAKYN Cloud also `vakyn-max` or `vakyn-fast`, or leave it
  out. Anything else is a `400`.
- `state`: a string, an object or an array; never null. Every question sees all of it.
- `questions`: an object; the key is the question's name and the key you read the answer by.
  - `type`: `noul`, `choice` or `score`.
  - `instructions`: the question, in words. A string, or an object or list (shown to the model
    as `key: value` and `- item` lines). It must carry the whole question: the question's name
    is never sent to the model.
  - `criteria`:
    - `choice`: required object `{option: description}`, 1–255 options (use at least 2). The
      option name is sent with its description; a description may be a string, object or list.
    - `score`: required list of level descriptions, lowest first, 1–10 levels (use at least 2).
      A level may be a string, object or list.
    - `noul`: optional `{"true": "...", "false": "..."}` to define what yes and no mean.
- No other fields. Questions in one request cannot see each other's answers.

## Response

```json
{
  "model": "VAKYN-4B",
  "answers": {
    "team":    {"type": "choice", "choice": "billing", "confidence": 1.0,
                "probabilities": {"billing": 1.0, "access": 0.0, "other": 0.0}, "stats": {}},
    "refund":  {"type": "noul", "noul": 1.0, "stats": {}},
    "urgency": {"type": "score", "score": 0.93, "legend": {"0": "Can wait", "1": "Today", "2": "Within the hour"},
                "probabilities": {"0": 0.23, "1": 0.62, "2": 0.15}, "confidence": 0.43, "stats": {}}
  },
  "usage": {"input_tokens": 87, "output_tokens": 0},
  "assets_used": null
}
```

(The answer VAKYN-4B gave to the request above. `model` names the model that answered; on VAKYN
Cloud, `vakyn-max` or `vakyn-fast`.)

- `noul`: probability that the answer is yes. There is no separate confidence: distance from 0.5
  is the confidence.
- `choice`: the top option, its `confidence`, and `probabilities` over every option.
- `score`: the probability-weighted level (fractional), the `legend`, and `probabilities` per level.
  Round or threshold it in code; the top level is `max(probabilities)`.
- Values are rounded to 2 decimals. Answers are not sampled: a request sent alone repeats exactly.
  Under concurrent load the numbers can differ slightly between runs (measured up to 0.04 with 8
  in flight). Keep thresholds away from knife-edges and re-check rows that sit close to one.

## Limits

| Limit | Value |
|---|---|
| State plus the longest question | 32,768 tokens |
| State plus all questions | 65,536 tokens |
| Options per `choice` | 1–255 |
| Levels per `score` | 1–10 |
| Request body | 64 MiB |
| Requests per second (VAKYN Cloud) | 60 per key |
| Requests at once (open-server) | `--max-queue`, default 32 |

Over a limit → `400`; nothing is cut. Rough size: 1 token ≈ 4 characters of English.

## Errors

| Status | Means | Do |
|---|---|---|
| `400` | over a limit, or an unknown model | shrink the state, split questions, check `model` |
| `401` | missing, wrong or revoked key | check the env variable, and that the key was made where the base URL points |
| `402` | VAKYN Cloud: no balance left (costs nothing) | top up or redeem a code at [vakyn.com/console/billing](https://vakyn.com/console/billing) |
| `422` | body does not match the schema | run the pre-send checklist |
| `429` | VAKYN Cloud: over 60 requests per second per key; open-server: queue full (`retry-after`, `retry-after-ms`) | wait and retry; lower concurrency |
| `502` | VAKYN Cloud: the model service sent an answer that could not be read | log the request id; retry once |
| `503` | open-server: model still loading (`retry-after`); VAKYN Cloud: model service not available | wait and retry |
| `500` | server error | log the request id; retry once |

Error bodies have a `detail` field: a message on open-server, `{"error_type", "message"}` on VAKYN
Cloud for its own errors. VAKYN Cloud never charges for an error.
