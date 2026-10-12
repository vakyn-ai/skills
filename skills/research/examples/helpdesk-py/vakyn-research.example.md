# Where VAKYN can help: helpdesk worker

Researched 2026-10-09 from the code in this folder (no call logs). No code was changed and no calls
were made. This is an example of the report `research` writes; in a real repo it is saved as
`vakyn-research.md`.

## Summary

1. **Route ticket to a team** (`helpdesk/triage.py:28`): a pick from four teams on every real
   ticket, on the larger model; a wrong pick is cheap to fix.
2. **Spam check** (`helpdesk/triage.py:23`): yes or no on every incoming email, the most frequent
   call in the app.
3. **Urgency rating** (`helpdesk/triage.py:39`): a 1 to 5 level on every real ticket, on the larger
   model; it decides who gets paged.

The first reply and the weekly summary are writing and stay with the chat model.

## Ranked spots

| # | Where | Decides | Question type | Gain | Risk | Effort | Priority | Next skill |
|---|---|---|---|---|---|---|---|---|
| 1 | `helpdesk/triage.py:28` | which team gets the ticket | `choice` | High (3) | Low (0) | Small (0) | 6 | `convert` |
| 2 | `helpdesk/triage.py:23` | spam or real request | `noul` | High (3) | Medium (1) | Small (0) | 5 | `convert` |
| 3 | `helpdesk/triage.py:39` | how urgent the ticket is | `score` | High (3) | Medium (1) | Small (0) | 5 | `convert` |

Priority = 2 × gain − risk − effort (gain High 3 / Medium 2 / Low 1; risk and effort High or
Large 2 / Medium 1 / Low or Small 0). Ties go to the lower risk, then the higher call volume, so
the spam check (3,000 a day) comes before urgency (2,000 a day).

## Spot details

### 1. Route ticket to a team (`helpdesk/triage.py:28`, `route_ticket`)

- **Decides:** which of billing, technical, account or sales handles the ticket.
- **Today:** `gpt-4o` in JSON mode, about 2,000 calls a day (code: 3,000 emails a day, a third
  spam), about 600 input and 30 output tokens per call. About $3.60 a day, $108 a month (assumed
  list price $2.50 per million input tokens and $10 per million output tokens, October 2026).
  Runs in the worker, before the reply is drafted.
- **VAKYN question:** `choice` over `billing`, `technical`, `account`, `sales`, each with a one-line
  description, plus `other` ("none of these teams fits"). State: subject and body of the email.
  Today an unknown team silently becomes `technical`; with `other` and a confidence, unsure
  tickets can go to a triage queue instead.
- **Risk:** Low. A wrong team means an agent moves the ticket. The draft reply names the team, so a
  wrong pick also shows up in the draft an agent reviews.
- **Effort:** Small. The options are already the `TEAMS` list; one function changes.
- **Next:** `convert`.

### 2. Spam check (`helpdesk/triage.py:23`, `is_spam`)

- **Decides:** whether an email is spam, a newsletter or an automated notice rather than a real
  request.
- **Today:** `gpt-4o-mini`, about 3,000 calls a day (code comment), about 560 input tokens and 1
  output token. About $0.25 a day (assumed list price $0.15 per million input tokens). Every email
  waits on it before anything else runs.
- **VAKYN question:** `noul`: "Is state.email spam, a newsletter or an automated notice rather than
  a request from a customer?" Better as two `noul` questions in one request (spam; automated
  notice) if the team treats them differently.
- **Risk:** Medium. A real email marked spam is never answered. Only mark spam above a high
  confidence; send unsure emails on as tickets.
- **Effort:** Small. One function; the string compare becomes a threshold on `noul`.
- **Next:** `convert`.

### 3. Urgency rating (`helpdesk/triage.py:39`, `rate_urgency`)

- **Decides:** how urgent the ticket is, 1 to 5.
- **Today:** `gpt-4o`, about 2,000 calls a day (code), about 620 input tokens and 1 output token.
  About $3.10 a day, $93 a month (same assumed price as spot 1).
- **VAKYN question:** `score` with five described levels, lowest first, written from the prompt
  ("can wait a week" … "outage, security problem or legal threat"). The threshold `URGENT_AT = 4`
  stays in code and reads the weighted `score`.
- **Risk:** Medium. Level 4 or 5 pages the on-call agent; a missed outage waits in the queue, an
  overrated ticket wakes someone. A separate `noul` for "security problem or legal threat" would
  make the most costly miss its own question.
- **Effort:** Small. Levels are already in the prompt; one function changes.
- **Next:** `convert`.

## Keep with the chat model

| Where | What it writes | Why |
|---|---|---|
| `helpdesk/replies.py:12` (`draft_reply`) | first reply to the customer | free text; it can take VAKYN's team and urgency as input |
| `helpdesk/reports.py:13` (`weekly_summary`) | weekly summary for the support lead | free text |

## Does not fit

| Where | What it does | Why not |
|---|---|---|
| `helpdesk/reports.py:13` | reads a week of tickets at once | writing, and 2,000 tickets a day is far over 32,768 tokens |
| `helpdesk/worker.py` `URGENT_AT` check | pages on-call at urgency 4+ | a threshold; stays in code |

## Assumptions and open questions

- Volumes come from the comment in `helpdesk/config.py` (3,000 emails a day, a third spam). Call
  logs would replace these with measured numbers.
- Prices are assumed list prices; please give your actual rates.
- Token counts are estimated from prompt length plus a typical one-page email.
- Does anyone check the spam folder? If not, spot 2 is higher risk than rated.
- How often do agents move a ticket to another team today? That is the bar VAKYN has to meet.

## Next steps

1. Pick one or more spots from the table (spot 1 is the safest start).
2. Run `convert` on `route_ticket`; `questions` helps word the team descriptions.
3. Test on about 30 of your own tickets with `check` before switching anything.
