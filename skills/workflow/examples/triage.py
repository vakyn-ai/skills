"""Triage a batch of repair requests by trade and urgency, many at a time. Standard library only.

Needs VAKYN_API_KEY. VAKYN_BASE_URL is optional (default https://api.vakyn.com).
"""

import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_URL = os.environ.get("VAKYN_BASE_URL", "https://api.vakyn.com")
MAX_RETRIES = 4  # retries 429 after the delay VAKYN asks for, and 5xx after a short wait


class RateLimited(Exception):
    """Still 429 after every retry."""


def decide(state: dict, questions: dict, timeout: float = 30.0) -> dict:
    """POST /v1/systemone with retries; returns the answers by question name."""
    body = json.dumps({"state": state, "questions": questions}).encode()
    headers = {"Authorization": f"Bearer {os.environ['VAKYN_API_KEY']}", "Content-Type": "application/json"}
    for attempt in range(MAX_RETRIES + 1):
        req = urllib.request.Request(f"{BASE_URL}/v1/systemone", data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)["answers"]
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            if attempt == MAX_RETRIES:
                if e.code == 429:
                    raise RateLimited() from e
                raise
            time.sleep(float(e.headers.get("retry-after") or 2 ** attempt))


TRADES = {
    "plumbing": "Leaks, taps, toilets, drains, water pressure",
    "electrical": "Lights, sockets, fuses, power cuts in the flat",
    "heating": "Radiators, boiler, hot water temperature",
    "appliance": "Oven, fridge, washing machine or other supplied appliance",
    "pests": "Mice, insects or other pests",
    "general": "Doors, windows, locks, floors, walls and other fixes inside the flat",
    "other": "None of these, or not a repair: noise complaints, parking, questions about rent",
}
URGENCY = [
    "Routine: cosmetic or minor, fine at the next planned visit",
    "This week: a nuisance, the flat is still usable",
    "Within 24 hours: daily life is hard, or a vulnerable person is affected",
    "Emergency now: danger to people or the building, such as gas smell, sparks or flooding",
]
# Both questions only need the request text, so they go in ONE request per record.
QUESTIONS = {
    "trade": {"type": "choice", "instructions": "Which trade is needed for the repair request in state.request?",
              "criteria": TRADES},
    "urgency": {"type": "score", "instructions": "How soon does the repair in state.request need someone on site?",
                "criteria": URGENCY},
}
MAX_IN_FLIGHT = 8  # VAKYN Cloud: under 60 requests/s per key; own server: below --max-queue
MIN_CONFIDENCE = 0.6  # starting value; set yours with check


def triage(record):
    try:
        answers = decide(
            {"building": record["building"], "unit": record["unit"], "request": record["text"]}, QUESTIONS
        )
    except RateLimited:  # still 429 after the retries: keep it for a later pass
        return {**record, "queue": "retry_later"}
    trade, urgency = answers["trade"], answers["urgency"]
    unsure = trade["choice"] == "other" or min(trade["confidence"], urgency["confidence"]) < MIN_CONFIDENCE
    if urgency["probabilities"].get("3", 0) > 0.2:  # a rule in code: any real chance of an emergency goes to on-call
        queue = "on_call_now"
    else:
        queue = "dispatcher_review" if unsure else trade["choice"]
    return {**record, "trade": trade["choice"], "urgency": urgency["score"], "queue": queue}


def main(records):
    # Bounded concurrency: at most MAX_IN_FLIGHT requests at once.
    with ThreadPoolExecutor(max_workers=MAX_IN_FLIGHT) as pool:
        results = list(pool.map(triage, records))
    for r in sorted(results, key=lambda r: -r.get("urgency", 0)):  # most urgent first
        print(f"{r['unit']:4} {r['queue']:18} {r.get('urgency', 0):.2f}  {r['text'][:60]}")


RECORDS = [
    {"building": "Elm Court", "unit": "3B", "text": "The bedroom radiator has been cold for two days and the flat is at 14 degrees. We have a newborn."},
    {"building": "Elm Court", "unit": "1A", "text": "Water is coming through the ceiling above the bathroom light and the light just went off."},
    {"building": "Elm Court", "unit": "5C", "text": "One kitchen cupboard door is a bit loose."},
    {"building": "Elm Court", "unit": "2D", "text": "Saw two mice behind the fridge this week."},
    {"building": "Elm Court", "unit": "4A", "text": "Can I get a second parking permit for my partner?"},
    {"building": "Elm Court", "unit": "6B", "text": "The oven does not heat up anymore, the hob still works."},
]

main(RECORDS)
