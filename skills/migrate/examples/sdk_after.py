"""AFTER: the same code on VAKYN Cloud. Only configuration changed.

    export TYPESAFE_BASE_URL=https://api.vakyn.com   # root, no /v1; or your own open-server's URL
    export TYPESAFE_API_KEY=...                      # a vk_ key from vakyn.com/console/keys; never in code
    export TYPESAFE_DEFAULT_MODEL=jev-latest         # works on both; on VAKYN Cloud also vakyn-fast

Run: uv run --with typesafe-sdk python sdk_after.py
"""

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

# No model= and no api_key=: the SDK reads TYPESAFE_DEFAULT_MODEL, TYPESAFE_BASE_URL and
# TYPESAFE_API_KEY. Rollback = set the three variables back to the hosted values.
# The default timeout is 10 s per attempt; on a CPU-only server of your own raise it.
client = TypeSafeClient(timeout=30.0)


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
        "model": result.model,  # log it: it names the model that answered
    }


if __name__ == "__main__":
    print(triage("The chain on the e-bike I rented this morning snapped two km from your shop. "
                 "I'm stuck on the river path, can someone come out?"))
