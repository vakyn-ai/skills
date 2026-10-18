# VAKYN Cloud: key, settings, first check

VAKYN Cloud is the hosted API at `https://api.vakyn.com`. There is nothing to install or run.
Goal: an API key in an environment variable and a first answer. Docs:
[quickstart](https://vakyn.com/docs/quickstart), [models](https://vakyn.com/docs/models),
[API reference](https://vakyn.com/docs/api).

## Get a key

The person does these steps themselves, in the browser:

1. Sign in at [vakyn.com/console](https://vakyn.com/console) with Google, GitHub or X. They get
   an organization of their own.
2. Add a prepaid balance under [Billing](https://vakyn.com/console/billing), or redeem a code
   there. There is no free tier; calls are refused with `402` when the balance is empty.
3. Create a key under [API keys](https://vakyn.com/console/keys). It starts with `vk_` and is
   shown once.

Ask them to put the key in their environment themselves, for example a git-ignored `.env` file:

```sh
VAKYN_BASE_URL=https://api.vakyn.com
VAKYN_API_KEY=vk_...
# for the official SDKs:
TYPESAFE_BASE_URL=https://api.vakyn.com
TYPESAFE_API_KEY=vk_...
```

Check `.env` is in `.gitignore` before they save it. Never ask them to paste the key into the
chat. Do not open or print `.env`; load it inside the command that needs it:

```sh
set -a; . ./.env; set +a; [ -n "$VAKYN_API_KEY" ] && echo set
```

A key pasted into the chat anyway: do not repeat it; they revoke it on the
[API keys](https://vakyn.com/console/keys) page and create a new one.

## Check

```sh
curl -s https://api.vakyn.com/v1/models
```

Free, and it needs no key. It lists the models, the aliases and each model's live price per
billion input tokens (`price_per_billion_input_tokens`). It does not check the key: the
[first call](../SKILL.md#first-call) does. A `401` there means a missing, wrong or revoked key,
and costs nothing.

## Models

| `model` | Use |
|---|---|
| `vakyn-max` | the default when `model` is left out |
| `vakyn-fast` | the cheaper option, for yes/no and score questions on short documents |
| `jev-latest`, `vakyn-latest` | aliases for `vakyn-max` |

`model` is optional on VAKYN Cloud and required on open-server. Write `jev-latest` in code that
should run on both, and mention `vakyn-fast` when price matters most.

## Cost

- Billing is per input token (`usage.input_tokens`), from the prepaid balance. Output is free and
  errors cost nothing.
- Never write a price into text, code or a report from memory. Read it from `GET /v1/models`, or
  link [vakyn.com/docs/models](https://vakyn.com/docs/models).
- Every question in a request is answered from one reading of the state, so put independent
  questions about the same record in one request.
- **Before more than a handful of requests**, estimate: input tokens per request (about 4
  characters of English per token, or `usage.input_tokens` from a pilot) × number of requests ×
  price per billion from `/v1/models` ÷ 1,000,000,000. Show the estimate and wait for a yes.

## Rate limit

60 requests per second per key. Over it, `429` with `retry-after`; the official SDKs wait and
retry. Keep bulk runs under it: bounded concurrency, summed over every process using the key.
Need more: [vakyn.com/contact](https://vakyn.com/contact).

## What else differs from open-server

| Topic | VAKYN Cloud |
|---|---|
| Keys | from the console; a key works only where it was made |
| Errors | `402` no balance left; `429` rate limit; `502` and `503` from the model service; bodies `{"detail": {"error_type", "message"}}` |
| Request id | `x-vakyn-request-id`, plus `x-typesafe-request-id` |
| Same | requests, answers, limits (32,768 / 65,536 tokens, 255 options, 10 levels), SDKs |

Moving between VAKYN Cloud and open-server is one change: the base URL and the key.
Running it on the person's own servers: [self-hosting](self-hosting.md).
