# Compose patterns

Real workflows chain two or three patterns. Rule of thumb: questions about the same record that do
not depend on each other share a request; a step that needs an earlier answer is a new request;
code sits between the steps.

## Spot risk, then route

Risky messages go to a person before any routing. The risk nouls and the team `choice` read the
same message and do not depend on each other, so they can share one request; code applies the
order.

```python
r = client.system_one(state=build_state(ticket), questions={**RISKS, "team": TEAM_Q})
risks = {k: r.nouls[k].noul for k in RISKS}
if risks["safety_issue"] > CLEAR or any(p >= FLAG for p in risks.values()):
    queue = "person_review"            # risk wins, whatever the team
else:
    team = r.choices["team"]
    queue = team.choice if team.choice != "other" and team.confidence >= MIN_CONFIDENCE else "triage_queue"
```

Patterns: [spot risk](patterns/spot-risk.md), [route](patterns/route.md).

## Check a claim per sentence

Code splits a page into sentences, keeps those that make a factual claim (or asks a `noul` "Does
state.sentence state a fact about the product?" first), then checks each claim against the source,
concurrently. The page passes only when every claim is `supported`.
Pattern: [check a claim](patterns/check-claim.md).

## Route, then a follow-up

A billing ticket then needs a billing topic. Two requests: the topic question is only sent when
the team is `billing` and sure, with `"team": "billing"` added to the state.
See [batching](batching.md#dependent-steps-separate-requests).

## Pick a tool, then fill it

VAKYN picks the step; the chat model fills the arguments for that one tool. On `ask_user` the chat
model writes the question; on `none` it replies. Pattern: [tool pick](patterns/tool-pick.md).

## Triage, then rate

Sort a batch first; then grade only the records that need it (for example, rate the draft reply
for every urgent ticket with a rubric). Patterns: [triage](patterns/triage.md),
[rubric](patterns/rubric.md).
