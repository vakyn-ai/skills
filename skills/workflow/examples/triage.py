"""Triage a batch of repair requests by trade and urgency, many at a time. pip install typesafe-sdk

Needs TYPESAFE_BASE_URL and TYPESAFE_API_KEY.
"""

import asyncio

from typesafe_sdk import AsyncTypeSafeClient, Choice, RetryPolicy, Score, TypeSafeRateLimitError

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
    "trade": Choice(instructions="Which trade is needed for the repair request in state.request?", criteria=TRADES),
    "urgency": Score(instructions="How soon does the repair in state.request need someone on site?", criteria=URGENCY),
}
MAX_IN_FLIGHT = 8  # stay below the server's queue (--max-queue)
MIN_CONFIDENCE = 0.6  # starting value; set yours with check


async def triage(client, gate, record):
    async with gate:  # bounded concurrency: at most MAX_IN_FLIGHT requests at once
        try:
            r = await client.system_one(
                state={"building": record["building"], "unit": record["unit"], "request": record["text"]},
                questions=QUESTIONS,
            )
        except TypeSafeRateLimitError:  # still 429 after the SDK's retries: keep it for a later pass
            return {**record, "queue": "retry_later"}
    trade, urgency = r.choices["trade"], r.scores["urgency"]
    unsure = trade.choice == "other" or min(trade.confidence, urgency.confidence) < MIN_CONFIDENCE
    if urgency.probabilities.get(3, 0) > 0.2:  # a rule in code: any real chance of an emergency goes to on-call
        queue = "on_call_now"
    else:
        queue = "dispatcher_review" if unsure else trade.choice
    return {**record, "trade": trade.choice, "urgency": urgency.score, "queue": queue}


async def main(records):
    gate = asyncio.Semaphore(MAX_IN_FLIGHT)
    retry = RetryPolicy(max_retries=4)  # retries 429 after the delay the server asks for
    async with AsyncTypeSafeClient(timeout=30.0, retry=retry) as client:
        results = await asyncio.gather(*(triage(client, gate, rec) for rec in records))
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

asyncio.run(main(RECORDS))
