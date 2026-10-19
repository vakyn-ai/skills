---
name: optimize
description: "Tune the wording of one VAKYN question automatically from the person's labeled cases: run it, group the misses by kind, add one rule per group to the instructions and option descriptions, keep a rewrite only if it scores better on a dev set, then confirm once on a reserved set. Use for prompt optimization, automatic prompt tuning (the idea behind DSPy optimizers), improving accuracy of a noul, choice or score question from labeled examples, bare or coded options that get confused, wording that works on vakyn-max but not vakyn-fast. One wrong answer: questions. Thresholds: check."
---

# VAKYN optimize: tune a question's wording from labeled cases

The person has a VAKYN question in use and cases a person has labeled. This skill runs a measured
loop: answer the cases, read the mistakes, rewrite the `instructions` and the option or level
descriptions with one new rule per kind of mistake, keep the rewrite only if it scores better, and
report the result once on cases the loop never saw. Nothing is trained: only the wording changes.
You (the agent) write the rewrites; the script measures them.

Shared material: [API reference](../get-started/references/api.md),
[pre-send checklist](../get-started/references/checklist.md), causes of bad answers in
[diagnose](../questions/references/diagnose.md), the dev and reserved split in
[tuning](../check/references/tuning.md).

## Pick the step

| The person… | Do |
|---|---|
| Has a question and labeled cases, wants it more accurate | [The loop](references/loop.md) |
| Shows misses and asks what rule to add | [Grouping misses](references/miss-groups.md), then [writing rules](references/writing-rules.md) |
| Has a finished run and asks whether to switch | [Reading the result](references/reading-results.md) |
| Has one wrong answer, no labels | `questions` skill, [diagnose](../questions/references/diagnose.md) |
| Wants a threshold for unsure answers | `check` skill, [thresholds](../check/references/thresholds.md) |
| Is still short after tuning, wants VAKYN trained on their cases | `train-request` skill |
| Wants to rename an option, add one or change the state | Not this loop: see the [rules](#rules) |

## Inputs

1. **The request to tune**: a request file in their project, with the model and **one** question.
2. **Labeled cases**: JSONL, one case per line: a stable `id`, the `text` or `state`, and the
   right `label` (the option key, `true` / `false`, or the level index from 0). Labels come from a
   person or from the real flow, as in `check`. Never from a chat model's guess.
3. **The model**: `vakyn-fast`, `vakyn-max`, or their own endpoint. Wording is tuned **per model**;
   the best wording for one can score lower on the other. Tuning for both is two runs.
4. **Budget**: rounds (default 5) and a hard limit on model calls.

## Steps

1. **Check the inputs.** At least 50 labeled cases, with every option that matters present. Fewer
   than 50, or an option with fewer than 5 cases: say what that does (a gain of one or two cases is
   noise; that option's result says nothing) and how many more to label. Go on only if the person
   agrees.
2. **Copy the script into their project**: [optimize.py](examples/optimize.py) (standard library).
   Edit its `build_state()` to match the app's state builder.
3. **Estimate before any call.** `start` prints the estimate: dev cases × (1 + rounds) + reserved
   cases × 2. On VAKYN Cloud each call spends balance: give the estimate and ask
   ([cost](../get-started/references/cloud.md#cost)); above `--confirm-above` the script waits for
   `--yes`.
4. **Start**: `python3 optimize.py start --request <file> --cases <file> --model <model>`. It splits
   the cases 70 / 30 by a hash of the id (same split as `check`), scores the current wording on dev,
   and prints the misses grouped by kind.
5. **One round** ([loop](references/loop.md)):
   1. Show the person the top groups of misses, with a few cases each.
   2. Find the cause of each group ([miss groups](references/miss-groups.md),
      [diagnose](../questions/references/diagnose.md)).
   3. Write **one candidate** as a new versioned file next to the old one (`intent.v2.request.json`),
      adding **one rule per group** ([writing rules](references/writing-rules.md)). Run the
      [pre-send checklist](../get-started/references/checklist.md) on it.
   4. `python3 optimize.py try --candidate <new file> --rule "<group>: <rule>"` (once per rule). The
      script keeps it only if it is better on dev; on a tie, the shorter wording stays.
6. **Stop** at the round limit, or after two rounds with no gain.
7. **Finish, once**: `python3 optimize.py finish --log promotions.jsonl`. It scores the starting
   and the best wording on the reserved set and promotes only by `check`'s rule: better on dev
   **and** not worse on reserved. Read it with [reading the result](references/reading-results.md).
8. **Report**: the before and after table on dev and reserved with counts, the rules kept and the
   misses each was for, the verdict and why, the calls used. Everything comes from the script's
   output and `report.md`; never type a number it did not print.

## Metrics

| Type | Kept when better on | Also shown |
|---|---|---|
| `choice` | accuracy | right / cases |
| `noul` | accuracy at the app's threshold (`--threshold`) | average precision; `--metric ap` when ranking or filtering matters |
| `score` | exact level | within one level, mean absolute error (tie-break) |

## Example (sample files)

Bare option codes on a bank's support messages:
[intent.v1.request.json](examples/intent.v1.request.json) (`"CRD": "CRD"`, `"DSP": "DSP"` …),
64 labeled cases in [cases.sample.jsonl](examples/cases.sample.jsonl), and a first round in
[intent.v2.request.json](examples/intent.v2.request.json): every group of misses came from the bare
codes, so the one rule is a description for every code, keys unchanged. Real `vakyn-fast` answers
for both wordings are stored in [answers.sample.jsonl](examples/answers.sample.jsonl), so the whole
loop runs with no key ([walk-through](references/loop.md#example-sample-files)).

## Rules

- **Never change option keys or the question name.** The person's code reads them. Only
  `instructions` and descriptions change. A person who asks to rename or add an option: say which
  code reads the keys (the branch on the pick, stored answers, logs, thresholds per option), that
  the old answers no longer compare, and ask first. Adding an escape option is the same: ask.
- **General rules, not copied cases.** A rule may carry a short made-up example; never copy a
  reserved case, and never list dev cases. Listing cases is how wording fits dev and not the flow.
- **No rules, sums, dates or thresholds in the question.** They belong in code
  ([state](../questions/references/state.md#move-exact-work-into-code)).
- **Out of scope**: option keys, thresholds (`check`), the state's structure (`questions`),
  training the model, tuning several questions together.
- **The reserved set is read once, by counts.** Never look at its cases, never run `finish` twice
  on one run.
- **Never invent scores.** No key, no server, no stored answers: write the script, the candidate
  files and the commands, say how to run them, and stop. No number in the reply.
- **Measure on their data, never quote ours.** The gain depends on the question, the cases and the
  model.
- **Keys stay in the environment** (`TYPESAFE_API_KEY`), never in files or the chat.
- **Be gentle with the API**: concurrency 8 by default, retries on `429` / `503` after
  `retry-after`, a clear stop on `401`, `402` or repeated `429`.
