# VAKYN skills for Claude Code

Find the decisions a chat model makes in your app, move them to VAKYN, and check the result on
your own data before you switch.

[![test](https://github.com/vakyn-ai/skills/actions/workflows/test.yml/badge.svg)](https://github.com/vakyn-ai/skills/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

VAKYN is a decision model. You send it a document and typed questions. It answers each one with
a probability, on your own hardware:

```
ticket: "I was charged twice this month and need one refunded."

Which team should get it?        choice → billing   1.00
Does it ask for a refund?        noul   → yes       1.00
How soon does it need a reply?   score  → today     0.64   (can wait 0.12 · within the hour 0.24)
```

The six skills in this plugin teach Claude Code to build with it.

## Install (30 seconds)

```bash
claude plugin marketplace add vakyn-ai/skills
claude plugin install vakyn@vakyn-ai
```

Run `/reload-plugins` in an open session, or start a new one.

No VAKYN server yet? Ask Claude:

```
Set up VAKYN on this machine.
```

It picks the model file for your hardware and walks you through install, start and API key.

## Try it

Ask in plain words. Claude picks the skill.

```
Where could VAKYN help in this repo?
Make VAKYN pick the tool in agent.py.
Build a router for our returns emails.
Why did it pick billing for this message?
Here's a week of side-by-side logs. Can we switch?
```

Or call one directly: `/vakyn:vakyn-convert`.

A real run on a small helpdesk app (Python, OpenAI SDK), trimmed:

```
> Where could VAKYN help in this repo?

The report is in vakyn-research.md. I didn't change any code or make any calls.

Top 3 places VAKYN could help:
1. Ticket routing (helpdesk/triage.py:28): picks one of 4 teams with gpt-4o, about
   2,000 times a day. The team list already exists and a wrong pick is cheap to fix.
2. Spam check (helpdesk/triage.py:23): a yes/no question on all ~3,000 emails a day.
   Only mark spam when VAKYN is confident.
3. Urgency rating (helpdesk/triage.py:39): a 1–5 score that decides whether someone
   gets paged. High risk, so run it alongside gpt-4o first.

Stays with the chat model: the draft reply (replies.py:12) and the weekly summary.

Next: run vakyn-convert on the routing spot, then test it with vakyn-check on about
30 past tickets.
```

## The skills

| Skill | What it does |
|---|---|
| `vakyn` | Checks if VAKYN fits, picks a model file, sets up the server, makes a first call. |
| `vakyn-research` | Finds the decisions in your app or process and ranks them in `vakyn-research.md`. Changes nothing. |
| `vakyn-questions` | Picks `noul`, `choice` or `score`, writes options and levels, fixes a bad answer. |
| `vakyn-convert` | Turns a prompt or a tool list (OpenAI, Anthropic, MCP) into VAKYN calls and Python or TypeScript code. |
| `vakyn-workflow` | Designs a new decision workflow: route, triage, pick a tool, check a claim, rate with a rubric, pick the best match, spot risk, fill a form. |
| `vakyn-check` | Runs a 30-record test against your chat model, reads side-by-side logs, sets confidence thresholds, reviews before go-live. |

A typical path:

1. `vakyn-research` finds where VAKYN fits.
2. `vakyn-convert` moves what you have, or `vakyn-workflow` builds something new.
3. `vakyn-check` proves it on your data before you switch.

## What the skills always do

- **Check every request before it is sent:** right shapes, limits, described options, an escape
  option such as `other` or `none`, one question per proposition.
- **Keep exact work in code.** Arithmetic, dates, thresholds and rules stay in your code. VAKYN
  answers the judgment.
- **Give unsure answers a path:** a person, a chat model, or a review queue.
- **Run side by side first.** A converted app keeps using your chat model and logs both answers
  until you switch.
- **Never invent answers.** If your server is not reachable, Claude says so and still writes the
  request and the code.
- **Keep your key out of the chat.** It lives in `VAKYN_API_KEY` (or `TYPESAFE_API_KEY` for the
  official SDKs).

Generated code uses the official TypeSafe SDKs (`typesafe-sdk`, `@typesafe-ai/sdk`). They work
with VAKYN's Jev-compatible API once their base URL points at your server.

## How we test it

- **Graded runs.** Each skill has cases that run Claude Code headless with the plugin on a real
  request, such as "convert this triage prompt" or "find the decisions in this app", and a grader
  scores the result. See [evals/](evals/README.md).
- **A real server.** Every request the skills write during those runs, and every example request
  in this repo, passes the pre-send checklist and is sent to a running VAKYN server.
- **Every push** runs offline checks on manifests, skills, links, wording and example requests.

## What you need

- Claude Code.
- A running VAKYN server ([open-server](https://github.com/vakyn-ai/open-server)) with a model
  file and an API key. The `vakyn` skill sets this up for you.

<details>
<summary><strong>Update</strong></summary>

Installed plugins update in the background when a new version is released. To update now:

```bash
claude plugin marketplace update vakyn-ai
claude plugin update vakyn@vakyn-ai
```

</details>

<details>
<summary><strong>Other coding agents</strong></summary>

The skills are packaged for Claude Code. Want them for another agent? Open an issue and say which.

</details>

<details>
<summary><strong>Develop</strong></summary>

```bash
claude --plugin-dir .                     # try the plugin from this folder
make test                                 # offline: manifests, skills, links, voice, example requests
VAKYN_API_KEY=... make test-live          # send every example request to VAKYN_BASE_URL
VAKYN_API_KEY=... make eval TAG=vakyn     # headless Claude Code runs per skill, graded
make release VERSION=x.y.z                # validate, bump, tag, push
```

`make eval` uses your Claude account (about $0.15–0.40 per case). The design is in
[spec/spec-skills-v1.md](spec/spec-skills-v1.md).

</details>

## License

MIT
