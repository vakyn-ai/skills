"""Weekly summary for the support lead, sent every Monday."""

from .config import OPENAI_MODEL_BEST
from .llm import ask

SUMMARY_PROMPT = """Summarize last week's support tickets for the support lead.
Group them into themes, name the three biggest problems, and suggest one fix for each.
Use short paragraphs."""


def weekly_summary(tickets: list[str]) -> str:
    joined = "\n\n---\n\n".join(tickets)
    return ask(OPENAI_MODEL_BEST, SUMMARY_PROMPT, joined)
