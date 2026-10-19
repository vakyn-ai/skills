---
name: get-started
description: "Get started with VAKYN, the decision model that answers typed questions (noul yes/no, choice, score) over a document with a confidence, on VAKYN Cloud (the hosted API). Use when someone wants to try VAKYN or get started; needs an account, a balance or an API key from the console; asks where to save the key so scripts and other skills find it; wants a first call; asks what VAKYN could do in their app or whether it fits; what the Jev-compatible API accepts; troubleshoots 401, 402, 422, 429, 503. Running it on their own servers: self-hosting reference. Moving from hosted Jev, TypeSafe or OpenRouter: migrate."
---

# VAKYN: get started

VAKYN reads a document (the **state**) and answers named questions about it. Each answer is a
probability distribution, not generated text:

- `noul`: yes or no → `noul: 0.91` (probability of yes)
- `choice`: one of several named options → `choice: "billing"`, `confidence`, `probabilities`
- `score`: a level on an ordered scale → `score: 1.86` (probability-weighted), `legend`, `probabilities`

It runs on **VAKYN Cloud**, the hosted API at `https://api.vakyn.com`: nothing to install, an
account and a prepaid balance in the console, one API key. The API is **Jev-compatible**, so the
official TypeSafe SDKs work once their base URL points at VAKYN.

You are the person's guide and builder. Help them decide, set up and write code. Do not use VAKYN
for your own reasoning.

## Pick the step

