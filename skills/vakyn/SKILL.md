---
name: vakyn
description: "Entry point for VAKYN, the decision model that answers typed questions (noul yes/no, choice, score) over a document with a confidence. Use when someone asks what VAKYN could do in their app, whether it fits their problem, how to turn an LLM prompt-and-parse step into a structured decision, which model file to run, how to install or start open-server, get an API key or make a first call; what the Jev-compatible API accepts; troubleshoots 401, 422, 429, 503, out of GPU memory or a server that won't start. Moving from hosted Jev, TypeSafe or OpenRouter: use vakyn-migrate."
---

# VAKYN: start here

VAKYN reads a document (the **state**) and answers named questions about it. Each answer is a
probability distribution, not generated text:

- `noul`: yes or no → `noul: 0.91` (probability of yes)
- `choice`: one of several named options → `choice: "billing"`, `confidence`, `probabilities`
- `score`: a level on an ordered scale → `score: 1.86` (probability-weighted), `legend`, `probabilities`

It runs on the person's own hardware with **open-server** and speaks the **Jev-compatible API**, so the
official TypeSafe SDKs work once their base URL points at the server.

You are the person's guide and builder. Help them decide, set up and write code. Do not use VAKYN
for your own reasoning.

## Pick the step

| The person wants to… | Do |
|---|---|
| Know what VAKYN could make possible in their app (no step chosen yet) | [Brainstorm](#brainstorm) below |
| Know if VAKYN fits their problem | [Fit check](references/fit-check.md) |
| Choose a model file for their machine | [Model choice](references/setup.md#choose-a-model-file) |
| Install and start the server, get an API key | [Setup](references/setup.md) |
| Make a first call | [First call](#first-call) below |
| Know what the API accepts, returns and refuses | [API reference](references/api.md) |
| Call it from Python or TypeScript | [SDK guide](references/sdk.md) |
| Fix an error: `401`, `422`, `429`, `503`, out of GPU memory, server won't start | [Setup checks](references/setup.md#check), [API errors](references/api.md#errors) |
| Move from hosted Jev, TypeSafe, OpenRouter or another decision API to their own server | `vakyn-migrate` skill |
| Find where VAKYN helps in an existing app | `vakyn-research` skill |
| Write or fix questions | `vakyn-questions` skill |
| Turn a chat-model prompt-and-parse step or a tool-calling app into a structured decision | `vakyn-convert` skill |
| Build a new decision workflow | `vakyn-workflow` skill |
| Test on their own data or get ready to go live | `vakyn-check` skill |
| Run VAKYN over a file or table of records | `vakyn-batch` skill |
| Let a cheap draft answer and VAKYN check it | `vakyn-cascade` skill |
| Grade outputs with a rubric | `vakyn-judge` skill |
| Turn an agent that repeats a written procedure into a cheaper program, moved over in stages | `vakyn-distill` skill |

When the request is vague ("help me use VAKYN"), ask what they want to decide and whether they
already have an app, then route with this table. A concrete request ("route these emails", "check
this answer against the doc") skips all questions: build it with the matching skill.

## Brainstorm

When someone asks what VAKYN could make possible in their app and has no step in mind:

1. Look at what they shared (code, a description, the product) and find where a person or a chat
   model reads text and picks from a few outcomes.
2. Offer 2–3 concrete directions tied to their app, one line each: the decision, the questions'
   types, what code does with the answer. Mix one easy win with one new capability, such as
   asking all branch questions up front, picking a value instead of generating it, or storing
   scores that users re-weigh (see the `vakyn-workflow` patterns).
3. Recommend one and say why (volume, cost of a mistake, how easy it is to check).
4. Hand off: `vakyn-research` to search their code for more spots, or `vakyn-workflow` /
   `vakyn-convert` to build the one they pick.

## First call

1. Check the server answers: `curl -s "$VAKYN_BASE_URL/v1/models" -H "Authorization: Bearer $VAKYN_API_KEY"`.
   No answer → [Setup](references/setup.md). `401` → wrong or missing key.
2. Start from [examples/first-call.request.json](examples/first-call.request.json): one question of
   each type over a short support ticket. Replace the state and questions with the person's own case.
3. Run the [pre-send checklist](references/checklist.md) on the request.
4. Send it with what the machine has. Check first (`command -v curl python3 node`):
   - curl: [examples/first-call.sh](examples/first-call.sh)
   - Python: [examples/first_call.py](examples/first_call.py)
   - TypeScript: [examples/first_call.ts](examples/first_call.ts)
5. Show the full answer and explain each field in one line. Point out the lowest-confidence answer
   and what more evidence in the state would change it.

## Rules for every vakyn skill

- **Keys stay out of the chat.** The API key lives in an environment variable (`VAKYN_API_KEY`, or
  `TYPESAFE_API_KEY` for the SDKs) or a git-ignored env file. Never ask the person to paste a key,
  never print one, never write one into a tracked file. If a key was pasted into the chat anyway,
  do not repeat it; tell them to revoke it (`vakyn keys revoke`) and create a new one.
- **Do not open or print `.env`.** No `cat`, no `grep`, no file viewer on it. Load it inside the one
  command that needs it: `set -a; . ./.env; set +a; curl …`. To check a key is set, test it
  without printing it: `[ -n "$VAKYN_API_KEY" ] && echo set`.
- **Never invent answers.** If no server is reachable, say so and write the request and code
  anyway; do not make up probabilities or "expected" outputs.
- **Check before sending.** Every request passes the [pre-send checklist](references/checklist.md).
- **Code decides what is exact.** Arithmetic, dates, thresholds and business rules live in the
  person's code; VAKYN answers the judgment.
- **Unsure answers have a path.** Every design says what happens below a confidence threshold: a
  person, a chat model, or a "needs review" queue.
- **Keys stay on the server in web apps.** Browser code calls the person's own backend; the
  backend holds the key and calls open-server. Never put the key in front-end code, and never
  call open-server from the browser with a key.
- **Base URL and model.** Default base URL `http://127.0.0.1:8080` (no `/v1`); model `jev-latest`.
