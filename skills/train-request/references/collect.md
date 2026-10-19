# What to collect

Read the person's project; change nothing. Everything here goes into the proposal as a short
description or a count, never as raw data. Name the file each fact came from, so the person can
check it.

## The decisions

| Look for | Where | Goes into the proposal as |
|---|---|---|
| Each VAKYN question: type, options or levels, instructions | Request files (`*.request.json`), SDK calls (`Choice(`, `Noul(`, `Score(`), `vakyn-research.md` | Question name, type, the options in one line each |
| What the state holds | The state builder (`build_state`, the dict or object sent as `state`) | Field names and what they hold ("the customer's email body, 50–400 words") |
| What code does with each answer | The branch on the pick, thresholds | One line: "billing goes to the refunds queue; below 0.8 to a person" |
| Language and document length | Sample inputs, the state builder, logs (counts only) | "English and German; most under 500 words, some contracts over 10,000" |
| Decisions not on VAKYN yet | `vakyn-research.md` ranking, prompts that parse a chat model's pick | Listed as possible next decisions, marked as not measured |

## The results

The proposal is only as strong as its measurements. Look for, in this order:

1. `optimize` runs: `optimize-run/report.md`, `run.json`, the promotion log. They give accuracy on
   dev and reserved, before and after wording tuning, with counts, per model.
2. `check` results: smoke-test results files, log summaries, threshold tables, calibration tables,
   drift reports.
3. Labeled-case files (`*.jsonl` with a `label`): how many per option, who labeled them.
4. Side-by-side logs from `convert` (`vakyn_pick`, `chat_pick`, `agree`): agreement, not accuracy.

From them, per question:

- accuracy (or exact level, or average precision) on reserved or held-out cases, with counts;
- the model it was measured on (`vakyn-fast` or `vakyn-max`);
- the **losing cells**: the biggest groups of misses after tuning (option pairs such as
  `refund -> billing: 14 of 40 refunds`; `noul` false negatives; `score` too high), and slices
  that fail more (a language, long documents, one document type);
- the share of answers below the threshold that go to a person today.

No results file: say so plainly in the proposal ("not measured yet"), and offer to run `check`
first. A proposal without measurements is still useful as a first contact, but say what it lacks.

## The setting

Ask in one round; leave out what the files already answer:

- **Value**: what a right answer saves or a wrong one costs (time, money, risk), in their words.
- **Target**: the accuracy, or the share sent to a person, that would make it worth switching.
- **Volume**: decisions per day or month, and peaks.
- **Speed**: how fast an answer must come back.
- **Where it runs**: VAKYN Cloud (region) or their own servers (hardware, no connection out).
- **Compliance**: personal or health data, GDPR, HIPAA, sector rules.
- **What they can share**: how many labeled cases, who labeled them, whether they can be shared
  under a DPA, or only made-up look-alikes.
- **Contact**: who at their company owns the decision.

## What not to collect

- Raw records, customer text, file contents, screenshots.
- Keys, tokens, connection strings, internal hostnames.
- Code beyond the question definitions; their code stays theirs.
- Anything from `~/.config/vakyn/env` or `.env` (never open them).
