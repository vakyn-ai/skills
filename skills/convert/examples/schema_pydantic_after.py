"""AFTER: the same ticket triage, with the decisions compiled into VAKYN questions.

Before: schema-pydantic-before.py, where the chat model fills all of TicketTriage.
After:  VAKYN answers category, urgent and sentiment; the chat model writes only the summary, plus
        any field VAKYN was unsure about. Code rebuilds the same TicketTriage, so callers do not change.

pip install typesafe-sdk openai pydantic
Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY (https://api.vakyn.com or your own server, and a vk_ key) and OPENAI_API_KEY.

Settings (environment):
  VAKYN_SCHEMA_MODE  side_by_side (default): the old structured-output call is used, as before;
                     VAKYN's answers are logged next to it. vakyn: the rebuilt object is used.
  VAKYN_SCHEMA_LOG   JSON lines log, one line per field (default vakyn-schema.jsonl).

python schema_pydantic_after.py --stub      runs two sample tickets; the chat model is stubbed
python schema_pydantic_after.py --request   prints the compiled request for the first sample
"""

import datetime
import json
import os
import sys
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, create_model
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

MODE = os.environ.get("VAKYN_SCHEMA_MODE", "side_by_side")
LOG_PATH = os.environ.get("VAKYN_SCHEMA_LOG", "vakyn-schema.jsonl")
MIN_CONFIDENCE = 0.6       # starting value; set yours with check
YES_AT, NO_AT = 0.8, 0.2   # starting value; set yours with check (between them: unsure)
STUB = "--stub" in sys.argv


# ---- The app's schema, unchanged (from schema-pydantic-before.py) --------------------------------

class Category(str, Enum):
    billing = "billing"
    shipping_label = "shipping_label"
    tracking = "tracking"
    account = "account"


class TicketTriage(BaseModel):
    category: Category = Field(
        description="billing: charges, invoices, plan changes and refunds. "
        "shipping_label: buying, printing or voiding a label. "
        "tracking: where a parcel is, late or lost parcels. "
        "account: sign-in, users and shop connections."
    )
    urgent: bool = Field(
        description="True when parcels cannot ship today because of the problem, "
        "or money is being taken by mistake right now."
    )
    sentiment: int = Field(ge=1, le=5, description="How the customer feels: 1 = angry, 3 = neutral, 5 = delighted.")
    summary: str = Field(description="One sentence for the support agent: the problem and what the customer wants.")


# ---- The compiled questions -----------------------------------------------------------------------
# Field descriptions became the criteria. The question text carries the meaning: the question's
# name ("urgent") is never sent to VAKYN.

QUESTIONS = {
    # enum -> choice. One option per enum value, plus `other`: the enum had no escape, and a
    # forced pick on a sales question or spam would be wrong.
    "category": Choice(
        instructions="Which category fits the problem in state.ticket?",
        criteria={
            "billing": "Charges, invoices, plan changes and refunds, even when a refund is asked for because of a broken label",
            "shipping_label": "Buying, printing or voiding a shipping label: blank, wrong or failed labels",
            "tracking": "Where a parcel is after it shipped: late, stuck or lost parcels",
            "account": "Sign-in, passwords, users and the connection to the customer's online shop",
            "other": "None of these: sales questions, feature ideas, spam, or no clear problem",
        },
    ),
    # bool -> noul. True and false described from the field description.
    "urgent": Noul(
        instructions="Is the problem in state.ticket urgent for the support team?",
        criteria={
            "true": "Parcels cannot go out today because of it, or a wrong charge is happening now",
            "false": "Shipping still works today and no money is being taken by mistake",
        },
    ),
    # int 1-5 -> score. Five levels in words, lowest first; level 0 is sentiment 1.
    "sentiment": Score(
        instructions="How does the customer who wrote state.ticket feel?",
        criteria=[
            "Angry: blames, threatens or insults",
            "Unhappy: frustrated or let down, but civil",
            "Neutral: states facts or asks a question with no clear feeling",
            "Positive: friendly or thankful",
            "Delighted: praises the product or the team warmly",
        ],
    ),
}
VAKYN_FIELDS = list(QUESTIONS)   # answered by VAKYN
KEPT_FIELDS = ["summary"]        # free text: stays with the chat model
CATEGORY_OPTIONS = set(QUESTIONS["category"].criteria)

# Start-up checks: every enum value is an option, and every field has exactly one owner.
assert {c.value for c in Category} <= CATEGORY_OPTIONS
assert set(VAKYN_FIELDS) | set(KEPT_FIELDS) == set(TicketTriage.model_fields)


# ---- VAKYN answers -> field values ----------------------------------------------------------------

vakyn = TypeSafeClient(timeout=30.0)


