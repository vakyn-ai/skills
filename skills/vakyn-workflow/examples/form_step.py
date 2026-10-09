"""Decide which form field to ask about next in a claim intake chat. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

from typesafe_sdk import Choice, TypeSafeClient

FIELDS = {  # every field of the form, with what it is for
    "emergency_help": "Whether the damage is still happening and the person needs an emergency repair sent now",
    "incident_date": "The exact date and time the damage happened, when the person has not given it",
    "damaged_items": "A list of what was damaged and roughly what it is worth",
    "photos": "Photos of the damage",
    "repair_quote": "A quote or invoice from a repairer",
}
ENDINGS = {
    "ready_to_submit": "Nothing more is needed now; the claim can be submitted",
    "needs_person": "The person is upset, confused or describing something the form cannot capture, "
                    "so hand over to a claims handler",
}
MIN_CONFIDENCE = 0.6  # starting value; set yours with vakyn-check. Below it, ask the empty fields in their fixed order

client = TypeSafeClient(timeout=30.0)


def next_field(filled: dict, latest_reply: str) -> str:
    empty = {k: v for k, v in FIELDS.items() if k not in filled}  # code knows what is filled
    if not empty:
        return "ready_to_submit"  # nothing to ask: no question needed
    options = {**empty, **ENDINGS}
    r = client.system_one(
        state={"form": "Home insurance claim", "filled": filled, "latest_reply": latest_reply},
        questions={"next_field": Choice(
            instructions=(
                "Which empty field of the form should the assistant ask about next? Ask first about what "
                "matters most for the person right now, given state.filled and state.latest_reply."
            ),
            criteria=options,
        )},
    )
    pick = r.choices["next_field"]
    if pick.choice not in options or pick.confidence < MIN_CONFIDENCE:
        return next(iter(empty))  # unsure: fall back to the fixed order
    return pick.choice  # a field (your chat model or template words the question), or an ending


STEPS = [
    ({"policy_number": "HX-20931", "claim_type": "water damage"},
     "A pipe burst under the kitchen sink last night. There is water all over the floor and it is still dripping."),
    ({"policy_number": "HX-20931", "claim_type": "water damage", "emergency_help": "plumber booked for 9am",
      "incident_date": "last night, around 11pm"},
     "The plumber is coming. The floor tiles and the cupboard under the sink are ruined."),
    ({"policy_number": "HX-20931", "claim_type": "water damage"},
     "I do not understand why you need all this. My neighbour's flat flooded mine, it is not even my pipe!"),
]
for filled, reply in STEPS:
    print(f"{next_field(filled, reply):16} | {reply[:60]}")
