# Guardrails for agents: allow, hold or block an agent's call

**Use when** an agent can take actions with real effects (refunds, emails to customers, changes
to accounts or data), some are hard to undo, and you want a check on every call, not only the
ones you already suspect.
**Not when** you are sorting incoming messages that need a person: that is
[spot risk](spot-risk.md). This pattern sits in front of the agent's *outgoing* call.

The check sits in front of the tool call, not inside the agent: your code calls VAKYN before the
API call goes out and acts on the answer.

## The request

State: the call (API and body), the agent's job in plain words (what it is for, what it may do,
its limits) and the context your systems know. Questions, all in one request:

- `action`: `choice` of `allow` / `ask_human` / `block`;
- the facts that decide it, each its own question: `irreversible` (`noul`), `damage` (`score`:
  easy / takes some work / hard / impossible to put right), `within_job` (`noul`).

[examples/guardrail-clear.request.json](../../examples/guardrail-clear.request.json) and
[examples/guardrail-borderline.request.json](../../examples/guardrail-borderline.request.json):
two EUR 900 refunds from a returns agent. Answers from a running VAKYN 4B:

| Case | action | irreversible | damage (confidence) | within_job | Result |
|---|---|---|---|---|---|
| Returned battery, checked in by the warehouse | allow 1.00 | 0.14 | 0.21 (0.79) | 0.99 | allow |
| "Never arrived", tracking says delivered, first order | block 0.93 | 0.29 | 0.77 (0.23) | 0.42 | hold for a person |

## The code

[examples/guardrail.py](../../examples/guardrail.py). The rule:

1. Work out how sure each answer is: `max(noul, 1 - noul)` for a `noul`, `confidence` otherwise.
2. If every answer is at least `SURE` sure, do what `action` says: run the call or block it.
3. Otherwise the call waits for a person, with the weakest answer as the reason
   ("damage is only 0.22 sure").
4. If VAKYN cannot be reached, hold the call. A guardrail never lets a call through unchecked.
5. Log every check: the call, the answers, the rule version and the decision. It is the record of
   what the agent tried to do and why it was allowed.

`SURE = 0.70` is the value in the docs example. For calls that are hard to undo, start at 0.8
([starting values](../../../check/references/thresholds.md)) and set yours on labeled checks with
the `check` skill.

## Common mistakes

- **One "is this safe?" question.** Ask the deciding facts separately: when a call is held, the
  person sees why, and you can tune the rule per fact.
- **A vague job.** `within_job` is only as good as the job text in the state. Write what the agent
  may do and its limits, with numbers ("up to EUR 1,000 per order").
- **Letting VAKYN's `allow` override your own limits.** Hard limits (amount caps, blocked
  accounts) are code, checked before VAKYN is asked.
- **Failing open.** A timeout or error must hold the call, not run it.

Same rule as routing by confidence, applied to actions instead of messages: see
[the unsure path](../unsure.md).