def ask_vakyn(ticket_text):
    """Returns (response, {field: (value, confidence, top)}); value is None when VAKYN is unsure,
    top is VAKYN's top answer either way (for the log). On any VAKYN error: (None, {}), and every
    field goes to the chat model."""
    try:
        r = vakyn.system_one(state={"ticket": ticket_text}, questions=QUESTIONS)
    except Exception as e:
        print(f"VAKYN failed: {e}", file=sys.stderr)
        return None, {}
    cat, p, sent = r.choices["category"], r.nouls["urgent"].noul, r.scores["sentiment"]
    category = cat.choice if cat.choice in {c.value for c in Category} and cat.confidence >= MIN_CONFIDENCE else None
    urgent = True if p >= YES_AT else False if p <= NO_AT else None
    sentiment = round(sent.score) + 1 if sent.confidence >= MIN_CONFIDENCE else None  # level 0..4 -> 1..5
    return r, {
        "category": (category, cat.confidence, cat.choice),   # `other` -> None: no enum value fits
        "urgent": (urgent, round(abs(2 * p - 1), 2), p >= 0.5),
        "sentiment": (sentiment, sent.confidence, round(sent.score) + 1),
    }


# ---- The chat model: only the fields VAKYN does not answer ---------------------------------------

def chat_fill(ticket_text, fields):
    """The old structured-output call, narrowed to `fields`. Same field types and descriptions."""
    Part = create_model("TicketTriagePart", **{f: (TicketTriage.model_fields[f].annotation,
                                                   TicketTriage.model_fields[f]) for f in fields})
    if STUB:  # no chat-model key in this demo: fixed values that pass the same validation
        stub = {"category": "billing", "urgent": False, "sentiment": 3,
                "summary": f"(stub summary) {ticket_text[:60]}..."}
        return Part(**{f: stub[f] for f in fields}).model_dump()
    from openai import OpenAI
    resp = OpenAI().chat.completions.parse(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": "Triage this support ticket for Parcelo, a shipping-label app."},
                  {"role": "user", "content": ticket_text}],
        response_format=Part,
    )
    return resp.choices[0].message.parsed.model_dump()


# ---- Rebuild the same typed object ----------------------------------------------------------------

@dataclass
class Triaged:
    value: TicketTriage                                   # the same type callers used before
    confidence: dict = field(default_factory=dict)        # field -> VAKYN confidence; None when the chat model wrote it
    source: dict = field(default_factory=dict)            # field -> "vakyn" or "chat"
    request_id: str | None = None


def triage(ticket_text) -> Triaged:
    r, answers = ask_vakyn(ticket_text)
    rid = r.request_id if r else None
    if MODE == "side_by_side":
        old = chat_fill(ticket_text, list(TicketTriage.model_fields))   # exactly as before
        log(rid, answers, old)
        return Triaged(TicketTriage(**old), {f: None for f in old}, {f: "chat" for f in old}, rid)

    unsure = [f for f in VAKYN_FIELDS if answers.get(f, (None,))[0] is None]
    from_chat = chat_fill(ticket_text, KEPT_FIELDS + unsure)   # one call: the summary plus unsure fields
    values = {f: v for f, (v, _, _) in answers.items() if v is not None} | from_chat
    log(rid, answers, from_chat)
    return Triaged(
        value=TicketTriage(**values),  # validated: a wrong type or value fails here, not downstream
        confidence={f: (answers[f][1] if f not in from_chat else None) for f in TicketTriage.model_fields},
        source={f: "chat" if f in from_chat else "vakyn" for f in TicketTriage.model_fields},
        request_id=rid,
    )


def log(rid, answers, chat):
    """One JSON line per decision field: VAKYN's value and confidence next to the chat model's."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        for q in VAKYN_FIELDS:
            v, c, mine = answers.get(q, (None, None, None))
            theirs = chat.get(q)
            theirs = theirs.value if isinstance(theirs, Enum) else theirs
            f.write(json.dumps({"ts": ts, "request_id": rid, "question": q, "vakyn_pick": mine,
                                "vakyn_confidence": c, "vakyn_sure": v is not None, "chat_pick": theirs, "mode": MODE,
                                "agree": None if None in (mine, theirs) else mine == theirs}) + "\n")


SAMPLES = [
    "Every label I print today comes out blank. I have 40 orders that must go out with the 4pm "
    "pickup and nothing works. This is the second time this month. Fix it now.",
    "Hi! Quick one: can I add a second user for my warehouse manager? Thanks, love the app.",
]

if __name__ == "__main__":
    if "--request" in sys.argv:
        print(json.dumps({"model": "jev-latest", "state": {"ticket": SAMPLES[0]},
                          "questions": {k: q.model_dump(exclude_none=True) for k, q in QUESTIONS.items()}},
                         indent=2))
        sys.exit()
    for text in SAMPLES:
        t = triage(text)
        print(type(t.value).__name__, t.value.model_dump(mode="json"))
        print("  confidence", t.confidence)
        print("  source    ", t.source)
