# Calling VAKYN from code

VAKYN answers on one HTTP endpoint: `POST /v1/systemone` with a JSON body. Any language with an HTTP
client calls it; there is nothing to install. The examples below use the Python standard library,
TypeScript's built-in `fetch`, and curl.

## Two variables

```sh
VAKYN_API_KEY=vk_...                    # from vakyn.com/console/keys, or `vakyn keys create`
VAKYN_BASE_URL=https://api.vakyn.com    # optional; the person's own server, e.g. http://localhost:8080
```

The base URL is the root without `/v1`. Leave `model` out on VAKYN Cloud (`vakyn-max` answers), or
set it to `vakyn-fast` when price matters most. On open-server `model` is required: use the name
`GET /v1/models` lists.

## One call

curl:

```sh
curl -sS "${VAKYN_BASE_URL:-https://api.vakyn.com}/v1/systemone" \
  -H "Authorization: Bearer $VAKYN_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"state": {"ticket": "I was charged twice."},
           "questions": {"refund": {"type": "noul", "instructions": "Does the ticket ask for money back?"}}}'
```

Python (standard library only):

```python
import json
import os
import urllib.request

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def decide(state, questions, timeout=30):
    """POST /v1/systemone; returns the answers by question name."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": state, "questions": questions}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"]


answers = decide(
    {"ticket": ticket_text},
    {
        "team": {"type": "choice", "instructions": "Which team should handle the ticket?",
                 "criteria": {"billing": "Charges, invoices, refunds",
                              "access": "Sign-in and permissions",
                              "other": "None of these fits"}},
        "refund": {"type": "noul", "instructions": "Does the ticket ask for money back?"},
        "urgency": {"type": "score", "instructions": "How soon does the ticket need a reply?",
                    "criteria": ["Can wait", "Today", "Within the hour"]},
    },
)
```

TypeScript (built-in `fetch`, Node 18+, Bun, Deno):

```ts
const BASE_URL = process.env.VAKYN_BASE_URL ?? "https://api.vakyn.com";

async function decide(state: unknown, questions: Record<string, unknown>) {
  const response = await fetch(`${BASE_URL}/v1/systemone`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.VAKYN_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ state, questions }),
  });
  if (!response.ok) throw new Error(`VAKYN ${response.status}: ${await response.text()}`);
  return (await response.json()).answers;
}

const answers = await decide({ ticket: ticketText }, {
  team: { type: "choice", instructions: "Which team should handle the ticket?",
          criteria: { billing: "Charges, invoices, refunds", access: "Sign-in and permissions",
                      other: "None of these fits" } },
  refund: { type: "noul", instructions: "Does the ticket ask for money back?" },
  urgency: { type: "score", instructions: "How soon does the ticket need a reply?",
             criteria: ["Can wait", "Today", "Within the hour"] },
});
```

Keys stay on the server: browser code calls the person's own backend, and the backend calls VAKYN.

## Reading answers

Answers come back under `answers`, by question name:

| Type | Fields |
|---|---|
| `choice` | `answers["team"]["choice"]`, `["confidence"]`, `["probabilities"]` (every option) |
| `noul` | `answers["refund"]["noul"]`: the probability of yes; distance from 0.5 is the confidence |
| `score` | `answers["urgency"]["score"]` (probability-weighted, fractional), `["legend"]`, `["probabilities"]`, `["confidence"]` |

Score `legend` and `probabilities` have string keys (`"0"`, `"1"`, …). The response also has
`model` (the model that answered) and `usage.input_tokens` (what was billed). Log the request id
from the `x-vakyn-request-id` response header. Full shapes: [API reference](api.md).

## Errors

Any status outside 2xx is an error with a JSON body `{"detail": ...}`. Python's `urllib` raises
`urllib.error.HTTPError` (`e.code`, `e.headers`, `e.read()`); `fetch` does not throw, so check
`response.ok`. What each status means: [API errors](api.md#errors). `402` (no balance left) and
`401` (wrong key) will not get better on retry; stop and tell the person.

## Retries

Retry `429`, `5xx` and connection errors a few times. A `429` (and a `503` while open-server loads
the model) carries `retry-after` in seconds: wait that long. Otherwise back off (1 s, 2 s, 4 s).

```python
import time
import urllib.error


def decide_with_retry(state, questions, attempts=4):
    for attempt in range(attempts):
        try:
            return decide(state, questions)
        except urllib.error.HTTPError as e:
            if (e.code != 429 and e.code < 500) or attempt == attempts - 1:
                raise
            time.sleep(float(e.headers.get("retry-after") or 2 ** attempt))
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
```

```ts
async function decideWithRetry(state: unknown, questions: Record<string, unknown>, attempts = 4) {
  for (let attempt = 0; ; attempt++) {
    const response = await fetch(`${BASE_URL}/v1/systemone`, {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.VAKYN_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ state, questions }),
    });
    if (response.ok) return (await response.json()).answers;
    const retry = response.status === 429 || response.status >= 500;
    if (!retry || attempt === attempts - 1) throw new Error(`VAKYN ${response.status}: ${await response.text()}`);
    const wait = Number(response.headers.get("retry-after")) || 2 ** attempt;
    await new Promise((resolve) => setTimeout(resolve, wait * 1000));
  }
}
```

Use a timeout of 30 seconds or more per attempt. On CPU, or with long documents and many
questions, raise it rather than letting retries pile up.

## Many requests at once

There is no batch endpoint: send independent requests concurrently, under a cap. VAKYN Cloud takes
60 requests per second per key, summed over every process using it; open-server queues up to
`--max-queue` requests (default 32). Over either, the answer is `429`, and the retry above waits.
On VAKYN Cloud every answered request spends balance: estimate the cost first ([cost](cloud.md#cost)).

Python, a thread pool:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(lambda row: decide_with_retry({"ticket": row}, questions), tickets))
```

TypeScript, `Promise.all` over small groups:

```ts
const results = [];
for (let i = 0; i < tickets.length; i += 8) {
  const group = tickets.slice(i, i + 8);
  results.push(...(await Promise.all(group.map((t) => decideWithRetry({ ticket: t }, questions)))));
}
```

## Cloud and self-hosted

- Keys start with `vk_` and come from the VAKYN console or the person's own server; a key works
  only where it was made.
- Moving between VAKYN Cloud and open-server is two changes: `VAKYN_BASE_URL` and `VAKYN_API_KEY`
  (plus `model`, which open-server requires).
