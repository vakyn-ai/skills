# Go-live review

Read the person's VAKYN code and config and walk this list. For each item, say **ok**, or what is
missing and the fix (with the code change). Limits and errors:
[API reference](../../get-started/references/api.md); SDK behavior: [SDK guide](../../get-started/references/sdk.md).

## Requests

1. **Independent questions share one request.** Questions about the same state that do not need
   each other's answers go in one `questions` object, not one call each. A question that needs
   another's answer goes in a second request.
2. **Size checked before sending.** State plus the longest question under 32,768 tokens, plus all
   questions under 65,536, body under 64 MiB. Over a limit gets 400 and nothing is cut. Long
   documents: trim to the evidence in code, or split, before the call; handle 400 as "too big", not
   as a reason to retry.
3. **Every request passes the [pre-send checklist](../../get-started/references/checklist.md).**
4. **Code checks the answer**: the pick is one of the offered options; answers are read by name.

## Load and errors

5. **Concurrency under the limit.** VAKYN Cloud takes 60 requests per second per key;
   open-server queues up to `--max-queue` requests (default 32). Beyond either, the answer is 429
   with `retry-after`. Cap in-flight calls in the app (a semaphore or a worker pool), summed over
   every app instance using the key or the server.
6. **429 and 503 are retried after `retry-after`.** The SDKs do this (2 retries with backoff). Hand-
   written HTTP code must read `retry-after` / `retry-after-ms` and wait; no tight loops.
7. **A timeout on every call.** The SDK default is 10 seconds per attempt. On CPU or with long
   states, raise it (for example 30 s) instead of letting retries pile up. Plain HTTP clients
   often have no timeout at all; set one.
8. **A fallback when VAKYN is down or keeps failing**: the chat model, a person, or a queue to
   retry later. The app must not stop or guess an answer. Decide it per question. On VAKYN Cloud,
   `402` (balance empty) takes the same fallback, and someone watches the balance: the
   organization's owners get an email when it runs low.

## Keys

9. **The key comes from the environment** (`TYPESAFE_API_KEY` / `VAKYN_API_KEY`) or a secret store;
   never in code, config in git, logs or error messages. If one is in a tracked file, it is leaked:
   revoke it and create a new one (VAKYN Cloud: the console's API keys page; open-server:
   `vakyn keys revoke`, `vakyn keys create --name <app>`), move it out.
   In the review, point to where the key is (file and line, or "the HEADERS line"); never write the
   key itself in your reply, not even to say which one to revoke.
10. **One key per app or environment**, so one can be rotated without stopping the others.
    Rotation: create the new key, deploy it, then revoke the old one.
11. **HTTPS beyond the machine.** VAKYN Cloud is HTTPS. open-server speaks plain HTTP; put a
    reverse proxy with TLS in front when the app runs elsewhere.

## Logging and monitoring

12. **Keep an audit record of every decision** ([format below](#audit-record)): request id
    (`x-typesafe-request-id`), model name from the response, the input or its hash, question
    hashes, every answer with its probabilities, the policy version, the outcome. Not the raw
    personal data, unless their policy allows it.
13. **Watch the unsure rate**: the share below the threshold per day. A rise means the inputs
    changed (drift), a question broke, or the model changed.
14. **Watch the pick mix**: the share of each option over time. A sudden shift is drift or a bug.
15. **Sample and label**: a few records a week, from above and below the threshold, labeled by a
    person, to keep checking the error rate.

## Changes

16. **Re-check after any change**: model file, question wording, options, state builder or the
    threshold itself. Run the [drift check](drift.md) on a stored reference batch, and the
    [threshold check](thresholds.md) again, before the change goes live; a CI job can run the drift
    check on every pull request that touches the questions.
17. **The model name is pinned or logged**, so answers can be tied to the model that gave them.
18. **Thresholds and rules are versioned like code**: a policy file in git (or a config with a
    version), read by the decision code, never literals scattered through it. Each audit record
    names the version and a hash of the file. A change goes through review, a [replay](replay.md)
    and the [promotion rule](tuning.md#the-promotion-rule).
19. **Questions are versioned too**: a hash of each question as sent, in every record, so a
    reworded question shows up as a new version.

## Output

A table: item, status (ok / fix / not applicable), what to change. Then the code changes for each
"fix", smallest first. Start with anything that leaks a key or can stop the app.

## Audit record

One JSON line per decision, written when the decision is made. It answers "which model, which
inputs, which policy version decided this case? Show me", and the same lines drive
[replay](replay.md) and [tuning](tuning.md).

| Field | What it holds |
|---|---|
| `case_id` | the person's id for the case (ticket, claim, alert) |
| `step` | which step of the workflow decided (`route_ticket`); one record per step when there are several |
| `ts` | UTC time |
| `request_id` | `x-typesafe-request-id` of the VAKYN request |
| `model` | model name from the response; add the model file as `/v1/models` describes it when it matters |
| `input` or `input_hash` + `input_ref` | the state as sent, or, where policy forbids keeping it, its hash and where the input is stored |
| `questions` | per question name, a hash of the question as sent |
| `answers` | per question: the pick and `confidence` with all `probabilities`, the `noul`, or the `score` with its probabilities |
| `policy_version`, `policy_hash` | the thresholds and rules file that decided, by name and content hash |
| `outcome`, `reason` | what the code decided, and the rule and numbers that made it ("wants_refund 1.00 >= 0.8") |

Example line: [answers.sample.jsonl](../examples/answers.sample.jsonl); template that writes it:
[replay.py](../examples/replay.py) `record`.

To answer "show me" for one case: find its line by `case_id`, then show the model, the input (or
fetch it by `input_ref` and check its hash), the question versions (find the question text by
hash in git), every answer with its probabilities, the policy file at that version, and the
reason. Re-running `decide()` on the stored answers with that policy file must give the stored
outcome; that proves the record is complete.

Keep the records as long as the person's retention rules say, write them append-only, and keep the
policy files and question texts they point to in git for as long.
