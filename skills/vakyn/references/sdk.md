# Calling VAKYN from code

VAKYN has no SDK of its own. Use TypeSafe's official SDKs and point them at the server. Plain HTTP
works too.

| Language | Package | Point it at the server |
|---|---|---|
| Python 3.10+ | `pip install typesafe-sdk` | `TYPESAFE_BASE_URL`, `TYPESAFE_API_KEY` |
| TypeScript / JavaScript | `npm install @typesafe-ai/sdk` | same variables, or `baseURL` / `apiKey` |
| Anything else | HTTP `POST /v1/systemone` | `Authorization: Bearer $VAKYN_API_KEY` |

Base URL is the server root without `/v1`. Model: `jev-latest` (the SDK default).

## Python

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient(timeout=30.0)  # reads TYPESAFE_BASE_URL and TYPESAFE_API_KEY
result = client.system_one(
    state={"ticket": ticket_text},
    questions={
        "team": Choice(
            instructions="Which team should handle state.ticket?",
            criteria={"billing": "Charges, invoices, refunds",
                      "access": "Sign-in and permissions",
                      "other": "None of these fits"},
        ),
        "refund": Noul(instructions="Does state.ticket ask for money back?"),
        "urgency": Score(instructions="How soon does state.ticket need a reply?",
                         criteria=["Can wait", "Today", "Within the hour"]),
    },
)
team = result.choices["team"]          # .choice, .confidence, .probabilities
refund = result.nouls["refund"].noul   # probability of yes
urgency = result.scores["urgency"]     # .score, .legend, .probabilities (integer keys)
print(result.request_id)
```

Many records: `AsyncTypeSafeClient` with `asyncio.gather`; the server queues up to `--max-queue`
requests and the SDK retries `429` after the delay the server asks for.

## TypeScript

```ts
import { choice, noul, score, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient({ timeout: 30_000 }); // reads TYPESAFE_BASE_URL and TYPESAFE_API_KEY
const { answers } = await client.systemOne({
  state: { ticket: ticketText },
  questions: {
    team: choice("Which team should handle state.ticket?", {
      billing: "Charges, invoices, refunds",
      access: "Sign-in and permissions",
      other: "None of these fits",
    }),
    refund: noul("Does state.ticket ask for money back?"),
    urgency: score("How soon does state.ticket need a reply?", ["Can wait", "Today", "Within the hour"]),
  },
});
console.log(answers.team.choice, answers.refund.noul, answers.urgency.score);
```

## Errors and retries

Both SDKs retry `408`, `429`, `5xx` and connection errors twice with backoff and honor `retry-after`.
Every other non-2xx raises an error with `status`, `body` and `request_id`:

- Python: `TypeSafeBadRequestError` (400), `TypeSafeAuthenticationError` (401),
  `TypeSafeUnprocessableEntityError` (422), `TypeSafeRateLimitError` (429 after retries),
  `TypeSafeAPIConnectionError` (server unreachable or timeout).
- TypeScript: `BadRequestError`, `AuthenticationError`, `UnprocessableEntityError`,
  `RateLimitError`, `APIConnectionError`.

The default timeout is 10 seconds per attempt. On CPU, or with long documents and many questions,
raise it rather than letting retries pile up.

## Differences from the hosted Jev service

- Model names: use `jev-latest` or the name from `/v1/models`; dated hosted model names do not exist here.
- Keys start with `vk_` and come from the person's own server.
- Requests, answers, limits and error bodies match.
