# Pitfalls

## Confidence is not accuracy

A `noul` of 0.99 says VAKYN is sure of its answer to the question asked. It does not say the
answer matches the expert. A badly worded criterion gets confident answers to the wrong question:
in the [alignment](alignment.md) example, the first draft of `next_step` passed "Our team will
review your meal preferences shortly" at 0.90; the experts failed it. Only expert labels measure
accuracy. More on what confidence means: [confidence](../../vakyn-questions/references/confidence.md).

## Agreement with a chat-model judge is not accuracy

Matching an existing chat-model judge shows the two graders behave alike, not that either is
right. Two graders can share a blind spot. Use the chat-model judge's grades to find outputs worth
labeling (where the two disagree), then measure both against expert labels.

## Criteria that need facts not in the state

"Is the price in the reply correct?" cannot be judged without the price list. Either put the facts
in the state (`sources`, `reference`, `rules`), or ask a `choice` with a cannot-tell option
(`not_enough_evidence`: "the state does not hold what is needed to check this") and send those
outputs to a person. A `noul` without the facts gets a guess.

## Rubric drift

Agreement numbers belong to one version of the criteria, the state builder and the model file.
When any of them changes, the old numbers no longer hold:

- re-run alignment on the held-out labels (the stored answers in
  [align.py](../examples/align.py) let you compare old and new side by side);
- re-check the thresholds ([thresholds](../../vakyn-check/references/thresholds.md));
- keep the criteria under version control and log the version with every grade.

Experts drift too: what counted as a next step last quarter may not now. Re-label a small sample
from time to time and compare.

## Smaller traps

- **Grading two outputs in one request.** Each answer then sees both. One output per request;
  pairwise is a `choice` asked in both orders.
- **One overall score.** It hides which criterion failed and cannot be re-weighted.
- **A 1–10 scale for a pass/fail judgment.** Ask a `noul`.
- **The output's own claims as evidence.** "As our policy says, refunds go to the card" in the
  output is not the policy. The policy goes in `state.rules`.
- **Counting `review` as pass.** An unsure must-pass criterion is a person's call.
