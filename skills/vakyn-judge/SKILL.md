---
name: vakyn-judge
description: "Grade chat-model or agent outputs against a rubric with VAKYN, for evals, CI and production monitoring, and make the grades match the person's experts. Use for LLM-as-judge, eval graders, rubric to questions, pass/fail criteria, groundedness or faithfulness checks, pairwise A/B comparison, agreement with expert or human labels, judge alignment, pytest, promptfoo or Langfuse scores, grading every trace. A grader inside a new app's flow: vakyn-workflow. Thresholds for routing unsure answers: vakyn-check."
---

# VAKYN judge: grade outputs against a rubric

The person has outputs from a chat model or an agent (replies, answers, summaries, tool runs) and a
rubric, written or in their head. This skill turns the rubric into VAKYN questions, grades each
output in one request, checks the grades against the person's experts, and wires the grader into
CI and monitoring. VAKYN grades; it does not write or fix the output.

Shared material: [API reference](../vakyn/references/api.md),
[SDK guide](../vakyn/references/sdk.md), [pre-send checklist](../vakyn/references/checklist.md),
question rules in the `vakyn-questions` skill
([question types](../vakyn-questions/references/question-types.md),
[options and levels](../vakyn-questions/references/options-and-levels.md),
[state](../vakyn-questions/references/state.md)).

## Pick the step

| The person… | Do |
|---|---|
| Has a rubric (a list, a doc, a judge prompt) and wants VAKYN to grade with it | [Rubric to questions](references/rubric-to-questions.md) |
| Wants to compare two outputs (model A vs B, old vs new prompt) | [Pairwise](references/rubric-to-questions.md#pairwise-two-outputs) |
| Has expert pass/fail labels, or says the grades look wrong | [Alignment](references/alignment.md) |
| Wants a CI gate, a promptfoo eval or Langfuse scores | [CI and monitoring](references/ci-and-monitoring.md) |
| Asks whether a high confidence means the grade is right | [Pitfalls](references/pitfalls.md) |
| Needs the threshold for routing unsure grades to a person | `vakyn-check` skill, [thresholds](../vakyn-check/references/thresholds.md) |

Usual order: rubric to questions → grade 10–20 outputs → expert labels → alignment → CI gate →
monitoring on every trace → re-run alignment when the rubric changes.

## Steps

1. **Collect the rubric** and two or three real outputs with what the expert said about each. Ask
   which criteria are must-pass (one failure fails the output) and how the rest are weighted.
2. **One question per criterion** ([rubric to questions](references/rubric-to-questions.md)):
   a `noul` per pass/fail criterion (one proposition, `true` and `false` described); a `score`
   only where the levels are truly ordered and each level is described; a `choice` with a
   cannot-tell option (`not_enough_evidence`) when the criterion may need facts that are not in
   the state. Split any criterion with "and" in it.
3. **State**: `task`, `input`, `output`, and `reference` or `sources` when they exist, `rules`.
   Evidence only, never a chat model's opinion of the output.
4. **One output per request, every criterion in that request.** Never two outputs in one request.
   Pairwise: a `choice` over the two, asked in both orders, combined in code.
5. **Verdict in code**: every must-pass criterion passes, then a weighted score over all of them.
   A must-pass criterion in the unsure band means "a person grades it", never a pass.
6. **Run the [checklist](../vakyn/references/checklist.md)** and write each request as a `.json`
   file (the literal JSON, so the person can read it and send it with curl). Send it if a server is
   reachable and show the real answers.
7. **Align with the experts** before trusting the grades: agreement per criterion on held-out
   labels ([alignment](references/alignment.md)).
8. **Wire it in**: pytest or promptfoo in CI, Langfuse scores on every trace
   ([CI and monitoring](references/ci-and-monitoring.md)).

## Examples

All answered by a running VAKYN 4B; numbers in the reference pages.

| File | What |
|---|---|
| [rubric.py](examples/rubric.py) | Five-criterion rubric for support replies as data, state builder, verdict in code |
| [support-reply-rubric.request.json](examples/support-reply-rubric.request.json) | A good reply, all five criteria in one request |
| [support-reply-failing.request.json](examples/support-reply-failing.request.json) | A reply that breaks two rules and asks for card details |
| [grounded-answer.request.json](examples/grounded-answer.request.json) | An answer checked against retrieved sources, with a cannot-tell option |
| [pairwise.request.json](examples/pairwise.request.json) | Two replies compared; run it again with the replies swapped |
| [judge.py](examples/judge.py) | Grade a JSONL of outputs ([replies.sample.jsonl](examples/replies.sample.jsonl)) |
| [align.py](examples/align.py) | Agreement per criterion on [40 expert labels](examples/expert-labels.sample.jsonl), offline from [stored answers](examples/vakyn-answers.sample.jsonl) |
| [test_replies.py](examples/test_replies.py) | pytest gate over [saved cases](examples/ci-cases.sample.jsonl) |
| [promptfooconfig.yaml](examples/promptfooconfig.yaml), [vakyn_assert.py](examples/vakyn_assert.py) | promptfoo Python assertion |
| [langfuse_scores.py](examples/langfuse_scores.py) | Grade recent traces, write scores back |

## Rules

- **One criterion, one question; one output, one request.** Combining is code's job.
- **The verdict is code.** Must-pass gates, weights, the pass mark and rounding never go into a
  question.
- **Confidence is not accuracy, and agreement with a chat-model judge is not accuracy.** Only the
  person's expert labels say whether a grade is right ([pitfalls](references/pitfalls.md)).
- **Never tune on the items you report.** Rewrite criteria from the tune part; report the held-out part.
- **Rewrite the criterion text before moving a threshold.** Most disagreements are wording.
- **Re-run alignment when the rubric, the state or the model file changes.**
- **Never invent grades.** No server, no numbers: write the requests and code; say how to send them.
- **Keys stay out of the chat and out of files**: `TYPESAFE_API_KEY` in the environment.
