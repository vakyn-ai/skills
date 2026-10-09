# Answer key: helpdesk-py

A small Python worker that reads a support inbox and uses the OpenAI SDK. Every chat-model call
goes through `ask()` in `helpdesk/llm.py`; the spots are the callers of `ask()`. Line numbers
point at each `ask(` call.

## Decision spots

| Where | What it decides | Question type | Signs in the code |
|---|---|---|---|
| `helpdesk/triage.py:23` `is_spam` | is this email spam or a real request | `noul` | "Answer only yes or no", `max_tokens=1`, `startswith("yes")` |
| `helpdesk/triage.py:28` `route_ticket` | which team gets the ticket | `choice` (billing, technical, account, sales, plus an escape option) | JSON mode, a fixed `TEAMS` list, `team in TEAMS` check |
| `helpdesk/triage.py:39` `rate_urgency` | how urgent the ticket is | `score` (5 described levels) | "Rate … from 1 to 5", "number only", `int(answer)` |

All three run on every incoming email (spam check) or every real ticket (routing, urgency).
Routing and urgency use the larger model. Next skill for all three: `vakyn-convert`.

## Writing spots (keep)

| Where | What it writes | Why it stays |
|---|---|---|
| `helpdesk/replies.py:12` `draft_reply` | first reply to the customer | free text |
| `helpdesk/reports.py:13` `weekly_summary` | weekly summary for the lead | free text, and a week of tickets can pass 32,768 tokens |

## Not chat-model calls

`helpdesk/inbox.py` (mail and database), `helpdesk/worker.py` (wiring; the urgency threshold
`URGENT_AT` is a rule and stays in code).
