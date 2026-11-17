# Batching: one request, several, or many at once

There is no batch endpoint. Three shapes cover every workflow.

## Independent questions: one request

Questions that only need the same state go in one request: trade and urgency for one repair
request; four risk nouls for one message; three rubric criteria for one reply. The state is read
once, so more questions add little time. Limit: state plus all questions under 65,536 tokens.

## Dependent steps: separate requests

If question B needs A's answer, B goes in a second request with A's answer in its state as a fact.
Questions in one request cannot see each other's answers.

```python
team = decide(s, {"team": TEAM_Q})["team"]   # POST /v1/systemone
if team["choice"] == "billing" and team["confidence"] >= MIN_CONFIDENCE:
    topic = decide({**s, "team": "billing"}, {"billing_topic": TOPIC_Q})["billing_topic"]
```

Code decides whether to send B at all: skip it when A was unsure or A's answer makes B pointless.

## Many records: concurrent, with a cap

One request per record, sent concurrently, with a fixed number in flight:

- Python: a `ThreadPoolExecutor(max_workers=8)` with one call per record
  ([triage.py](../examples/triage.py), [check_claim.py](../examples/check_claim.py)).
- TypeScript: a pool of 8 workers taking records from one list ([triage.ts](../examples/triage.ts)).

Set the cap under the limit: 60 requests per second per key on VAKYN Cloud, the server's queue
size (`--max-queue`, default 32) on open-server. Over it, VAKYN answers `429` with
`retry-after` (seconds); the code waits that long and retries (the examples retry 429 and 5xx a
few times; allow more tries for big batches). A record that still fails with `429` is kept for a later pass, never
dropped. Raise the client timeout (30 s in the examples) on CPU or with long states. On VAKYN
Cloud a big batch spends the person's balance: estimate it first
([cost](../../get-started/references/cloud.md#cost)) and ask, or hand it to the `batch` skill.

## Never

- Put many records in one state and ask about "each" of them. One record per request.
- Send a dependent question in the same request as the one it depends on.
- Fire the whole batch at once with no cap.
