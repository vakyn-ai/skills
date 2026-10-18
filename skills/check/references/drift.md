# Drift check: did a change move the answers?

A drift check re-runs a fixed set of records after a change and compares the answers with the
ones stored before it. It catches silent changes: a new model file, a server upgrade, a reworded
question, a new state builder. It needs no labels; it tells the person **what moved**, and the
labels (or a person reading the changed records) decide whether the move is better or worse.

## The reference batch (saved once)

- **100 to 300 records** that look like the real flow: every option, the hard cases, "none of
  these", long and short inputs. Redact personal data first. Keep the file in the repo or next to it.
- **The questions exactly as the app sends them**, in one request file, asked together as the app
  asks them.
- **Stored per record and question**: record id, question name, a hash of the question text, the
  pick, confidence, probabilities (or `noul`), request id, model name from the response, the model
  file and quantization as `/v1/models` describes it (or as the person knows it; on VAKYN Cloud
  the model name such as `vakyn-max`), the server version when self-hosted, and the date.
- **Low concurrency: 1 or 2 in flight.** A request sent alone repeats exactly. Under concurrent load
  the numbers can move slightly between runs (measured up to 0.04 with 8 in flight; see the
  [API reference](../../start/references/api.md)). Run the reference batch and every re-run the same way.

## When to re-run it

After any change to: the model (`vakyn-max` or `vakyn-fast`), the model file or its quantization,
the server version, a question's text,
options or escape option, the state builder, or the model name the app asks for. Also on a
schedule (for example weekly) to prove nothing moved.

## What the report shows

Per question:

| Item | Meaning |
|---|---|
| Setup | model name, model file, server version, question text hash: reference vs now, changes marked |
| Picks changed | share of records whose pick changed by more than the noise tolerance |
| Mean absolute change | the largest probability move per record, averaged |
| Moved more than the tolerance | how many records really moved; smaller moves count as noise |
| Crossed the threshold | records that moved from acted-on to unsure, or back, or to another acted-on pick |
| Picks per option | count per option, reference vs now, and the share that shifted |
| Changed records | biggest move first, with old and new pick and confidence |

**Noise tolerance**: with the same pick and every probability within the tolerance (0.05 by
default, just above the measured 0.04), a record counts as unchanged. A pick that flips within the
tolerance is a near tie: listed apart, to check by hand.

**Pass or fail** against limits the person sets: share of picks changed, mean change, share
crossing the threshold. Placeholders in the script are 2%, 0.02 and 2%; ask what the person can
accept. A failed check exits 1, so it can stop a CI job.

## Steps

1. Agree the reference records, the limits and the threshold the app uses
   ([starting values](thresholds.md#starting-values-and-sample-sizes) until labels set it).
2. Save the reference batch on the setup they trust: `python3 drift.py save --request
   drift.request.json --records records.jsonl --out reference.jsonl` (concurrency 1).
3. Re-run it unchanged once. Expect no changes; if records move, find out why before trusting
   anything (other load on the server, a different server or model).
4. After a change, run `drift.py check`. Report the setup changes, the numbers, and the changed
   records biggest first.
5. A change that was meant to move answers (a reworded question) fails on purpose: a person reads
   the changed records, labels them, and re-checks the [threshold](thresholds.md) and
   [calibration](calibration.md). If it is better, save a new reference batch in the same change.
6. A change that was not meant to move answers (a server upgrade, a new copy of the same model file)
   should pass. If it fails, do not ship it; look at the changed records first.

Script: [drift.py](../examples/drift.py) with [drift.request.json](../examples/drift.request.json)
(edit `build_state()` to match the app). CI: [drift-ci.yml](../examples/drift-ci.yml), a GitHub
Actions job that runs on pull requests touching questions, prompts or the state builder, against a
test server, and fails when a limit is broken. The key comes from a repo secret, never from the file.

## Example (live run on this repo's sample)

Reference batch: the 79 tickets in [labeled.sample.jsonl](../examples/labeled.sample.jsonl), two
questions (`team`, a `choice`; `wants_refund`, a `noul`), saved at concurrency 1 on VAKYN-4B
(`/v1/models`: "UQFF Q8_0 on mistral.rs"). Re-run unchanged at concurrency 1: 0 of 79 picks
changed, mean change 0.000 for both questions, check passed. Re-run at 8 in flight: still 0 picks
changed, mean change at most 0.001.

Then the `product` option of `team` was narrowed from "How the product works, bugs, broken or
faulty items" to "Bugs and error messages in the app", and the check was run again:

```text
=== question: team ===
  question text: CHANGED (925c62f84451 -> a67dc5458a47)
  compared 79 records
  picks changed:              10/79 (12.7%)  [limit 2.0%]
  mean absolute change:       0.120  (largest probability move per record) [limit 0.020]
  moved more than 0.05:       16/79; at or below it counts as noise
  crossed the threshold:      13/79 (16.5%)  [limit 2.0%]
  near ties that flipped within noise: 1 (re-check these by hand)
  picks per option (reference -> now), shift 10.1%:
    access         17 -> 15  
    billing        19 -> 19  
    other          18 -> 26  
    product        11 -> 5   
    shipping       14 -> 14  
  changed records, biggest first:
    t042     product    1.00 -> other      1.00  move 1.00  product -> other
    t051     product    1.00 -> other      1.00  move 1.00  product -> other
    t048     product    1.00 -> other      0.97  move 0.98  product -> other
    t062     product    1.00 -> other      0.94  move 0.98  product -> other
    t066     product    0.93 -> other      0.94  move 0.91  product -> other
    ...
  result: FAIL (picks changed, mean change, threshold crossings)

=== question: wants_refund ===
  question text: same (054b8ee7b230 -> 054b8ee7b230)
  picks changed:              0/79 (0.0%)  [limit 2.0%]
  mean absolute change:       0.001  (largest probability move per record) [limit 0.020]
  result: pass

DRIFT CHECK FAILED: a limit is broken. Review the changed records before shipping.
```

How to read it: the edit moved broken items ("The kettle I bought stopped heating after three
days", t042) and product questions (t051) from `product` to `other`. That was not the intent, so
the old wording stays. The other question in the same request did not move beyond noise.
