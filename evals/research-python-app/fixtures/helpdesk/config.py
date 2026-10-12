"""Settings for the helpdesk worker. Values come from the environment in production."""

import os

OPENAI_MODEL_FAST = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
OPENAI_MODEL_BEST = os.getenv("OPENAI_MODEL_BEST", "gpt-4o")

# The shared inbox receives about 3,000 emails a day; roughly a third are spam.
INBOX_POLL_SECONDS = 30
TEAMS = ["billing", "technical", "account", "sales"]
URGENT_AT = 4  # urgency 4 or 5 pages the on-call agent
