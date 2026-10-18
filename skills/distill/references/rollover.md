# Roll over in stages, then report

The agent keeps working while the program earns traffic. Template:
[rollout.md](../examples/rollout.md).

## Stages

1. **Learn.** The first cases (about 100, or what the person has) stay with the agent, fully
   traced, with notes. They become the development set; the reserved set is split off first.
2. **Shadow.** The program runs on every new case and only logs. The agent decides. Compare per
   case: the agent's outcome, the program's outcome, the label.
3. **Share.** A growing share of new cases may try the program: for example 50%, then 75%, then
   90%. Pick cases by a hash of the case id, so the split is stable. Anything the program
   escalates goes to the agent, whole, so no case is left undecided.
4. **All.** Every case tries the program; the agent stays as the fallback and persons keep the
   hard judgments.

Move one stage per batch, and only when the batch report meets the bar the person set before the
batch (agreement with labels on handled cases, no costly mistake such as approving a case the
label escalates, an escalation rate). A costly mistake sends the rollout back one stage.

## New versions

After each batch, read the disagreements and the escalations, then propose a candidate version.

- **Which question first:** the one with the lowest confidence on the wrongly decided cases
  ([tuning](../../check/references/tuning.md#which-question-to-rewrite-first)).
- **Promote only if better:** the candidate beats the current version on the development set and
  is not worse on the reserved set
  ([promotion rule](../../check/references/tuning.md#the-promotion-rule)).
- **Code-only changes** (a rule, a threshold, the order of steps) are replayed on the stored
  decision records, with no model calls ([replay](../../check/references/replay.md)).
  **Question changes** are re-asked on the development set
  ([drift check](../../check/references/drift.md)).
- Fingerprint every version (procedure, agent prompt, program, questions, thresholds) and keep
  the scores behind each promotion.

## Report

Write it from the decision records and the traces, with a short script; every figure measured or
as logged, with where it came from.

| Figure | From |
|---|---|
| Cases, and the share handled by the program without escalation | decision records |
| Escalation rate: to the agent, to a person | decision records |
| Agreement with labels on handled cases; the agent's on the same cases | records + labels; traces + labels |
| Disagreements to review, by case id, with the reasons | records + labels |
| VAKYN requests and agent look-ups per case; time per case (with the machine) | decision records |
| Agent tool calls, cost and time per case | traces, as logged |
| Program cost per case | look-ups × the agent's price per look-up (from the person) + VAKYN: on VAKYN Cloud, the requests' `usage.input_tokens` × the price from `GET /v1/models`; on their own server, its running cost. Never a guessed price |

Say which set the figures come from. Agreement on the development set is not a result: the
program was written while looking at those cases. Only the reserved set and live batches count.
Agreement with the agent is not accuracy; labels decide.

Template output: the `report()` function in [program.py](../examples/program.py).
