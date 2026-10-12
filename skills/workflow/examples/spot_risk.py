"""Flag messages that need a person: one noul per risk, combined in code. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

from typesafe_sdk import Noul, TypeSafeClient

RISKS = {  # several risks can be true at once, so each is its own noul (not one choice)
    "refund_demand": Noul(
        instructions="Does state.message ask for money back?",
        criteria={"true": "Asks for a refund, a chargeback or compensation in money",
                  "false": "Asks for something else, such as a repair, a swap or information"}),
    "legal_threat": Noul(
        instructions="Does state.message threaten legal action?",
        criteria={"true": "Mentions a lawyer, court, a claim, or reporting the company to an authority",
                  "false": "Complains without any legal step"}),
    "safety_issue": Noul(
        instructions="Does state.message describe a danger to the safety of people?",
        criteria={"true": "Fire, smoke, burns, electric shock, injury, a child or pet put at risk",
                  "false": "The problem only affects the product, the order or money"}),
    "public_complaint": Noul(
        instructions="Does state.message threaten to complain in public?",
        criteria={"true": "Threatens a bad review, a social media post or going to the press",
                  "false": "No public complaint is mentioned"}),
}
FLAG = 0.8   # at or above: the risk is there. Starting value; set yours with check
CLEAR = 0.2  # at or below: the risk is not there; in between is unsure. Starting value
# Settings: a missed safety issue costs more than a false alarm, so tune them per risk on your own data.

client = TypeSafeClient(timeout=30.0)


def screen(message: str, order: dict) -> tuple[str, list[str]]:
    r = client.system_one(state={"channel": "chat", "order": order, "message": message}, questions=RISKS)
    p = {k: r.nouls[k].noul for k in RISKS}
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
