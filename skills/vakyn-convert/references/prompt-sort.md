# Convert a chat-model prompt: the sort table

A prompt that sorts, routes, flags or rates things is a list of instructions. Some are judgments
VAKYN can answer. Some are exact work that code does better. Some ask for written text, which stays
with the chat model. Some only exist because a chat model writes free text, and can go.

Worked example: [ticket-triage.prompt.txt](../examples/ticket-triage.prompt.txt) →
[ticket-triage.md](../examples/ticket-triage.md) → [ticket-triage.request.json](../examples/ticket-triage.request.json).

## 1. Split the prompt into single instructions

Number every instruction, one per line. Split sentences that do two things ("set the category and
the priority" is two lines). Keep the person's wording so they recognize each line.

## 2. Sort each line

Ask these in order and stop at the first yes.

| Ask | If yes, it goes to | Example line |
|---|---|---|
| Does it ask for text a person reads (a reply, a summary, a title)? | **keep** with the chat model | "Draft a friendly first reply" |
| Is it exact: arithmetic, dates, a lookup, a rule over known fields, a format change? | **code** | "Older than 48 hours with no reply → overdue" |
| Does it only shape the chat model's output (role, tone of the JSON, "respond only in JSON", "think step by step")? | **drop** | "Respond only with JSON" |
| Is it a rule that draws a line between answers? | **fold** into an option or level description | "Refund requests are always billing" |
| Yes or no about one fact? | **`noul`** | "Say whether they threaten to cancel" |
| One of several named, exclusive answers? | **`choice`** (add an escape option) | "Category: billing, bug, …" |
| A place on an ordered scale? | **`score`** (levels described in words) | "Priority P1 / P2 / P3" |
| Several facts that can all be true at once? | one **`noul`** each | "Tag all that apply: refund, legal, safety" |

Notes on the hard cases:

- **Mixed lines.** "P1 if they cannot use the product at all; raise one level for Enterprise" is a
  `score` (how badly it stops them) plus **code** (the plan bump). Split it.
- **Labels with rules inside.** A priority like P1–P3 is usually a scale plus rules. Ask VAKYN the
  judgment as a `score` with levels that describe what you observe, then map the level to P1–P3 in
  code, where the plan and contract rules also live.
- **Language, length, counts.** A library or a line of code does these exactly. If the person only
  supports a few languages and wants it in one call, a `choice` with `other` works too.
- **Few-shot examples in the prompt.** Do not send them to VAKYN. Keep them as test records with a
  known right answer for the `vakyn-check` skill.
- **Instructions for the kept text** ("be concise and professional") move with the kept part.

## 3. Show the table

Show one row per numbered line: the line (short), where it goes, and the question name or the code
it becomes. The person should see every line accounted for, including the dropped ones and why.

```
| # | Instruction (short)             | Goes to   | Becomes                                  |
|---|---------------------------------|-----------|------------------------------------------|
| 1 | category: billing, bug, …       | choice    | category (+ other)                       |
| 4 | refunds are always billing      | fold      | billing description                      |
| 7 | overdue after 48 h, no reply    | code      | is_overdue(ticket)                       |
| 9 | draft a first reply             | keep      | chat model, after VAKYN answers          |
|11 | respond only with JSON          | drop      | VAKYN answers are already fields         |
```

## 4. Write the request

All VAKYN questions that only need the ticket go in **one** request. Follow the `vakyn-questions`
skill for options, levels and state; put the record under its own key (`ticket`, `message`), with
no fields VAKYN does not need. Run the [checklist](../../vakyn/references/checklist.md).

## 5. Write the code

Show the person's call site after the change:

1. Build the state from the record. Call VAKYN once with all questions.
2. Read answers by question name. Check each `choice` is one of the offered options.
3. Run the code rules (plan bump, overdue, language) on the record and the answers.
4. Call the chat model only for the kept lines, and give it VAKYN's answers as facts, so the reply
   matches the category.
5. Unsure answers: below the person's threshold, send the record to the old prompt (the chat model
   decides as before) or to a "needs review" queue. Say which, and log both.

Run it side by side first, like a tool pick: keep the old prompt's answer in use, log VAKYN's next
to it, and switch once the `vakyn-check` skill shows the two agree where it matters.
