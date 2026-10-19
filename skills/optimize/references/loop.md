# The loop

Automatic prompt tuning for one VAKYN question: measure the current wording on labeled cases,
rewrite it from its mistakes, keep a rewrite only if it scores better, and confirm once on cases
the loop never used. The agent writes the rewrites; [optimize.py](../examples/optimize.py)
measures, keeps the books and enforces the rules.

## What goes in

| Input | Notes |
|---|---|
| Request file | The model and exactly one question; the state is an example, each case's state replaces it |
| Labeled cases (JSONL) | `id` (stable), `text` or `state`, `label`: option key, `true` / `false`, or level index from 0 |
| Model | `--model vakyn-fast` or `vakyn-max`; default: the request's. Tune per model |
| Budget | `--rounds` (5), `--max-calls` (hard stop), `--confirm-above` (ask above this estimate) |
| `noul` only | `--threshold` the app uses (0.5), `--metric ap` when ranking or filtering matters |

`build_state()` in the script builds the state from a case: `{"message": text}` by default. Make it
the app's own state builder, so the wording is tuned on the input the app really sends.

## The split

Cases go to **dev** (about 70%) or **reserved** (about 30%) by a hash of the case id, with the same
function as `check`'s [promote.py](../../check/examples/promote.py). The split never changes between
runs, and new cases fall on either side. Rounds only ever send dev cases; reserved cases are sent by
`finish`, once, and only their counts are printed.

## Commands

```sh
export TYPESAFE_API_KEY=...            # from the environment or a secret store, never a file
python3 optimize.py start  --request intent.v1.request.json --cases cases.jsonl --model vakyn-fast
python3 optimize.py try    --candidate intent.v2.request.json --rule "DSP -> CRD: ..." --rule "..."
python3 optimize.py try    --candidate intent.v3.request.json --rule "..."
python3 optimize.py finish --log promotions.jsonl
```

Everything lives in the run folder (`--run`, default `optimize-run/`): `run.json` (the state of the
run), `answers.jsonl` (every answer, by wording hash, model and case id) and `report.md`. A stored
answer is never asked again, so a stopped run continues where it stopped and a finished run can be
replayed with no key.

## One round

1. **Misses**: the script prints the dev misses grouped by kind, biggest first
   ([miss groups](miss-groups.md)). Show the top groups to the person with a few cases each.
2. **Cause**: for each group, the cause from [diagnose](../../questions/references/diagnose.md).
3. **Candidate**: copy the current best file to the next version and add **one rule per group**
   ([writing rules](writing-rules.md)). Same question name, same type, same keys.
4. **Checklist**: run the [pre-send checklist](../../start/references/checklist.md) on it.
5. **Score**: `try`. Kept only if better on dev; on a tie, the shorter wording stays. A discarded
   candidate is not lost: it is in `run.json` with its score.
6. **Stop** after the round limit, or after two rounds with no gain (the script says so).

One or two rounds usually take most of the gain: the first fixes the big groups (often bare or vague
options), the second a boundary or a cue. Later rounds write rules for ever smaller groups, which
is where wording starts to fit the dev cases.

## Budget

`start` prints the estimate before any call: dev cases × (1 + rounds) + reserved cases × 2 (both
wordings, at the end). Stored answers make the real number lower. On VAKYN Cloud, give the person
the estimate with the cost from `GET /v1/models` ([cost](../../start/references/cloud.md#cost)) and
wait for a yes; above `--confirm-above` the script stops until `--yes`. `--max-calls` stops the run
when it would go over, with the answers so far kept.

The script sends 8 requests at a time, retries `429` and `503` after `retry-after`, and stops with a
clear message on `401` (key), `402` (balance) or a `429` that does not clear. Keep the total under
the key's rate limit (VAKYN Cloud: 60 requests per second).

## The end

`finish` scores the starting and the best wording on the reserved set, applies `check`'s promotion
rule, appends one line to the promotion log, and writes `report.md`. Read it with
[reading the result](reading-results.md). A run is closed after `finish`: more rounds need a new run
folder, and the reserved set should grow first.

## Example (sample files)

[intent.v1.request.json](../examples/intent.v1.request.json) asks which team code fits a bank
customer's message, with bare codes as options (`"CRD": "CRD"`).
[cases.sample.jsonl](../examples/cases.sample.jsonl) holds 64 labeled messages: 44 dev and 20
reserved. [answers.sample.jsonl](../examples/answers.sample.jsonl) holds VAKYN's real answers on
`vakyn-fast` for both wordings, so this runs with no key:

```sh
mkdir optimize-run && cp answers.sample.jsonl optimize-run/answers.jsonl
python3 optimize.py start --request intent.v1.request.json --cases cases.sample.jsonl --rounds 1
```

```text
Question 'intent' (choice), model vakyn-fast, wording 53dc5b11bd9c.
64 labeled cases: 44 dev, 20 reserved (split by a hash of the case id).
Estimate: up to 128 calls to VAKYN (44 dev x (1 + 1 rounds) + 20 reserved x 2, at the end). ...

Current wording on dev: accuracy 0.477 (21 of 44)
Misses on dev, grouped by kind (write one rule per group, biggest first):
  DSP -> TRF: 6
    c013 (0.26): {"message": "There's a payment of 89.99 to a shop called NOVAMART that I never made."}
    ...
  CRD -> OTH: 5
    c001 (0.17): {"message": "I lost my debit card on the train this morning. Please block it."}
    ...
  DSP -> FEE: 5
  CRD -> ACC: 2
  CRD -> TRF: 1
```

Every group has the same cause: the options are bare codes, so the model guesses what `DSP` or
`CRD` means, at low confidence. One rule fixes them all: describe every option.
[intent.v2.request.json](../examples/intent.v2.request.json) does that and keeps every key.

```sh
python3 optimize.py try --candidate intent.v2.request.json \
    --rule "DSP -> TRF, DSP -> FEE, CRD -> OTH, CRD -> ACC: bare codes; describe what belongs in every option"
python3 optimize.py finish
```

```text
Round 1: intent.v2.request.json (4c7ff97b8e62)
  best so far  accuracy 0.477 (21 of 44)   [intent.v1.request.json]
  candidate    accuracy 0.955 (42 of 44)
Keep the candidate: better on dev.

Reserved set (20 cases; counts only)
  start  accuracy 0.650 (13 of 20)   [intent.v1.request.json]
  best   accuracy 0.850 (17 of 20)   [intent.v2.request.json]

Better on dev: yes. Not worse on reserved: yes.
Verdict: PROMOTE intent.v2.request.json
Dev gained 0.28 more than reserved (20 reserved cases: one case is 0.05). Check that every rule is
general, not about single dev cases; ...
```

How to read it: the one rule is general (it names no case), so the gap between dev and reserved is
mostly the small reserved set: 20 cases, and the start already got 13 of them right. Promote, and
grow the reserved set from the live flow. The two dev misses left are single cases (a stolen card's
payments, the fee for a replacement card): one case each is not a group, so no round 2.
These numbers are for this sample on `vakyn-fast`; the person's question and cases give their own.
