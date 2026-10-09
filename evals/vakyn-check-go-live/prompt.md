---
tags: [vakyn-check]
runs: 1
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

We go live with VAKYN on Monday: about 5,000 tickets a day, spikes of a few hundred at once, two app
servers sharing one VAKYN server started with the defaults. Can you review this before we ship?
Just tell me what to change.

```python
import asyncio, httpx

VAKYN_URL = "http://10.0.4.12:8080/v1/systemone"
HEADERS = {"Authorization": "Bearer vk_live_3c1d9a7e5b2f8046"}

async def ask(client, ticket, name, question):
    body = {"model": "jev-latest", "state": {"ticket": ticket["body"]}, "questions": {name: question}}
    r = await client.post(VAKYN_URL, json=body, headers=HEADERS, timeout=None)
    return r.json()["answers"][name]

async def handle(client, ticket):
    team = await ask(client, ticket, "team", TEAM_QUESTION)
    refund = await ask(client, ticket, "refund", REFUND_QUESTION)
    urgency = await ask(client, ticket, "urgency", URGENCY_QUESTION)
    if team["confidence"] > 0.5:
        route(ticket, team["choice"], refund["noul"] > 0.5, urgency["score"])
    else:
        route(ticket, "general", False, 0)

async def main(tickets):
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(handle(client, t) for t in tickets))
```
