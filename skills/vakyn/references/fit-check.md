# Fit check: is this a decision?

Use when someone describes a problem and asks whether VAKYN fits. Answer with a verdict first, then
the question types that would carry it.

## The test

VAKYN fits a step when **all three** hold:

1. **The answer is one of a known set.** Yes or no, one named option out of up to 255, or a level
   out of up to 10. If the output is a sentence, a summary or an email, it is writing, not a decision.
2. **The evidence fits in the request.** The document and the question together stay under 32,768
   tokens (about 100 pages of plain text is too much; a ticket, a contract section, a page of a web
   site, a log excerpt is fine). Longer material needs code to pick the relevant part first.
3. **A person could decide it by reading.** If a careful reader with the document in hand would
   agree on the answer, VAKYN can learn to give it. If it needs a database lookup, a calculation or
   live data, code does that part and passes the result in the state.

## Verdicts

| Verdict | When | Say |
|---|---|---|
| **Fits** | All three hold | Name the question type(s) and sketch the request |
| **Fits in part** | Some steps are decisions, others are writing or lookup | Split it: which steps VAKYN answers, which stay with code or a chat model |
| **Does not fit** | The output is free text, or nothing is being chosen | Say so plainly and suggest keeping their current approach |

## Common shapes

| They say | It is | Question type |
|---|---|---|
| "route", "assign", "which team", "categorize" | one option from a list | `choice` |
| "is this…", "does it mention…", "should we flag…" | one proposition | `noul` |
| "how urgent", "how good", "rate", "severity" | a level on a scale | `score` |
| "which tool", "next step", "which action" | one option from a list, plus "none" | `choice` |
| "tag with all that apply" | several independent propositions | one `noul` per tag, in one request |
| "extract the date / amount / name" | finding a value | code finds candidates, `choice` picks one |
| "summarize", "reply", "draft", "translate" | writing | not VAKYN; keep the chat model |
| "how many", "total", "before or after" | counting or arithmetic | code |

## Worked verdict

> "Our support inbox gets 2,000 emails a day. A chat model reads each one, picks a team, decides
> if it is urgent and writes a first reply."

**Fits in part.** Picking the team is a `choice` (billing / access / product / other). Urgency is a
`score` (can wait / today / within the hour). The first reply is writing: keep the chat model, and
give it VAKYN's team and urgency as input. Next: `vakyn-convert` if the prompt exists today,
`vakyn-workflow` to design it fresh.
