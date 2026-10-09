# Ticket triage prompt → VAKYN

Input: [ticket-triage.prompt.txt](ticket-triage.prompt.txt), a chat-model prompt that triages
support tickets and returns JSON. Output: [ticket-triage.request.json](ticket-triage.request.json)
and the code below. Method: [prompt-sort](../references/prompt-sort.md).

## Sort table

| # | Instruction (short) | Goes to | Becomes |
|---|---|---|---|
| 1 | category: billing, bug, account access, feature request, other | `choice` | `category`, with `other` as the escape option |
| 2 | P1 cannot use it / P2 important feature broken / P3 else | `score` + code | `impact` (4 described levels); code maps the level to P1–P3 |
| 3 | Enterprise plan raises priority one level | code | `if plan == "enterprise": priority = max(1, priority - 1)` |
| 4 | refund requests are always billing | fold | written into the `billing` and `bug` descriptions |
| 5 | threatens to cancel or move | `noul` | `cancel_threat` |
| 6 | detect the language | code | a language-detection library |
| 7 | older than 48 h with no reply → overdue | code | timestamps from the ticket system |
| 8 | one-sentence summary for the agent | keep | chat model |
| 9 | short first reply to the customer | keep | chat model, given the category as a fact |
| 10 | be concise and professional | keep | moves with lines 8–9 |
| 11 | respond only with JSON | drop | VAKYN answers are already named fields |
| – | two few-shot examples | drop | kept as test records for `vakyn-check` |

Three judgments go to VAKYN in one request; four lines become code; three stay with the chat model.

## Answers from a running VAKYN 4B

The sample ticket: exports fail for the third time, dashboards work, they may leave at renewal, and
they ask for a refund.

- `category`: `billing`, confidence 0.99. The folded rule did its job: a bug complaint with a
  refund request lands in billing.
- `impact`: 1.99, level 2 at 0.98 ("an important feature is broken; the rest works") → P2.
- `cancel_threat`: 0.88.

## Code (Python)

```python
import json

from typesafe_sdk import TypeSafeClient

vakyn = TypeSafeClient(timeout=30.0)
REQUEST = json.load(open("ticket-triage.request.json"))  # questions as written; state per ticket
MIN_CONFIDENCE = 0.8  # set it from your own labeled tickets with the vakyn-check skill

def triage(ticket):  # ticket: your record with subject, body, plan, created_at, replied
    r = vakyn.system_one(state={"ticket": {"subject": ticket.subject, "body": ticket.body}},
                         questions=REQUEST["questions"])
    category = r.choices["category"]
    if category.choice not in REQUEST["questions"]["category"]["criteria"] or category.confidence < MIN_CONFIDENCE:
        return old_prompt_triage(ticket)               # unsure: the chat model decides, as before
    level = round(r.scores["impact"].score)            # 0..3
    priority = {3: 1, 2: 2}.get(level, 3)              # P1, P2, else P3
    if ticket.plan == "enterprise":
        priority = max(1, priority - 1)
    return {
        "category": category.choice,
        "priority": f"P{priority}",
        "churn_risk": r.nouls["cancel_threat"].noul >= 0.5,
        "language": detect_language(ticket.body),
        "overdue": not ticket.replied and hours_since(ticket.created_at) > 48,
        "vakyn_request_id": r.request_id,
    }
# The summary and the first reply stay with the chat model, after triage, with the category given.
```

Run it side by side first: keep `old_prompt_triage` in use, log both results per ticket, and
switch after the `vakyn-check` skill has compared them.
