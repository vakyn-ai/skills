# Side by side, switch, roll back

VAKYN runs next to the old service first. The old answers stay in use until the person
has seen how often the two agree on their own requests.

## 1. Record requests

About 30 real requests, covering every option and the hard cases (sample sizes and what they
can prove: [thresholds](../../check/references/thresholds.md#starting-values-and-sample-sizes)).
Sources, cheapest first:

1. **Their logs**, with the old answers: no call to the old service is needed. Save each as
   `{"id", "request", "old_answers"}` (one JSON object per line) and run `compare.py --a recorded`.
2. **Their logs without answers**: replay against both. This calls the old service again, which
   costs money and sends data out. **Ask first** and wait for a yes.
3. **No logs**: write requests from real records with them, in their code's shape.

Redact personal data before anything leaves their machine.

## 2. Replay and compare

[compare.py](../examples/compare.py) replays a JSONL file against two `/v1/systemone` base URLs
(or saved answers and one URL) and reports agreement per question, every disagreement, failed
lines and time per request. Sample input: [recorded.sample.jsonl](../examples/recorded.sample.jsonl).

```sh
python3 compare.py recorded.jsonl --a https://api.typesafe.ai --b https://api.vakyn.com --dry   # plan only
OLD_API_KEY=... VAKYN_API_KEY=... python3 compare.py recorded.jsonl --a https://api.typesafe.ai --b https://api.vakyn.com
```

Own open-server instead: `--b` is its URL (for example `http://localhost:8080`). Write the
commands for the person to run with their keys; never ask for a key in the chat. On VAKYN Cloud
the `--b` side spends balance (30 requests is little, but say so); the default concurrency of 4
stays far under the 60 requests per second per key.
For sources that do not speak `/v1/systemone` (OpenAI Decisions, Clef on Workers AI), convert
the recorded requests first ([field maps](field-maps.md)) and use `--a recorded` with their
logged answers converted the same way.

Report: agreement per question, each disagreement side by side, failed lines with their
status, measured time per request with where it ran named. Say, in these words: "agreement is
not accuracy". Their labels on the disagreements decide which side is right
([log summary and labeling](../../check/references/log-summary.md)).

## 3. Side by side in the app (optional, for busy paths)

When the decision runs often, ship both for a while: the old service answers, VAKYN answers
too, both are logged as JSON lines with the request id, the old answer is used. The pattern and
log format are in `convert` ([code shape](../../convert/references/code-shape.md));
the summary is in `check`.

## 4. Switch

Switch by configuration, not by editing code: set the base URL, key and model variables (or
the app's own flag) to VAKYN in one place. Check thresholds again on VAKYN's answers;
starting values are on the [thresholds](../../check/references/thresholds.md) page.
Before production: the [go-live review](../../check/references/go-live.md).

## 5. Rollback plan

Write it down before switching:

- the old values of every variable that changed (base URL, model, key name), kept where the
  team can set them back in one step; the old key stays valid until the new path has run for
  an agreed period;
- what triggers a rollback (error rate, unsure rate, a disagreement type that matters);
- who switches back, and how (config change and restart; no code change, no deploy if possible);
- code removed in the move (gateway fallbacks, refusal handling, cost tracking) stays in version
  control until rollback is no longer needed.
