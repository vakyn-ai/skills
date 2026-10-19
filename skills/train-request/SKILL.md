---
name: train-request
description: "Write a training request for the VAKYN loop: look at the person's app, their VAKYN questions and results on their own data, find where VAKYN is still wrong or unsure after the wording is tuned, and write a short proposal (vakyn-proposal.md) the person sends to VAKYN, saying what VAKYN should be trained on for their use case. Use when someone asks for a custom model, to train or adapt VAKYN on their decisions, to improve accuracy beyond wording, what to send VAKYN to get it trained, or how to contact VAKYN about their use case. Wording fixes first: optimize. Finding decisions first: research."
---

# VAKYN train-request: ask for VAKYN trained on your work

The person uses VAKYN (or plans to) and it is not yet right enough on some of their decisions.
VAKYN improves through **the loop**: measure it on the person's cases, find the cases it gets
wrong or is unsure about, train exactly there, and measure again on the same cases. This skill
prepares the person's side of the loop: it looks at their setup, gathers what VAKYN would need to
know, and writes a proposal **the person reads and sends themselves**. It sends nothing.

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
5. **Write `vakyn-proposal.md`** from the [template](references/proposal.md), in the person's
   project. No raw records, no personal data, no keys, no internal code: describe the decisions and
   use short **made-up examples** that show the pattern. Under 5,000 characters, so it fits the
   contact form.
6. **Show it and stop.** The person reads every line and decides what to send. Point out anything
   that may be confidential (customer names, product names, volumes) so they can cut it.

## Send it

The person sends it, not you:

- the [contact form](https://vakyn.com/contact), topic **Test it on your data**, with the proposal
  pasted as the message; or
- email to the address on the contact page, with `vakyn-proposal.md` attached.

The labeled cases themselves are shared later, only after VAKYN replies and the terms are agreed
(a DPA for GDPR, a BAA for HIPAA when needed). The proposal only says how many exist and what they
look like.

## Rules

- **Send nothing.** No form posts, no emails, no uploads from the agent. The person sends.
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
