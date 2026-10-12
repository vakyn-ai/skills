# Step map: supplier onboarding (sample)

From [sop.sample.md](sop.sample.md) and the ten agent runs in
[traces.sample.jsonl](traces.sample.jsonl). The program that follows it:
[program.py](program.py).

## What the traces show

| | Measured from the traces (synthetic sample) |
|---|---|
| Cases | 10, all labeled by a reviewer |
| Agent tool calls per case | 5.6 (2 to 9) |
| Agent cost per case, as logged | $0.40 ($0.06 to $0.93) |
| Agent agreement with labels | 9 of 10 (sup-0107: approved with a tax certificate older than 12 months) |
| Calls that decided a case | the first email read, the portal list, one registry record (sup-0103, sup-0108) |
| Calls the notes call wasted | 6 registry look-ups and 2 web searches on matches that shared nothing with the applicant; 1 web search after the bank rule had decided; 3 attachment opens that repeated the portal |

## The steps

| # | Step (procedure section) | Kind | How | Stop early? |
|---|---|---|---|---|
| 1 | Is it a new supplier application? (1) | decision: route | `choice` with `other` | yes: anything else closes the case |
| 2 | Category, personal data, payment terms (3) | decision: classify from the agent's output schema | enum → `choice` with `unclear`; two booleans → `noul`; same request as 1 | |
| 3 | Required documents and dates (2) | code | portal slots, issue and expiry dates against the received date | |
| 4 | Bank country (5) | code | equal to the registered country | yes: compliance outranks every later outcome |
| 5 | Which matches could be the applicant? (4) | decision: sift | the same `noul` for every match, one request; drop only clear noes | yes: no match kept, no look-ups |
| 6 | Registry record per kept match (4) | look-up: small agent step | one tool, a fixed output schema, fields checked against the cited page | yes: an equal registration number settles it in code |
| 7 | Which kept match is the applicant, if any? (4) | decision: pick | `choice` over kept matches + `none_of_these` + `cannot_tell` | yes: a match stops the case |
| 8 | Confirmed match or cannot tell (4) | hard judgment | a compliance officer | |
| 9 | Outcome (6) | code | the procedure's order of outcomes | |
| 10 | Unsure answer in 1, 2 or 7 | fallback | the whole case goes back to the agent, as before; an unsure sift answer keeps the match (it is looked up) | |

Writing the "please send these documents" email stays a template filled by code; no step needs a
chat model to write.

## Triage and early stops

- **The look-ups were the cost.** Nine of the 17 tool calls in sup-0103 and sup-0104 were
  registry look-ups and web searches. A sift over the match list costs one VAKYN request and keeps only
  the matches that could change the outcome.
- **Look up the most likely match first.** An equal registration number is exact, so code
  decides it and the rest are never looked up.
- **Order the steps by what can still change the outcome.** A bank-country mismatch already gives
  the top outcome after `not_an_application`, so screening is skipped.

## Rubric check per decision

| Step | The question carries | Fixed after the first run |
|---|---|---|
| 1 route | the five email kinds; the portal list as evidence | an offer with documents in the portal read as a sales pitch until the portal list was in the state |
| 2 classify | category definitions; what counts as personal data | "serving our staff is not handling their data" was missing |
| 5 sift | the full matching rule: similar name **and** country, address or person; legal form does not count | "similar name" was not defined; a same-country match with a shared main word was dropped |
| 7 pick | registration number, directors and address decide; `cannot_tell` for conflicts | |

These fixes came from looking at the ten sample cases, so they are the development set here. The
program now agrees with all ten labels; that says nothing until it runs on cases set aside before
the fixes ([rollout.md](rollout.md)).
