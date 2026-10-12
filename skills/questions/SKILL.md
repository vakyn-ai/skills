---
name: questions
description: "Write and fix VAKYN questions. Use when someone is writing a VAKYN request and asks whether a judgment should be a noul (yes/no), choice or score; wants options, an escape option (\"other\", \"none\", \"not enough evidence\"), structured option descriptions (includes, not) or score levels written; asks what to put in the state; has a rule, date or sum inside a question; or got a VAKYN answer that looks wrong, unsure or confidently wrong (\"why did it pick billing?\", \"why is the noul 0.4?\") and wants the cause and a rewrite. Also explains what confidence means."
---

# VAKYN questions: write and fix

A VAKYN request is a **state** (the evidence) and named **questions** about it. Most bad answers
come from the request, not the model: a question that asks two things, options that overlap, no
way to say "none of these", a state that holds someone's conclusion instead of the evidence, or a
rule the model was asked to compute. This skill writes requests that avoid these and repairs
requests that hit them.

Field shapes, limits and errors: [API reference](../start/references/api.md). Code:
[SDK guide](../start/references/sdk.md). Every request you write or fix passes the
[pre-send checklist](../start/references/checklist.md).

## Pick the step

| The person… | Do |
|---|---|
| Has a judgment and asks how to ask it | [Choose the type](references/question-types.md) |
| Needs options, an escape option or score levels | [Options and levels](references/options-and-levels.md) |
| Has options that get mixed up, or long definitions | [Structured descriptions](references/options-and-levels.md#structured-descriptions) |
| Asks what to send as the state | [Design the state](references/state.md) |
| Has rules, sums, dates or thresholds in a question | [Move it into code](references/state.md#move-exact-work-into-code) |
| Has several questions, some depending on others | [One request or two](references/question-types.md#one-request-or-two) |
| Shows a request and an answer that looks wrong | [Diagnose and rewrite](references/diagnose.md) |
| Asks what confidence means | [Confidence](references/confidence.md) |
| Asks where to set a threshold | the `check` skill |

## Write a request

1. **List the judgments.** Write each as one plain sentence: "which team gets this message",
   "does it ask for money back", "how soon does it need a reply".
2. **Take out what code can do.** Totals, dates, "over $500", "more than 3 days", lookups and
   policy rules stay in code. Only the part that needs reading and judgment goes to VAKYN.
3. **Pick a type per judgment** ([question types](references/question-types.md)):
   - yes or no about one fact → `noul`;
   - one of several named, exclusive options → `choice`;
   - a place on an ordered scale → `score`;
   - several facts that can all be true → one `noul` each.
4. **Write the answers.** `choice`: stable snake_case names, a description each, and an escape
   option. When options are easy to mix up, make the description an object with what it covers,
   includes and is not ([structured descriptions](references/options-and-levels.md#structured-descriptions)). `score`: 3–5 levels described by what you would observe, lowest first.
   `noul`: add `true` / `false` descriptions when the line between them is a policy.
   ([options and levels](references/options-and-levels.md))
5. **Build the state.** An object with plain field names. Evidence in; conclusions, other models'
   opinions and unrelated text out. Text from users or the web sits under its own key
   (`message`, `page_text`). ([state](references/state.md))
6. **Name the subject in each question, in plain words:** "Which team should handle the
   customer's message?", not "Which team?" and never "option 2". The question's name never
   reaches the model, so the instructions must say the whole question.
7. **Group by dependency.** Questions that only need the state go in one request. A question that
   needs another's answer goes in a second request, with that answer in its state.
8. **Run the [checklist](../start/references/checklist.md)**, then send it with what the machine has
   (see the `start` skill, First call). Show the answer next to the request.

## Fix a bad answer

The person shows a request and the response, or says "it picked X but should be Y". Follow
[diagnose](references/diagnose.md):

1. Read the full distribution, not only the pick. Where did the probability go?
2. Find the cause in the request: missing evidence, vague or overlapping options, no escape
   option, two questions in one, a conclusion in the state, the wrong subject, or a rule the model
   was asked to compute.
3. Rewrite the request. Change only what the cause needs, so the person sees what fixed it. Fix
   every cause you found, even when it renames a question; then show the code change it needs.
4. Explain in two or three plain lines: what was wrong, what changed, what to expect now.
5. If a server is reachable, send both and show both answers. If not, say so; never predict
   numbers.

## Examples (before and after)

Each pair is a weak request, the fixed one and a note on what changed. All were sent to a running
VAKYN 4B; the notes quote the real answers.

| Pair | What was wrong |
|---|---|
| [no-escape](examples/no-escape.md) | No "other" option, labels without descriptions: a partnership pitch went to `product` at 0.95 |
| [compound-noul](examples/compound-noul.md) | "Angry and asking for a refund?" gave 0.37 and hid a clear refund request |
| [conclusion-in-state](examples/conclusion-in-state.md) | A "health: green" note in the state and levels `"1"`–`"5"` blurred a clear churn signal |
| [rules-in-code](examples/rules-in-code.md) | Price and delivery rules in the question, products by position: it picked one over budget |

Start a new request from the closest `*.request.json`.

## Rules

- **Confidence is not accuracy.** It says how the probability is spread. A badly asked question
  can be answered with confidence 0.95 and still be wrong (see [no-escape](examples/no-escape.md)).
  Thresholds come from the person's own examples where the right answer is known: use the
  `check` skill.
- **Code decides what must be exact.** VAKYN answers judgments; code does arithmetic, dates,
  thresholds and rules, and checks the pick is one of the offered options.
- **Read answers by name.** Question names and option names are what code reads; never rely on the
  position of an option.
- **Never invent answers.** No server, no numbers. Write the request and say how to send it.
