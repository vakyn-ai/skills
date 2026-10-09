---
name: vakyn-batch
description: "Run a whole file or table through VAKYN: CSV, JSONL, Parquet, a SQLite, Postgres or DuckDB table, or a log dump. Use for bulk labeling, tagging or scoring every row (\"add a team column to 50k tickets\", \"sort this export\", \"AI column\"), a resumable batch script with progress and ETA, or answer and confidence columns with unsure rows for review. Pilot first, never overwrites source data. To design the questions use vakyn-workflow; to compare with a chat model on 30 records or set thresholds use vakyn-check."
---

# VAKYN batch: run a file or table

The person has rows (a ticket export, a table of reviews, a log dump) and VAKYN questions that work
on a few examples. This skill writes a script **into the person's project** that runs every row
through VAKYN and writes the answers next to the data: pilot first, then the full run, with
resume, progress and a review file for unsure rows.

The files in [examples/](examples/) are templates to adapt, not tools to run from the plugin.
Shared material: [API reference](../vakyn/references/api.md), [SDK guide](../vakyn/references/sdk.md),
[pre-send checklist](../vakyn/references/checklist.md),
[thresholds](../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes) (the
starting values for `unsure`).

## Pick the step

| The person… | Do |
|---|---|
| Has data and questions, wants a batch run | [Plan](references/plan.md), then the steps below |
| Has data but no questions yet | Questions first: `vakyn-workflow` (new) or `vakyn-questions` |
| Has a CSV or JSONL file | [batch_csv.py](examples/batch_csv.py) |
| Has a SQLite, Postgres or DuckDB table, Parquet, or a log dump | [Sources](references/sources.md), [batch_sql.py](examples/batch_sql.py) |
| Has a slow or fragile loop already | [Script parts](references/script.md): add the missing ones |
| Wants VAKYN next to their chat model on ~30 records | `vakyn-check` smoke test, not this skill |
| Has labeled rows and asks where to set `unsure` | `vakyn-check` thresholds |

## Steps

1. **Ask** ([plan](references/plan.md#1-ask-in-one-message)): the data and its row id, the
   questions, the evidence columns, the server, where answers go.
2. **Pick the columns.** Only evidence goes into the state. Call personal-data columns
   personal data, by name ("`guest_email` is personal data; not sent"), and leave them out unless
   a question needs them and the person agrees. Replace emails and phone
   numbers in free text in code. Say what leaves the process: which columns, to which server.
3. **Write one row's request**, run the [checklist](../vakyn/references/checklist.md), save it as
   a `.json` file next to the script. Independent questions share one request per row.
4. **Write the script** in the project's language from the template. It must have every part in
   [script parts](references/script.md): bounded concurrency (8; never above `--max-queue`,
   default 32), retries on 429 and 503 honoring `retry-after`, a timeout above the SDK's 10 s,
   a checkpoint and resume, a progress line (done/total, %, rows/s, ETA, errors), answer
   columns, `unsure`, a review file, and a summary.
5. **Send the plan message** ([plan](references/plan.md#3-the-plan-message)) and wait for a yes.
6. **Pilot**: 30 rows spread over the data. Show every row's answers, the unsure ones, the time
   per row and the projected full-run time. Fix questions that misbehave and pilot again.
7. **Stop and ask** before the full run.
8. **Full run**, then the summary: counts per answer, unsure share, errors, time, the files.
   Next: label some review rows and set real thresholds with `vakyn-check`.

No server reachable: write the script and the request, say how to run the pilot, and never invent
answers or speeds.

## Output columns

Per question: `team` + `team_confidence` (`choice`), `refund_p` + `refund` yes / no / unsure
(`noul`), `urgency` + `urgency_score` + `urgency_confidence` (`score`). Then `unsure`,
`unsure_why`, `request_id`, `error`. Unsure rows also go to `<name>.review.csv`.
Details: [script parts](references/script.md#answer-columns).

## Examples

| File | What |
|---|---|
| [batch_csv.py](examples/batch_csv.py) | CSV or JSONL, `AsyncTypeSafeClient`, checkpoint in `<out>.progress.jsonl` |
| [batch_sql.py](examples/batch_sql.py) | SQLite, answers in a new table, keyset reads, upserts |
| [tickets.sample.csv](examples/tickets.sample.csv) | 120 synthetic support tickets with personal-data columns |
| [ticket-row.request.json](examples/ticket-row.request.json) | One row's request: three questions |

Measured on the sample (VAKYN-4B, one RTX 5090, 8 in flight, 3 questions per row): about 33 rows
per second, pilot median 108 ms per row. Measure on the person's machine; never quote these as theirs.

## Rules

- **Pilot before the full run, and ask before the full run.**
- **Never write over the source.** New file or new table; changing source rows or schema needs a
  yes, and then goes through a reviewed copy step.
- **Keep every row.** Failed rows are saved with their error and retried on the next run; the
  summary counts them. Nothing is dropped from the counts.
- **Never resend done rows** to get different numbers. One run's answers are the record.
- **Ask before personal data leaves the process**, and name the columns that do.
- **Keys stay out of the chat and out of files**: `TYPESAFE_API_KEY` in the environment.
