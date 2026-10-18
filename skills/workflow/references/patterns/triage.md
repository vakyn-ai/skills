# Triage: sort a batch by type and urgency

**Use when** many records arrive together (a morning's repair requests, an inbox, a backlog) and
each needs a type and a place in the order.
**Not when** only one record arrives at a time; that is [route](route.md) plus an urgency `score`.

## The request

[examples/triage.request.json](../../examples/triage.request.json): per record, one `choice` for
the trade (with `other` for anything that is not a repair) and one `score` for urgency with four
levels described by what you would see, lowest first. Both questions need only the record, so they
share one request.

Answer from a running VAKYN 4B: a cold radiator for two days with a newborn at home → `heating`
(1.00), urgency 2.03 ("Within 24 hours", probability 0.97).

## The code

[examples/triage.py](../../examples/triage.py) (asyncio) ·
[examples/triage.ts](../../examples/triage.ts) (worker pool)

- One request per record, sent concurrently with a cap (`MAX_IN_FLIGHT = 8`): an
  `asyncio.Semaphore` in Python, a fixed pool of workers in TypeScript. Keep it under 60 requests
  per second per key on VAKYN Cloud, and below `--max-queue` on the person's own server.
- The SDK retries `429` after the delay VAKYN asks for (`RetryPolicy(max_retries=4)`). A
  record that still gets `429` is kept for a later pass, never dropped.
- Code sorts by the urgency score and applies the safety rule: any record with more than 0.2
  probability on "Emergency now" goes to the on-call person, whatever the rest says.

Run on six records: water through a ceiling light → `on_call_now` (2.91); cold radiator →
`heating` (2.02); oven → `appliance` (1.70); mice → `pests` (0.99); a parking permit question →
`dispatcher_review` (`other`); a loose cupboard door → `general` (0.29).

## Unsure path

`other`, or either answer below `MIN_CONFIDENCE` → the dispatcher's review list. Emergencies skip
the threshold: for them a false alarm is cheap and a miss is not.

## Common mistakes

- **Urgency as a `choice`.** "low / medium / high" as options loses the order; a `score` gives a
  number you can sort by.
- **Bare levels.** `"1"` to `"4"` or "low" to "critical" without a description of what each looks like.
- **One request for the whole batch** (all records in one state). Each record gets its own request;
  send them concurrently.
- **No cap.** `gather` over 10,000 records goes past the rate limit (or fills the server queue)
  and turns into a wall of `429`s. On VAKYN Cloud it also spends balance on all 10,000 at once:
  estimate the cost and ask before a run that size.
- **A missing trade.** A loose cupboard door went to `appliance` until `general` was added. Read
  the first answers on real records and fill gaps in the options.
