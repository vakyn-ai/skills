"""First call over plain HTTP, Python standard library only (nothing to install).

Needs VAKYN_API_KEY (vk_...). VAKYN_BASE_URL is optional: https://api.vakyn.com, or your own server.
"""

import json
import os
import urllib.request

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")

body = {
    "state": {
        "channel": "email",
        "customer": {"plan": "team", "seats": 12},
        "message": "Since this morning nobody on our team can sign in. We have a client demo at 3pm.",
    },
    "questions": {
        "outage": {
            "type": "noul",
            "instructions": "Does the customer's message say they cannot use the product right now?",
        },
        "team": {
            "type": "choice",
            "instructions": "Which team should handle the customer's message?",
            "criteria": {
                "billing": "Invoices, charges and refunds",
                "access": "Sign-in, passwords and permissions",
                "product": "Bugs and how-to questions",
                "other": "None of these teams fits",
            },
        },
        "urgency": {
            "type": "score",
            "instructions": "How soon does the customer's message need a reply?",
            "criteria": ["Can wait a few days", "Today", "Within the hour"],
        },
    },
}

req = urllib.request.Request(
    f"{BASE_URL}/v1/systemone",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    request_id = r.headers.get("x-vakyn-request-id")
    answers = json.load(r)["answers"]

team = answers["team"]
print("outage :", answers["outage"]["noul"])
print("team   :", team["choice"], team["confidence"])
print("urgency:", answers["urgency"]["score"])
print("request:", request_id)
