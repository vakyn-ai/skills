# Alignment: make the grades match the experts

A grader is useful when it agrees with the people whose judgment it replaces. Measure that per
criterion, on labels the rewrites never saw.

## 1. Collect expert labels

- Real outputs from the system being graded, including bad ones. Ask the experts for the outputs
  they argue about; those teach the most.
- Per output, per criterion: pass or fail, and a short reason for every fail. One line per output:

```json
{"id": "r02", "input": "...", "output": "...",
 "pass": {"answers_request": false, "follows_rules": true, "asks_for_secret": true, "next_step": false, "tone": true},
 "reasons": {"next_step": "No owner, no time, nothing the customer can do."}}
```

- Labels from people, not from a chat model. How many: the
  [sample-size list](../../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes)
  (the same counts apply to agreement rates).
- Ask for the person's target before measuring: "at least 90% agreement on every criterion".

## 2. Split before looking

Split once, at random with a fixed seed, before reading any result: about 70% to read
disagreements and rewrite criteria on (tune), 30% held out (check). **Never tune on the items you
report.** Rewrites that fit the tune part always look better there; only the held-out part says
whether they generalize. If you need several rounds, keep a third part for the final report or
collect new labels.

## 3. Measure per criterion

For each criterion, on the tune part:

| Number | Meaning |
|---|---|
| agreement | VAKYN and the expert give the same pass/fail, as a count and a rate ("26 of 28, 93%") |
| false pass | VAKYN pass, expert fail: the costly one for a gate |
| false fail | VAKYN fail, expert pass: noise that makes people ignore the gate |
| unsure | answers in the unsure band (`noul` between 0.2 and 0.8 by default), which go to a person anyway |

Always give the counts next to the rates. 11 of 12 and 99 of 108 are both 92%.

## 4. Read the disagreements, then rewrite the criterion text

For each disagreement on the tune part, read the output and the expert's reason, then ask in order:

1. **Is the label right?** Experts disagree with each other too. Ask; fix the label or keep it.
2. **Is a fact missing from the state?** The expert used a rule or a fact VAKYN never saw. Add it
   to the state (`rules`, `sources`, `reference`).
3. **Does the question mean what the expert means?** Rewrite the question and the `true` / `false`
   descriptions (or the levels) in the expert's words, from their reasons.
4. **Does the criterion hold two things?** Split it.
5. **Does it need exact rules, dates or arithmetic?** Move that part into code.
6. Only then consider a threshold: the [thresholds](../../vakyn-check/references/thresholds.md)
   page, on these labels.

Moving a threshold first hides a wording problem: the grader keeps asking the wrong question, just
with a different cut-off.

## 5. Re-measure on the held-out part

Report the held-out table. Stop when every criterion meets the person's target there. If one does
not, go back to step 4 with its tune-part disagreements, or label more outputs.

## Example: support replies

[align.py](../examples/align.py) on [40 synthetic labels](../examples/expert-labels.sample.jsonl),
28 to tune, 12 held out, VAKYN 4B (Q8_0, one RTX 5090). Answers are stored in
[vakyn-answers.sample.jsonl](../examples/vakyn-answers.sample.jsonl), so it runs offline:
`python3 align.py --compare first aligned`.

First draft, tune part: `answers_request` 23 of 28, `follows_rules` 21 of 28, `next_step` 23 of 28.
The disagreements and the experts' reasons showed three causes:

| Criterion | What the disagreements showed | Change |
|---|---|---|
| `next_step` | "We are looking into it" passed; experts fail it ("no owner, no time") | Question "say what happens next?" → "give the customer a concrete next step?", with `true`: "what the customer can do now, or what the team will do and by when" |
| `follows_rules` | Replies that offered nothing failed; experts judge only what is offered or promised | Question → "Is everything `state.output` commits to allowed by `state.rules`?"; `true` says a reply that offers nothing breaks no rule |
| `follows_rules` | A refund to the card passed; experts know card refunds are not allowed | The rule was not in the state: added "never refund money to the card" |
| `answers_request` | Replies that asked for a password failed; experts said they do work on the request (another criterion fails them) | `true` now says "even if it goes about it in a way another criterion fails" |

Thresholds were not touched. Held-out part (12 replies), agreement:

| Criterion | First draft | Aligned |
|---|---|---|
| `answers_request` | 10 of 12 | 12 of 12 |
| `follows_rules` | 9 of 12 | 10 of 12 |
| `asks_for_secret` | 12 of 12 | 12 of 12 |
| `next_step` | 6 of 12 | 10 of 12 |
| `tone` | 12 of 12 | 12 of 12 |

Against a 90% target, `follows_rules` and `next_step` are still below on the held-out part. The
remaining `follows_rules` misses on the tune part all sat near 0.5 (0.46 to 0.61), in the unsure
band, so they go to a person; one needs date logic ("Thursday is after the Wednesday cut-off")
that belongs in code. And 12 held-out items cannot show 90% with any certainty: the next step is
more labels, not more rewrites on the same 28.
