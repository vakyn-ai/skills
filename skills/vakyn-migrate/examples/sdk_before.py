"""BEFORE: hosted Jev through the official Python SDK, with a pinned hosted model name.

The model name and the key are written into the code, so moving means a code change.
"""

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient(model="jev-1.13.0", timeout=10.0)  # TYPESAFE_API_KEY = hosted key


def triage(message: str) -> dict:
    result = client.system_one(
        state={"message": message},
        questions={
            "team": Choice(
                instructions="Which desk should answer state.message?",
                criteria={
                    "repairs": "Broken parts, flat tires, brakes, gears",
                    "bookings": "Reserving, changing or cancelling a rental",
                    "billing": "Charges, deposits, refunds",
                    "other": "None of these fits",
                },
            ),
            "refund": Noul(instructions="Does state.message ask for money back?"),
            "urgency": Score(
                instructions="How soon does state.message need a reply?",
                criteria=["This week", "Today", "Within the hour"],
            ),
        },
    )
    return {
        "team": result.choices["team"].choice,
        "team_confidence": result.choices["team"].confidence,
        "refund": result.nouls["refund"].noul,
        "urgency": result.scores["urgency"].score,
        "request_id": result.request_id,
    }
