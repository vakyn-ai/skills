# VAKYN skills for Claude Code

VAKYN is a decision model. You send it a document and typed questions; it answers each one with a
confidence, on your own hardware:

```
ticket: "I was charged twice this month and need one refunded."

team     choice  → billing      1.00
refund   noul    → yes          1.00
urgency  score   → today        1.12 on 0–2 (can wait / today / within the hour)
```

These skills teach Claude Code to help you build with it: find where it fits in what you have,
write the questions, convert your prompts and tool-calling apps, design new workflows, and check
the result on your own data before you switch.

## Install

```bash
claude plugin marketplace add vakyn-ai/skills
claude plugin install vakyn@vakyn-ai
```

Run `/reload-plugins` in an open session, or start a new one. Ask in plain words ("where could
VAKYN help in this repo?") and Claude picks the skill, or call one directly: `/vakyn:vakyn-convert`.

<details>
<summary><strong>Update</strong></summary>

Installed plugins update in the background when a new version is released. To update now:

```bash
claude plugin marketplace update vakyn-ai
claude plugin update vakyn@vakyn-ai
```

</details>

## What you need

- A running **open-server** with a VAKYN model and an API key. No server yet? Ask Claude
  "set up VAKYN on this machine": the `vakyn` skill picks the model file for your hardware and
  walks you through install, start and key.
- Your key in an environment variable (`VAKYN_API_KEY`, or `TYPESAFE_API_KEY` for the official
  SDKs). Claude never asks you to paste it into the chat.

## The skills

| Skill | Use it to | Try |
|---|---|---|
| `vakyn` | check if VAKYN fits, pick a model file, set up the server, make a first call, look up the API | "I have a 12 GB GPU, which VAKYN model should I run?" |
| `vakyn-research` | find the places in an app or process where a chat model makes decisions VAKYN could make; writes a ranked `vakyn-research.md`, changes nothing | "Where could VAKYN help in this repo?" |
| `vakyn-questions` | choose `noul`, `choice` or `score`, write options and levels, design the state, fix a bad answer | "Why did it pick billing for this message?" |
| `vakyn-convert` | turn a chat-model prompt or a tool list (OpenAI, Anthropic, MCP) into VAKYN calls and Python or TypeScript code; VAKYN picks the tool, the chat model fills the arguments; side by side first | "Make VAKYN pick the tool in `agent.py`." |
| `vakyn-workflow` | design a new decision workflow from eight patterns: route, triage, tool pick, check a claim, rate with a rubric, pick the best match, spot risk, fill a form step | "Build a router for our returns emails." |
| `vakyn-check` | run a 30-record test against your current chat model, read a side-by-side log, set confidence thresholds from your labels, review before going live | "Here's a week of side-by-side logs. Can we switch?" |

A typical path: `vakyn-research` → `vakyn-convert` or `vakyn-workflow` → `vakyn-check`.

## How the skills work

- **Every request is checked before it is sent**: right shapes, limits, described options, an
  escape option such as `other` or `none`, one question per proposition.
- **Code does what must be exact.** Arithmetic, dates, thresholds and rules stay in your code;
  VAKYN answers the judgment.
- **Unsure answers have a path**: a person, a chat model, or a review queue.
- **No invented answers.** If your server is not reachable, Claude says so and still writes the
  request and the code.
- Generated code uses the official TypeSafe SDKs (`typesafe-sdk`, `@typesafe-ai/sdk`), which work
  with VAKYN's Jev-compatible API once their base URL points at your server.

## Other coding agents

The skills are packaged for Claude Code. Want them for another agent? Open an issue and say which.

## Develop

```bash
claude --plugin-dir .                     # try the plugin from this folder
make test                                 # offline: manifests, skills, links, voice, example requests
VAKYN_API_KEY=... make test-live          # send every example request to VAKYN_BASE_URL
VAKYN_API_KEY=... make eval TAG=vakyn     # headless Claude Code runs per skill, graded
make release VERSION=x.y.z                # validate, bump, tag, push
```

`make eval` uses your Claude account (about $0.15–0.40 per case). See [evals/README.md](evals/README.md).
The design is in [spec/spec-skills-v1.md](spec/spec-skills-v1.md).

## License

MIT
