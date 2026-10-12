# Collect runs

The program is only as good as the runs it is distilled from. Before reading anything, check the
person has (or can start logging) one record per case with what the agent did and how it ended.

## Where the traces are

Look for them before asking: `*.jsonl`, `traces/`, `runs/`, `logs/`, an exported folder from a
tracing tool. Common shapes:

| Source | What a case is | Where the steps are |
|---|---|---|
| Own JSONL log | one line per case, or one line per step with a case id | `steps`, `messages`, `events` |
| Claude Agent SDK, OpenAI Agents SDK, LangGraph, a custom loop | one session or run id | the message list: tool calls and tool results in order |
| OpenTelemetry export (JSON) | one trace id | spans; tool calls are child spans with the tool name and arguments as attributes |
| Langfuse export | one trace | observations of type span or generation, with input, output, cost and latency |

Read them **locally**, with a short script in the person's language. Never paste trace contents
into a chat model, a web tool or a report beyond counts, ids, tool names, times and costs. Traces
hold customer data.

## What to log per case

If the agent does not log this, add it before anything else and let it run on real cases:

| Field | Why |
|---|---|
| `case_id`, `ts`, procedure version, agent version | which rules and which agent produced it |
| `input` | the case as the agent received it (or a pointer to it) |
| `steps[]`: tool name, arguments, result (or a summary), error, time | which steps decided the case, which were wasted |
| `final_output` | the agent's structured result; its schema becomes questions later |
| `cost_usd`, `latency_s` | the baseline the program must beat, as logged |
| `label` | the outcome a person confirmed (added later by a reviewer) |
| `notes` | the agent's own short notes (below) |

Sample: [traces.sample.jsonl](../examples/traces.sample.jsonl) (ten synthetic supplier
applications).

## The notes prompt

Add this to the end of the agent's task, after it submits its result. Keep the answer short; long
notes are not read.

```
Before you finish, write notes for whoever turns this job into a fixed program.
In 1 to 3 sentences: which step decided this case, which steps added nothing,
and what you wished you had known at the start.
```

Notes point at waste ("the look-up changed nothing") and at missing rules ("I did not know a
different legal form still counts"). Read them next to the steps; never treat a note as a fact
about the case.

## Enough runs

- Distill from cases that cover every outcome in the procedure, including the rare ones
  (escalations, rejections). A few cases per outcome show the shape; proving a rate takes more
  ([sample sizes](../../vakyn-check/references/thresholds.md#starting-values-and-sample-sizes)).
- Get labels from a person for the runs you will measure against. The agent's own outcome is not a
  label; it is the thing being measured.
- **Split off the reserved set now**, before reading the runs, by a hash of the case id
  ([dev and reserved sets](../../vakyn-check/references/tuning.md#two-sets-of-labeled-cases)).
  Read only the development cases while building.
