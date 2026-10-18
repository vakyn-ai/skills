# Write the program

Write it in the person's stack: plain Python or TypeScript functions are the default. No
framework, workflow engine or DSL is needed; if they already use one (LangGraph, a job queue),
each step becomes a node or a job with the same insides. Template:
[program.py](../examples/program.py).

## Parts

| Part | What it is |
|---|---|
| Typed records | a dataclass, Pydantic model, TypeScript type or Zod schema for the case and for what passes between steps (`Case`, `Result`) |
| One function per step | `run_case()` calls them in the map's order; each early stop is a `return` |
| VAKYN requests | built from constants; independent questions about the same evidence share one request ([batching](../../workflow/references/batching.md)); each passes the [checklist](../../start/references/checklist.md) and is saved as a `.json` file |
| Code steps | dates, counts, equality, the order of outcomes; exact, tested like any code |
| Agent steps | small: one or two tools, a fixed output schema, a timeout; stubbed in examples and tests |
| Settings | thresholds in one versioned block or file; a changed number is a new version |
| Escalation | who gets what: the full agent for unsure answers, a person for hard judgments |
| Decision record | one line per VAKYN request and one per case outcome |

## VAKYN questions

- Write each with the `questions` rules: one judgment, described options, an escape option,
  the subject named in plain words.
- Classify steps come from the agent's output schema
  ([output schema](../../convert/references/output-schema.md)): enum → `choice`, boolean →
  `noul`, the field description → criteria.
- Sift: one `noul` per list item, all in one request, each naming its item by key
  (`state.hits.h2`). Put the full rule in the `noul` criteria, the same for every item.
- Pick: options are the item ids with one line each, plus `none_of_these`, plus `cannot_tell` when
  conflicting evidence must go to a person.
- Read answers by name; check a pick is an offered option before acting on it.

## Agent steps

The agent keeps only what needs the outside world. Shrink each one:

- one task, one or two tools, the inputs it needs and nothing else;
- a fixed output schema with a `source` per field;
- **check each field against its cited source** before the program uses it; a field the source
  does not support goes back to the same agent session once, then is dropped and the case
  escalates;
- a timeout and a retry limit; on failure, escalate the case.

In examples and tests, stub the agent step with canned results. Never call a paid model from an
example.

## Escalation

| Cause | Goes to | Why |
|---|---|---|
| A VAKYN answer below its threshold, or an escape option where none is expected | the full agent, with the whole case | the old flow still works; nothing gets worse |
| The procedure says a person decides, or `cannot_tell` | a person | hard judgment |
| An agent step fails or its fields are not supported by their source | the full agent, or a person when the step was the hard part | |
| VAKYN unreachable | the full agent | behave as before |

Thresholds: starting values from
[thresholds](../../check/references/thresholds.md#starting-values-and-sample-sizes), marked
as starting values. When a missed case costs far more than an extra check (screening, fraud,
safety), make the cut-off asymmetric: drop or clear only on a clear no.

## The decision record

One JSON line per VAKYN request, written by the same function that sends it:

`ts`, `case_id`, `step`, program version, settings version, `model` (from the response),
`request_id`, a hash of the questions, a hash of the input (and the input itself, or where it is
kept), and **every answer with its probabilities**. One more line per case: outcome, who handled
it, reasons.

This one log is the audit trail, the replay source and the report source. With it, a changed
threshold or rule re-decides every stored case without calling VAKYN:
`python program.py traces.jsonl --replay decisions.jsonl --set sift_drop_at=0.1`. A changed
question or input needs a live answer; the replay says which cases. More:
[replay](../../check/references/replay.md),
[audit record](../../check/references/go-live.md#audit-record).

## Before handing over

1. `python3 -m py_compile` or `npx tsc --noEmit`.
2. Every request through the checklist; send each saved `.json` if VAKYN is reachable.
3. Run the program on the development cases (live VAKYN, stubbed agent steps) and print the
   report ([report](rollover.md#report)). VAKYN not reachable: say so; never invent answers.
