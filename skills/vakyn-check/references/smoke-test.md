# Smoke test: about 30 records, side by side

Goal: before any full run, see on the person's own records how often VAKYN and their current chat
model pick the same, where they differ, how often VAKYN is unsure, and what each call takes in time
and money.

## 1. Agree the setup (ask, don't assume)

Ask, in one message:

1. **Which records?** A file, a table, a log export. Where it lives.
2. **Which question?** The judgment their chat model makes now (route, yes/no check, rate, pick a
   tool). If the VAKYN request is not written yet, write it with the `vakyn-questions` skill first.
3. **Which chat model, and how is it called?** Their own prompt and provider.
4. **May records go to that chat model for this test?** If it is an external API, the records leave
   their machine and each call costs money. Say so plainly and **wait for a yes**. Without a yes,
   use answers the chat model already gave (from their logs) or run VAKYN alone.
5. **Are there person labels?** Records where someone already said what is right. They are worth
   more than any agreement number.

VAKYN on their own server keeps data on their machine. Still confirm which server
(`TYPESAFE_BASE_URL`) before sending.

## 2. Pick the sample

- About 30 records. Fewer hides problems; many more is a full run, not a smoke test.
- Cover every option or class at least twice (round-robin over labels when there are labels).
- Include hard cases on purpose, and name them in the plan: mixed topics (a late parcel *and* a
  refund), very short or vague messages, records where the answer is "none of these". A sample of
  only easy records proves nothing.
- Redact personal data before anything is sent: names, emails, phone numbers, account numbers,
  addresses. Do it in code, show what was replaced, and keep the mapping on their machine only.

## 3. Same question for both

- Same evidence: the chat model gets the same state VAKYN gets, nothing more.
- Same options with the same descriptions, escape option included. Ask the chat model for exactly
  one option name. This is the default comparison.
- Their production prompt usually has fewer options (no "other") or different wording. If they
  want it too, run it as a third column, and say it compares two setups, not two models.

## 4. Write the script into their project

Write it in their language (Python or TypeScript) with the official SDK, in their repo (for
example `scripts/vakyn_smoke_test.py`). Template: [smoke_test.py](../examples/smoke_test.py), with
the request [smoke-test.request.json](../examples/smoke-test.request.json). In TypeScript use
`@typesafe-ai/sdk` the same way ([SDK guide](../../vakyn/references/sdk.md)).

The script must:

- stop at the sample size; the full batch is a separate, later decision;
- write every answer to a results file (`smoke-results.jsonl`), including wrong and odd ones;
- record the request id, time per call, and chat-model tokens (for cost);
- read the chat model's existing answers from a file when the person did not approve sending.

Run the [pre-send checklist](../../vakyn/references/checklist.md) on the request before the first
call.

## 5. Before running: the plan message

Tell the person, in plain words and in this order, before anything is sent:

1. **Sample**: how many records, that every option is covered, and which hard cases are in it
   (name them, or ask the person for known hard records).
2. **Personal data**: what the script removes before sending, and that the removed values stay on
   their machine.
3. **Same question**: both get the same evidence and the same options, escape option included.
4. **Consent**: what would leave the machine, to whom, and roughly how many paid calls. Ask for a
   yes. Until then only the VAKYN side runs.
5. **What the report will show** (next step), and that agreement is not accuracy: their labels
   decide who is right.
6. **What you need from them**: records, server address, key set in the environment, prices.

## 6. Report

Show, in this order:

1. Counts: records, agreement `k/n` and %, VAKYN unsure count at the working threshold.
2. If labels exist: how many each got right. **That** is the accuracy number, not agreement.
3. Every disagreement side by side: record id, short redacted text, VAKYN pick and confidence,
   chat-model pick, label if any.
4. Every unsure VAKYN answer with its probabilities: where did the probability go?
5. Time per call for each (median and max, measured on this run, with the machine named) and
   chat-model cost from its tokens and the person's price. Never guess a speed or a price.
6. What to do next: fix questions ([diagnose](../../vakyn-questions/references/diagnose.md)) if
   disagreements cluster on two overlapping options; label disagreements; then thresholds.

## Rules

- **Agreement is not accuracy.** Both can be wrong the same way. When a person's label exists,
  compare to the label.
- **Never rerun to get a better-looking answer.** VAKYN gives the same numbers for the same
  request. A change to the question is a new test; keep both results.
- **Keep every answer.** Do not drop odd records from the count.
- **Stop before the full batch.** Show the report and let the person decide.
