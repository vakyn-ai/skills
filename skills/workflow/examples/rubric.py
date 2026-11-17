"""Grade a support reply on three rubric criteria and combine them in code. Standard library only.

Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import urllib.request

RUBRIC = {  # criterion -> (question, levels lowest first, weight)
    "answers_question": ("How fully does state.agent_reply deal with what state.customer_message asks for?", [
        "Ignores the request or answers a different one",
        "Touches the request but leaves the main need open",
        "Handles the main need, with a gap a customer would notice",
        "Handles everything the customer asked, with a clear next step"], 0.5),
    "follows_policy": ("How well does state.agent_reply follow state.policy?", [
        "Breaks a rule in the policy",
        "Gets a policy detail wrong or misleading",
        "Within the policy, with a small gap",
        "Fully within the policy"], 0.3),
    "tone": ("How does the tone of state.agent_reply come across to the customer?", [
        "Rude, cold or blaming",
        "Neutral but stiff, reads like a template",
        "Friendly and polite",
        "Warm and personal while staying brief"], 0.2),
}
MIN_CONFIDENCE = 0.6  # starting value; set yours with check
POLICY = ("Refunds: full refund within 30 days of purchase. After 30 days, store credit only. "
          "Agents may not promise dates for engineering fixes.")

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


def grade(customer_message: str, agent_reply: str) -> dict:
    answers = decide(  # independent criteria: one request, one score each
        {"policy": POLICY, "customer_message": customer_message, "agent_reply": agent_reply},
        {k: {"type": "score", "instructions": q, "criteria": levels} for k, (q, levels, _) in RUBRIC.items()},
    )
    scores = {k: answers[k] for k in RUBRIC}
    top = {k: len(RUBRIC[k][1]) - 1 for k in RUBRIC}
    total = sum(RUBRIC[k][2] * s["score"] / top[k] for k, s in scores.items())  # weighted, 0 to 1
    unsure = [k for k, s in scores.items() if s["confidence"] < MIN_CONFIDENCE]
    if scores["follows_policy"]["score"] < 1.5:  # a rule in code: any policy breach goes to a lead
        verdict = "lead_review"
    else:
        verdict = "lead_review" if unsure else ("pass" if total >= 0.7 else "coach")
    return {"total": round(total, 2), "verdict": verdict, "unsure": unsure,
            **{k: round(s["score"], 2) for k, s in scores.items()}}


CASES = [
    ("I bought the annual plan 10 days ago and it does not work with our scanner. I want my money back.",
     "Sorry about that! I have started a full refund to your card; you will see it in 5 to 10 business days."),
    ("The export button crashes the app. When will this be fixed?",
     "Our engineers will have this fixed by Friday, guaranteed."),
    ("I bought the plan 3 months ago and want a refund.",
     "Refunds are not possible."),
    ("I bought the plan 3 months ago and want a refund.",
     "Sorry it did not work out. It has been more than 30 days, so I cannot refund the card, "
     "but I have added the full amount to your account as store credit."),
]
for msg, reply in CASES:
    print(grade(msg, reply), "|", reply[:50])
