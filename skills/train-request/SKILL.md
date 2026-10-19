---
name: train-request
description: "Write a training request for the VAKYN loop: look at the person's app, their VAKYN questions and results on their own data, find where VAKYN is still wrong or unsure after the wording is tuned, write a short proposal of what VAKYN should be trained on for their use case, and, after the person reads it and says yes, send it to VAKYN with their API key (POST /v1/training-requests) and follow its status. Use when someone asks for a custom model, to train or adapt VAKYN on their decisions, to improve accuracy beyond wording, what to send VAKYN to get it trained, or how to contact VAKYN about their use case. Wording fixes first: optimize. Finding decisions first: research."
---

# VAKYN train-request: ask for VAKYN trained on your work

The person uses VAKYN (or plans to) and it is not yet right enough on some of their decisions.
VAKYN improves through **the loop**: measure it on the person's cases, find the cases it gets
wrong or is unsure about, train exactly there, and measure again on the same cases. This skill
prepares the person's side of the loop: it looks at their setup, gathers what VAKYN would need to
know, writes a proposal, and sends it **only after the person reads it and says yes**, through the
training-requests API with their own key. They follow it in the console.

Shared material: [research](../research/SKILL.md) (finding decisions),
[optimize](../optimize/SKILL.md) (wording first), [check](../check/SKILL.md) (measuring on their
data), [VAKYN Cloud](../get-started/references/cloud.md).

## Pick the step

| The person… | Do |
|---|---|
| Has no VAKYN questions yet | `research` to find the decisions, then `workflow` or `convert`; come back with results |
| Has questions but never measured them on labeled cases | `check` (smoke test, labels), then `optimize`; come back |
| Has measured and tuned, and is still short on some decisions | [What to collect](references/collect.md), then [the proposal](references/proposal.md) |
| Asks what happens to their data, or what to share | [Privacy](references/proposal.md#privacy) |
| Has a proposal ready | [Send it](#send-it) |
| Asks what happened to a request they sent | `send_request.py status` ([API](references/api.md#follow-it)) |

## Steps

1. **Wording first.** A training request is for what wording cannot fix. Ask whether each question
   went through `optimize` (or at least `questions`' diagnose). If not, do that first and say why:
   it costs only their own model calls and often closes most of the gap.
2. **Look at the environment** ([collect](references/collect.md)): the app's decision points (reuse
   `vakyn-research.md` when it exists), the request files, the state builder, results files from
   `check` or `optimize` (`report.md`, promotion logs, labeled-case files), volumes from logs or
   code, where it runs. Read; change nothing.
3. **Find the losing cells**: per question, where VAKYN is still wrong or unsure on labeled cases,
   grouped by kind (option pairs, `noul` direction, `score` too high or low, a language, long
   documents, a type of document). Counts from their files only; never estimate a number that no
   file shows.
4. **Ask what is missing** in one short round: what a right answer is worth or a wrong one costs,
   the accuracy they need, volume, how fast an answer must come, where it must run (VAKYN Cloud or
   their own servers, region), and how many labeled cases they could share and under what terms.
5. **Write two files** in the person's project: `vakyn-proposal.md` from the
   [template](references/proposal.md), and `training-request.json`, the same content in the
   [API's fields](references/api.md#send) with the whole proposal in `proposal_markdown`. No raw
   records, no personal data, no keys, no internal code: describe the decisions, and give short
   **made-up examples** (`made_up: true`). Keep the proposal under 5,000 characters, so the
   contact-form fallback still works.
6. **Check, show, ask.** Copy [send_request.py](examples/send_request.py) into their project; run
   `check`, then `show`. The person reads every line; point out anything that may be confidential
   (customer or product names, volumes) so they can cut it. Ask: "Send this to VAKYN?"

## Send it

Only after a clear yes to the request as shown:

1. `python3 send_request.py status` first: the same use case may already be with VAKYN.
2. `python3 send_request.py send training-request.json --yes`. On `201`, give the person the console
   link (`vakyn.com/console/training/tr_…`); VAKYN replies there. A `422` lists the fields to fix:
   fix, show again, ask again. Other answers: [API](references/api.md#answers).
3. Later: `python3 send_request.py status [id]` shows the status, any quote and VAKYN's messages.

**Fallback** (no key, self-hosted only, or the API is not there): the person pastes
`vakyn-proposal.md` into the [contact form](https://vakyn.com/contact), topic **Test it on your
data**, or emails it.

The labeled cases themselves are shared later, only after VAKYN replies and the terms are agreed
(a DPA for GDPR, a BAA for HIPAA when needed), never in the request.

## Rules

- **Send only with a yes, only through the API.** Show the exact request first; no yes, nothing
  is sent. Never post the contact form, send email or upload files for the person.
- **No data leaves in the proposal.** Made-up examples only; counts and rates from their files;
  redact names of customers, people and internal systems unless the person asks to keep them.
- **Never invent results.** Every accuracy, count or rate comes from a file in their project, named
  in the proposal. No results yet: say so, and offer `check` first.
- **No promises for VAKYN.** No price, timeline, accuracy after training or guarantee. The FAQ says
  the price is quoted per use case once VAKYN has seen the sample; say that if asked.
- **Keys stay out of everything.** Never read `~/.config/vakyn/env` or `.env`; never put a key in
  the proposal.
- **One proposal per use case.** Several unrelated decisions: one proposal each, ranked, unless the
  person wants one message.
