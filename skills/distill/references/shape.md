# Find the shape: the step map

Read the procedure (SOP) and the development traces side by side. Write one row per step the
procedure asks for, plus any step the agent does that the procedure does not mention. Every row
gets exactly one kind.

## The four kinds

| Kind | Signs in the traces and the procedure | Becomes |
|---|---|---|
| **Decision** | the agent reads text and settles what something is: which kind, which branch, which item, yes or no | a VAKYN question (below) |
| **Mechanical** | dates, ages, counts, sums, equal-or-not, "any two of these means stop", ordering of outcomes | plain code |
| **Look-up or act** | something must be found or done outside: search a registry, fetch a file, write to a system | a small agent step: one or two tools, a fixed output schema |
| **Hard judgment** | the procedure says a person decides, or no question settles it from the evidence | escalate: to a person, or to the full agent |

The rule: **VAKYN decides what a thing is; code decides what follows.** "Is this match the
applicant?" is VAKYN's. "A match means escalate, and escalation outranks a missing document" is
code.

Writing (a reply, a summary, an email) is none of these: it stays with a chat model or a template
([fit check](../../start/references/fit-check.md)).

## Decision sub-kinds

| Sub-kind | What it does | Question shape | More |
|---|---|---|---|
| **route** | picks the branch for the whole case | one `choice` over branches + an escape option | [route](../../workflow/references/patterns/route.md) |
| **classify from schema** | fills the agent's structured output | enum → `choice`, boolean → `noul`, field descriptions → criteria | [output schema](../../convert/references/output-schema.md) |
| **sift** | the same yes or no for every item of a list, keep the ones that pass | one `noul` per item, one request, item named by its key | [spot risk](../../workflow/references/patterns/spot-risk.md), [judgments as data](../../workflow/references/patterns/reusable-judgments.md) |
| **pick** | one item of a short list, or none | `choice` over item ids + `none_of_these` (+ `cannot_tell`) | [best match](../../workflow/references/patterns/best-match.md) |

Values the agent copied out of text (an amount, a date) are a pick too:
[pick instead of generate](../../workflow/references/patterns/pick-value.md). Several branch
follow-ups in one request: [fan out](../../workflow/references/patterns/fan-out.md).

## Triage and early stop

Look at which steps cost the most (tool calls, time, cost in the traces) and ask, per costly step:

1. **Could its result change the outcome?** If the outcome is already settled (an earlier rule
   gives the top outcome), skip it. Write the order of outcomes down; it tells you when nothing
   left can change the result.
2. **Which items need it?** A sift question first ("could this item matter?"), then the costly
   step only on the items that pass. Drop an item only on a clear no; when a missed item is
   costly, set the drop cut-off low (asymmetric).
3. **In what order?** Most likely first, so an exact check (an equal id, a matching number) can
   end the loop early.

The notes ("the look-up changed nothing") point at these. Mark each row of the step map with its
early stop, if any.

## The rubric check

Splitting a procedure into steps can leave a step with half the rules. For each decision row:

- List what the procedure says about that decision: criteria, exceptions, blockers, what does not
  count ("a different legal form alone does not rule it out").
- Read the question **as it will be sent** (instructions, options, the state) and tick each item.
  Anything missing goes into the option descriptions or the `noul` criteria, or the state gets
  the evidence it refers to.
- Undefined words in the procedure ("similar name") need a definition before a question can use
  them. Ask the procedure's owner; do not invent one silently.

More: [the whole rubric per step](../../check/references/tuning.md#each-judging-step-gets-the-whole-rubric).

## Output

A table like [step-map.md](../examples/step-map.md): step, procedure section, kind, how, early
stop; then the triage notes and the rubric check. Show it to the person before writing code.
