"""Pick the help article that best answers a question, from the top search results. Standard library only.

Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import urllib.request

ARTICLES = [  # what your search returned; code drops what fails a hard rule before asking
    {"id": "hc_204", "lang": "en", "published": True, "title": "Change your email address",
     "summary": "update the address we send all mail to"},
    {"id": "hc_311", "lang": "en", "published": True, "title": "Notification settings",
     "summary": "turn each email type on or off, such as summaries, alerts and product news"},
    {"id": "hc_118", "lang": "en", "published": True, "title": "Failed payments",
     "summary": "why a payment fails and how to retry it"},
    {"id": "hc_402", "lang": "en", "published": True, "title": "Unsubscribe from marketing",
     "summary": "stop newsletters and offers with one link"},
    {"id": "hc_087", "lang": "en", "published": True, "title": "Close your account",
     "summary": "delete your account and all data"},
    {"id": "hc_311_de", "lang": "de", "published": True, "title": "Benachrichtigungen",
     "summary": "E-Mail-Arten ein- und ausschalten"},
]
MIN_CONFIDENCE = 0.6  # starting value; set yours with check

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


def best_article(question: str, lang: str) -> str | None:
    candidates = [a for a in ARTICLES if a["lang"] == lang and a["published"]][:20]  # rules in code
    options = {a["id"]: f"{a['title']}: {a['summary']}" for a in candidates}  # name items by their own id
    options["no_good_match"] = "None of these articles answers the question"
    answers = decide(
        {"question": question},
        {"article": {
            "type": "choice",
            "instructions": "Which help article best answers the customer question in state.question?",
            "criteria": options,
        }},
    )
    pick = answers["article"]
    if pick["choice"] not in options or pick["choice"] == "no_good_match" or pick["confidence"] < MIN_CONFIDENCE:
        return None  # no article: hand the question to a person or the chat model
    return pick["choice"]


for q in [
    "How do I stop the weekly summary emails? I still want alerts when a payment fails.",
    "My card was declined this morning, what now?",
    "Can I pay by bank transfer instead of card?",
]:
    print(f"{best_article(q, 'en') or 'to_person':10} | {q}")
