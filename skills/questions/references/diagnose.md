# Diagnose a bad answer and rewrite the request

You need the request and the full response. If the person only has the pick ("it said billing"),
ask for both; the cause is usually in the request, and the distribution shows where to look.

## 1. Read the answer

| What you see | What it usually means |
|---|---|
| `choice` split between two options (0.45 / 0.40) | The two options overlap, or both are true |
| `choice` spread thin over many options | Vague descriptions, or the state lacks the deciding fact |
| A confident pick that is plainly wrong | No option fits and there is no escape option; or a conclusion in the state; or the question is about another subject |
| `noul` near 0.5 | Two propositions in one question, missing evidence, or a yes/no boundary that needs `true` / `false` descriptions |
| `score` spread over many levels, low confidence | Levels are bare numbers or labels, overlap, or measure two things |
| A wrong answer to a rule ("under $50", "older than 30 days") | Arithmetic or a rule the model was asked to compute |

## 2. Find the cause

Check the request for each cause, in this order. More than one can apply.

| Cause | How to spot it | Fix |
|---|---|---|
| **Missing evidence** | The deciding fact (date, plan, earlier message, policy) is not in the state | Add it to the state, or add a `not_enough_evidence` option |
| **Vague options or levels** | Bare labels (`"billing": "Billing"`), `"1"`–`"5"`, `"medium"` | One-line descriptions of what belongs in each; levels described by what you would observe |
| **Overlapping options** | Two options can both fit the input | Sharpen the boundary in the descriptions, or one `noul` per option |
| **No escape option** | Every option is a real category and the input fits none | Add `other` / `no_match` / `not_enough_evidence` with a description |
| **Compound question** | `and` / `or` in a `noul`, or a score over two dimensions | Split into one question per proposition; combine in code |
| **Conclusion in the state** | A summary, verdict, health flag or another model's opinion sits next to the evidence | Remove it; keep the evidence it was based on |
| **Wrong subject** | The question says "it" or "the text" and the state has several texts; or it asks about the writer when the person meant the product | Name the field in plain words: "the agent's reply", "the customer who wrote the message" (`state.reply` also works) |
| **Rule or arithmetic in the question** | Sums, dates, thresholds, lists of allowed values | Compute in code; pass the result as a fact or narrow the options |
| **Instructions inside the data** | User text in the state tells the model what to answer | Keep user text under its own key; check the pick in code |
| **Positions instead of names** | `option_1`, "the second product", "answer A or B" | Name options by the item's id with a description |

## 3. Rewrite

- Change what the cause needs and keep the rest, so the person can see which change mattered.
- Keep the question names the code reads where you can, but never keep a compound question to
  save a name. Split it, and give the person the line of code that rebuilds the old value from the
  new answers (`remove = personal_info > 0.8 or insult > 0.8`).
- Run the [pre-send checklist](../../start/references/checklist.md) on the rewrite.
- Save the rewrite as a `.json` file next to the original when the person works in a project.

## 4. Explain

Two or three plain lines per cause:

> **Cause:** no option fits a partnership pitch, so VAKYN had to pick a team; `product` won at 0.95.
> **Change:** added `other` with a description of what it covers, and described every team.
> **Expect:** off-topic messages land in `other`; route `other` to a person in code.

## 5. Check

If VAKYN is reachable, send the old and the new request and show both answers side by side.
If the new one is not better, look for a second cause. If VAKYN is not reachable, say so and do
not predict numbers.

One bad answer is one record. Before calling the request fixed, try it on a few more of the
person's records, including easy ones, so the rewrite does not break what already worked. For a
real test on many records, use the `check` skill. With 50 or more labeled cases, the `optimize`
skill runs this page as a measured loop: it groups the misses, adds one rule per group and keeps a
rewrite only if it scores better ([the loop](../../optimize/references/loop.md)).
