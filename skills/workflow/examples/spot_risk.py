"""Flag messages that need a person: one noul per risk, combined in code. Standard library only.

Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import urllib.request

RISKS = {  # several risks can be true at once, so each is its own noul (not one choice)
    "refund_demand": {
        "type": "noul",
        "instructions": "Does state.message ask for money back?",
        "criteria": {"true": "Asks for a refund, a chargeback or compensation in money",
                     "false": "Asks for something else, such as a repair, a swap or information"}},
    "legal_threat": {
        "type": "noul",
        "instructions": "Does state.message threaten legal action?",
        "criteria": {"true": "Mentions a lawyer, court, a claim, or reporting the company to an authority",
                     "false": "Complains without any legal step"}},
    "safety_issue": {
        "type": "noul",
        "instructions": "Does state.message describe a danger to the safety of people?",
        "criteria": {"true": "Fire, smoke, burns, electric shock, injury, a child or pet put at risk",
                     "false": "The problem only affects the product, the order or money"}},
    "public_complaint": {
        "type": "noul",
        "instructions": "Does state.message threaten to complain in public?",
        "criteria": {"true": "Threatens a bad review, a social media post or going to the press",
                     "false": "No public complaint is mentioned"}},
}
FLAG = 0.8   # at or above: the risk is there. Starting value; set yours with check
CLEAR = 0.2  # at or below: the risk is not there; in between is unsure. Starting value
# Settings: a missed safety issue costs more than a false alarm, so tune them per risk on your own data.

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")


def decide(state: dict, questions: dict, timeout: float = 30.0) -> dict:
    """POST /v1/systemone; returns the answers by question name."""
    req = urllib.request.Request(
        f"{BASE_URL}/v1/systemone",
        data=json.dumps({"state": state, "questions": questions}).encode(),
        headers={"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["answers"]


def screen(message: str, order: dict) -> tuple[str, list[str]]:
    answers = decide({"channel": "chat", "order": order, "message": message}, RISKS)
    p = {k: answers[k]["noul"] for k in RISKS}
    flagged = [k for k, v in p.items() if v >= FLAG]
    unsure = [k for k, v in p.items() if CLEAR < v < FLAG]
    if p["safety_issue"] > CLEAR:  # rules in code: safety first, even when unsure
        return "safety_team_now", flagged + unsure
    if "legal_threat" in flagged:
        return "legal_team", flagged
    if flagged or unsure:
        return "person_review", flagged + unsure
    return "normal_queue", []


ORDER = {"product": "Ember 2000 fan heater", "delivered_days_ago": 9}
for msg in [
    "The heater started smoking last night and the plug is melted. I want a full refund.",
    "Third time asking. Refund me by Friday or my lawyer will file a claim, and I will post about it everywhere.",
    "Does the heater have a timer? I could not find it in the manual.",
]:
    queue, why = screen(msg, ORDER)
    print(f"{queue:16} {', '.join(why):45} | {msg[:50]}")
