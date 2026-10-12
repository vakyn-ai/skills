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
| – | two few-shot examples | drop | kept as test records for `check` |

Three judgments go to VAKYN in one request; four lines become code; three stay with the chat model.

## Answers from a running VAKYN 4B

The sample ticket: exports fail for the third time, dashboards work, they may leave at renewal, and
they ask for a refund.

- `category`: `billing`, confidence 0.99. The folded rule did its job: a bug complaint with a
  refund request lands in billing.
- `impact`: 1.99, level 2 at 0.98 ("an important feature is broken; the rest works") → P2.
- `cancel_threat`: 0.88, at or above the yes cut-off (0.8), so `churn_risk` is true.

## Code (Python)

Every decision has an unsure path: a `category` or `impact` below the threshold, or a
`cancel_threat` in the middle band, is answered by the old prompt instead, as before.

```python
import datetime
import json
import os

from typesafe_sdk import TypeSafeClient

vakyn = TypeSafeClient(timeout=30.0)
REQUEST = json.load(open("ticket-triage.request.json"))  # questions as plain dicts; state per ticket
CATEGORIES = REQUEST["questions"]["category"]["criteria"]
MODE = os.environ.get("VAKYN_TRIAGE_MODE", "side_by_side")  # the person flips it to "vakyn" after check
MIN_CONFIDENCE = 0.6     # starting value; set yours with check
YES_AT, NO_AT = 0.8, 0.2  # starting value; set yours with check (between them: unsure)

def priority_from(level, plan):  # rules in code
    priority = {3: 1, 2: 2}.get(level, 3)            # P1, P2, else P3
    return max(1, priority - 1) if plan == "enterprise" else priority

def ask_vakyn(ticket):
    """VAKYN's answers, None for each one it is unsure about; (None, {}) when VAKYN fails."""
    try:
        r = vakyn.system_one(state={"ticket": {"subject": ticket.subject, "body": ticket.body}},
                             questions=REQUEST["questions"])
    except Exception:
        return None, {}
    cat, impact, p = r.choices["category"], r.scores["impact"], r.nouls["cancel_threat"].noul
    return r, {
        "category": cat.choice if cat.choice in CATEGORIES and cat.confidence >= MIN_CONFIDENCE else None,
        "level": round(impact.score) if impact.confidence >= MIN_CONFIDENCE else None,  # 0..3
        "churn_risk": True if p >= YES_AT else False if p <= NO_AT else None,
    }

def triage(ticket):  # ticket: your record with subject, body, plan, created_at, replied
    r, v = ask_vakyn(ticket)
    old = None
    if MODE == "side_by_side" or not v or None in v.values():
        old = old_prompt_triage(ticket)  # side by side, VAKYN failed, or unsure on any decision
    log_answers(r, v, old, ticket)
    if MODE == "side_by_side" or not v:
        result = dict(old)                # the old prompt's answer is used, as before
    else:
        result = {
            "category": v["category"] or old["category"],
            "priority": f"P{priority_from(v['level'], ticket.plan)}" if v["level"] is not None else old["priority"],
            "churn_risk": v["churn_risk"] if v["churn_risk"] is not None else old["churn_risk"],
        }
    result.update(language=detect_language(ticket.body),
                  overdue=not ticket.replied and hours_since(ticket.created_at) > 48,
                  vakyn_request_id=r and r.request_id)
    return result
# The summary and the first reply stay with the chat model, after triage, with the category given.

def log_answers(r, v, old, ticket, path="vakyn-triage.jsonl"):
    """One line per question, the format check reads. Null fields: that side was not asked or failed."""
    old = old or {}
    chat = {"category": old.get("category"), "priority": old.get("priority"),
            "cancel_threat": None if old.get("churn_risk") is None else "yes" if old["churn_risk"] else "no"}
    mine = {q: (None, None, None) for q in chat}
    if r is not None:
        cat, impact, p = r.choices["category"], r.scores["impact"], r.nouls["cancel_threat"].noul
        mine = {
            "category": (cat.choice, cat.confidence, dict(cat.probabilities)),
            "priority": (f"P{priority_from(round(impact.score), ticket.plan)}", impact.confidence,  # compared
                         {str(k): x for k, x in impact.probabilities.items()}),                   # after the rules
            "cancel_threat": ("yes" if p >= 0.5 else "no", abs(2 * p - 1), {"yes": p, "no": 1 - p}),
        }
    unsure = {"category": "category", "priority": "level", "cancel_threat": "churn_risk"}
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(path, "a") as f:
        for q, (pick, conf, probs) in mine.items():
            used = "vakyn" if MODE == "vakyn" and v and v[unsure[q]] is not None else "chat"
            f.write(json.dumps({"ts": ts, "request_id": r and r.request_id, "question": q,
                                "vakyn_pick": pick, "vakyn_confidence": conf, "vakyn_probabilities": probs,
                                "chat_pick": chat[q], "agree": None if None in (pick, chat[q]) else pick == chat[q],
                                "mode": MODE, "used": used}) + "\n")
```

Side by side is the default: the old prompt's answer is used, VAKYN's is logged next to it per
question ([log format](../references/code-shape.md#prompts-with-several-questions)). Switch with
`VAKYN_TRIAGE_MODE=vakyn` after the `check` skill has compared them.
