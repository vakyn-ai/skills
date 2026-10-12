# Rate and rank the spots

For each decision spot, rate gain, risk and effort, then rank. Write every number with where it
came from: **log** (measured), **code** (read from config or comments), or **assumed** (your
estimate; say what it rests on).

## Gain: how much the spot costs today

Collect per spot:

- **Calls a day.** From logs if present. Otherwise from code: comments, queue or cron settings,
  how the call sits in the flow (a check on every email runs more often than a step after it).
  Otherwise assume and say so ("assumed 1,000 emails a day; please correct").
- **Current model** and **tokens per call** (prompt length plus typical input; output tokens).
- **Cost.** Calls a day × tokens × the price per token. Take prices from logs or from the person;
  if you use a published list price, write the price and the date you assumed. Never present an
  assumed price as measured.
- **Wait time.** Does a person or a request wait on it (in the request path), or does it run in
  the background? From logs if present (`latency_ms`), otherwise "in request path" or "background".

| Gain | When |
|---|---|
| High | 1,000+ calls a day; or 100 to 1,000 a day on a large model or with a person waiting on each answer |
| Medium | 100 to 1,000 calls a day otherwise; or under 100 a day with a person waiting on each answer |
| Low | under 100 calls a day otherwise, even on a large model |

Volume comes first. Gain is the cost and wait that go away, and both grow with calls a day. A large
model on a call that runs a few times a day costs little in total: that is not High gain by itself.

VAKYN runs on the person's own server, so there is no per-call fee; the gain is the chat-model
cost and wait time that goes away, plus a confidence on every answer. Do not quote VAKYN speed or
accuracy numbers here; `check` measures them on the person's own data.

## Risk: what a wrong answer does downstream

Follow the answer through the code: what reads it, what happens next.

| Risk | When | Example |
|---|---|---|
| Low | a wrong answer is cheap and visible, a person sees it next | ticket goes to the wrong team and is moved |
| Medium | a wrong answer costs time or money, or hides something | a real email marked spam and never read |
| High | a wrong answer harms a customer, breaks a rule or acts without review | a refund issued, an account closed, legal or safety flag missed |

High risk does not rule a spot out. It means: run side by side first, and send unsure answers to a
person or the chat model.

## Effort: how big the change is

| Effort | When |
|---|---|
| Small | one call, clear options already in code (a list, an enum, yes/no), one place reads the answer |
| Medium | options must be written out from a prompt, several rules to split into separate questions, or a tool list (pick-then-fill) |
| Large | options live in a database or exceed 255, the evidence needs cutting to fit, or nothing exists yet (a process step) |

## Rank

Give points and sort by **priority = 2 × gain − risk − effort**:

| | High / Large | Medium | Low / Small |
|---|---|---|---|
| Gain | 3 | 2 | 1 |
| Risk | 2 | 1 | 0 |
| Effort | 2 | 1 | 0 |

Ties: lower risk first, then higher call volume. Gain counts double because a spot that rarely
runs is not worth changing even when it is easy. Show the points in the table so the person can
disagree with one rating and see the order change.

## Using call logs

Logs and traces (JSONL, CSV, Langfuse, Helicone, LangSmith or OpenTelemetry exports) give real
numbers. Read a few lines first to learn the fields, then total them with what the machine has
(`jq`, `python3`, or by reading if the file is small). Do not send them anywhere.

1. Map each log entry to a spot: a function or tag field, the prompt's first words, or the model
   and token shape.
2. Per spot: calls, mean input and output tokens, mean and slowest `latency_ms`, total cost.
3. Scale to a day: calls ÷ hours covered × 24 (say that this assumes the window is typical).
4. When logs and code disagree (a comment says 3,000 a day, the log says more), use the log and
   note the difference.
5. Log entries that match no spot found in the code: list them under open questions.
