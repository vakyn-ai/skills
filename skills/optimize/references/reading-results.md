# Reading the result

`optimize.py finish` scores the starting wording and the best wording once on the reserved set,
prints a verdict, and writes `report.md` in the run folder. This page is how to read it and what to
tell the person.

## The verdict

Same rule as `check` ([tuning](../../check/references/tuning.md#the-promotion-rule)):

| Better on dev | Not worse on reserved | Verdict |
|---|---|---|
| yes | yes | **Promote**: switch the app to the new file |
| yes | no | **Keep** the start: the wording fits the dev cases, not the flow |
| no | any | **Keep**: no round beat the start |

Say it in those words, with the counts from the script, for example: "right on 21 of 44 dev cases
before, 42 after; 13 of 20 reserved before, 17 after". Counts, not only rates, so the person sees how small
the sets are.

## How sure the result is

- With 20 reserved cases, one case is 5 points. "Not worse" on a small reserved set is a weak bar:
  say so, and suggest labeling more cases from the live flow before relying on it.
- A gain of one or two cases on dev is noise. The script keeps it, but do not report it as a
  real gain.
- The result is for **the model it was tuned on**. A round that helps `vakyn-fast` can hurt
  `vakyn-max`, and the other way round. Before switching another model to the new wording, run
  `start` with `--model` set to that model on a new run folder, and keep one file per model if
  the best wordings differ.

## Overfitting

Signs the wording fits the dev cases and not the flow:

- dev rose much more than reserved (the script warns when dev gained 10 points more);
- rules that mention details of single cases (a shop name, an amount, a date);
- many rules for small groups (one or two cases each);
- reserved got worse while dev got better (the script does not promote).

Fix: go back to the best wording with fewer, more general rules (one per large group), and run
again on a **new** run folder. The reserved set has been seen once by counts; that is allowed, but
each new look leaks a little, so add fresh labeled cases to it over time.

## After promoting

1. Switch the app to the new request file; keep the old file for rollback.
2. The promotion log (`--log`) has both wording hashes, scores on both sets, the verdict, the date,
   the model and the calls. Keep it in the repo next to the request files.
3. Run a [drift check](../../check/references/drift.md) on the reference batch: a changed question
   changes answers outside the labeled cases too.
4. If the app uses a threshold, check it again on the new wording
   ([thresholds](../../check/references/thresholds.md)): confidence can move.

## What to report

- The before and after table (from `report.md`), with counts.
- Each rule kept and the group of misses it was written for.
- The verdict and the reason in one line.
- Model calls used, and on VAKYN Cloud the cost estimate the person agreed to.
- What would make the result stronger: more labeled cases, more reserved cases, one more option
  that is rare in the labels.
- Still short of the target after tuning: the misses wording cannot fix are what the VAKYN loop
  trains on. The `train-request` skill writes that request from this report.

Never report a score that the script did not print. If the run did not happen (no key, no
server), say what to run and stop.
