"""First call with the official SDK: pip install typesafe-sdk.

Needs TYPESAFE_BASE_URL (your server, e.g. http://127.0.0.1:8080) and TYPESAFE_API_KEY (vk_...).
"""

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient(timeout=30.0)
result = client.system_one(
    state={
        "channel": "email",
        "customer": {"plan": "team", "seats": 12},
        "message": "Since this morning nobody on our team can sign in. We have a client demo at 3pm.",
    },
    questions={
        "outage": Noul(instructions="Does state.message say the customer cannot use the product right now?"),
        "team": Choice(
            instructions="Which team should handle state.message?",
            criteria={
                "billing": "Invoices, charges and refunds",
                "access": "Sign-in, passwords and permissions",
                "product": "Bugs and how-to questions",
                "other": "None of these teams fits",
            },
        ),
        "urgency": Score(
            instructions="How soon does state.message need a reply?",
            criteria=["Can wait a few days", "Today", "Within the hour"],
        ),
    },
)

team = result.choices["team"]
print("outage :", result.nouls["outage"].noul)
print("team   :", team.choice, team.confidence)
print("urgency:", result.scores["urgency"].score)
print("request:", result.request_id)
