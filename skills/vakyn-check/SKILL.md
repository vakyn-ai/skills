---
name: vakyn-check
description: "Prove a VAKYN setup on the person's own data and keep it right. Use to test VAKYN against their chat model on a sample (\"smoke test\", \"does it agree with GPT?\"); summarize a side-by-side log; pick thresholds from labels (\"what threshold for 2% errors?\"); check calibration or reliability (\"is 0.9 really 90%?\"); run a drift or regression check after a model upgrade or prompt change, or a CI check for question changes; or review VAKYN code before go-live (limits, 429, timeouts, keys, logging, fallback). Wording fixes: vakyn-questions."
---

# VAKYN check: test on your data, then go live

The person has VAKYN questions that work on a few examples. This skill shows whether they hold up
on the person's own records, how they compare with the chat model in use today, where to set the
threshold for unsure answers, and what the code needs before production.

Write small scripts **into the person's project**, in their language (Python or TypeScript, with
the official SDK; see the [SDK guide](../vakyn/references/sdk.md)). The files in
[examples/](examples/) are templates to adapt, not tools to run from these skills.

## Pick the step

| The person… | Do |
|---|---|
| Wants to try VAKYN on their records next to their chat model | [Smoke test](references/smoke-test.md) |
| Has a side-by-side log from a converted app | [Log summary](references/log-summary.md) |
| Has labeled records and asks where to set the threshold | [Thresholds](references/thresholds.md) |
| Asks whether confidence means what it says ("is 0.9 really 90%?") | [Calibration](references/calibration.md) |
| Changed the model file, server, questions or state builder; wants a CI check | [Drift check](references/drift.md) |
| Is about to go live, or shows VAKYN code for review | [Go-live review](references/go-live.md) |
| Gets odd answers on many records | Fix the question first: `vakyn-questions` skill |

Usual order: smoke test → side by side in the app (`vakyn-convert`) → log summary → label the
disagreements → thresholds and calibration → go-live review → drift check after every change.

## Smoke test (about 30 records)

1. Ask which records, which question, which chat model and how it is called today, and whether
   person labels exist.
2. **Ask before sending data anywhere outside their machine.** A hosted chat model receives the
   records and charges per call. Without a clear yes, use the chat model's past answers from their
   logs, or run VAKYN alone. Confirm which VAKYN server too.
3. Pick a sample that covers every option, with named hard cases (mixed topics, vague, "none of
   these"); redact personal data in code before anything is sent.
4. Same evidence and the same options (escape option included) for both, by default. Their
   production prompt as it is can be an extra column. Run the
   [pre-send checklist](../vakyn/references/checklist.md).
5. Run it, stop at the sample size, keep every answer in a results file.
6. Report agreement, accuracy against labels when they exist, every disagreement side by side,
   every unsure answer, measured time per call and chat-model cost. Then stop and let them decide.

Before anything runs, send the plan ([plan message](references/smoke-test.md#5-before-running-the-plan-message)),
and say in it, in these words: "agreement is not accuracy"; their labels decide who is right.

Template: [smoke_test.py](examples/smoke_test.py) with
[smoke-test.request.json](examples/smoke-test.request.json).

## Log summary

Read the JSON-lines log (`ts`, `request_id`, `vakyn_pick`, `vakyn_confidence`,
`vakyn_probabilities`, `chat_pick`, `agree`, `mode`, `used`, and `question` when a converted
prompt logs several questions; details in [log summary](references/log-summary.md)). Count the
lines where VAKYN failed apart. Per question, report agreement overall and per option, confusion
pairs, the share below each threshold and agreement above it, and the disagreements to label
first. End with a recommendation and what evidence would change it. Template:
[log_summary.py](examples/log_summary.py) on [side-by-side.sample.jsonl](examples/side-by-side.sample.jsonl).

## Thresholds

From person-labeled records ([how many](references/thresholds.md#starting-values-and-sample-sizes))
and the person's target error
rate: hold out about 30%, tabulate coverage and error rate per candidate threshold on the rest,
pick the lowest threshold that meets the target, check it on the held-out part, and say how far
the sample can prove it. Starting values, until labels exist, are on the same page. `noul` uses distance from 0.5 or separate yes / no cut-offs; `choice` and
`score` use `confidence`. Template: [thresholds.py](examples/thresholds.py) on
[labeled.sample.jsonl](examples/labeled.sample.jsonl).

## Calibration

On the same labeled file: group records by confidence (`noul`: by the `noul` value, both sides),
and per group show count, mean confidence, share right, gap and a 95% range; then the calibration
error (weighted mean gap) in plain words, per question. Mark groups with too few records and
read nothing from them; under 50 records, say it cannot judge calibration yet
([sample sizes](references/thresholds.md#starting-values-and-sample-sizes)). Only their own labeled
records from the real flow; never public benchmarks. Template: [calibration.py](examples/calibration.py).

## Drift check

Save a reference batch once (100–300 representative records, answers stored with question hash,
model name, model file, request id) at concurrency 1 or 2. Re-run it after any change to the model
file, server, question text or state builder; report picks changed, mean change, threshold
crossings, picks per option and the changed records biggest first. Moves within the noise
tolerance do not count. Pass or fail against the person's limits; in CI on pull requests that touch
questions. Template: [drift.py](examples/drift.py), [drift-ci.yml](examples/drift-ci.yml).

## Go-live review

Walk the [checklist](references/go-live.md): batching, size limits, concurrency vs `--max-queue`
and 429 `retry-after`, timeouts, key handling and rotation, logging request ids and model name,
unsure rate and drift, fallback when the server is down, re-check after changes. Give a table of
item, status and fix, then the code changes.

## Rules

- **Agreement is not accuracy.** Two models can be wrong the same way. When a person's label
  exists, compare to the label.
- **Never rerun to get a better-looking answer.** The same request gives the same numbers. A changed
  question is a new test; keep both results.
- **Keep every answer.** No dropping odd records from counts or tables.
- **Ask before data leaves the machine or money is spent.** Wait for the yes; no paid chat-model
  call and no full batch without it.
- **Measure, never guess.** Times and costs come from this run on this machine, with the machine
  named. No server, no numbers: write the script and say how to run it.
- **Keys stay out of the chat and out of code.** A key found in code or a log is named by where it
  is (file and line), never repeated in the reply. See the `vakyn` skill rules.
