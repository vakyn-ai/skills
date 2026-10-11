# Fan out: ask every branch's question in one request

**Use when** a first decision picks a branch and each branch needs its own follow-up question,
and waiting for two requests in a row is too slow: route a message, then the billing topic, the
sign-in problem or the bug's impact.
**Not when** the follow-up needs the first answer as evidence (put that answer in a second
request's state, see [compose](../compose.md)), or there are so many branches that most of the
request is wasted.

## The request

[examples/fan-out.request.json](../../examples/fan-out.request.json): a `choice` for the team,
plus one question per branch, all over the same message. No question sees another's answer, so
each branch question **states its premise**: "Suppose the customer's message is about billing.
Which billing topic is it about? If it is not about billing at all, pick not_billing."

Answer from a running VAKYN 4B: "Our company card expired last week and the renewal payment
failed…" → team `billing` (1.00), billing topic `payment_failed` (1.00).

The same request also answered the bug question with `bug_blocks_work` 2.45 on that billing
message. That answer is about a premise that is false here; the code never reads it.

## The code

[examples/fan_out.py](../../examples/fan_out.py)

- One request holds the team question and all branch questions.
- Code reads `team` first, then only the answer for that branch. The other answers are ignored,
  however sure or unsure they look.

Run on three messages: expired card → `billing/payment_failed`; "nobody on our team can sign
in" → `access/urgent` (`locked_out_everyone` 1.00); PDF export crashes → `product_queue` (bug
level 2.23, below the 2.5 urgent cut).

## Unsure path

The team answer decides everything, so it gets the threshold: `other` or low confidence → the
triage queue. A branch answer that is unsure (or an escape such as `not_billing` on the billing
branch) → that team's general queue.

## Common mistakes

- **No premise in the branch question.** "Which billing topic is it?" over a sign-in message
  forces a billing pick with nothing to go on. State the premise and give an escape option.
- **Reading answers from other branches.** They answer a question whose premise is false. Do not
  log them as findings or show them to users.
- **Fanning out too wide.** Extra questions are cheap because the state is read once, but each
  one still adds to the request size limit and to what you maintain. Fan out to the few common
  branches; send rare ones as a second request.
