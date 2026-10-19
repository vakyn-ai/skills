# Plan the run: before anything is sent

A batch run sends every row of the person's data to VAKYN: VAKYN Cloud, or their own server.
Agree the setup first, then pilot, then the full run. Nothing is sent before the person said yes to the plan.

## 1. Ask, in one message

1. **Which data?** The file or table, where it lives, how many rows, and the row id column. Resume
   needs one stable, unique id per row. No id column: use a hash of the row's content, or the row
   number only when the file never changes.
2. **Which questions?** If the requests are not written yet, write them with the
   `workflow` or `questions` skill first. Batching runs questions; it does not design them.
3. **Which columns are evidence?** Only those go into the state. Everything else stays in the
   person's process.
4. **Where does it run?** VAKYN Cloud (`TYPESAFE_BASE_URL=https://api.vakyn.com`, the default)
   or their own server (its URL, and whether it runs with the default `--max-queue` of 32). The
   key goes in `TYPESAFE_API_KEY` in the environment (never in the chat or in a file).
5. **Where do answers go?** A new file next to the input, or a new table. Never over the source.

## 2. Pick the columns

Go through every column and put it in one of three groups:

| Group | Goes into the state? | Examples |
|---|---|---|
| Evidence the questions need | yes, under a plain key | subject, message body, product, plan |
| Personal data | no, unless a question needs it and the person agrees | name, email, phone, address, account or card number, IP |
| Not needed | no | created_at, internal ids, channel, columns the code uses itself |

- **Flag personal data by name** ("`customer_name` and `customer_email` are personal data; the
  questions do not need them, so the script leaves them out").
- **Free text can hold personal data too.** Replace emails and phone numbers in the sent text in
  code (the examples do), and say so. Other kinds (names inside the text, account numbers) need
  their own rule; ask how strict the person needs to be.
- **Say what leaves the process.** On VAKYN Cloud the rows travel to `api.vakyn.com`; on their
  own server they stay on their network but still travel to it, and its logs may keep request ids
  and sizes. Name the address and the columns sent. Data that must not leave their network:
  their own server ([self-hosting](../../get-started/references/self-hosting.md)).
- Code that decides from a column exactly (plan tier, a date, an amount) keeps it in code, not in
  the state. See the `questions` rules.

## 3. The plan message

Send this before the pilot, in plain words and in this order:

1. **Data**: file or table, rows, id column.
2. **Sent per row**: the columns (and their state keys), what is replaced in free text, the
   address (VAKYN Cloud or their server). **Not sent**: every other column, by name. **Personal data**: say which columns are
   personal data, in those words, and that they stay out unless the person says otherwise.
3. **Questions**: one line each, all in one request per row when they are independent.
4. **Output**: the answer columns, the unsure rule (starting values from the
   [thresholds page](../../check/references/thresholds.md#starting-values-and-sample-sizes)),
   the review file, and that the source is only read.
5. **Pilot first**: 30 rows spread over the data, then a stop to look at the answers and the
   time per row before the full run.
6. **Cost (VAKYN Cloud)**: rows × input tokens per row (about 4 characters of English per token)
   × the price per billion input tokens from `GET /v1/models`. Say it is an estimate; the pilot
   measures `usage.input_tokens`. Never quote a price from memory.
7. **What you need from them**: a yes, the key set in the environment, a balance on VAKYN Cloud
   (or their server running).

## 4. Pilot (30 rows)

- Rows spread over the whole file or table (every k-th row), not the first 30: data sorted by
  date or source hides problems at the end.
- Show every pilot row: id, a short text, each answer with its confidence, and the unsure reason.
- Show the time: median and max per row, rows per second at the chosen concurrency, and the full
  run's time at that rate. Say the pilot rate includes warm-up; the full run's progress line shows
  the steady rate. On VAKYN Cloud also show the input tokens per row and the full run's cost at
  the price from `GET /v1/models`.
- Point at what looks wrong: a question that is unsure on most rows, one option that takes almost
  every row, an escape option picked for rows that clearly fit. Fix the question
  (`questions` skill, [diagnose](../../questions/references/diagnose.md)) and pilot
  again before the full run. A changed question is a new pilot; keep both results.
- Then **stop and ask** before the full run. Pilot answers are kept; the full run skips them.

## 5. Before the full run

- A few hundred labeled rows or more? Set the threshold from them with `check` first.
  Otherwise use the starting values and say they are starting values.
- Big runs take long: the progress line gives the ETA after warm-up. A run that takes hours goes
  in a process that survives the terminal (`nohup`, `tmux`, a job runner), with its output in a
  log file. A stop at any point loses at most the requests in flight.
