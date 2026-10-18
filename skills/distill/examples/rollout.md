# Rollout plan: supplier onboarding program

Template. Replace the bracketed values; keep every heading. Figures in it come from logs and
labels, never from estimates.

## Versions in play

| | Version | Fingerprint |
|---|---|---|
| Procedure | `sop-2026-09` | hash of the procedure file |
| Agent (fallback and stage 0) | [harness, model, prompt version] | hash of the prompt and tool list |
| Program | `supplier-onboarding 1` | git commit |
| Questions | per step | `question_hash` in each decision record |
| Thresholds | `thresholds-2026-10-12a` | the settings block in the program |

A change to any of these is a new version. Record the version set with every case.

## Case sets

| Set | Cases | Rule |
|---|---|---|
| Development | [n] labeled cases, about 70% | read freely while writing and fixing the program |
| Reserved | [n] labeled cases, about 30% | split off **before** writing the program, by a hash of the case id; only its counts are read, once per candidate version; never read case by case |
| Live batches | each stage below | the agent's outcome, the program's outcome and the reviewer's label, per case |

Add fresh labeled cases to the reserved set from each live batch; every look at it leaks a little.
How many labels prove a rate: [sample sizes](../../check/references/thresholds.md#starting-values-and-sample-sizes).

## Stages

| Stage | Share the program may try | Fallback | Moves on when |
|---|---|---|---|
| 0. Learn | 0%: the agent handles the first [100] cases, with full traces and notes | none | the step map and program exist and pass the development set |
| 1. Shadow | 0% acting; the program runs on every case and only logs | the agent decides every case | agreement with labels on the program's handled cases is at least the agent's, on [n] cases |
| 2. Half | [50]% of new cases, chosen by a hash of the case id | every escalated or unsure case goes to the agent, whole | the batch report meets the bar below |
| 3. Most | [75]%, then [90]% | the same | the same, on each batch |
| 4. All | 100% may try | the agent stays as fallback; persons keep the hard judgments | |

Never more than one stage per batch. Any case the program escalates is still decided, by the
agent or a person, so customers see no gap.

## The bar for each batch

- Agreement with labels on cases the program handled: at least [the agent's rate on the same
  batch], with every disagreement read.
- No wrong `approve` where the label is `escalate_compliance`. One is a stop: back to the
  previous stage and fix the step that let it through.
- Escalation rate: [target, such as under 20%]. Rising escalations mean a question needs work,
  not a lower threshold.

## Promoting a new program version

After each batch, the author may propose version N+1 (a reworded question, a new rule, a
threshold). It goes live only if:

1. it beats the current version on the development set, as defined before the run (fewer wrong
   outcomes first, then fewer escalations);
2. it is not worse on the reserved set;
3. code-only changes were replayed on the stored decision records first (no model calls);
   question changes were re-asked on the development set.

Keep, per promotion: both version sets, both scores on both sets, the replay or re-run output and
who approved it.

## Report per batch

| | Agent (traces) | Program (decision records) |
|---|---|---|
| Cases | | |
| Share handled without escalation | 100% | |
| Escalated to the agent / to a person | | |
| Agreement with labels | | |
| Tool calls or requests per case | | |
| Cost per case | as logged | VAKYN requests × input tokens × [price from GET /v1/models] on VAKYN Cloud (or own server's running cost) + look-ups × [agent price per look-up] |
| Time per case | as logged | measured |
| Disagreements to review | | list of case ids |
