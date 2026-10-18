"""Route each support ticket to a team. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL (https://api.vakyn.com, or your own server) and TYPESAFE_API_KEY (vk_...).
"""

from typesafe_sdk import Choice, TypeSafeClient

TEAMS = {
    "billing": "Invoices, charges, refunds, plan changes and seat counts",
    "access": "Signing in, passwords, two-factor codes, user roles and permissions",
    "integrations": "Connections to other tools: Slack, webhooks, API tokens, imports and exports",
    "bugs": "Something in the app itself is broken, slow or shows an error",
    "other": "Not a support request for these teams: sales, partnerships, press, job applications, spam",
}
MIN_CONFIDENCE = 0.6  # starting value; set yours with check

client = TypeSafeClient(timeout=30.0)


def build_state(ticket: dict) -> dict:
    """Evidence only: the ticket text and facts from your records. No guesses about the team."""
    return {
        "channel": ticket["channel"],
        "customer": {"plan": ticket["plan"], "seats": ticket["seats"]},
        "subject": ticket["subject"],
        "message": ticket["body"],
    }


def route(ticket: dict) -> tuple[str, float]:
    result = client.system_one(
        state=build_state(ticket),
        questions={
            "team": Choice(
                instructions="Which support team should handle the ticket in state.subject and state.message?",
                criteria=TEAMS,
            )
        },
    )
    team = result.choices["team"]
    if team.choice not in TEAMS:  # code checks the pick is one we offered
        raise ValueError(f"unexpected option {team.choice!r} (request {result.request_id})")
    if team.choice == "other" or team.confidence < MIN_CONFIDENCE:
        return "triage_queue", team.confidence  # unsure or off-topic: a person routes it
    return team.choice, team.confidence


TICKETS = [
    {"channel": "web form", "plan": "business", "seats": 40, "subject": "Slack alerts stopped",
     "body": "Since we rotated our API token yesterday, the Slack alerts from your app stopped arriving."},
    {"channel": "email", "plan": "starter", "seats": 3, "subject": "Charged twice",
     "body": "My card shows two charges for March. Please refund one of them."},
    {"channel": "email", "plan": "none", "seats": 0, "subject": "Partnership idea",
     "body": "We run a podcast for operations teams and would love to talk about a sponsorship."},
]

for t in TICKETS:
    queue, confidence = route(t)
    print(f"{queue:13} {confidence:.2f}  {t['subject']}")
