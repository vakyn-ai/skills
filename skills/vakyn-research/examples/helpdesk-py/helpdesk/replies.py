"""Write the first reply a support agent reviews before sending."""

from .config import OPENAI_MODEL_BEST
from .llm import ask

REPLY_PROMPT = """You are a friendly support agent for Acme Cloud.
Write a short first reply to the customer: thank them, restate the problem in one sentence,
say which team has the ticket and what happens next. Plain text, no more than 120 words."""


def draft_reply(ticket: str, team: str) -> str:
    return ask(OPENAI_MODEL_BEST, REPLY_PROMPT, f"Team: {team}\n\nTicket:\n{ticket}", temperature=0.4)
