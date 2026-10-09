# Go-live review

Read the person's VAKYN code and config and walk this list. For each item, say **ok**, or what is
missing and the fix (with the code change). Limits and errors:
[API reference](../../vakyn/references/api.md); SDK behavior: [SDK guide](../../vakyn/references/sdk.md).

## Requests

1. **Independent questions share one request.** Questions about the same state that do not need
   each other's answers go in one `questions` object, not one call each. A question that needs
   another's answer goes in a second request.
2. **Size checked before sending.** State plus the longest question under 32,768 tokens, plus all
   questions under 65,536, body under 64 MiB. Over a limit gets 400 and nothing is cut. Long
   documents: trim to the evidence in code, or split, before the call; handle 400 as "too big", not
   as a reason to retry.
3. **Every request passes the [pre-send checklist](../../vakyn/references/checklist.md).**
4. **Code checks the answer**: the pick is one of the offered options; answers are read by name.

## Load and errors

5. **Concurrency below `--max-queue`.** The server queues up to `--max-queue` requests (default 32)
   and answers 429 with `retry-after` beyond that. Cap in-flight calls in the app (a semaphore or a
   worker pool) at or below that number, summed over every app instance using the server.
6. **429 and 503 are retried after `retry-after`.** The SDKs do this (2 retries with backoff). Hand-
   written HTTP code must read `retry-after` / `retry-after-ms` and wait; no tight loops.
7. **A timeout on every call.** The SDK default is 10 seconds per attempt. On CPU or with long
   states, raise it (for example 30 s) instead of letting retries pile up. Plain HTTP clients
   often have no timeout at all; set one.
8. **A fallback when the server is down or keeps failing**: the chat model, a person, or a queue to
   retry later. The app must not stop or guess an answer. Decide it per question.

## Keys

9. **The key comes from the environment** (`TYPESAFE_API_KEY` / `VAKYN_API_KEY`) or a secret store;
   never in code, config in git, logs or error messages. If one is in a tracked file, it is leaked:
   revoke it (`vakyn keys revoke`), create a new one (`vakyn keys create --name <app>`), move it out.
   In the review, point to where the key is (file and line, or "the HEADERS line"); never write the
   key itself in your reply, not even to say which one to revoke.
10. **One key per app or environment**, so one can be rotated without stopping the others.
    Rotation: create the new key, deploy it, then revoke the old one.
11. **HTTPS beyond the machine.** open-server speaks plain HTTP; put a reverse proxy with TLS in
    front when the app runs elsewhere.

## Logging and monitoring

12. **Log every decision**: request id (`x-typesafe-request-id`), question name, pick, confidence
    (and probabilities when cheap), model name from the response, timestamp. Not the raw personal
    data, unless their policy allows it.
13. **Watch the unsure rate**: the share below the threshold per day. A rise means the inputs
    changed (drift), a question broke, or the model changed.
14. **Watch the pick mix**: the share of each option over time. A sudden shift is drift or a bug.
15. **Sample and label**: a few records a week, from above and below the threshold, labeled by a
    person, to keep checking the error rate.

## Changes

16. **Re-check after any change**: model file, question wording, options, state builder or the
    threshold itself. Run the smoke test and the [threshold check](thresholds.md) again before
    the change goes live.
17. **The model name is pinned or logged**, so answers can be tied to the model that gave them.

## Output

A table: item, status (ok / fix / not applicable), what to change. Then the code changes for each
"fix", smallest first. Start with anything that leaks a key or can stop the app.
