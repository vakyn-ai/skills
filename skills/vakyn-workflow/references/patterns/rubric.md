# Rate with a rubric: score on described levels

**Use when** something gets a grade on a scale: a support reply, an essay, a job application, a
pull request description. Several criteria → several scores, combined in code.
**Not when** the grade is a count or a sum (words, years, errors found by a tool): compute it.

## The request

[examples/rubric.request.json](../../examples/rubric.request.json): the policy, the customer's
message and the agent's reply in the state; three `score` questions, one per criterion, four
levels each, lowest first, every level described by what a reader would see.

Answer from a running VAKYN 4B for a correct refund reply: `answers_question` 2.82,
`follows_policy` 2.79 (confidence 0.79), `tone` 2.00 ("Friendly and polite", 0.97).

## The code

[examples/rubric.py](../../examples/rubric.py)

- One request holds every criterion (they are independent).
- Code turns each score into 0–1 (`score / (levels - 1)`), weighs them and adds them up.
- Code applies the hard rule: `follows_policy` below 1.5 goes to a lead, whatever the total.

Run on four replies: a correct refund → `pass` (total 0.91); "fixed by Friday, guaranteed" →
`lead_review` (policy 0.01); "Refunds are not possible" after 3 months → `lead_review` (policy
0.94: store credit was due); store credit offered → `pass` (0.71).

## Unsure path

Any criterion below `MIN_CONFIDENCE` → a lead grades it. A score's confidence is low when the
probability is spread over levels far apart; read `probabilities` to see where.

## Common mistakes

- **Two things in one level.** "Follows the policy exactly and explains it clearly" split the
  answer for a correct reply (confidence 0.45). Levels that only describe the policy ("Fully
  within the policy") brought it to 0.86. Each criterion measures one thing; add a criterion for the other.
- **One overall score.** "How good is this reply?" hides why. One score per criterion, combined in
  code, can be explained and re-weighted.
- **Weights in the question.** "Policy counts double" belongs in code.
- **Bare levels** (`"1"`–`"5"`) or levels by adjective ("poor", "good") with nothing observable.
- **Reading `score` as a level.** It is a weighted average (2.45 is not a level). For a level,
  take the most likely one from `probabilities`.
