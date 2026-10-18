# The batch script: what every part does

Write the script into the person's project (for example `scripts/vakyn_batch.py`), in their
language, with the official SDK ([SDK guide](../../start/references/sdk.md)). Start from
[batch_csv.py](../examples/batch_csv.py) for files and [batch_sql.py](../examples/batch_sql.py) for
tables. Each part below is in both.

## One request per row, all questions in it

Independent questions about the same row (team, refund, urgency) share one request: the state is
read once. A question that needs another's answer goes in a second request for the rows that need
it. Never put several rows in one state. See [batching](../../workflow/references/batching.md).
Run the [pre-send checklist](../../start/references/checklist.md) on one row's request and save it
as a `.json` file next to the script ([ticket-row.request.json](../examples/ticket-row.request.json)).

## Bounded concurrency

- A fixed number of requests in flight: a pool of workers taking rows from a queue (Python
  `asyncio` with `AsyncTypeSafeClient`; TypeScript: N workers over one list). Never one task per row
  for the whole file at once.
- **Default 8.** On VAKYN Cloud, stay under 60 requests per second per key; self-hosted, never
  above the server's `--max-queue` (default 32). Both are summed over every process using the
  key or the server. The examples refuse more than 32.
- More is not faster. Measured on open-server with [batch_csv.py](../examples/batch_csv.py), 400 short tickets,
  3 questions per row, VAKYN-4B on one RTX 5090, server started with defaults and shared with
  other jobs: 1 in flight 21.5 rows/s, 4 → 31.9, 8 → 32.7 to 34.5 (several runs), 16 → 25.2, 32 → 22.5 with 2 rows
  still failing with `429` after every retry. Measure on the person's machine in the pilot.

## Retries and timeouts

- `RetryPolicy(max_retries=6, backoff_max=30, timeout=600, respect_retry_after=True)`: the SDK retries `408`, `429` and
  `5xx` and waits the `retry-after` the server sends. The SDK's own default gives up after 2
  retries and 30 s, which is short for a long run.
- Client timeout 60 s per attempt (the SDK default is 10 s). Raise it on CPU or with long states.
- A row that still fails is **kept with its error** in the checkpoint and counted, never dropped.
  A rerun tries it again. `400` (too big) will fail again: trim the state in code
  ([long documents](../../workflow/references/long-documents.md)).
- Plain HTTP code instead of the SDK: read `retry-after` / `retry-after-ms` on `429` and `503`
  and wait that long; no tight loops.

## Checkpoint and resume

- After each row (file) or batch of rows (table), the result is saved with the row id:
  a sidecar `<out>.progress.jsonl`, one line per row, flushed; or the results table, committed.
- On start, rows already answered without an error are skipped. A rerun of the same command
  resumes; a stop (Ctrl-C, a crash, `--limit`) loses at most the requests in flight.
- The output file is rebuilt from the checkpoint in input order, so the same results always give
  the same file, however many runs it took. Tested on the sample: pilot, `--limit 40`, then the
  rest gave the same file as a second full rerun; a Ctrl-C in the middle of 1,440 rows resumed
  with no row sent twice.
- **Never resend done rows to "refresh" them.** Under concurrent load the same request can come
  back a few hundredths apart (seen on the sample: up to 0.04 between two runs), enough to move a
  row across a threshold. One run's answers are the record.

## Progress

Print a line every few seconds: `done/total (%)  rows/s  ETA  errors`. The rate skips the first
wave of requests (warm-up) and uses the last 30 seconds, so the ETA follows the steady rate, not
the slow start. Example from a run of 1,440 rows:

```text
1/1440 (0%)  warming up  ETA after warm-up  errors 0
130/1440 (9%)  31.0 rows/s  ETA 0.7 min  errors 0
```

## Answer columns

Per question, named after the question:

| Type | Columns |
|---|---|
| `choice` | `team` (the pick, checked against the offered options), `team_confidence` |
| `noul` | `refund_p` (probability of yes), `refund` = `yes` / `no` / `unsure` from the cut-offs |
| `score` | `urgency` (top level's short name), `urgency_score` (weighted), `urgency_confidence` |

Plus `unsure` (true or false), `unsure_why` (which questions), `request_id`, `input_tokens` (from `usage`; the cost on VAKYN Cloud), `error`. Keep the
full probabilities only when the person asks; they are large and easy to recompute.

## Unsure rows and the review file

- `unsure` comes from the starting values on the
  [thresholds page](../../check/references/thresholds.md#starting-values-and-sample-sizes),
  as named settings at the top of the script, plus any escape option pick (`other`, `none`).
  Say they are starting values until the person's labels set them (`check`).
- Unsure rows also go to a separate review file with the columns that were sent, so a person can
  check them without the full output. Their labels are the input for real thresholds.

## Summary at the end

Rows, answered, errors, not done; counts per answer for each question; the unsure share; the first
few errors; this run's rows and time. Example (sample file, 120 rows):

```text
Rows: 120  answered: 120  errors: 0  not done: 0
  team: billing 45, access 25, other 22, bug 18, how_to 10
  refund: no 96, yes 20, unsure 4
  urgency: low 49, high 42, medium 29
  unsure: 46/120 (38%)
```

Report it to the person with the measured time, the machine, and where the files are.
