# Calling VAKYN from code

VAKYN has no SDK of its own. Use TypeSafe's official SDKs and point them at VAKYN Cloud
(`https://api.vakyn.com`) or at the person's own server. Plain HTTP works too.

| Language | Package | Point it at VAKYN |
|---|---|---|
| Python 3.10+ | `pip install typesafe-sdk` | `TYPESAFE_BASE_URL`, `TYPESAFE_API_KEY` |
| TypeScript / JavaScript | `npm install @typesafe-ai/sdk` | same variables, or `baseURL` / `apiKey` |
| Anything else | HTTP `POST /v1/systemone` | `Authorization: Bearer $VAKYN_API_KEY` |

```sh
TYPESAFE_BASE_URL=https://api.vakyn.com   # or the person's own server, e.g. http://localhost:8080
TYPESAFE_API_KEY=vk_...                   # from vakyn.com/console/keys, or `vakyn keys create`
```

Base URL is the root without `/v1`. Model: `jev-latest` (the SDK default), which works on both.
Both SDKs also read `TYPESAFE_DEFAULT_MODEL`: leave it unset, or set it to a name from
`/v1/models` (on VAKYN Cloud, `vakyn-fast` is the cheaper option).

## Python

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient(timeout=30.0)  # reads TYPESAFE_BASE_URL and TYPESAFE_API_KEY
result = client.system_one(
    state={"ticket": ticket_text},
    questions={
        "team": Choice(
            instructions="Which team should handle the ticket?",
            criteria={"billing": "Charges, invoices, refunds",
                      "access": "Sign-in and permissions",
                      "other": "None of these fits"},
        ),
        "refund": Noul(instructions="Does the ticket ask for money back?"),
        "urgency": Score(instructions="How soon does the ticket need a reply?",
                         criteria=["Can wait", "Today", "Within the hour"]),
    },
)
team = result.choices["team"]          # .choice, .confidence, .probabilities
refund = result.nouls["refund"].noul   # probability of yes
urgency = result.scores["urgency"]     # .score, .legend, .probabilities (integer keys)
print(result.request_id)
```

Many records: `AsyncTypeSafeClient` with `asyncio.gather` under a cap (a semaphore). VAKYN Cloud
takes 60 requests per second per key; open-server queues up to `--max-queue` requests (default
32). Over either, the answer is `429` and the SDK retries after the delay it asks for. On VAKYN
Cloud every answered request spends balance: estimate the cost first
([cost](cloud.md#cost)).

## TypeScript

```ts
import { choice, noul, score, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient({ timeout: 30_000 }); // reads TYPESAFE_BASE_URL and TYPESAFE_API_KEY
const { answers } = await client.systemOne({
  state: { ticket: ticketText },
  questions: {
    team: choice("Which team should handle the ticket?", {
      billing: "Charges, invoices, refunds",
      access: "Sign-in and permissions",
      other: "None of these fits",
    }),
    refund: noul("Does the ticket ask for money back?"),
    urgency: score("How soon does the ticket need a reply?", ["Can wait", "Today", "Within the hour"]),
  },
});
console.log(answers.team.choice, answers.refund.noul, answers.urgency.score);
```

## Errors and retries

Both SDKs retry `408`, `429`, `5xx` and connection errors twice with backoff and honor `retry-after`.
Every other non-2xx (such as `402`, no balance left on VAKYN Cloud) raises an error with `status`,
`body` and `request_id`:

- Python: `TypeSafeBadRequestError` (400), `TypeSafeAuthenticationError` (401),
  `TypeSafeUnprocessableEntityError` (422), `TypeSafeRateLimitError` (429 after retries),
  `TypeSafeAPIConnectionError` (server unreachable or timeout).
- TypeScript: `BadRequestError`, `AuthenticationError`, `UnprocessableEntityError`,
  `RateLimitError`, `APIConnectionError`.

The default timeout is 10 seconds per attempt. On CPU, or with long documents and many questions,
raise it rather than letting retries pile up.

## Differences from the hosted Jev service

- Model names: use `jev-latest` or a name from `/v1/models`; dated hosted model names do not exist here.
- Keys start with `vk_` and come from the VAKYN console or the person's own server; a key works
  only where it was made.
- Requests, answers and limits match.
