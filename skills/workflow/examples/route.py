"""Route each support ticket to a team. Standard library only, nothing to install.

Needs VAKYN_API_KEY (vk_...). VAKYN_BASE_URL is optional (default https://api.vakyn.com, or your own server).
"""

import json
import os
import urllib.request

TEAMS = {
    "billing": "Invoices, charges, refunds, plan changes and seat counts",
    "access": "Signing in, passwords, two-factor codes, user roles and permissions",
    "integrations": "Connections to other tools: Slack, webhooks, API tokens, imports and exports",
    "bugs": "Something in the app itself is broken, slow or shows an error",
    "other": "Not a support request for these teams: sales, partnerships, press, job applications, spam",
}
MIN_CONFIDENCE = 0.6  # starting value; set yours with check

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def decide(state: dict, questions: dict, timeout: float = 30.0) -> tuple[dict, str]:
    """POST /v1/systemone; returns the answers by question name and the request id."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": state, "questions": questions}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"], r.headers.get("x-vakyn-request-id", "")


def build_state(ticket: dict) -> dict:
    """Evidence only: the ticket text and facts from your records. No guesses about the team."""
    return {
        "channel": ticket["channel"],
        "customer": {"plan": ticket["plan"], "seats": ticket["seats"]},
        "subject": ticket["subject"],
        "message": ticket["body"],
    }


def route(ticket: dict) -> tuple[str, float]:
    answers, request_id = decide(
        build_state(ticket),
        {
            "team": {
                "type": "choice",
                "instructions": "Which support team should handle the ticket in state.subject and state.message?",
                "criteria": TEAMS,
            }
        },
    )
    team = answers["team"]
    if team["choice"] not in TEAMS:  # code checks the pick is one we offered
        raise ValueError(f"unexpected option {team['choice']!r} (request {request_id})")
    if team["choice"] == "other" or team["confidence"] < MIN_CONFIDENCE:
        return "triage_queue", team["confidence"]  # unsure or off-topic: a person routes it
    return team["choice"], team["confidence"]


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
