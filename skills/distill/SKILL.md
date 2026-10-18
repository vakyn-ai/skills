---
name: distill
description: "Turn an agent that does a repetitive job from a written procedure (SOP) into a cheaper, inspectable program: code + VAKYN questions + small agent steps, with traffic moved over in stages and the agent as fallback. Use for agent traces or runs (JSONL, OpenTelemetry, Langfuse) to distill, an agent that costs too much per case, mapping SOP steps to decisions vs code vs look-ups, early stops, or a staged rollout. One prompt or tool list: convert. New task with no agent: workflow."
---

# VAKYN distill: agent runs to a decision program

The person has an agent (Claude Agent SDK, OpenAI Agents SDK, LangGraph, Pi, a custom loop) doing
the same job case after case from a written procedure: reviewing supplier applications, invoice
disputes, claims. It works, but every case pays for a full agent run and nobody can say exactly why
it decided what it did. This skill turns its runs into a program: plain code for what is exact,
VAKYN questions for what must be decided, small agent steps only where something must be found or
done outside, and a person for the hard calls. Then it moves traffic over in stages, with the agent
as fallback.

**VAKYN decides what a thing is; code decides what follows.**

Shared material: [pre-send checklist](../start/references/checklist.md),
[SDK guide](../start/references/sdk.md), the `questions` rules, the `workflow`
patterns, and the `check` pages for
[thresholds](../check/references/thresholds.md#starting-values-and-sample-sizes),
[replay](../check/references/replay.md) and [tuning](../check/references/tuning.md).

## Pick the step

| The person… | Do |
|---|---|
| Has an agent but no traces, or traces without outcomes | [Collect runs](references/collect.md) |
| Has traces and a procedure | [Find the shape](references/shape.md): the step map |
| Has a step map and wants the code | [Write the program](references/program.md) |
| Has a program and wants to move traffic | [Roll over in stages](references/rollover.md) |
| Has a batch and asks how it went | [Report](references/rollover.md#report) |
| Has one prompt or tool list, no agent loop | the `convert` skill |
| Has a new task and no agent | the `workflow` skill |

## Steps

1. **Collect runs.** Find the traces on the machine and read them locally; they never leave it.
   Per case you need the input, every tool call with its result, error and time, the final
   output, cost, latency, a person's label and the agent's 1–3 sentence notes. Missing: add the
   logging and the [notes prompt](references/collect.md#the-notes-prompt) first. Split off the
   reserved set by a hash of the case id **before** reading any case.
2. **Find the shape.** With the procedure and the development traces, mark every step as one kind
   ([shape](references/shape.md)):
   - **decision** → a VAKYN question: *route* (branch), *classify* from the agent's output schema,
     *sift* (the same `noul` for every list item, one request), *pick* (one item or none);
   - **mechanical** → code (dates, counts, equality, the order of outcomes);
   - **look-up or act** → a small agent step (one or two tools, a fixed output schema);
   - **hard judgment** → escalate to a person or the full agent.

   Then find triage and early stops: which costly steps can still change the outcome, which list
   items need them, and when nothing left can. Check each decision gets the whole rubric it
   needs. Show the step map before writing code.
3. **Write the program** in the person's stack, plain functions by default
   ([program](references/program.md)): typed records between steps, one function per step, each
   early stop a `return`, VAKYN requests through the checklist and saved as `.json` files,
   thresholds as a versioned settings block, an escalation path for every unsure answer, and a
   decision record per request (inputs or their hash, question hash, every answer with its
   probabilities, settings version, model name, request id). Stub agent steps in examples; never
   call a paid model from them.
4. **Run it** on the development cases with live VAKYN and stubbed agent steps, and send each
   saved request. VAKYN not reachable: say so, write everything anyway, never invent answers.
5. **Roll over in stages** ([rollover](references/rollover.md), template
   [rollout.md](examples/rollout.md)): the first cases stay with the agent; then shadow; then
   e.g. 50%, 75%, 90% may try the program with the agent as fallback for anything escalated. A
   new version goes live only if it beats the current one on the development set and is not worse
   on the reserved set. Code-only changes are replayed on stored answers.
6. **Report** each batch: cost per case, share handled by the program, escalation rate,
   agreement with labels, disagreements to review. Measured or as logged, with the source of
   each figure.

## Examples (synthetic supplier onboarding)

| File | What it is |
|---|---|
| [sop.sample.md](examples/sop.sample.md) | the written procedure the agent follows |
| [traces.sample.jsonl](examples/traces.sample.jsonl) | ten agent runs: tool calls, results, errors, cost, latency, label, notes |
| [step-map.md](examples/step-map.md) | the step map, triage and early stops, rubric check |
| [classify.request.json](examples/classify.request.json) | route + classify from the output schema, one request; real answer `new_application` 0.80, `software` 0.99, personal data 0.99 |
| [sift.request.json](examples/sift.request.json) | one `noul` per screening match; real answers 0.97, 1.00, 0.08: two kept, one dropped |
| [pick.request.json](examples/pick.request.json) | one kept match or none, with its registry record; real answer `none_of_these` 1.00 |
| [program.py](examples/program.py) | the program: code, VAKYN, a stubbed look-up agent, escalation, decision records, `--replay` |
| [rollout.md](examples/rollout.md) | the staged plan, promotion rule and batch report |

Answers come from VAKYN-4B on open-server, on CPU. The program on the ten sample cases: all handled
without escalation and all ten outcomes equal to the labels, 1.5 VAKYN requests and 0.2 look-ups
per case against 5.6 agent tool calls. Those ten are its development set: its questions were fixed
while looking at them, so this proves the plumbing, not the accuracy.

## Rules

- **Traces stay local.** Read them with a script on the machine; quote counts, ids, tool names,
  times and costs, never case contents.
- **The agent is the fallback**, never removed in one step. Unsure answers, failed look-ups and
  VAKYN being down all go back to it.
- **The reserved set is never read while authoring.** Only its counts, once per candidate.
- **Agreement is not accuracy.** The agent's outcome is not a label; a person's is.
- **Never invent numbers.** Costs, rates and savings come from traces, records and labels, with
  their source; chat-model prices from the person, VAKYN Cloud prices from `GET /v1/models`.
- **Ask before each stage's traffic.** On VAKYN Cloud every case the program decides spends
  balance; estimate each stage's cost ([cost](../start/references/cloud.md#cost)) and keep under
  60 requests per second per key.
- **Keys stay out of the chat and out of files** (see the `start` skill rules).