| The person wants to… | Do |
|---|---|
| Start from nothing | [Get started](#get-started) below, all five steps |
| Know what VAKYN could make possible in their app (no step chosen yet) | [Brainstorm](#brainstorm) below |
| Know if VAKYN fits their problem | [Fit check](references/fit-check.md) |
| Get or replace an API key, add balance | [VAKYN Cloud](references/cloud.md#get-a-key) |
| Save the key so every project, script and skill finds it | [Save the key](references/cloud.md#save-the-key) |
| Make a first call | [First call](#first-call) below |
| Know what the API accepts, returns and refuses | [API reference](references/api.md) |
| Call it from Python or TypeScript | [SDK guide](references/sdk.md) |
| Fix an error: `401`, `402`, `422`, `429`, `503` | [API errors](references/api.md#errors) |
| Run VAKYN on their own servers (data cannot leave their network) | [Self-hosting](references/self-hosting.md) |

## Get started

### 1. Open the console

The person does this in the browser; you cannot sign in for them. Send them to
[vakyn.com/console](https://vakyn.com/console): sign in with Google, GitHub or X, and an
organization of their own is created.

### 2. Add a balance, create a key

- Billing: add a prepaid balance, or redeem a code
  ([vakyn.com/console/billing](https://vakyn.com/console/billing)). There is no free tier; calls
  are refused with `402` when the balance is empty.
- API keys: create one ([vakyn.com/console/keys](https://vakyn.com/console/keys)). It starts with
  `vk_` and is shown once.

### 3. Save the key once per machine

Every skill, script and SDK here reads the key from the environment, so save it once, in a file
only the person can read: `~/.config/vakyn/env` with `VAKYN_BASE_URL`, `VAKYN_API_KEY`,
`TYPESAFE_BASE_URL` and `TYPESAFE_API_KEY` ([how, with the commands and Windows](references/cloud.md#save-the-key)).
Create the file without the key; the person pastes the key in their editor, never in the chat.
**Ask first**, then add the one line that loads it to their shell startup file. Check with
`[ -n "$VAKYN_API_KEY" ] && echo set`. A project that needs another key keeps it in its own
git-ignored `.env`.

### 4. First call

[First call](#first-call) below: one request, a few input tokens from the new balance.

### 5. Next

Offer the next skill: `research` (find decisions in their app), `convert` (a prompt or tool list),
`workflow` (something new), `batch` (a file or table).

## Other skills

| The person wants to… | Skill |
|---|---|
| Move from hosted Jev, TypeSafe, OpenRouter or another decision API | `migrate` |
| Find where VAKYN helps in an existing app | `research` |
| Write or fix questions | `questions` |
| Turn a prompt-and-parse step or a tool-calling app into decisions | `convert` |
| Build a new decision workflow | `workflow` |
| Run VAKYN over a file or table; a cheap draft checked by VAKYN; grade outputs | `batch`; `cascade`; `judge` |
| Turn an agent that repeats a written procedure into a program | `distill` |
| Test on their own data or get ready to go live | `check` |
| Make a question more accurate from labeled cases | `optimize` |
| Ask VAKYN to train on their decisions (a custom model) | `train-request` |

A vague request ("help me use VAKYN"): ask what they want to decide and whether they have an app,
then route. A concrete one ("route these emails"): build it with the matching skill.

## Brainstorm

When someone asks what VAKYN could make possible in their app and has no step in mind:

1. Look at what they shared (code, a description, the product) and find where a person or a chat
   model reads text and picks from a few outcomes.
2. Offer 2–3 concrete directions tied to their app, one line each: the decision, the questions'
   types, what code does with the answer. Mix one easy win with one new capability, such as
   asking all branch questions up front, picking a value instead of generating it, or storing
   scores that users re-weigh (see the `workflow` patterns).
3. Recommend one and say why (volume, cost of a mistake, how easy it is to check).
4. Hand off: `research` to search their code for more spots, or `workflow` /
   `convert` to build the one they pick.

## First call

1. Check the key is set without printing it: `[ -n "$VAKYN_API_KEY" ] && echo set`. Not set →
   load `~/.config/vakyn/env`, or go back to [steps 1–3](#get-started). Base URL: `VAKYN_BASE_URL`,
   or `https://api.vakyn.com`. One request needs no cost estimate, but it does need a balance.
2. Start from [examples/first-call.request.json](examples/first-call.request.json): one question of
   each type over a short support ticket. Replace the state and questions with the person's own case.
3. Run the [pre-send checklist](references/checklist.md) on the request.
4. Send it with what the machine has. Check first (`command -v curl python3 node`):
   - curl: [examples/first-call.sh](examples/first-call.sh)
   - Python: [examples/first_call.py](examples/first_call.py)
   - TypeScript: [examples/first_call.ts](examples/first_call.ts)
   A `401` means a wrong or missing key; `402`, an empty balance (top up in the console).
5. Show the full answer and explain each field in one line. Point out the lowest-confidence answer
   and what more evidence in the state would change it.

## Rules for every skill in this set

- **Keys stay out of the chat.** The key lives in the environment (`VAKYN_API_KEY`, or
  `TYPESAFE_API_KEY` for the SDKs), loaded from `~/.config/vakyn/env` or a git-ignored `.env`.
  Never ask the person to paste a key, never print one, never write one into a tracked file. A key
  pasted into the chat anyway: do not repeat it; they revoke it on the console's API keys page
  (open-server: `vakyn keys revoke`) and create a new one.
- **Do not open or print `.env` or `~/.config/vakyn/env`.** Load it inside the command that needs
  it (`set -a; . ~/.config/vakyn/env; set +a; curl …`); check with `[ -n "$VAKYN_API_KEY" ] && echo set`.
- **Never invent answers.** If VAKYN is not reachable, say so and write the request and code
  anyway; do not make up probabilities or "expected" outputs.
- **Check before sending.** Every request passes the [pre-send checklist](references/checklist.md).
- **Code decides what is exact.** Arithmetic, dates, thresholds and business rules live in the
  person's code; VAKYN answers the judgment.
- **Unsure answers have a path.** Every design says what happens below a confidence threshold: a
  person, a chat model, or a "needs review" queue.
- **Keys stay on the server in web apps.** Browser code calls the person's own backend; the
  backend holds the key and calls VAKYN. Never put the key in front-end code, and never call
  VAKYN from the browser with a key.
- **Base URL and model.** Default base URL `https://api.vakyn.com` (no `/v1`); self-hosted is the
  person's server URL (default `http://localhost:8080`). Model `jev-latest`, which works on both;
  on VAKYN Cloud `vakyn-fast` is the cheaper option.
- **Ask before spending.** On VAKYN Cloud every answered request spends the person's balance. Before
  any run beyond a handful of requests, estimate input tokens × the price from `GET /v1/models`
  ([cost](references/cloud.md#cost)), show it and wait for a yes. Never write a price from memory,
  never promise a free tier. Keep under 60 requests per second per key; self-hosted, under the
  server's `--max-queue`.
