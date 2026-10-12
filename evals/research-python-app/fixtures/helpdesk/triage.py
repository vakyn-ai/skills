"""Decide what happens to each incoming ticket."""

import json

from .config import OPENAI_MODEL_BEST, OPENAI_MODEL_FAST, TEAMS
from .llm import ask

SPAM_PROMPT = """You screen a support inbox.
Is the following email spam, a newsletter or an automated notice rather than a real customer request?
Answer only yes or no."""

ROUTE_PROMPT = f"""You route support tickets.
Pick the team that should handle the ticket. Teams: {", ".join(TEAMS)}.
Return JSON: {{"team": "<one of {"|".join(TEAMS)}>", "reason": "<short reason>"}}"""

URGENCY_PROMPT = """Rate how urgent this ticket is from 1 to 5.
1 = question that can wait a week, 3 = blocks part of the customer's work,
5 = outage, security problem or legal threat.
Reply with the number only."""


def is_spam(email: str) -> bool:
    answer = ask(OPENAI_MODEL_FAST, SPAM_PROMPT, email, max_tokens=1)
    return answer.lower().startswith("yes")


def route_ticket(ticket: str) -> str:
    raw = ask(
        OPENAI_MODEL_BEST,
        ROUTE_PROMPT,
        ticket,
        response_format={"type": "json_object"},
    )
    team = json.loads(raw).get("team", "")
    return team if team in TEAMS else "technical"


def rate_urgency(ticket: str) -> int:
    answer = ask(OPENAI_MODEL_BEST, URGENCY_PROMPT, ticket, max_tokens=2)
    try:
        return max(1, min(5, int(answer)))
    except ValueError:
        return 3
